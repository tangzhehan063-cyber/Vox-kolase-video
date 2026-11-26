"""Sprites, part B: the human world — oats, horses, stable, Drais, the machine, the road, the clock, the bicycle."""
import math, random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from paperkit import *

SKIN = (236, 196, 160)
CHESTNUT = (150, 82, 52)
GREYHORSE = (150, 150, 160)
BLACKHORSE = (58, 48, 54)


def oat_sheaf(state="gold", w=520, h=820, seed=7):
    """Bundle of oat stalks. 'gold' = healthy, 'dead' = grey, bent, thin."""
    rnd = random.Random(seed)
    p = Painter(w, h, seed)
    col = STRAW if state == "gold" else (150, 136, 112)
    grain_col = (240, 206, 112) if state == "gold" else (120, 108, 90)
    n = 11 if state == "gold" else 6
    for i in range(n):
        t = i / (n - 1) - 0.5
        bx = w / 2 + t * 110
        topx = w / 2 + t * 330 + rnd.uniform(-20, 20)
        topy = 120 + abs(t) * 80 + rnd.uniform(0, 40)
        bend = 0 if state == "gold" else rnd.uniform(60, 150) * (1 if t >= 0 else -1)
        pts = [(bx, h - 20), (bx + (topx - bx) * 0.4, h * 0.55), (topx + bend * 0.5, topy + 60), (topx + bend, topy + (60 if state == "dead" else 0))]
        p.line(pts, 17 if state == "gold" else 12, col, rim=0.2)
        hx, hy = pts[-1]
        for k in range(5 if state == "gold" else 3):
            yy = hy + k * 30
            for sgn in (-1, 1):
                gx = hx + sgn * (26 + k * 3)
                p.poly([(gx - 8, yy), (gx + 8, yy), (gx + sgn * 6, yy + 40)], grain_col, cut=False, rim=0.3)
    # twine
    p.line([(w / 2 - 150, h * 0.66), (w / 2 + 150, h * 0.62)], 22, CORAL if state == "gold" else (110, 96, 90), rim=0.2)
    return p.done(border=6)


def bucket(w=420, h=420, seed=3, empty=True):
    p = Painter(w, h, seed)
    p.line([(70, 130), (w / 2, 20), (w - 70, 130)], 14, (70, 66, 72), rim=0.1)
    p.poly([(50, 120), (w - 50, 120), (w - 90, h - 20), (90, h - 20)], (134, 138, 150), shade_amt=0.5, sdir=(1, 0.5), dot=16)
    p.poly([(50, 120), (w - 50, 120), (w - 56, 156), (56, 156)], (96, 100, 112))
    p.ellipse((52, 104, w - 52, 150), INK if empty else STRAW, rim=0.0)
    return p.done(border=12)


def horse(w=900, h=800, color=CHESTNUT, mane=(46, 34, 36), seed=9, facing=1):
    """Geometric paper horse, facing right."""
    p = Painter(w, h, seed)
    # far legs (darker) first
    dark = shade(color, 0.78)
    p.poly([(520, 430), (580, 430), (590, 600), (572, 760), (540, 760), (545, 600)], dark, amp=1.0)
    p.poly([(250, 420), (320, 430), (300, 600), (270, 760), (236, 760), (252, 600)], dark, amp=1.0)
    # tail
    p.poly([(168, 300), (120, 360), (96, 520), (140, 560), (160, 430), (196, 350)], mane, amp=1.5)
    # body
    p.ellipse((170, 250, 640, 520), color, shade_amt=0.55, sdir=(0.2, 1.0), dot=18)
    # neck + head
    p.poly([(540, 300), (610, 120), (720, 84), (760, 140), (690, 220), (650, 360)], color, shade_amt=0.4, sdir=(0.8, 1.0), dot=15)
    p.poly([(700, 84), (850, 116), (900, 210), (866, 240), (800, 200), (744, 180), (706, 168)], color, shade_amt=0.35, sdir=(0.6, 1.0), dot=13)
    p.poly([(706, 90), (722, 24), (748, 94)], color, amp=0.8)
    p.circle(792, 148, 9, INK, rim=0, cut=False) if False else p.ellipse((782, 140, 802, 160), INK, rim=0.0)
    p.poly([(886, 210), (900, 218), (894, 238), (872, 232)], (210, 150, 120), amp=0.5)
    # mane
    p.poly([(612, 120), (640, 100), (670, 120), (660, 160), (690, 170), (664, 210), (640, 220), (630, 270), (610, 250), (580, 300), (560, 290), (590, 200)], mane, amp=1.6)
    # near legs
    p.poly([(560, 420), (630, 420), (640, 600), (622, 760), (586, 760), (594, 610)], color, amp=1.0, shade_amt=0.4, sdir=(1, 0.2), dot=14)
    p.poly([(190, 410), (270, 420), (250, 600), (222, 760), (188, 760), (200, 600)], color, amp=1.0, shade_amt=0.4, sdir=(1, 0.2), dot=14)
    for hx in (604, 205, 556, 252):
        p.poly([(hx - 20, 744), (hx + 24, 744), (hx + 30, 772), (hx - 26, 772)], mane, amp=0.5)
    im = p.done(border=12)
    return im.transpose(Image.FLIP_LEFT_RIGHT) if facing < 0 else im


