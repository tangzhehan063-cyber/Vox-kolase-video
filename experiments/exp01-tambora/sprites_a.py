"""Sprites, part A: the physical world — globe, volcano, ash, sun, thermometer, calendar, map pins."""
import json, math, random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from paperkit import *

# Coarse, hand-simplified outlines (lon, lat). Deliberately chunky: they get cut from paper.
CONTINENTS = {
 "eurasia": [(-9,37),(-9,43),(-1.5,43.5),(-4.5,48),(2,51),(5,53.5),(8,54.5),(8.5,57),(10.5,57.5),(10,54.5),(14,54),
  (20,55),(21,57),(24,59.5),(30,60),(23,60.5),(21,64),(25,65.5),(17,62),(19,59),(16,56),(12,56),(10,59),(5,58),
  (5,62),(14,67),(25,71),(40,67),(44,68),(60,69),(70,73),(80,73.5),(100,77),(112,74),(130,71),(142,72.5),(160,70),
  (170,66),(172,60),(163,59),(155,57),(156,51),(143,59),(135,54),(141,48),(133,43),(129,41),(129,35),(126,34.5),
  (125,39.5),(121,40.5),(122,37),(119,35),(122,31),(121,28),(114,22.5),(108,21.5),(106,17),(109,12),(105,9),
  (101,13),(100,8),(103,1.5),(98,8),(98,16),(94,17),(90,22),(87,21.5),(80,15),(77,8),(73,17),(72,21),(67,24.5),
  (57,25.5),(56,27),(50,30),(48,29.5),(51,24.5),(56,26),(57,23),(59,22.5),(52,16),(43,13),(39,21),(35,28),
  (34.5,31),(36,36.5),(30,36.5),(27,37),(26.5,40.5),(23,40),(24,38),(22,37),(20,40),(15,45),(13,45.5),(12.5,44),
  (16,41.5),(18.5,40),(16,38),(12,41.5),(8.5,44.5),(3,43),(0,39),(-1,37.5),(-6,36.5)],
 "africa": [(-17,21),(-13,27.5),(-9.5,30),(-6,35.8),(10,37),(11,33),(20,32.5),(32,31),(34,28),(37,22),(43,12),
  (51,12),(46,5),(41,-2),(39,-8),(40.5,-15),(35,-24),(32,-29),(27,-34),(20,-35),(18,-32),(14,-22),(12,-14),
  (13,-5),(9,3),(4,6),(-5,5),(-8,4.5),(-13,8),(-17,14.5)],
 "britain": [(-5.5,50),(1.5,51),(1.7,53),(-0.5,56),(-2,58.5),(-5,58.5),(-6,56),(-3,54.5),(-4.5,52)],
 "sumatra": [(95.3,5.5),(98,4),(104,-1),(106,-6),(102,-4),(97,1)],
 "java": [(105.2,-6.3),(111,-6.4),(114.5,-7.6),(108,-8.2)],
 "borneo": [(109,1.5),(113,3),(117,7),(119,5),(117,1),(116,-4),(110,-3)],
 "sulawesi": [(119.5,-5),(120.5,1),(124.5,1),(122,-1.5),(123.5,-5),(121,-4)],
 "sumbawa": [(116.7,-8.2),(119.2,-8.1),(118.8,-9),(117,-8.9)],
 "newguinea": [(131,-1),(141,-2.5),(150,-10),(141,-9),(138,-8),(133,-4)],
 "australia": [(113,-22),(114,-26),(115,-34),(124,-33.5),(131,-31.5),(138,-35),(141,-38),(147,-38.5),(150,-37),
  (153,-30),(153,-25),(146,-19),(142,-10.7),(141,-17),(136,-12),(131,-11.5),(126,-14),(122,-17)],
 "india_sl": [(79.8,9.5),(81.8,7.5),(80.5,6),(79.8,7.5)],
 "japan": [(130,31.5),(132,34),(135,35),(140,36),(141.5,41),(141,38),(140,35),(137,33.5),(134,33),(131,33)],
}
LON0, LAT0 = 63.0, 14.0     # globe centre: both Indonesia and Germany stay on the visible face
TAMBORA = (118.0, -8.25)
MANNHEIM = (8.47, 49.49)


