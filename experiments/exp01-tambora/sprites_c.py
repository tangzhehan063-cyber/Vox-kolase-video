"""Sprites, part C: small props — pedal, walker, flash, rocks, bubble, dust, dim sun, road dashes."""
import math, random
from PIL import Image, ImageDraw
from paperkit import *
from sprites_a import sun


def pedal(w=360, h=360, seed=3):
    p = Painter(w, h, seed)
    p.circle(130, 180, 88, (150, 150, 160), shade_amt=0.5, sdir=(1, 1), dot=12)
    p.circle(130, 180, 22, INK, rim=0)
    p.poly([(116, 170), (146, 170), (250, 280), (230, 306)], (110, 110, 122), amp=0.8)
    p.poly([(214, 290), (322, 296), (318, 328), (210, 322)], INK, amp=0.8)
    return p.done(border=10)


def walker(w=260, h=620, seed=4, color=(120, 60, 80)):
    p = Painter(w, h, seed)
    p.poly([(96, 330), (136, 330), (96, 600), (60, 600)], INK, amp=0.8)
    p.poly([(120, 330), (160, 330), (190, 600), (150, 600)], (60, 54, 66), amp=0.8)
    p.poly([(60, 590), (112, 590), (122, 616), (54, 616)], INK, amp=0.5)
    p.poly([(146, 590), (200, 590), (214, 616), (146, 616)], INK, amp=0.5)
    p.poly([(80, 150), (176, 150), (186, 350), (74, 350)], color, shade_amt=0.45, sdir=(1, 1), dot=12)
    p.poly([(168, 170), (226, 250), (204, 270), (150, 200)], color, amp=0.8)
    p.circle(130, 100, 44, SKIN if False else (236, 196, 160), rim=0.2)
    p.poly([(88, 70), (176, 70), (170, 48), (94, 48)], INK, amp=0.6)
    return p.done(border=10)


def flash(s=900, seed=2):
    p = Painter(s, s, seed)
    c = s / 2
    p.poly(star_poly(c, c, s * 0.48, s * 0.2, 14, 0.1), MARIGOLD, amp=2)
    p.poly(star_poly(c, c, s * 0.34, s * 0.14, 14, 0.35), (252, 224, 130), amp=2)
    p.circle(c, c, s * 0.12, CREAM, rim=0.1)
    return p.done(border=0)


def rock(s=90, seed=1, color=ROCK):
    rnd = random.Random(seed)
    p = Painter(s, s, seed)
    pts = []
    for i in range(7):
        a = 2 * math.pi * i / 7
        r = s * rnd.uniform(0.3, 0.48)
        pts.append((s / 2 + r * math.cos(a), s / 2 + r * math.sin(a)))
    p.poly(pts, color, amp=0.6, shade_amt=0.4, dot=8)
    return p.done(border=5)


def bubble(w=560, h=420, seed=5):
    pad = 60
    p = Painter(w + 2 * pad, h + 2 * pad + 140, seed)
    blob_cloud(p, (w + 2 * pad) / 2, (h + 2 * pad) * 0.5, w * 0.92, h * 0.96, (252, 250, 244), seed=seed, puffs=7,
               shade_amt=0.3, sdir=(0.5, 1), dot=16, tone=(214, 212, 206))
    p.circle(pad + w * 0.28, h + pad + 55, 36, (252, 250, 244), rim=0.2)
    p.circle(pad + w * 0.18, h + pad + 120, 22, (252, 250, 244), rim=0.2)
    return p.done(border=10)


def dust(s=120, seed=2):
    """Soft cluster of round paper puffs (circles only - no flat base)."""
    p = Painter(s, s, seed)
    for cx, cy, r in ((0.30, 0.62, 0.22), (0.52, 0.50, 0.28), (0.72, 0.62, 0.22), (0.50, 0.70, 0.20)):
        p.circle(cx * s, cy * s, r * s, (238, 230, 210), rim=0.12)
    return p.done(border=0)


def dim_sun(seed=2):
    return sun(560, color=(170, 160, 150), core=(206, 198, 184), border=14, seed=seed)


def road_dashes(w=2160, h=60):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 270):
        d.rectangle([x + 20, 8, x + 170, h - 8], fill=(246, 240, 224, 255))
    return im


def road_strip(w=1080, h=420, seed=1):
    p = Painter(w, h, seed)
    p.poly([(0, 40), (w, 20), (w, h), (0, h)], (112, 104, 100), shade_amt=0.4, sdir=(0.2, 1), dot=18)
    p.poly([(0, 40), (w, 20), (w, 56), (0, 76)], (170, 160, 146), amp=1.0)
    return p.done(border=0, crop=False)


def mini(img, h):
    return img.resize((max(1, int(img.width * h / img.height)), h), Image.LANCZOS)