def horse_head(color=CHESTNUT, w=520, h=640, seed=2):
    """Head + neck in profile, peeking out of a stall; muzzle to the right."""
    p = Painter(w, h, seed)
    mane = (46, 34, 36)
    p.poly([(120, h), (170, 420), (220, 260), (280, 130), (330, 90), (385, 118), (470, 250), (512, 326), (500, 376),
            (448, 380), (398, 332), (352, 300), (338, 390), (356, h)], color, shade_amt=0.5, sdir=(1, 0.8), dot=15)
    p.poly([(300, 104), (312, 20), (348, 96)], color, amp=0.8)
    p.poly([(286, 112), (214, 282), (150, 480), (122, h), (192, h), (216, 462), (256, 304), (312, 150)], mane, amp=1.6)
    p.ellipse((372, 164, 394, 186), INK, rim=0)
    p.ellipse((478, 320, 492, 336), shade(color, 0.5), rim=0)
    p.poly([(478, 300), (512, 326), (500, 376), (466, 372)], (214, 160, 130), amp=0.5)
    return p.done(border=10)


def stable(w=1000, h=900, seed=8):
    """Barn front with three dark stall openings. Heads/doors are separate layers."""
    p = Painter(w, h, seed)
    p.poly([(0, 300), (w / 2, 20), (w, 300)], (96, 52, 46), shade_amt=0.4, sdir=(1, 1), dot=18)
    p.poly([(60, 300), (w / 2, 80), (w - 60, 300), (w - 60, 330), (60, 330)], (70, 40, 40), amp=1.4)
    p.poly([(40, 330), (w - 40, 330), (w - 40, h - 10), (40, h - 10)], (176, 78, 60), shade_amt=0.35, sdir=(1, 1), dot=18)
    for x in range(100, w - 40, 60):                 # planks
        p.line([(x, 340), (x, h - 14)], 3, (130, 56, 46), rim=0, cut=False) if False else p.poly([(x, 340), (x + 3, 340), (x + 3, h - 14), (x, h - 14)], (132, 58, 46), cut=False, rim=0)
    openings = [(100, 360, 340, h - 40), (380, 360, 620, h - 40), (660, 360, 900, h - 40)]
    for (x0, y0, x1, y1) in openings:
        p.poly([(x0 - 14, y0 - 14), (x1 + 14, y0 - 14), (x1 + 14, y1 + 6), (x0 - 14, y1 + 6)], (232, 214, 180), amp=1.0)
        p.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], (40, 30, 36), amp=0.8, rim=0.1)
        p.poly([(x0, y1 - 64), (x1, y1 - 64), (x1, y1), (x0, y1)], (96, 76, 60), amp=0.8)
    meta = dict(openings=openings, size=(w, h))
    return p.done(border=12, crop=False), meta


