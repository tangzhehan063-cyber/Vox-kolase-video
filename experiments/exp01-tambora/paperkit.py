"""Experiment-local drawing kit: paper-cut shapes with grain, halftone shade and a darker rim.

Why this exists: the engine's subject sprites come from an external image model
(sprite_sheets.py -> nano_banana_pro -> chroma_sprites.py). That model is not available in
this session, and the shipped sprite library only holds infinite-scroll objects. So the
subjects for THIS film are drawn locally as scissored paper pieces. Grounds, tape, confetti,
banners and clippings still come from the engine's own library/paper.py.
"""
import math, os, random, sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "skills", "vox-editorial", "library"))
import paper  # the engine's own element factory

# paper.py looks for fonts in ~/.claude/skills/editorial-carousel (not present here and we
# were told not to touch global skills) -> point it at the copies in ./fonts instead.
paper.ANTON = os.path.join(HERE, "fonts", "Anton.ttf")
paper.FIGTREE = os.path.join(HERE, "fonts", "Figtree.ttf")
ANTON, FIGTREE = paper.ANTON, paper.FIGTREE

SS = 2  # supersample for crisp edges

INK = (30, 27, 30)
CREAM = (243, 234, 214)
COBALT = (46, 84, 178)
MARIGOLD = (247, 176, 44)
CORAL = (232, 96, 74)
TEAL = (32, 160, 138)
PINK = (233, 96, 140)
VIOLET = (124, 88, 176)
ORANGE = (241, 130, 62)
ROCK = (62, 52, 60)
ASH1, ASH2, ASH3 = (92, 92, 104), (132, 132, 144), (176, 176, 186)
WOOD = (172, 112, 64)
STRAW = (228, 188, 92)
RED = (214, 52, 44)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


def font(path, size):
    return ImageFont.truetype(path, int(size))


def jitter(pts, amp=1.6, seg=34, seed=0):
    """Subdivide edges and nudge the points: a scissored edge, not a vector one."""
    rnd = random.Random(seed)
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        k = max(1, int(L / seg))
        for j in range(k):
            t = j / k
            x = a[0] + (b[0] - a[0]) * t + rnd.uniform(-amp, amp)
            y = a[1] + (b[1] - a[1]) * t + rnd.uniform(-amp, amp)
            out.append((x, y))
    return out


