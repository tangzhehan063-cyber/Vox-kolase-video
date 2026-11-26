"""The eight scenes. Every cue is a fraction of a beat, resolved against timing.json,
so replacing the estimated clock with real Gemini audio re-times the whole film."""
import json, math, os, random

import numpy as np
from PIL import Image, ImageDraw

from render import Layer, Scene, W, H, clamp, ease_out, ease_io, smap
from paperkit import *
import paperkit
from sprites_a import ortho, TAMBORA, MANNHEIM, thermometer
from sprites_b import marker_stroke

HERE = os.path.dirname(os.path.abspath(__file__))
SP = f"{HERE}/assets/sprites"
META = json.load(open(f"{HERE}/assets/meta.json"))
_cache = {}

STEEL = (84, 88, 112)
VIOLET_G = (124, 88, 176)
TEAL_G = (32, 160, 138)


def A(name):
    if name not in _cache:
        _cache[name] = Image.open(f"{SP}/{name}.png").convert("RGBA")
    return _cache[name]


def banner(text, width=760, seed=1, size=None, tape=True):
    return paper.banner(text, width, seed=seed, size=size, tape=tape)


def word(text, size, colour=INK, seed=0):
    return paper.word_sprite(text, size, colour, seed)


class Clock:
    """Resolve (beat, fraction) -> scene-local seconds."""

    def __init__(self, T, scene_start):
        self.b = {b["id"]: b for b in T["beats"]}
        self.s0 = scene_start

    def __call__(self, beat, frac=0.0):
        b = self.b[beat]
        return b["start"] - self.s0 + frac * b["speech"]

    def end(self, beat):
        b = self.b[beat]
        return b["start"] - self.s0 + b["dur"]


# --------------------------------------------------------------------------- dynamic layers
_dyn = {}


def marker_dyn(pts, dur, width=22, color=RED, seed=1):
    key = id(pts)

    def fn(lt):
        p = clamp(lt / dur)
        q = round(p * 36)
        if q == 0:
            return None
        k = (key, q, width, color)
        if k not in _dyn:
            _dyn[k] = marker_stroke(pts, q / 36, width, color, seed=seed)
        return _dyn[k]
    return fn