def drais_standing(w=480, h=980, seed=11, look=1):
    """Stylised 1810s gentleman inventor: top hat, tailcoat. Faces right."""
    p = Painter(w, h, seed)
    COAT = (46, 70, 140)
    # legs / boots
    p.poly([(190, 560), (250, 560), (254, 900), (200, 900)], (52, 46, 56), amp=1.0)
    p.poly([(250, 560), (310, 560), (312, 900), (262, 900)], (62, 56, 66), amp=1.0)
    p.poly([(180, 880), (262, 880), (292, 950), (176, 950)], INK, amp=0.8)
    p.poly([(256, 880), (326, 880), (356, 950), (250, 950)], INK, amp=0.8)
    # coat with tails
    p.poly([(176, 300), (330, 300), (360, 600), (330, 700), (300, 560), (250, 600), (200, 700), (160, 600)], COAT, shade_amt=0.5, sdir=(1, 1), dot=15)
    p.poly([(230, 304), (276, 304), (272, 520), (232, 520)], (248, 244, 232), amp=0.8)          # waistcoat
    p.poly([(232, 304), (276, 304), (254, 350)], CORAL, amp=0.6)                                 # cravat
    # arm raised to chin (thinking)
    p.poly([(300, 320), (350, 340), (360, 470), (400, 380), (396, 290), (352, 280)], COAT, amp=1.0)
    p.circle(380, 270, 28, SKIN, rim=0.2)
    # head
    p.circle(262, 220, 62, SKIN, shade_amt=0.4, sdir=(0.9, 0.9), dot=11)
    p.poly([(300, 214), (330, 232), (302, 250)], SKIN, amp=0.4)       # nose
    p.circle(290, 206, 6, INK, rim=0, cut=False) if False else p.ellipse((284, 200, 296, 212), INK, rim=0)
    p.poly([(206, 190), (240, 150), (212, 250)], (96, 62, 46), amp=1.0)  # hair
    # top hat
    p.poly([(190, 168), (332, 168), (318, 28), (206, 28)], INK, shade_amt=0.4, sdir=(1, 0.2), dot=12, tone=(80, 76, 84))
    p.poly([(168, 164), (354, 164), (346, 186), (176, 186)], (40, 36, 42), amp=0.8)
    p.poly([(206, 142), (320, 142), (318, 160), (208, 160)], CORAL, amp=0.6)
    im = p.done(border=12)
    return im if look > 0 else im.transpose(Image.FLIP_LEFT_RIGHT)


def wheel(d=520, seed=5):
    """A wooden carriage wheel; spokes make rotation readable."""
    R = d // 2
    S = d + 40
    p = Painter(S, S, seed)
    c = S / 2
    p.circle(c, c, R, INK, rim=0.0)
    p.circle(c, c, R - 18, WOOD, rim=0.3)
    p.circle(c, c, R - 46, (0, 0, 0), rim=0)  # placeholder cleared below
    # clear inner disc by repainting transparent
    im = p.im
    ImageDraw.Draw(im).ellipse([(c - R + 46) * SS, (c - R + 46) * SS, (c + R - 46) * SS, (c + R - 46) * SS], fill=(0, 0, 0, 0))
    for i in range(8):
        a = math.pi * i / 4
        p.line([(c, c), (c + (R - 40) * math.cos(a), c + (R - 40) * math.sin(a))], 15, shade(WOOD, 1.1), rim=0.3)
    p.circle(c, c, 34, (96, 62, 40), rim=0.3)
    p.circle(c, c, 12, INK, rim=0, cut=False)
    return p.done(border=0, crop=False)


def draisine_frame(w=1400, h=900, seed=12):
    """Beam, saddle, fork and steering bar in machine space (hubs at (260,640) and (1140,640))."""
    p = Painter(w, h, seed)
    # beam
    p.poly([(240, 600), (1150, 560), (1156, 624), (246, 664)], WOOD, shade_amt=0.4, sdir=(0.2, 1), dot=14)
    # rear fork pieces
    p.poly([(236, 640), (284, 640), (320, 420), (284, 410)], shade(WOOD, 0.85), amp=1.0)
    # saddle / seat block
    p.poly([(520, 590), (780, 580), (770, 520), (560, 516)], (120, 60, 46), shade_amt=0.4, sdir=(1, 1), dot=12)
    # steering stem + armrest cushion + handlebar
    p.poly([(1100, 600), (1150, 590), (1070, 300), (1030, 310)], shade(WOOD, 0.9), amp=1.0)
    p.poly([(900, 250), (1100, 230), (1120, 300), (920, 330)], (120, 60, 46), shade_amt=0.4, sdir=(1, 1), dot=12)    # arm cushion
    p.poly([(1040, 290), (1180, 270), (1200, 300), (1060, 322)], shade(WOOD, 0.8), amp=1.0)
    p.poly([(1110, 624), (1170, 624), (1160, 660), (1120, 660)], INK, amp=0.5)
    p.poly([(1096, 560), (1160, 560), (1170, 640), (1096, 640)], shade(WOOD, 0.8), amp=0.6)
    return p.done(border=0, crop=False)