class Painter:
    """Layered paper pieces on one transparent canvas. Coordinates are in final pixels."""

    def __init__(self, w, h, seed=0):
        self.w, self.h, self.seed = w, h, seed
        self.im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
        self.n = 0
        self._noise = None

    # ---- masks -------------------------------------------------------------------
    def _m(self):
        return Image.new("L", self.im.size, 0), None

    def _scaled(self, pts):
        return [(x * SS, y * SS) for x, y in pts]

    def mask_poly_raw(self, pts, cut=True, amp=1.3):
        pts = self._scaled(pts)
        if cut:
            pts = jitter(pts, amp * SS, 36 * SS, self.seed + self.n)
        m = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(m).polygon(pts, fill=255)
        return m

    def mask_ellipse(self, box):
        m = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(m).ellipse([v * SS for v in box], fill=255)
        return m

    def mask_line(self, pts, width, round_ends=True):
        m = Image.new("L", self.im.size, 0)
        d = ImageDraw.Draw(m)
        P = self._scaled(pts)
        d.line(P, fill=255, width=int(width * SS), joint="curve")
        if round_ends:
            r = width * SS / 2
            for x, y in (P[0], P[-1]):
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return m

    # ---- fill ----------------------------------------------------------------------
    def noise(self):
        if self._noise is None:
            rng = np.random.default_rng(self.seed + 11)
            n = rng.normal(0, 1, (self.im.size[1] // 2 + 1, self.im.size[0] // 2 + 1))
            n = np.kron(n, np.ones((2, 2)))[: self.im.size[1], : self.im.size[0]]
            self._noise = n
        return self._noise

    def add(self, mask, color, shade_amt=0.0, sdir=(0.7, 0.7), rim=0.30, dot=15, grain=7, tone=None, cut=None):
        """Fill a mask with paper. shade_amt>0 adds a halftone shadow toward sdir."""
        self.n += 1
        W, H = self.im.size
        m = np.asarray(mask, dtype=np.uint8) > 127
        if not m.any():
            return
        ys, xs = np.where(m)
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        sub = m[y0:y1, x0:x1]
        h, w = sub.shape
        col = np.empty((h, w, 3), dtype=np.float32)
        col[:] = color
        col += self.noise()[y0:y1, x0:x1, None] * grain * 0.5
        if shade_amt > 0:
            yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
            g = ((xx / max(w, 1) - 0.5) * sdir[0] + (yy / max(h, 1) - 0.5) * sdir[1])
            g = (g - g.min()) / max(1e-6, g.max() - g.min())
            g = np.clip((g - (1 - shade_amt)) / max(shade_amt, 1e-3), 0, 1)
            step = dot * SS
            c, s = math.cos(0.785), math.sin(0.785)
            u = (xx * c + yy * s) % step - step / 2
            v = (-xx * s + yy * c) % step - step / 2
            r = np.sqrt(u * u + v * v)
            dots = r < (g * step * 0.62)
            dark = np.array(tone or shade(color, 0.66), dtype=np.float32)
            col[dots] = dark
        # rim: darker band just inside the cut edge (paper thickness)
        er = Image.fromarray((sub * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))
        inner = np.asarray(er) > 127
        edge = sub & ~inner
        col[edge] = col[edge] * (1 - rim) + np.array(shade(color, 0.55), dtype=np.float32) * rim
        piece = np.zeros((H, W, 4), dtype=np.uint8)
        piece[y0:y1, x0:x1, :3] = np.clip(col, 0, 255).astype(np.uint8)
        a = np.asarray(Image.fromarray((sub * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)))
        piece[y0:y1, x0:x1, 3] = a
        self.im.alpha_composite(Image.fromarray(piece, "RGBA"))

    def poly(self, pts, color, cut=True, amp=1.3, **kw):
        self.add(self.mask_poly_raw(pts, cut, amp), color, **kw)

    def ellipse(self, box, color, **kw):
        self.add(self.mask_ellipse(box), color, **kw)

    def circle(self, cx, cy, r, color, **kw):
        self.ellipse((cx - r, cy - r, cx + r, cy + r), color, **kw)

    def line(self, pts, width, color, **kw):
        self.add(self.mask_line(pts, width), color, rim=kw.pop("rim", 0.15), **kw)

    def rrect(self, box, r, color, **kw):
        m = Image.new("L", self.im.size, 0)
        ImageDraw.Draw(m).rounded_rectangle([v * SS for v in box], radius=r * SS, fill=255)
        self.add(m, color, **kw)

    def text(self, xy, s, size, color, fnt=ANTON, anchor="la", spacing=0):
        d = ImageDraw.Draw(self.im)
        d.text((xy[0] * SS, xy[1] * SS), s, font=font(fnt, size * SS), fill=color + (255,), anchor=anchor)

    # ---- output ----------------------------------------------------------------------
    def done(self, border=0, shadow=True, crop=True):
        im = self.im.resize((self.w, self.h), Image.LANCZOS)
        if crop:
            bb = im.getbbox()
            if bb:
                im = im.crop(bb)
        if border:
            im = paper.sticker(im, border=border, shadow=shadow, blur=2)
        return im


def blob_cloud(p, cx, cy, w, h, color, seed=0, puffs=8, **kw):
    """Lumpy cloud: union of circles on a flat-ish base."""
    rnd = random.Random(seed)
    m = Image.new("L", p.im.size, 0)
    d = ImageDraw.Draw(m)
    for i in range(puffs):
        t = i / max(1, puffs - 1)
        r = h * rnd.uniform(0.36, 0.62) * (1 - abs(t - 0.5) * 0.7)
        x = cx - w / 2 + w * (0.12 + 0.76 * t)
        y = cy - r * 0.35 * rnd.uniform(0.2, 1.0)
        d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=255)
    d.rounded_rectangle([(cx - w * 0.42) * SS, (cy - h * 0.12) * SS, (cx + w * 0.42) * SS, (cy + h * 0.32) * SS],
                        radius=int(h * 0.22 * SS), fill=255)
    p.add(m, color, **kw)


def star_poly(cx, cy, r_out, r_in, n, rot=0):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + math.pi * i / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts
