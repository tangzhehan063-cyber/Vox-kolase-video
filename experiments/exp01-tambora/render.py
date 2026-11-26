#!/usr/bin/env python3
"""Timeline compositor for Experiment 01.

Re-uses the engine's multiplane ideas (depth -> parallax, drift, draw order, per-layer
entrance/breath/spin, back-overshoot easing) but adds what multiplane.render() cannot do:
  * layers that enter/exit at ANY time in the scene (cues), not only in the first second
  * keyframed motion per layer, rotation about a pivot, continuous spin, wrap-around scroll
  * dynamic layers (marker strokes, thermometer, counters) computed per frame
  * scene transitions (torn wipe, ash rise, push, page drop, iris)
  * frame-range workers, so 1080x1920 renders in parallel

usage: python3 render.py --preview            # 540x960, out/preview.mp4
       python3 render.py --final              # 1080x1920, out/tambora_silent.mp4
       python3 render.py --stills 1.0 9.5 ... # PNG stills at those global times (preview size)
"""
import argparse, json, math, os, random, subprocess, sys, time
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

W, H, FPS = 1080, 1920, 30
HOLD_END = 0.7           # seconds the last frame lingers after the final beat


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_io(t):
    return t * t * (3 - 2 * t)


def back(t, s=1.7):
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ layers
class Layer:
    def __init__(self, img=None, x=W / 2, y=H / 2, h=None, sc=None, d=0.6, t0=0.0, enter="pop", din=0.55,
                 t1=None, exit="fade", dout=0.45, rot=0.0, kf=None, pivot=None, cam=1.0, amp=None, spin=None,
                 rate=0.0, z=0, alpha=1.0, flip=False, scroll=None, dyn=None, kind="obj", breath=True,
                 hold_dx=0.0, track=None, scroll_start=0.0):
        self.img, self.x, self.y, self.d = img, x, y, d
        self.t0, self.enter, self.din = t0, enter, din
        self.t1, self.exit, self.dout = t1, exit, dout
        self.rot, self.kf, self.pivot, self.cam = rot, kf or [], pivot, cam
        self.z, self.alpha, self.scroll, self.dyn, self.kind = z, alpha, scroll, dyn, kind
        self.rate, self.breath, self.track = rate, breath, track
        self.scroll_start = scroll_start
        if img is not None:
            if flip:
                self.img = img.transpose(Image.FLIP_LEFT_RIGHT)
            if h is not None:
                sc = h / self.img.height
            self.sc = sc or 1.0
        else:
            self.sc = sc or 1.0
        self.amp = (10 * d if amp is None else amp) if kind != "ground" else 0
        self.spin = (2.5 * (random.Random(int(x * 7 + y * 13)).random() - 0.5)) if spin is None else spin
        self.ph = random.Random(int(x * 3 + y * 5 + d * 100)).uniform(0, 6.28)
        self.fq = random.Random(int(x + y * 2)).uniform(0.5, 0.95)
        self._base = None
        self._base_sc = None


class Scene:
    def __init__(self, name, ground, layers, cam=None, dur=None):
        self.name, self.ground, self.layers, self.cam, self.dur = name, ground, layers, cam, dur


def default_cam(t):
    u = clamp(t / 6.0)
    return 1 + 0.06 * ease_out(u), 30 * ease_out(u), -18 * ease_out(u)


# ------------------------------------------------------------------ transforms
def kf_eval(kf, t):
    """kf: [(t, dict(dx, dy, s, rot, a))] -> interpolated dict, held outside the range."""
    if not kf:
        return None
    if t <= kf[0][0]:
        return dict(kf[0][1])
    if t >= kf[-1][0]:
        return dict(kf[-1][1])
    for (ta, a), (tb, b) in zip(kf, kf[1:]):
        if ta <= t <= tb:
            u = ease_io((t - ta) / max(1e-6, tb - ta)) if not a.get("lin") else (t - ta) / max(1e-6, tb - ta)
            out = {}
            for k in set(a) | set(b):
                if k == "lin":
                    continue
                out[k] = lerp(a.get(k, 0 if k != "s" and k != "a" else 1), b.get(k, 0 if k != "s" and k != "a" else 1), u)
            return out
    return dict(kf[-1][1])