def rider_top(w=520, h=700, seed=13):
    """Seated rider from the hips up, leaning on the arm cushion."""
    p = Painter(w, h, seed)
    COAT = (46, 70, 140)
    p.poly([(120, 420), (250, 300), (330, 330), (300, 520), (160, 560)], COAT, shade_amt=0.5, sdir=(1, 1), dot=14)
    p.poly([(90, 380), (60, 470), (150, 520), (170, 420)], COAT, amp=1.0)        # coat tail
    p.poly([(240, 300), (360, 360), (440, 340), (452, 380), (344, 424), (250, 380)], COAT, amp=1.0)  # arm forward
    p.circle(448, 362, 24, SKIN, rim=0.2)
    p.circle(284, 226, 58, SKIN, shade_amt=0.4, sdir=(0.9, 0.9), dot=11)
    p.poly([(332, 222), (360, 238), (334, 254)], SKIN, amp=0.4)
    p.ellipse((306, 208, 318, 220), INK, rim=0)
    p.poly([(230, 196), (262, 156), (234, 250)], (96, 62, 46), amp=1.0)
    p.poly([(208, 174), (344, 174), (334, 40), (222, 40)], INK, shade_amt=0.4, sdir=(1, 0.2), dot=12, tone=(80, 76, 84))
    p.poly([(190, 170), (366, 170), (358, 192), (198, 192)], (40, 36, 42), amp=0.8)
    p.poly([(222, 150), (334, 150), (332, 166), (224, 166)], CORAL, amp=0.6)
    return p.done(border=0, crop=False)


def leg(w=170, h=560, seed=14):
    """One leg, hip at top-centre (for a swinging pivot)."""
    p = Painter(w, h, seed)
    p.poly([(40, 10), (130, 10), (112, h - 90), (60, h - 90)], (58, 52, 64), shade_amt=0.4, sdir=(1, 0.2), dot=12)
    p.poly([(52, h - 100), (126, h - 100), (150, h - 30), (160, h - 10), (40, h - 10), (46, h - 50)], INK, amp=0.8)
    return p.done(border=0, crop=False)


def hills(w=1400, h=520, colors=((84, 150, 90), (60, 128, 96)), seed=3):
    p = Painter(w, h, seed)
    rnd = random.Random(seed)
    pts = [(0, h)]
    x = 0
    while x < w:
        pts.append((x, h * rnd.uniform(0.35, 0.65)))
        x += rnd.randint(140, 260)
    pts += [(w, h * 0.5), (w, h)]
    p.poly(pts, colors[0], shade_amt=0.35, sdir=(0.6, 1), dot=18)
    return p.done(border=0, crop=False)


def pine(w=300, h=560, color=(40, 112, 88), seed=1):
    p = Painter(w, h, seed)
    p.poly([(w / 2 - 22, h - 120), (w / 2 + 22, h - 120), (w / 2 + 22, h), (w / 2 - 22, h)], (96, 62, 44), amp=0.6)
    for i, (yy, ww) in enumerate([(h - 110, w * 0.92), (h - 260, w * 0.74), (h - 400, w * 0.52)]):
        p.poly([(w / 2 - ww / 2, yy), (w / 2 + ww / 2, yy), (w / 2, yy - h * 0.34)], color, shade_amt=0.45, sdir=(1, 0.6), dot=13)
    return p.done(border=8, crop=False)


def signpost(text="MANNHEIM", w=620, h=640, seed=4):
    p = Painter(w, h, seed)
    p.poly([(w / 2 - 20, 150), (w / 2 + 20, 150), (w / 2 + 20, h), (w / 2 - 20, h)], (110, 76, 52), amp=0.6)
    p.poly([(30, 40), (w - 90, 40), (w - 20, 100), (w - 90, 160), (30, 160)], (252, 250, 244), amp=1.0, rim=0.25)
    p.text((w / 2 - 36, 100), text, 76, INK, anchor="mm")
    return p.done(border=10, crop=False)


def clock(d=520, angle=0.0, seed=2, sweep=None):
    """Wall clock; `angle` rotates the minute hand (radians, 0 = 12 o'clock, clockwise)."""
    R = d // 2
    S = d + 80
    p = Painter(S, S, seed)
    c = S / 2
    p.circle(c, c, R, INK, rim=0)
    p.circle(c, c, R - 20, (252, 250, 244), rim=0.2)
    for i in range(12):
        a = math.pi * 2 * i / 12
        L = 40 if i % 3 == 0 else 22
        p.line([(c + (R - 34) * math.sin(a), c - (R - 34) * math.cos(a)), (c + (R - 34 - L) * math.sin(a), c - (R - 34 - L) * math.cos(a))], 9, INK, rim=0, cut=False) if False else p.line([(c + (R - 34) * math.sin(a), c - (R - 34) * math.cos(a)), (c + (R - 34 - L) * math.sin(a), c - (R - 34 - L) * math.cos(a))], 9, INK, rim=0)
    # hour hand fixed pointing at 12 - a sweep shows "about an hour"
    p.line([(c, c), (c, c - R * 0.42)], 20, INK, rim=0.1)
    p.line([(c, c), (c + R * 0.74 * math.sin(angle), c - R * 0.74 * math.cos(angle))], 12, CORAL, rim=0.1)
    p.circle(c, c, 20, INK, rim=0)
    return p.done(border=10)