def ellipse_pts(cx, cy, rx, ry, a0=-100, a1=300, n=40):
    return [(cx + rx * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + ry * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def cross_pts(cx, cy, r):
    return [(cx - r, cy - r), (cx + r, cy + r)], [(cx + r, cy - r), (cx - r, cy + r)]


def arc_pts(p0, p1, bulge, n=40):
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    nx, ny = -(p1[1] - p0[1]), (p1[0] - p0[0])
    L = math.hypot(nx, ny) or 1
    cx, cy = mx + nx / L * bulge, my + ny / L * bulge
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t * t * p1[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t * t * p1[1]) for t in (i / n for i in range(n + 1))]


def arrow_parts(p0, p1, bulge=0, head=58):
    shaft = arc_pts(p0, p1, bulge, 16)
    (x0, y0), (x1, y1) = shaft[-3], shaft[-1]
    a = math.atan2(y1 - y0, x1 - x0)
    hs = [[(x1, y1), (x1 - head * math.cos(a + 0.5), y1 - head * math.sin(a + 0.5))],
          [(x1, y1), (x1 - head * math.cos(a - 0.5), y1 - head * math.sin(a - 0.5))]]
    return shaft, hs


def dotted_dyn(pts, dur, color=(252, 250, 244), r=9, gap=34):
    """Dotted route that grows along `pts`."""
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    tot = L[-1]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, y0 = int(min(xs) - r * 2), int(min(ys) - r * 2)
    w, h = int(max(xs) + r * 2 - x0), int(max(ys) + r * 2 - y0)

    def at(s):
        for i in range(1, len(L)):
            if L[i] >= s:
                u = (s - L[i - 1]) / max(1e-6, L[i] - L[i - 1])
                return (pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * u, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * u)
        return pts[-1]

    def fn(lt):
        p = clamp(lt / dur)
        if p <= 0:
            return None
        q = round(p * 60)
        k = ("dot", id(pts), q)
        if k not in _dyn:
            im = Image.new("RGBA", (w * 2, h * 2), (0, 0, 0, 0))
            d = ImageDraw.Draw(im)
            s = 0.0
            while s <= tot * q / 60:
                x, y = at(s)
                d.ellipse([(x - x0 - r) * 2, (y - y0 - r) * 2, (x - x0 + r) * 2, (y - y0 + r) * 2], fill=color + (255,))
                s += gap
            _dyn[k] = (im.resize((w, h), Image.LANCZOS), (x0, y0))
        return _dyn[k]
    return fn


def thermo_dyn(level_fn, centre):
    def fn(lt):
        lv = round(level_fn(lt) * 40) / 40
        k = ("th", lv)
        if k not in _dyn:
            _dyn[k] = thermometer(lv)
        im = _dyn[k]
        return im, (centre[0] - im.width / 2, centre[1] - im.height / 2)
    return fn


def counter_dyn(target, dur, size, centre, suffix=" KM", seed=1):
    def fn(lt):
        p = ease_out(clamp(lt / dur))
        v = int(round(target * p / 100.0) * 100)
        k = ("ctr", v, size)
        if k not in _dyn:
            s = f"{v:,}{suffix}"
            _dyn[k] = word(s, size, INK, seed)
        im = _dyn[k]
        return im, (centre[0] - im.width / 2, centre[1] - im.height / 2)
    return fn


# --------------------------------------------------------------------------- shared dressing
def backdrop(seed, dens=1.0, avoid=None, front=True, pre=0.0):
    """Engine-style back plane: newsprint, tape, rear confetti, front confetti (never centred)."""
    rnd = random.Random(seed * 131)
    out = []
    for i in range(int(3 * dens)):
        cw = rnd.randint(190, 290)
        out.append(Layer(paper.clipping(cw, int(cw * rnd.uniform(0.75, 1.3)), seed=seed * 10 + i),
                         x=rnd.choice([rnd.uniform(70, 230), rnd.uniform(850, 1010)]), y=rnd.uniform(150, 1750),
                         sc=1.0, d=rnd.uniform(0.18, 0.28), t0=pre - 0.7 + rnd.uniform(0, 0.8), enter="fade",
                         rot=rnd.uniform(-8, 8), kind="clip"))
    for i in range(int(2 * dens)):
        out.append(Layer(paper.tape_strip(rnd.randint(150, 230), rnd.randint(52, 76), rnd.choice([-30, -14, 18, 34]), seed=seed * 20 + i),
                         x=rnd.uniform(90, 990), y=rnd.uniform(110, 1810), sc=1.0, d=rnd.uniform(0.16, 0.24),
                         t0=pre - 0.6 + rnd.uniform(0, 0.8), enter="fade", kind="tape"))
    kinds = ["triangle", "shard", "zigzag", "ring", "square", "dot", "triangle", "shard"]
    for i in range(int(9 * dens)):
        d = rnd.uniform(0.34, 0.48)
        s = int(rnd.uniform(34, 60) * (0.7 + 0.6 * d))
        out.append(Layer(paper.confetti(rnd.choice(kinds), rnd.choice(PALETTE_), s, seed=rnd.randrange(9999)),
                         x=rnd.uniform(60, 1020), y=rnd.uniform(100, 1820), sc=1.0, d=d,
                         t0=pre - 0.5 + rnd.uniform(0, 1.0), enter="pop", din=0.5, spin=rnd.uniform(-14, 14), kind="confetti"))
    if front:
        for i in range(int(7 * dens)):
            d = rnd.uniform(0.92, 1.06)
            s = int(rnd.uniform(46, 80) * (0.7 + 0.6 * d))
            cx = rnd.choice([rnd.uniform(40, 250), rnd.uniform(830, 1040)])
            out.append(Layer(paper.confetti(rnd.choice(kinds), rnd.choice(PALETTE_), s, seed=rnd.randrange(9999)),
                             x=cx, y=rnd.uniform(100, 1820), sc=1.0, d=d, t0=pre - 0.3 + rnd.uniform(0, 1.0),
                             enter="pop", din=0.5, spin=rnd.uniform(-14, 14), kind="confetti"))
    return out


PALETTE_ = paper.PALETTE


def snowfall(t_start, n=26, seed=1, span=8.0):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        h = rnd.randint(34, 84)
        d = 0.28 + (h - 34) / 50 * 0.75
        t0 = t_start + rnd.uniform(0, 2.5)
        fall = rnd.uniform(5.5, 8.5)
        kf = [(t0, dict(dy=0, dx=0, rot=0, lin=True))]
        for k in range(1, 9):
            kf.append((t0 + fall * k / 8, dict(dy=2300 * k / 8, dx=46 * math.sin(k * 1.1 + i), rot=70 * k / 8, lin=True)))
        out.append(Layer(A("snow"), x=rnd.uniform(20, 1060), y=-120, h=h, d=d, t0=t0, enter="none", kf=kf, amp=0, breath=False, z=1, alpha=0.9))
    return out


def ballistic(vx, vy, g, t_end, n=8):
    ks = []
    for i in range(n + 1):
        t = t_end * i / n
        ks.append((t, dict(dx=vx * t, dy=vy * t + 0.5 * g * t * t, rot=300 * t, a=1.0, lin=True)))
    return ks


def shift_kf(kf, t0):
    return [(t0 + t, v) for t, v in kf]


def mp_factory(cx, cy, s):
    """Machine-space (frame canvas 1400x900) -> screen."""
    return lambda mx, my: (cx + (mx - 700) * s, cy + (my - 450) * s)


def draisine_layers(cx, cy, s, c_frame, c_wheel1, c_wheel2, c_rider, c_legs, c_roll, d=0.8, z0=0, t_end=60.0,
                    roll_speed=360.0, push=True, enter_wheels=("left", "right"), flip=False):
    """Machine assembled from parts. Returns a list of Layers."""
    mp = mp_factory(cx, cy, s)
    L = []
    fx, fy = mp(700, 450)
    L.append(Layer(A("frame"), x=fx, y=fy, sc=s, d=d, t0=c_frame, enter="drop", din=0.6, amp=3, z=z0 + 1, spin=0))
    for hub, tw, en in (((260, 640), c_wheel1, enter_wheels[0]), ((1140, 640), c_wheel2, enter_wheels[1])):
        x, y = mp(*hub)
        L.append(Layer(A("wheel"), x=x, y=y, sc=s * 0.93, d=d + 0.01, t0=tw, enter=en, din=0.6, amp=3, spin=0, z=z0 + 2,
                       kf=[(tw, dict(rot=0, lin=True)), (c_roll, dict(rot=0, lin=True)), (t_end, dict(rot=roll_speed * (t_end - c_roll), lin=True))]))
    rx, ry = mp(650 + (260 - 230), 505 + (350 - 540))
    L.append(Layer(A("rider"), x=rx, y=ry, sc=s, d=d + 0.02, t0=c_rider, enter="drop", din=0.55, amp=3, spin=0, z=z0 + 4,
                   kf=[(c_roll, dict(dy=0, lin=True))] + [(c_roll + i * 0.5, dict(dy=(-5 if i % 2 else 5) * s, lin=True)) for i in range(1, int((t_end - c_roll) / 0.5))]))
    if push:
        for k, phase in enumerate((0.0, math.pi)):
            hx, hy = mp(640, 540)
            ls = s * 0.64
            lx, ly = hx, hy + 280 * 0.64 * s
            kfs = []
            t = c_legs
            while t < t_end:
                kfs.append((t, dict(rot=26 * math.sin(2 * math.pi * (t - c_legs) / 1.0 + phase), lin=True)))
                t += 0.1
            L.append(Layer(A("leg"), x=lx, y=ly, sc=ls, d=d + (0.015 if k else 0.005), t0=c_legs - 0.4, enter="fade", din=0.3,
                           pivot=(0.5, 0.0), amp=0, spin=0, z=z0 + 3, kf=kfs, breath=False))
    return L


# --------------------------------------------------------------------------- scenes
def build(T):
    sc = T["scenes"]
    names = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    builders = [S1, S2, S3, S4, S5, S6, S7, S8]
    film = []
    trans = {
        "S2": ("torn_wipe", 0.7, 1, None), "S3": ("rise", 0.8, 1, None), "S4": ("push", 0.6, 1, None),
        "S5": ("drop", 0.7, 1, None), "S6": ("iris", 0.75, 1, ((smap(630, 585)[0]) / W, smap(630, 585)[1] / H)), "S7": ("torn_wipe", 0.7, 2, None),
        "S8": ("iris", 0.75, 1, ((smap(330, 1400)[0]) / W, smap(330, 1400)[1] / H)),
    }
    for n, b in zip(names, builders):
        s0, s1 = sc[n]["start"], sc[n]["end"]
        c = Clock(T, s0)
        scene = b(c, s1 - s0)
        rec = dict(name=n, scene=scene, start=s0, end=s1)
        if n in trans:
            k, ln, seed, ctr = trans[n]
            rec.update(tr_kind=k, tr_len=ln, tr_seed=seed, tr_centre=ctr)
        film.append(rec)
    return dict(scenes=film)


def gpt(meta_c, scale, ll):
    """Globe-space point -> screen. meta_c = (cx, cy, size_px_on_screen_center)."""
    gx, gy, R = meta_c
    u, v, vis = ortho(*ll)
    return gx + u * R, gy + v * R


# ------------------------------------------------ S1: the hook
def S1(c, dur):
    gx, gy, gs = 490, 900, 0.86
    R = 500 * gs
    PT = gpt((gx, gy, R), None, TAMBORA)
    PG = gpt((gx, gy, R), None, MANNHEIM)
    L = backdrop(1, 1.0)
    L.append(Layer(A("globe"), x=gx, y=gy, sc=gs, d=0.55, t0=-0.55, enter="grow", din=0.7, amp=4, spin=0, z=1))
    # the volcano, bottom-centred on Tambora; visible and erupting inside the first half second
    vs = 0.40
    vx, vy = PT[0] - 20, PT[1] + 14 - 430 * vs
    crater = (vx, vy + (190 - 450) * vs)
    L.append(Layer(A("flash"), x=crater[0], y=crater[1] - 40, h=520, d=0.8, t0=0.04, enter="grow", din=0.25, t1=0.4, dout=0.35, amp=0, spin=0, z=2))
    L.append(Layer(A("volcano"), x=vx, y=vy, sc=vs, d=0.82, t0=-0.3, enter="pop", din=0.45, amp=3, spin=0, z=3))
    for i, (dx, dy, h, d, t0) in enumerate([(-20, -80, 190, 0.9, 0.12), (-10, -190, 230, 0.95, 0.28), (-60, -310, 270, 1.0, 0.44),
                                            (-30, -440, 290, 0.92, 0.62), (-80, -570, 280, 0.86, 0.8)]):
        nm = ["ash1", "ash2", "ash3", "ash4", "ash1"][i]
        L.append(Layer(A(nm), x=crater[0] + dx, y=crater[1] + dy, h=h, d=d, t0=t0, enter="grow", din=0.55, amp=6,
                       kf=[(t0, dict(dy=0, s=1, lin=True)), (t0 + 6, dict(dy=-70, s=1.12, lin=True))], z=4 + i))
    rnd = random.Random(4)
    for i in range(9):
        r = A("rock") if "rock" in _cache else None
        from sprites_c import rock as mkrock
        img = mkrock(rnd.randint(50, 90), seed=i, color=rnd.choice([ROCK, CORAL, (120, 100, 110)]))
        L.append(Layer(img, x=crater[0], y=crater[1], sc=1.0, d=rnd.uniform(0.9, 1.05), t0=0.06 + rnd.uniform(0, 0.15), enter="none",
                       amp=0, spin=0, breath=False, z=9, t1=0.06 + 1.5, exit="fade", dout=0.25,
                       kf=shift_kf(ballistic(rnd.uniform(-380, 260), rnd.uniform(-720, -440), 900, 1.6), 0.06)))
    # the other corner: a tiny stable and a horse at Germany, crossed out
    t_b = c(1, 0.50)
    ss = 0.26
    sx, sy = PG[0] - 10, PG[1] - 4 - 450 * ss
    L.append(Layer(A("stable"), x=sx, y=sy, sc=ss, d=0.85, t0=t_b, enter="pop", din=0.5, amp=2, spin=0, z=6))
    hs = 0.26
    hx_, hy_ = PG[0] + 150, PG[1] + 12 - 390 * hs
    L.append(Layer(A("horse"), x=hx_, y=hy_, sc=hs, d=0.88, t0=c(1, 0.62), enter="pop", din=0.5, amp=2, spin=0, z=7))
    s1, s2 = cross_pts(hx_, hy_ - 4, 96)
    L.append(Layer(dyn=marker_dyn(s1, 0.28, 24), d=0.95, t0=c(1, 0.80), enter="none", z=10))
    L.append(Layer(dyn=marker_dyn(s2, 0.28, 24, seed=2), d=0.95, t0=c(1, 0.80) + 0.22, enter="none", z=10))
    # "2 YEARS LATER" slapped on at the time-jump
    L.append(Layer(banner("2 YEARS LATER", 800, seed=11), x=540, y=1450, sc=1.0, d=1.1, t0=c(1, 0.40), enter="slam", din=0.4, kind="title", z=12, rot=-3, amp=4))
    # the question: a dotted line between the two corners with a "?" in the middle
    arc = arc_pts(PT, PG, 120)
    L.append(Layer(dyn=dotted_dyn(arc, 1.1, r=8, gap=30), d=0.9, t0=c(1, 0.82), enter="none", z=8))
    mid = arc[len(arc) // 2]
    L.append(Layer(A("q_card"), x=mid[0], y=mid[1], h=210, d=1.0, t0=c(1, 0.82) + 0.6, enter="pop", din=0.45, rot=-8, z=13))

    def cam(t):
        u = clamp(t / 7.0)
        shake = 0.0
        if 0.12 < t < 1.1:
            shake = 16 * math.exp(-(t - 0.12) * 3.5) * math.sin(t * 58)
        return 1 + 0.07 * ease_out(u), 24 * ease_out(u) + shake, -10 * ease_out(u) + shake * 0.6
    return Scene("S1", (COBALT, 1), L, cam)


# ------------------------------------------------ S2: the eruption
def S2(c, dur):
    L = backdrop(2, 0.8, front=True)
    vs = 1.05
    vx, vy = 540, 1370 - 430 * vs * 0.0 - 0
    vy = 1330
    crater = (vx, vy + (190 - 450) * vs)
    t_b = c(2, 0.45)       # "blows apart"
    L.append(Layer(A("volcano"), x=vx, y=vy, sc=vs, d=0.6, t0=-0.5, enter="rise", din=0.8, amp=3, spin=0, z=2))
    # a calm wisp before the blast
    L.append(Layer(A("ash3"), x=crater[0] + 30, y=crater[1] - 110, h=190, d=0.78, t0=c(2, 0.15), enter="grow", din=0.7, amp=5, z=3,
                   t1=t_b, exit="fade", dout=0.3))
    L.append(Layer(A("flash"), x=crater[0], y=crater[1] - 30, h=720, d=0.7, t0=t_b, enter="grow", din=0.25, t1=t_b + 0.25, dout=0.4, amp=0, spin=0, z=4))
    plume = [(10, -150, 330, 0.9, "ash1"), (-90, -380, 400, 0.96, "ash2"), (80, -650, 470, 1.0, "ash4"), (-110, -930, 540, 0.95, "ash1"),
             (90, -1200, 600, 0.88, "ash4"), (-30, -1470, 560, 0.8, "ash2")]
    for i, (dx, dy, h, d, nm) in enumerate(plume):
        t0 = t_b + 0.12 * i
        L.append(Layer(A(nm), x=crater[0] + dx, y=crater[1] + dy, h=h, d=d, t0=t0, enter="grow", din=0.7, amp=7, z=5 + i,
                       kf=[(t0, dict(dy=0, s=1, lin=True)), (t0 + 6, dict(dy=-80, s=1.1, lin=True))]))
    from sprites_c import rock as mkrock
    rnd = random.Random(8)
    for i in range(12):
        img = mkrock(rnd.randint(46, 96), seed=i, color=rnd.choice([ROCK, CORAL, (120, 100, 110), ORANGE]))
        L.append(Layer(img, x=crater[0], y=crater[1], sc=1.0, d=rnd.uniform(0.85, 1.08), t0=t_b + rnd.uniform(0, 0.15), enter="none", amp=0, spin=0,
                       breath=False, z=16, t1=t_b + 1.7, exit="fade", dout=0.3,
                       kf=shift_kf(ballistic(rnd.uniform(-420, 420), rnd.uniform(-980, -620), 1100, 1.8), t_b)))
    L.append(Layer(banner("APRIL 1815", 800, seed=21), x=540, y=215, sc=1.0, d=1.15, t0=c(2, 0.02), enter="slam", din=0.45, kind="title", z=20, rot=-2, amp=3))
    L.append(Layer(A("tag_tambora"), x=770, y=1170, h=150, d=0.72, t0=c(2, 0.27), enter="pop", din=0.45, rot=-4, z=21))
    L.append(Layer(word("VEI 7", 210, (255, 214, 64), 5), x=815, y=520, sc=1.0, d=1.05, t0=c(2, 0.66), enter="slam", din=0.4, rot=6, z=22))

    def cam(t):
        up = ease_io(clamp((t - t_b) / 2.6))
        shake = 0.0
        if t_b < t < t_b + 1.2:
            shake = 20 * math.exp(-(t - t_b) * 3.0) * math.sin(t * 61)
        return 1 + 0.04 * clamp(t / 5.0), 14 * ease_out(clamp(t / 6)) + shake, 430 * up + shake * 0.7
    return Scene("S2", (CORAL, 2), L, cam)


# ------------------------------------------------ S3: the planet wrapped
def S3(c, dur):
    gx, gy, gs = 540, 930, 0.84
    L = backdrop(3, 0.6, front=False)
    L.append(Layer(A("globe"), x=gx, y=gy, sc=gs, d=0.55, t0=-0.5, enter="grow", din=0.7, amp=4, spin=0, z=3))
    sx, sy = 850, 330
    t_dim = c(3, 0.58)
    L.append(Layer(A("sun"), x=sx, y=sy, sc=0.62, d=0.4, t0=-0.3, enter="pop", din=0.5, amp=6, z=1, t1=t_dim, exit="fade", dout=0.9))
    L.append(Layer(A("dim_sun"), x=sx, y=sy, sc=0.62, d=0.4, t0=t_dim, enter="fade", din=0.9, amp=6, z=1))
    belt = [  # (name, x, y, h, depth, enter side, cue)
        ("ash4", 150, 640, 470, 0.34, "left", 0.02), ("ash2", 930, 1230, 400, 0.36, "right", 0.05),
        ("ash1", 330, 740, 330, 0.96, "left", 0.06), ("ash2", 740, 980, 330, 0.99, "right", 0.14),
        ("ash3", 420, 1180, 300, 1.0, "left", 0.2), ("ash4", 690, 700, 380, 0.97, "right", 0.26),
        ("ash1", 240, 1010, 300, 1.02, "left", 0.32),
    ]
    for i, (nm, x, y, h, d, side, cu) in enumerate(belt):
        t0 = c(3, cu)
        L.append(Layer(A(nm), x=x, y=y, h=h, d=d, t0=t0, enter=side, din=0.8, amp=7, z=4 + i,
                       kf=[(t0, dict(dx=0, lin=True)), (t0 + 6, dict(dx=(140 if side == "left" else -140), lin=True))]))
    L.append(Layer(A("ash2"), x=sx - 10, y=sy + 10, h=380, d=1.0, t0=t_dim + 0.1, enter="right", din=0.9, amp=5, z=12))
    cen = (930, 1440)
    t_th = c(3, 0.62)
    L.append(Layer(dyn=thermo_dyn(lambda lt: 1.0 - 0.58 * ease_io(clamp((lt - 0.6) / 1.5)), cen), d=1.0, t0=t_th, enter="rise", din=0.6, z=13))

    def cam(t):
        u = clamp(t / 5.0)
        return 1 + 0.045 * ease_out(u), -26 * ease_out(u), 10 * ease_out(u)
    return Scene("S3", (STEEL, 3), L, cam)


# ------------------------------------------------ S4: the year without a summer
def S4(c, dur):
    L = backdrop(4, 0.9, front=True)
    cal = A("calendar")
    s = 1.12
    cx, cy = 540, 960
    L.append(Layer(cal, x=cx, y=cy, sc=s, d=0.6, t0=-0.35, enter="drop", din=0.75, amp=2, spin=0, z=2, rot=-2))

    def cpt(px, py):
        return cx + (px - 380) * s, cy + (py - 480) * s
    for i, cu in enumerate((0.26, 0.36, 0.46)):
        x, y = cpt(610, 70 + 250 + i * 220 + 92)
        L.append(Layer(A("snow"), x=x, y=y, h=150, d=0.8, t0=c(4, cu), enter="slam", din=0.35, z=3 + i, rot=8 * (i - 1)))
    L += snowfall(c(4, 0.26), 26, seed=4)
    L.append(Layer(A("dim_sun"), x=880, y=250, sc=0.5, d=0.35, t0=-0.3, enter="pop", din=0.5, amp=6, z=1))
    L.append(Layer(A("ash2"), x=840, y=300, h=250, d=0.9, t0=-0.2, enter="right", din=0.7, z=6))
    L.append(Layer(banner("NO SUMMER", 820, seed=31), x=540, y=1350, sc=1.0, d=1.1, t0=c(4, 0.50), enter="slam", din=0.4, kind="title", rot=-5, z=9, amp=3))
    L.append(Layer(A("oat_dead"), x=150, y=1560, h=640, d=1.0, t0=c(4, 0.56), enter="left", din=0.7, z=8, rot=-6))
    L.append(Layer(A("oat_dead"), x=950, y=1530, h=600, d=1.05, t0=c(4, 0.63), enter="right", din=0.7, z=8, rot=7, flip=True))

    def cam(t):
        u = clamp(t / 5.0)
        return 1 + 0.05 * ease_out(u), 24 * ease_out(u), -12 * ease_out(u)
    return Scene("S4", ((243, 234, 214), 4), L, cam)


# ------------------------------------------------ S5: oats run short -> Drais -> the idea
def S5(c, dur):
    L = backdrop(5, 0.8, front=True)
    ss = 0.95
    stx, sty = 540, 1020
    t6 = c(6, 0.0)
    st_meta = META["stable"]
    L.append(Layer(A("stable"), x=stx, y=sty, sc=ss, d=0.55, t0=-0.4, enter="rise", din=0.7, amp=2, spin=0, z=2,
                   kf=[(t6 + 0.1, dict(dx=0, dy=0, s=1.0)), (t6 + 1.2, dict(dx=150, dy=80, s=0.74))]))
    # three heads peek out of the stalls, then sink away one by one ("horses starve")
    ops = st_meta["openings"]
    names = ["head_chest", "head_grey", "head_black"]
    exits = [c(5, 0.62), c(5, 0.76), c(5, 0.90)]
    for i, ((x0, y0, x1, y1), nm, tx) in enumerate(zip(ops, names, exits)):
        hx = stx + ((x0 + x1) / 2 + 12 - 514) * ss
        hy = sty + ((y1 - 60) + 12 - 456) * ss - 640 * 0.34 * 1.0
        L.append(Layer(A(nm), x=hx, y=hy, sc=0.50, d=0.58, t0=-0.3 + 0.1 * i, enter="rise", din=0.6, amp=2, spin=0, z=3 + i,
                       t1=tx, exit="sink", dout=0.9, rot=(-2, 1.5, -1)[i],
                       kf=[(0.25 * k, dict(dy=7 * math.sin(k * 0.9 + i * 2.1), rot=2.0 * math.sin(k * 0.7 + i), lin=True)) for k in range(0, 70)]))
    # oats: healthy sheaf -> grey dead sheaf; bucket
    t_dead = c(5, 0.45)
    L.append(Layer(A("oat_gold"), x=900, y=1600, h=640, d=0.9, t0=c(5, 0.16), enter="pop", din=0.5, z=8, t1=t_dead, exit="fade", dout=0.5))
    L.append(Layer(A("oat_dead"), x=900, y=1600, h=620, d=0.9, t0=t_dead, enter="fade", din=0.6, z=8))
    L.append(Layer(A("bucket"), x=600, y=1660, h=300, d=0.9, t0=c(5, 0.30), enter="pop", din=0.5, z=8, rot=4))
    L.append(Layer(banner("OATS", 560, seed=41), x=540, y=215, sc=1.0, d=1.1, t0=c(5, 0.20), enter="slam", din=0.4, kind="title", z=20, rot=-3,
                   t1=c(6, 0.10), exit="up", dout=0.6))
    # Drais steps in and thinks
    L.append(Layer(A("drais"), x=230, y=1350, h=800, d=0.92, t0=c(6, 0.10), enter="left", din=0.85, amp=3, z=14))
    L.append(Layer(banner("KARL DRAIS", 720, seed=42), x=540, y=215, sc=1.0, d=1.1, t0=c(6, 0.20), enter="slam", din=0.4, kind="title", z=20, rot=2))
    bx, by = 640, 640
    L.append(Layer(A("bubble"), x=bx, y=by, sc=0.82, d=0.97, t0=c(6, 0.52), enter="grow", din=0.55, amp=4, z=16))
    L.append(Layer(A("q_card"), x=bx - 10, y=by - 55, h=200, d=1.0, t0=c(6, 0.58), enter="pop", din=0.4, z=17, rot=-6,
                   t1=c(6, 0.76), exit="shrink", dout=0.3))
    L.append(Layer(A("wheel"), x=bx - 10, y=by - 55, h=300, d=1.0, t0=c(6, 0.78), enter="spin", din=0.7, z=18, amp=0,
                   kf=[(c(6, 0.78), dict(rot=0, lin=True)), (c(6, 0.78) + 12, dict(rot=1300, lin=True))]))

    def cam(t):
        u = clamp(t / 12.0)
        return 1 + 0.05 * ease_out(u), 20 * ease_out(u), -14 * ease_out(u)
    return Scene("S5", (MARIGOLD, 5), L, cam)


# ------------------------------------------------ S6: the machine
def S6(c, dur):
    L = backdrop(6, 0.6, front=False)
    s = 0.74
    mcx, mcy = 540, 1120
    mp = mp_factory(mcx, mcy, s)
    ground_y = mp(0, 900)[1]
    gy = smap(540, ground_y)[1]          # where the machine's wheels touch down after the safe-zone mapping
    c_roll = c(8, 0.0)
    t_end = dur + 3.0
    from sprites_a import sun as mksun, ash_cloud
    # sky: a big marigold sun and slow cream clouds
    L.append(Layer(mksun(560, color=MARIGOLD, core=(252, 208, 96)), x=820, y=470, sc=0.85, d=0.12, t0=-0.5, enter="grow", din=0.8, amp=3, z=0, spin=0, safe=False))
    sky = Image.new("RGBA", (2160, 520), (0, 0, 0, 0))
    for i, (x, y, w, h) in enumerate([(120, 130, 520, 300), (800, 300, 440, 260), (1380, 90, 560, 320), (1900, 280, 400, 240)]):
        cl = ash_cloud(w, h, (250, 246, 236), seed=i + 3, border=8, puffs=7)
        sky.alpha_composite(cl, (x, y))
    L.append(Layer(sky, x=540, y=330, sc=1.0, d=0.2, t0=-0.5, enter="fade", din=0.8, scroll=22, scroll_start=-1.0, z=1, amp=0, breath=False, safe=False))
    # world: scrolling hills + treeline + road. Static until the ride begins.
    L.append(Layer(A("hills_a"), x=540, y=gy - 190, sc=1.0, d=0.3, t0=-0.5, enter="rise", din=0.8, scroll=30, scroll_start=c_roll, z=2, amp=0, breath=False, safe=False))
    L.append(Layer(A("hills_b"), x=540, y=gy - 80, sc=1.0, d=0.42, t0=-0.45, enter="rise", din=0.8, scroll=80, scroll_start=c_roll, z=3, amp=0, breath=False, safe=False))
    rnd = random.Random(9)
    strip = Image.new("RGBA", (2160, 620), (0, 0, 0, 0))
    for i in range(7):
        im = A("pine" if i % 2 == 0 else "pine2")
        k = rnd.uniform(0.7, 1.0)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        strip.alpha_composite(im, (int(i * 300 + rnd.uniform(-40, 40)), 620 - im.height))
    L.append(Layer(strip, x=540, y=gy - 230, sc=0.8, d=0.6, t0=-0.4, enter="rise", din=0.8, scroll=260, scroll_start=c_roll, z=4, amp=0, breath=False, safe=False))
    fill = Image.new("RGBA", (1080, 1100), (110, 102, 98, 255))
    L.append(Layer(fill, x=540, y=gy + 300 + 210 + 530, sc=1.0, d=0.62, t0=-0.5, enter="rise", din=0.7, z=5, amp=0, breath=False, safe=False))
    L.append(Layer(A("road"), x=540, y=gy + 300, sc=1.0, d=0.62, t0=-0.5, enter="rise", din=0.7, z=5, amp=0, breath=False, safe=False))
    from sprites_c import road_dashes
    L.append(Layer(road_dashes(), x=540, y=gy + 235, sc=1.0, d=0.66, t0=-0.4, enter="fade", din=0.6, scroll=620, scroll_start=c_roll, z=6, amp=0, breath=False, safe=False))
    # numerals + assembly
    L.append(Layer(word("1817", 260, INK, 8), x=300, y=300, sc=1.0, d=1.05, t0=c(7, 0.02), enter="slam", din=0.45, rot=-6, z=30,
                   t1=c(8, 0.05), exit="up", dout=0.6))
    L += draisine_layers(mcx, mcy, s, c(7, 0.16), c(7, 0.26), c(7, 0.33), c(7, 0.40), c(7, 0.70), c_roll, d=0.8, z0=10, t_end=t_end)
    # marker rings around the two wheels ("Two wheels")
    for i, hub in enumerate(((260, 640), (1140, 640))):
        x, y = mp(*hub)
        L.append(Layer(dyn=marker_dyn(ellipse_pts(x, y, 235, 235, -110, 280), 0.55, 20, seed=i), d=0.9, t0=c(7, 0.46) + 0.4 * i, enter="none", z=40,
                       t1=c(7, 0.66), exit="fade", dout=0.4))
    # "No pedals": a pedal, crossed out
    L.append(Layer(A("pedal"), x=800, y=620, h=300, d=1.0, t0=c(7, 0.58), enter="pop", din=0.4, z=41, rot=8, t1=c(8, 0.05), exit="up", dout=0.6))
    s1, s2 = cross_pts(800, 620, 135)
    L.append(Layer(dyn=marker_dyn(s1, 0.25, 26), d=1.02, t0=c(7, 0.62), enter="none", z=42, t1=c(8, 0.05), exit="up", dout=0.6))
    L.append(Layer(dyn=marker_dyn(s2, 0.25, 26, seed=2), d=1.02, t0=c(7, 0.62) + 0.2, enter="none", z=42, t1=c(8, 0.05), exit="up", dout=0.6))
    # dust behind the pushing feet, then the ride
    rnd = random.Random(3)
    for k in range(18):
        t = c(7, 0.74) + k * 0.55
        L.append(Layer(A("dust"), x=mp(300, 880)[0] + rnd.uniform(-30, 30), y=ground_y - 20, h=rnd.randint(100, 150), d=0.82, t0=t, enter="grow", din=0.3,
                       t1=t + 0.45, exit="fade", dout=0.4, amp=0, z=39, kf=[(t, dict(dx=0, dy=0, lin=True)), (t + 0.9, dict(dx=-260 if t > c_roll else -60, dy=-40, lin=True))]))
    # MANNHEIM signpost sweeps past (low, behind the rider), walker is left behind
    L.append(Layer(A("sign"), x=1450, y=gy - 150, h=380, d=0.72, t0=c(8, 0.0) - 0.2, enter="none", z=11, amp=0, breath=False, safe=False,
                   kf=[(c(8, 0.0) - 0.2, dict(dx=0, lin=True)), (c(8, 0.0) + 2.6, dict(dx=-1950, lin=True))]))
    L.append(Layer(A("walker"), x=820, y=gy - 170, h=330, d=0.74, t0=c(8, 0.28), enter="rise", din=0.4, z=11, amp=0, breath=False, safe=False,
                   kf=[(c(8, 0.28), dict(dx=0, lin=True)), (c(8, 0.28) + 4.5, dict(dx=-1750, lin=True))]))
    # "No oats required"
    L.append(Layer(A("bucket"), x=860, y=520, h=260, d=1.0, t0=c(8, 0.70), enter="pop", din=0.4, z=41, rot=-6))
    s1, s2 = cross_pts(860, 520, 120)
    L.append(Layer(dyn=marker_dyn(s1, 0.25, 26), d=1.02, t0=c(8, 0.78), enter="none", z=42))
    L.append(Layer(dyn=marker_dyn(s2, 0.25, 26, seed=2), d=1.02, t0=c(8, 0.78) + 0.2, enter="none", z=42))

    def cam(t):
        u = clamp(t / 13.0)
        ride = ease_io(clamp((t - c_roll) / 2.0))
        push = ease_io(clamp((t - c_roll) / 4.0))
        return 1 + 0.03 * ease_out(u) + 0.07 * push, -40 * ride, -8 * ease_out(u)
    return Scene("S6", (TEAL_G, 6), L, cam)


# ------------------------------------------------ S7: the timing
def S7(c, dur):
    L = backdrop(7, 0.7, front=True)
    tags = [("tag1815", 330, 560, -7, 0.04), ("tag1816", 740, 980, 5, 0.30), ("tag1817", 330, 1400, -4, 0.52)]
    for nm, x, y, r, cu in tags:
        L.append(Layer(A(nm), x=x, y=y, h=240, d=0.9, t0=c(9, cu), enter="slam", din=0.45, rot=r, z=5, amp=3))
    L.append(Layer(A("volcano"), x=770, y=560, sc=0.30, d=0.8, t0=c(9, 0.10), enter="pop", din=0.5, z=4, amp=3))
    L.append(Layer(A("snow"), x=330, y=970, h=250, d=0.8, t0=c(9, 0.33), enter="pop", din=0.5, z=4, amp=3, spin=6))
    L.append(Layer(A("wheel"), x=770, y=1400, h=330, d=0.8, t0=c(9, 0.55), enter="spin", din=0.7, z=4, amp=3,
                   kf=[(c(9, 0.55), dict(rot=0, lin=True)), (c(9, 0.55) + 8, dict(rot=900, lin=True))]))
    for x, y, cu, r in ((190, 220, 0.04, -9), (880, 250, 0.10, 8)):
        L.append(Layer(A("q_card"), x=x, y=y, h=210, d=1.05, t0=c(9, cu), enter="pop", din=0.45, rot=r, z=8, t1=c(9, 0.50), exit="shrink", dout=0.4, amp=8))
    # short arrows between the tags (never across the numbers), then a ring round each year
    for (p0, p1, bl, cu) in (((470, 705), (610, 850), -40, 0.40), ((690, 1120), (470, 1275), 40, 0.60)):
        shaft, hs = arrow_parts(p0, p1, bl)
        L.append(Layer(dyn=marker_dyn(shaft, 0.35, 16, seed=3), d=0.95, t0=c(9, cu), enter="none", z=3))
        for h_ in hs:
            L.append(Layer(dyn=marker_dyn(h_, 0.15, 16, seed=4), d=0.95, t0=c(9, cu) + 0.32, enter="none", z=3))
    for i, (x, y) in enumerate(((330, 560), (740, 980), (330, 1400))):
        L.append(Layer(dyn=marker_dyn(ellipse_pts(x, y, 275, 150, -100, 275, 40), 0.5, 20, seed=5 + i), d=1.0, t0=c(9, 0.72) + 0.42 * i, enter="none", z=9))

    def cam(t):
        u = clamp(t / 5.0)
        return 1 + 0.04 * ease_out(u), -18 * ease_out(u), 10 * ease_out(u)
    return Scene("S7", (VIOLET_G, 7), L, cam)


# ------------------------------------------------ S8: the payoff
def S8(c, dur):
    gx, gy, gs = 540, 610, 0.60
    R = 500 * gs
    PT = gpt((gx, gy, R), None, TAMBORA)
    PG = gpt((gx, gy, R), None, MANNHEIM)
    L = backdrop(8, 0.8, front=False)
    L.append(Layer(A("globe"), x=gx, y=gy, sc=gs, d=0.55, t0=-0.4, enter="grow", din=0.7, amp=4, spin=0, z=2))
    L.append(Layer(A("pin"), x=PT[0], y=PT[1] - 50, h=120, d=0.9, t0=c(10, 0.10), enter="pop", din=0.4, z=5))
    L.append(Layer(A("pin"), x=PG[0], y=PG[1] - 50, h=120, d=0.9, t0=c(10, 0.18), enter="pop", din=0.4, z=5))
    arc = arc_pts(PT, PG, 90)
    L.append(Layer(dyn=dotted_dyn(arc, 1.5, r=8, gap=28), d=0.92, t0=c(10, 0.58), enter="none", z=6))
    L.append(Layer(dyn=counter_dyn(12000, 1.5, 150, (540, 975)), d=1.05, t0=c(10, 0.66), enter="slam", din=0.4, z=10))
    # the lineage: draisine -> modern bicycle, stacked like stairs
    L += draisine_layers(300, 1285, 0.46, -1.9, -1.8, -1.75, -1.7, -1.5, c(10, 0.1), d=0.82, z0=20, t_end=dur + 3.0, roll_speed=240)
    L.append(Layer(A("bike"), x=700, y=1640, h=400, d=0.95, t0=c(10, 0.20), enter="right", din=0.9, z=30, amp=2, spin=0))
    shaft, hs = arrow_parts((545, 1445), (600, 1535), -50)
    L.append(Layer(dyn=marker_dyn(shaft, 0.4, 20, seed=2), d=1.0, t0=c(10, 0.34), enter="none", z=31))
    for h_ in hs:
        L.append(Layer(dyn=marker_dyn(h_, 0.15, 20, seed=3), d=1.0, t0=c(10, 0.34) + 0.35, enter="none", z=31))
    L.append(Layer(banner("FROM ASH TO WHEELS", 960, seed=51, tape=False), x=540, y=170, sc=1.0, d=1.1, t0=c(10, 0.80), enter="slam", din=0.45, kind="title", z=40, rot=-2))

    def cam(t):
        u = clamp(t / 7.0)
        return 1 + 0.035 * ease_out(u), 14 * ease_out(u), -10 * ease_out(u)
    return Scene("S8", (COBALT, 8), L, cam)