def layer_xf(l, t):
    """-> (dx, dy, sc_mult, rot, alpha) in design pixels, or None when invisible."""
    lt = t - l.t0
    if lt < 0:
        return None
    dx = dy = rot = 0.0
    sm, al = 1.0, l.alpha
    k = clamp(lt / l.din)
    e = back(k) if l.enter in ("pop", "grow", "slam", "spin") else ease_out(k)
    r = 1 - e
    en = l.enter
    if en == "pop":
        sm *= 0.55 + 0.45 * e; rot += 6 * r; al *= clamp(lt / 0.18)
    elif en == "grow":
        sm *= max(0.001, e); al *= clamp(lt / 0.12)
    elif en == "slam":
        sm *= 1 + 0.9 * r; al *= clamp(lt / 0.10); rot += -8 * r
    elif en == "spin":
        sm *= max(0.001, e); rot += 240 * r; al *= clamp(lt / 0.12)
    elif en == "rise":
        dy += 300 * r * (0.5 + l.d); al *= clamp(lt / 0.25)
    elif en == "drop":
        dy -= 520 * r * (0.5 + l.d); al *= clamp(lt / 0.2)
    elif en == "left":
        dx -= 820 * r; al *= clamp(lt / 0.2)
    elif en == "right":
        dx += 820 * r; al *= clamp(lt / 0.2)
    elif en == "fade":
        al *= clamp(lt / l.din)
    elif en == "none":
        pass
    if l.t1 is not None and t >= l.t1:
        xt = clamp((t - l.t1) / l.dout)
        ex = l.exit
        if xt >= 1 and ex != "stay":
            return None
        if ex == "fade":
            al *= 1 - xt
        elif ex == "fall":
            dy += 1500 * xt * xt; rot += 25 * xt; al *= 1 - clamp((xt - 0.6) / 0.4)
        elif ex == "sink":
            dy += 520 * ease_io(xt); al *= 1 - clamp((xt - 0.3) / 0.7)
        elif ex == "shrink":
            sm *= 1 - ease_io(xt); al *= 1 - clamp((xt - 0.5) / 0.5)
        elif ex == "left":
            dx -= 1300 * xt * xt
        elif ex == "right":
            dx += 1300 * xt * xt
        elif ex == "up":
            dy -= 1500 * xt * xt
    ks = kf_eval(l.kf, t)
    if ks:
        dx += ks.get("dx", 0); dy += ks.get("dy", 0)
        sm *= ks.get("s", 1.0); rot += ks.get("rot", 0); al *= ks.get("a", 1.0)
    if l.rate:
        rot += l.rate * lt
    return dx, dy, sm, rot, al


