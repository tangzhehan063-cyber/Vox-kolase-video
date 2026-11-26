#!/usr/bin/env python3
"""Draw every sprite once and cache to assets/sprites/*.png (+ meta.json)."""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = f"{HERE}/assets/sprites"
os.makedirs(OUT, exist_ok=True)


def job(name):
    from sprites_a import globe, volcano, ash_cloud, sun, thermometer, snowflake, calendar, pin, question_card, year_tag
    from sprites_b import (oat_sheaf, bucket, horse, horse_head, stable, drais_standing, wheel, draisine_frame,
                           rider_top, leg, hills, pine, signpost, clock, bicycle, CHESTNUT, GREYHORSE, BLACKHORSE)
    from sprites_c import pedal, walker, flash, rock, bubble, dust, dim_sun, road_strip
    from paperkit import COBALT, CREAM, CORAL, ASH1, ASH2, ASH3
    meta = {}
    table = {
     "globe": lambda: globe(),
     "volcano": volcano, "sun": sun, "dim_sun": dim_sun, "calendar": calendar, "pin": pin,
     "q_card": question_card, "snow": snowflake,
     "ash1": lambda: ash_cloud(620, 400, ASH1, 1), "ash2": lambda: ash_cloud(560, 360, ASH2, 2, puffs=7),
     "ash3": lambda: ash_cloud(520, 330, ASH3, 3, puffs=7), "ash4": lambda: ash_cloud(760, 460, ASH1, 4, puffs=9),
     "oat_gold": oat_sheaf, "oat_dead": lambda: oat_sheaf("dead"), "bucket": bucket,
     "horse": horse, "horse_grey": lambda: horse(color=GREYHORSE, seed=3), "horse_black": lambda: horse(color=BLACKHORSE, seed=4),
     "head_chest": lambda: horse_head(CHESTNUT), "head_grey": lambda: horse_head(GREYHORSE, seed=3),
     "head_black": lambda: horse_head(BLACKHORSE, seed=4),
     "stable": lambda: stable(), "drais": drais_standing, "wheel": wheel, "frame": draisine_frame,
     "rider": rider_top, "leg": leg, "hills_a": lambda: hills(1400, 520, ((84, 150, 90),)),
     "hills_b": lambda: hills(1400, 420, ((60, 128, 96),), 8), "pine": pine,
     "pine2": lambda: pine(color=(84, 150, 90), seed=2), "sign": signpost, "clock": clock, "bike": bicycle,
     "pedal": pedal, "walker": walker, "flash": flash, "bubble": bubble, "dust": dust, "road": road_strip,
     "tag1815": lambda: year_tag("1815"), "tag1816": lambda: year_tag("1816"), "tag1817": lambda: year_tag("1817"),
     "tag_tambora": lambda: year_tag("TAMBORA", 640, 170),
    }
    r = table[name]()
    if isinstance(r, tuple):
        img, m = r
        meta[name] = m
    else:
        img = r
    img.save(f"{OUT}/{name}.png")
    return name, img.size, meta


def tall_names():
    return ["globe", "volcano", "sun", "dim_sun", "calendar", "pin", "q_card", "snow", "ash1", "ash2", "ash3", "ash4",
            "oat_gold", "oat_dead", "bucket", "horse", "horse_grey", "horse_black", "head_chest", "head_grey", "head_black",
            "stable", "drais", "wheel", "frame", "rider", "leg", "hills_a", "hills_b", "pine", "pine2", "sign", "clock",
            "bike", "pedal", "walker", "flash", "bubble", "dust", "road", "tag1815", "tag1816", "tag1817", "tag_tambora"]


if __name__ == "__main__":
    t = time.time()
    meta = {}
    with ProcessPoolExecutor(4) as ex:
        for name, size, m in ex.map(job, tall_names()):
            meta.update(m)
            print(f"{name:12s} {size}")
    json.dump(meta, open(f"{HERE}/assets/meta.json", "w"), indent=1)
    print("built in", round(time.time() - t, 1), "s")