def bicycle(w=1500, h=900, frame=COBALT, seed=21):
    """Modern safety bicycle (diamond frame), facing right. Wheels are returned inside the image."""
    p = Painter(w, h, seed)
    R = 300
    rx, fx, cy = 330, 1170, 580
    for cx_ in (rx, fx):
        p.circle(cx_, cy, R, INK, rim=0)
        p.circle(cx_, cy, R - 16, (0, 0, 0), rim=0)
    im = p.im
    for cx_ in (rx, fx):
        ImageDraw.Draw(im).ellipse([(cx_ - R + 16) * SS, (cy - R + 16) * SS, (cx_ + R - 16) * SS, (cy + R - 16) * SS], fill=(0, 0, 0, 0))
    for cx_ in (rx, fx):
        for i in range(12):
            a = math.pi * i / 6
            p.line([(cx_, cy), (cx_ + (R - 14) * math.cos(a), cy + (R - 14) * math.sin(a))], 4, (210, 206, 200), rim=0)
        p.circle(cx_, cy, 22, INK, rim=0)
    bb = (700, 600)                    # bottom bracket
    seat = (600, 300)
    head = (1020, 310)
    def tube(a, b, wd=36, col=frame):
        p.line([a, b], wd, col, rim=0.25)
    tube((rx, cy), bb); tube((rx, cy), seat); tube(bb, seat); tube(seat, head); tube(bb, head, 40)
    tube(head, (fx, cy)); tube((head[0] - 10, head[1] - 20), (head[0] + 40, head[1] - 140), 22, (60, 56, 64))
    p.line([(head[0] - 10, head[1] - 150), (head[0] + 130, head[1] - 130)], 16, INK, rim=0)
    p.poly([(seat[0] - 90, seat[1] - 50), (seat[0] + 70, seat[1] - 56), (seat[0] + 60, seat[1] - 20), (seat[0] - 70, seat[1] - 10)], (124, 60, 46), amp=0.8)
    p.line([(seat[0] + 4, seat[1] - 10), (seat[0] - 4, seat[1] - 40)], 14, (60, 56, 64), rim=0)
    p.line([(bb[0] - 90, bb[1] + 40), (bb[0] + 90, bb[1] - 40)], 14, (60, 56, 64), rim=0)
    p.circle(bb[0], bb[1], 30, (200, 196, 190), rim=0.2)
    p.poly([(bb[0] + 70, bb[1] - 50), (bb[0] + 150, bb[1] - 50), (bb[0] + 150, bb[1] - 30), (bb[0] + 70, bb[1] - 30)], INK, amp=0.3)
    return p.done(border=12)


def marker_stroke(pts, progress, width=22, color=RED, canvas=None, seed=1):
    """Thick marker line drawn on to `progress` (0..1), with a slightly wobbly path. Returns (img, (x0, y0))."""
    rnd = random.Random(seed)
    pts = list(pts)
    # arc-length param
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    tot = L[-1]
    target = tot * max(0.0, min(1.0, progress))
    out = [pts[0]]
    for i in range(1, len(pts)):
        if L[i] <= target:
            out.append(pts[i])
        else:
            seg = (target - L[i - 1]) / max(1e-6, L[i] - L[i - 1])
            out.append((pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * seg, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * seg))
            break
    xs = [p[0] for p in out]; ys = [p[1] for p in out]
    pad = width + 6
    x0, y0 = int(min(xs) - pad), int(min(ys) - pad)
    W, H = int(max(xs) + pad - x0), int(max(ys) + pad - y0)
    im = Image.new("RGBA", (max(W, 2) * 2, max(H, 2) * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = [((x - x0) * 2, (y - y0) * 2) for x, y in out]
    if len(P) >= 2:
        d.line(P, fill=color + (235,), width=int(width * 2), joint="curve")
        r = width
        for x, y in (P[0], P[-1]):
            d.ellipse([x - r, y - r, x + r, y + r], fill=color + (235,))
    im = im.resize((max(W, 2), max(H, 2)), Image.LANCZOS)
    return im, (x0, y0)