# ------------------------------------------------------------------ frame renderer
class Renderer:
    def __init__(self, scale):
        self.S = scale
        self.w, self.h = int(round(W * scale)), int(round(H * scale))
        self.ground_cache = {}

    def ground(self, colour, seed):
        key = (colour, seed)
        if key not in self.ground_cache:
            sys.path.insert(0, os.path.join(HERE, "..", "..", "skills", "vox-editorial", "library"))
            import paperkit
            g = paperkit.paper.ground((int(W * 1.18), int(H * 1.18)), colour, seed=seed).convert("RGB")
            self.ground_cache[key] = g.resize((int(g.width * self.S), int(g.height * self.S)), Image.LANCZOS)
        return self.ground_cache[key]

    def prep(self, l):
        if l.img is None:
            return None
        s = l.sc * self.S
        if l._base is None or l._base_sc != s:
            w, h = max(1, int(l.img.width * s)), max(1, int(l.img.height * s))
            l._base = l.img.resize((w, h), Image.LANCZOS) if (w, h) != l.img.size else l.img
            l._base_sc = s
        return l._base

    def frame(self, scene, t):
        S = self.S
        zoom, panx, pany = (scene.cam or default_cam)(t)
        g = self.ground(*scene.ground)
        cv = Image.new("RGBA", (self.w, self.h))
        gx = (self.w - g.width) // 2 - int(panx * 0.05 * S)
        gy = (self.h - g.height) // 2 - int(pany * 0.05 * S)
        cv.paste(g, (gx, gy))
        cx0, cy0 = W / 2, H / 2
        order = sorted(scene.layers, key=lambda l: (l.d, l.z))
        for l in order:
            xf = layer_xf(l, t)
            if xf is None or xf[4] <= 0.004:
                continue
            dx, dy, sm, rot, al = xf
            d = l.d
            lt = t - l.t0
            zs = 1 + (zoom - 1) * (0.25 + 1.35 * d) * (0.5 if l.kind == "title" else 1.0) * l.cam
            drift_x = math.sin(t * l.fq + l.ph) * l.amp
            drift_y = math.cos(t * l.fq * 0.78 + l.ph) * l.amp * 0.85
            breath = 1 + (math.sin(t * 1.05 + l.ph) * 0.010 * d if l.breath and l.kind != "ground" else 0)
            spin = l.spin * math.sin(t * 0.55 + l.ph) * 0.35
            camx = panx * d * l.cam * (0.35 if l.kind == "title" else 1.0)
            camy = pany * d * l.cam * (0.35 if l.kind == "title" else 1.0)
            tx, ty = (l.track(t) if l.track else (0, 0))
            px = l.x + dx + drift_x + camx + tx
            py = l.y + dy + drift_y + camy + ty
            # zoom the position about frame centre too (real parallax, not only scale)
            px = cx0 + (px - cx0) * (1 + (zoom - 1) * (0.25 + 1.35 * d) * l.cam * 0.55)
            py = cy0 + (py - cy0) * (1 + (zoom - 1) * (0.25 + 1.35 * d) * l.cam * 0.55)
            if l.dyn is not None:
                r = l.dyn(lt)
                if r is None:
                    continue
                img, (ox, oy) = r
                px = ox + dx + camx + tx
                py = oy + dy + camy + ty
                self._blit(cv, img, px * S, py * S, 1.0 * S, 0, al, topleft=True)
                continue
            base = self.prep(l)
            if l.scroll:
                wdt = base.width / S
                shift = (max(0.0, t - l.scroll_start) * l.scroll) % wdt
                k = -1
                while True:
                    xx = px - wdt * 0.5 - shift + k * wdt
                    if xx > W:
                        break
                    if xx + wdt > 0:
                        self._blit(cv, base, (xx + wdt / 2) * S, py * S, 1.0, 0, al)
                    k += 1
                continue
            f = zs * sm * breath
            self._blit(cv, base, px * S, py * S, f, rot + l.rot + spin, al, pivot=l.pivot)
        return cv.convert("RGB")

    def _blit(self, cv, img, cx, cy, f, ang, al, pivot=None, topleft=False):
        im = img
        if abs(f - 1) > 0.004:
            w2, h2 = max(1, int(im.width * f)), max(1, int(im.height * f))
            if w2 > 6000 or h2 > 6000:
                return
            im = im.resize((w2, h2), Image.BILINEAR)
        ox = oy = 0.0
        if abs(ang) > 0.05:
            if pivot is not None:
                pxo, pyo = (pivot[0] - 0.5) * im.width, (pivot[1] - 0.5) * im.height
                a = math.radians(-ang)          # PIL rotates counter-clockwise
                rx = pxo * math.cos(a) - pyo * math.sin(a)
                ry = pxo * math.sin(a) + pyo * math.cos(a)
                ox, oy = pxo - rx, pyo - ry
            im = im.rotate(ang, expand=True, resample=Image.BILINEAR)
        w2, h2 = im.size
        if al < 0.995:
            a = im.getchannel("A").point(lambda v: int(v * al))
            im = im.copy()
            im.putalpha(a)
        x = int(cx + ox - (0 if topleft else w2 / 2))
        y = int(cy + oy - (0 if topleft else h2 / 2))
        if x >= cv.width or y >= cv.height or x + w2 <= 0 or y + h2 <= 0:
            return
        cv.alpha_composite(im, (x, y)) if (x >= 0 and y >= 0) else self._clipped(cv, im, x, y)

    @staticmethod
    def _clipped(cv, im, x, y):
        sx, sy = max(0, -x), max(0, -y)
        im = im.crop((sx, sy, im.width, im.height))
        cv.alpha_composite(im, (x + sx, y + sy))