def ortho(lon, lat, lon0=LON0, lat0=LAT0):
    """Orthographic projection -> (u, v, visible) with u,v in [-1,1], v down."""
    l, p, l0, p0 = map(math.radians, (lon, lat, lon0, lat0))
    x = math.cos(p) * math.sin(l - l0)
    y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0)
    c = math.sin(p0) * math.sin(p) + math.cos(p0) * math.cos(p) * math.cos(l - l0)
    return x, -y, c > 0


def _proj_poly(poly, subdiv=6):
    """Project a lon/lat polygon, pushing hidden points to the limb."""
    pts = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        for k in range(subdiv):
            t = k / subdiv
            lon, lat = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            x, y, vis = ortho(lon, lat)
            if not vis:
                r = math.hypot(x, y) or 1
                x, y = x / r, y / r
            pts.append((x, y))
    return pts


def globe(d=1000, border=20, ocean=CREAM, land=TEAL, seed=3):
    """Paper globe. Returns (image, meta) - meta has centre/radius so scenes can pin places."""
    R = d // 2
    pad = border + 40
    S = 2 * (R + pad)
    cx = cy = S // 2
    p = Painter(S, S, seed)
    # white sticker rim + drop shadow
    sh = Image.new("RGBA", p.im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse([(cx - R - border + 9) * SS, (cy - R - border + 14) * SS,
                                (cx + R + border + 9) * SS, (cy + R + border + 14) * SS], fill=(40, 30, 15, 120))
    p.im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(9 * SS / 2)))
    p.circle(cx, cy, R + border, (252, 251, 247), rim=0.0, grain=4)
    p.circle(cx, cy, R, ocean, shade_amt=0.55, sdir=(0.8, 0.9), tone=shade(ocean, 0.80), dot=20, rim=0.1)
    # graticule: thin lines, drawn UNDER the land
    d_ = ImageDraw.Draw(p.im)
    gcol = shade(ocean, 0.80) + (255,)
    for lat in range(-60, 90, 30):
        pts = []
        for lon in range(-180, 181, 5):
            x, y, vis = ortho(lon, lat)
            if vis:
                pts.append(((cx + x * R) * SS, (cy + y * R) * SS))
            elif len(pts) > 1:
                d_.line(pts, fill=gcol, width=3 * SS // 2)
                pts = []
        if len(pts) > 1:
            d_.line(pts, fill=gcol, width=3 * SS // 2)
    for lon in range(-180, 180, 30):
        pts = []
        for lat in range(-85, 86, 5):
            x, y, vis = ortho(lon, lat)
            if vis:
                pts.append(((cx + x * R) * SS, (cy + y * R) * SS))
            elif len(pts) > 1:
                d_.line(pts, fill=gcol, width=3 * SS // 2)
                pts = []
        if len(pts) > 1:
            d_.line(pts, fill=gcol, width=3 * SS // 2)
    clip = Image.new("L", p.im.size, 0)
    ImageDraw.Draw(clip).ellipse([(cx - R) * SS, (cy - R) * SS, (cx + R) * SS, (cy + R) * SS], fill=255)
    tint = {"sumbawa": CORAL, "java": CORAL, "sumatra": CORAL, "borneo": CORAL, "sulawesi": CORAL,
            "newguinea": CORAL, "australia": MARIGOLD, "africa": (84, 150, 90), "britain": TEAL,
            "india_sl": TEAL, "japan": TEAL}
    for name, poly in CONTINENTS.items():
        pp = [(cx + x * R, cy + y * R) for x, y in _proj_poly(poly)]
        m = p.mask_poly_raw(pp, cut=True, amp=1.2)
        m = Image.fromarray(np.minimum(np.asarray(m), np.asarray(clip)))
        p.add(m, tint.get(name, land), shade_amt=0.5, sdir=(0.9, 0.7), dot=17, rim=0.35)
    img = p.done(border=0, crop=False)
    meta = dict(size=S, cx=cx, cy=cy, R=R)
    return img, meta


def globe_point(meta, lonlat):
    u, v, vis = ortho(*lonlat)
    return meta["cx"] + u * meta["R"], meta["cy"] + v * meta["R"]


def volcano(w=1000, h=900, seed=5, border=0):
    p = Painter(w, h, seed)
    apex_l, apex_r = (392, 196), (608, 196)
    # distant ridge
    p.poly([(0, 880), (60, 700), (170, 640), (260, 600), (330, 680), (380, 880)], (112, 96, 108), shade_amt=0.4, dot=18)
    p.poly([(700, 880), (770, 640), (860, 600), (950, 690), (1000, 880)], (112, 96, 108), shade_amt=0.4, sdir=(1, 1), dot=18)
    # two facets of the cone: lit left, shadowed right
    left = [(40, 880), (160, 700), (255, 520), (345, 330), apex_l, (500, 215), (470, 880)]
    right = [(500, 215), apex_r, (655, 330), (745, 520), (845, 700), (970, 880), (470, 880)]
    p.poly(left, (96, 80, 92), shade_amt=0.45, sdir=(-0.8, 0.9), dot=16)
    p.poly(right, ROCK, shade_amt=0.55, sdir=(0.9, 0.8), dot=16, tone=(36, 28, 34))
    # strata bands (cut as separate scraps so the mountain reads as layered paper)
    p.poly([(180, 680), (300, 700), (360, 600), (250, 560)], (120, 100, 112), amp=2)
    p.poly([(620, 560), (730, 610), (690, 700), (590, 650)], (84, 70, 82), amp=2)
    # crater glow
    p.ellipse((388, 168, 612, 232), ORANGE, rim=0.35)
    p.ellipse((420, 178, 580, 220), MARIGOLD, rim=0.2)
    # lava runs, two scraps each so there is an outer red and a bright core
    lava1 = [(460, 214), (500, 216), (506, 300), (536, 380), (520, 470), (556, 560), (520, 640), (470, 560), (484, 470), (452, 380), (470, 300)]
    lava2 = [(540, 218), (566, 218), (606, 330), (630, 440), (600, 520), (570, 440), (552, 330)]
    p.poly(lava1, CORAL, rim=0.4)
    p.poly([(478, 222), (494, 222), (500, 320), (516, 420), (500, 520), (484, 420), (474, 320)], MARIGOLD, amp=1)
    p.poly(lava2, CORAL, rim=0.4)
    return p.done(border=border, crop=False)


def ash_cloud(w=600, h=400, color=ASH1, seed=0, border=10, puffs=8):
    pad = 120   # draw on a bigger sheet so no puff is cut by the canvas
    p = Painter(w + 2 * pad, h + 2 * pad, seed)
    blob_cloud(p, (w + 2 * pad) / 2, (h + 2 * pad) * 0.56, w * 0.86, h * 0.9, color, seed=seed, puffs=puffs,
               shade_amt=0.55, sdir=(0.6, 1.0), dot=18, tone=shade(color, 0.62))
    return p.done(border=border)


def sun(d=560, color=MARIGOLD, core=(252, 208, 96), border=14, seed=2):
    R = d // 2
    S = d + 160
    p = Painter(S, S, seed)
    c = S / 2
    rays = 14
    for i in range(rays):
        a = 2 * math.pi * i / rays
        long = i % 2 == 0
        r0, r1 = R * 0.86, R * (1.28 if long else 1.14)
        w = 0.19 if long else 0.15
        pts = [(c + r0 * math.cos(a - w), c + r0 * math.sin(a - w)),
               (c + r1 * math.cos(a), c + r1 * math.sin(a)),
               (c + r0 * math.cos(a + w), c + r0 * math.sin(a + w))]
        p.poly(pts, color, amp=1.2)
    p.circle(c, c, R * 0.92, color, shade_amt=0.45, sdir=(0.7, 0.8), dot=17)
    p.circle(c, c, R * 0.62, core, rim=0.15)
    return p.done(border=border)


def thermometer(level=1.0, w=230, h=760, border=14, seed=4):
    """level 1.0 = full mercury; 0 = nearly empty. Drawn on demand so it can animate."""
    p = Painter(w, h, seed)
    tw = 74
    x0 = (w - tw) / 2
    bulb_r = 66
    top, bot = 40, h - 2 * bulb_r - 6
    p.rrect((x0, top, x0 + tw, bot + 30), 36, (250, 248, 240), rim=0.2)
    p.circle(w / 2, h - bulb_r - 10, bulb_r, (250, 248, 240), rim=0.2)
    # ticks
    for i in range(11):
        y = top + 60 + (bot - top - 90) * i / 10
        L = 38 if i % 5 == 0 else 22
        p.line([(x0 + tw + 12, y), (x0 + tw + 12 + L, y)], 5, INK, rim=0)
    # mercury
    inner = 22
    mtop = top + 56 + (bot - top - 60) * (1 - max(0.04, min(1.0, level)))
    p.rrect((w / 2 - inner / 2, mtop, w / 2 + inner / 2, bot + 20), 10, CORAL, rim=0.1)
    p.circle(w / 2, h - bulb_r - 10, bulb_r - 14, CORAL, rim=0.2, shade_amt=0.5, sdir=(0.7, 0.9), dot=12)
    return p.done(border=border)


def snowflake(s=120, color=COBALT, seed=0):
    p = Painter(s, s, seed)
    c = s / 2
    for i in range(3):
        a = math.pi * i / 3
        p.line([(c - c * 0.9 * math.cos(a), c - c * 0.9 * math.sin(a)), (c + c * 0.9 * math.cos(a), c + c * 0.9 * math.sin(a))], s * 0.09, color, rim=0.1)
    for i in range(6):
        a = math.pi * i / 3
        bx, by = c + c * 0.62 * math.cos(a), c + c * 0.62 * math.sin(a)
        for sgn in (-1, 1):
            ax = a + sgn * 0.7
            p.line([(bx, by), (bx + c * 0.28 * math.cos(ax), by + c * 0.28 * math.sin(ax))], s * 0.06, color, rim=0.1)
    return p.done(border=0)


def calendar(w=760, h=960, seed=6, year="1816"):
    p = Painter(w, h, seed)
    top = 70
    # binder pad shadow pieces
    p.poly([(26, top + 26), (w - 10, top + 20), (w - 22, h - 20), (14, h - 8)], (222, 212, 190), amp=2)
    p.poly([(10, top), (w - 28, top - 6), (w - 12, h - 36), (0, h - 30)], (252, 250, 244), amp=2, rim=0.25)
    p.poly([(10, top), (w - 28, top - 6), (w - 24, top + 190), (6, top + 196)], CORAL, amp=2)
    for i in range(7):
        x = 70 + i * 100
        p.circle(x, top + 8, 17, (60, 56, 60), rim=0.1)
        p.line([(x, top - 40), (x, top + 10)], 11, (150, 150, 160), rim=0.1)
    p.text((w / 2 - 6, top + 96), year, 170, (252, 250, 244), anchor="mm")
    months = ["JUN", "JUL", "AUG"]
    for i, m in enumerate(months):
        y = top + 250 + i * 220
        p.poly([(52, y), (w - 70, y - 6), (w - 62, y + 180), (44, y + 186)], (236, 242, 252), amp=2, rim=0.2)
        p.text((84, y + 92), m, 112, COBALT, anchor="lm")
    return p.done(border=0, crop=False)


def pin(s=140, color=CORAL, seed=1):
    p = Painter(s, int(s * 1.35), seed)
    c = s / 2
    p.poly([(c - s * 0.36, s * 0.48), (c, s * 1.3), (c + s * 0.36, s * 0.48)], color, amp=0.6)
    p.circle(c, s * 0.45, s * 0.4, color, shade_amt=0.4, sdir=(0.8, 0.9), dot=10)
    p.circle(c, s * 0.45, s * 0.16, (252, 250, 244), rim=0.1)
    return p.done(border=8)


def question_card(s=420, seed=2, color=CREAM):
    p = Painter(s, s, seed)
    p.poly([(14, 20), (s - 18, 10), (s - 8, s - 22), (22, s - 8)], color, amp=2, rim=0.25)
    p.text((s / 2, s / 2 + 22), "?", int(s * 0.9), INK, anchor="mm")
    return p.done(border=12)


def year_tag(text, w=420, h=210, color=CREAM, seed=0, ink=INK):
    p = Painter(w, h, seed)
    p.poly([(60, 10), (w - 14, 14), (w - 8, h - 14), (60, h - 8), (10, h / 2)], color, amp=1.6, rim=0.25)
    p.circle(58, h / 2, 17, (0, 0, 0, 0)[:3], rim=0) if False else None
    p.text((w / 2 + 26, h / 2 + 6), text, int(h * 0.74), ink, anchor="mm")
    img = p.done(border=10)
    # punch the string hole after the border so it reads as a hole
    d = ImageDraw.Draw(img)
    ox = 10 + 26
    return img