# ------------------------------------------------------------------ transitions
def _jag(n, amp, seed):
    rnd = np.random.default_rng(seed)
    v = rnd.normal(0, 1, n // 8 + 2)
    v = np.interp(np.arange(n), np.arange(0, n + 8, 8)[: len(v)], v[: len(np.arange(0, n + 8, 8))])
    return v * amp


def transition(kind, A, B, u, S, seed=1, centre=None):
    """A, B: RGB uint8 arrays. u in 0..1. Returns an RGB uint8 array."""
    h, w, _ = A.shape
    u = ease_io(clamp(u))
    if kind == "torn_wipe":              # diagonal torn paper edge, left -> right (seed odd) or right -> left
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        slope = 0.32
        jag = _jag(h, 16 * S, seed)[:, None]
        line = (-w * 0.5 + u * (w * 2.0)) + (yy - h / 2) * slope + jag
        if seed % 2 == 0:
            xx = w - xx
        d = line - xx
        out = np.where((d > 0)[..., None], B, A)
        band = (d > -38 * S) & (d <= 0)
        shadow = (d > -90 * S) & (d <= -38 * S)
        out = out.copy()
        out[shadow] = (out[shadow] * 0.78).astype(np.uint8)
        out[band] = np.array([252, 250, 244], dtype=np.uint8)
        # B side already shown for d>0; band is paper strip
        return out
    if kind == "rise":                   # grey ash cloud sweeps upward and reveals B
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        wave = (np.sin(xx / (95 * S)) * 46 + np.sin(xx / (41 * S) + 1.3) * 22) * S
        edge = h * 1.18 - u * h * 1.55 + wave
        out = np.where((yy > edge)[..., None], B, A)
        # B is revealed BELOW... invert: cloud covers A from the bottom, then B shown under it
        cloud = (yy > edge - 150 * S) & (yy <= edge)
        shade = np.clip((yy - (edge - 150 * S)) / (150 * S), 0, 1)[..., None]
        col = (np.array([84, 86, 100]) * (0.8 + 0.4 * (1 - shade))).astype(np.uint8)
        out = out.copy()
        out[cloud] = col[cloud]
        return out
    if kind == "push":                   # A slides left, B follows, paper strip between
        off = int(u * (w + int(40 * S)))
        out = np.empty_like(A)
        out[:, : max(0, w - off)] = A[:, off:] if off < w else A[:, :0]
        out[:, max(0, w - off):] = B[:, : w - max(0, w - off)]
        sx = max(0, w - off)
        out[:, max(0, sx - int(20 * S)): sx + int(20 * S)] = np.array([252, 250, 244], dtype=np.uint8)
        return out
    if kind == "drop":                   # A falls away like a torn page, revealing B
        im = Image.fromarray(A).convert("RGBA")
        ang = -9 * u * u
        dy = int(u * u * h * 1.25)
        dx = int(-u * 60 * S)
        canvas = Image.fromarray(B).convert("RGBA")
        rot = im.rotate(ang, resample=Image.BILINEAR, expand=False, center=(w / 2, 0), translate=(dx, dy))
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        m = rot.getchannel("A")
        # soft shadow cast on B
        shd = Image.new("RGBA", (w, h), (0, 0, 0, 110))
        shd.putalpha(m.filter(ImageFilter.GaussianBlur(14 * S)).point(lambda v: int(v * 0.43)))
        canvas.alpha_composite(shd, (int(14 * S), int(18 * S)))
        # `rotate` leaves uncovered area transparent already because input has alpha 255 only where A was
        im2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        im2.alpha_composite(rot)
        canvas.alpha_composite(im2)
        return np.asarray(canvas.convert("RGB"))
    if kind == "iris":                   # circular reveal of B from `centre`, with a white paper ring
        cx, cy = (centre or (0.5, 0.5))
        cx, cy = cx * w, cy * h
        R = u * math.hypot(max(cx, w - cx), max(cy, h - cy)) * 1.05
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dist = np.hypot(xx - cx, yy - cy)
        out = np.where((dist < R)[..., None], B, A)
        ring = (dist >= R - 30 * S) & (dist < R + 6 * S) & (u > 0.01) & (u < 0.995)
        out = out.copy()
        out[ring] = np.array([252, 250, 244], dtype=np.uint8)
        return out
    return B if u > 0.5 else A


# ------------------------------------------------------------------ film
def load_film():
    import scenes
    T = json.load(open(f"{HERE}/timing.json"))
    film = scenes.build(T)
    return T, film


def film_frame(film, T, rd, t):
    sc = film["scenes"]
    # find the active scene by global time
    idx = 0
    for i, s in enumerate(sc):
        if t >= s["start"] - 1e-6:
            idx = i
    s = sc[idx]
    A = rd.frame(s["scene"], t - s["start"])
    nxt = sc[idx + 1] if idx + 1 < len(sc) else None
    if nxt is not None:
        tr = nxt["tr_len"]
        if t > nxt["start"] - tr:
            u = (t - (nxt["start"] - tr)) / tr
            Bf = rd.frame(nxt["scene"], t - nxt["start"])
            a = np.asarray(A)
            b = np.asarray(Bf)
            out = transition(nxt["tr_kind"], a, b, u, rd.S, seed=nxt.get("tr_seed", 1), centre=nxt.get("tr_centre"))
            return Image.fromarray(out)
    # (a scene that STARTS inside a previous transition is handled above; later frames render alone)
    return A


def render_range(args):
    scale, f0, f1, out = args
    T, film = load_film()
    rd = Renderer(scale)
    w, h = rd.w, rd.h
    pr = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
                           "-preset", "medium", "-crf", "17" if scale >= 1 else "23", "-pix_fmt", "yuv420p", out],
                          stdin=subprocess.PIPE)
    for f in range(f0, f1):
        im = film_frame(film, T, rd, f / FPS)
        pr.stdin.write(im.tobytes())
    pr.stdin.close()
    pr.wait()
    return out


def total_frames(T):
    return int(round((T["total"] + HOLD_END) * FPS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--stills", nargs="*", type=float)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    os.makedirs(f"{HERE}/out", exist_ok=True)
    T = json.load(open(f"{HERE}/timing.json"))
    if a.stills is not None:
        _, film = load_film()
        rd = Renderer(0.5)
        os.makedirs(f"{HERE}/frames_qc", exist_ok=True)
        for t in a.stills:
            film_frame(film, T, rd, t).save(f"{HERE}/frames_qc/still_{t:06.2f}.png")
            print("still", t)
        return
    scale = 1.0 if a.final else 0.5
    name = a.out or ("tambora_silent.mp4" if a.final else "preview.mp4")
    n = total_frames(T)
    per = math.ceil(n / a.procs)
    jobs = [(scale, i * per, min(n, (i + 1) * per), f"{HERE}/out/_part{i}.mp4") for i in range(a.procs) if i * per < n]
    t = time.time()
    with Pool(len(jobs)) as p:
        parts = p.map(render_range, jobs)
    lst = f"{HERE}/out/_parts.txt"
    open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
    subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy",
                           f"{HERE}/out/{name}"])
    for x in parts:
        os.remove(x)
    print(f"rendered {n} frames @ {int(W*scale)}x{int(H*scale)} in {time.time()-t:.0f}s -> out/{name}")


if __name__ == "__main__":
    main()
