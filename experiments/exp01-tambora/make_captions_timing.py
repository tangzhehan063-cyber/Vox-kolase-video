#!/usr/bin/env python3
"""Build overlay/vo/timing.json (vox-skill schema) + overlay/src/shared/captions.ts from OUR timing.json.

Word times are ESTIMATED (weighted by letters, extra weight on punctuation) inside each beat's speech window.
Run this again after Gemini VO lands (timing.py first): beat windows become real, word times stay approximate
until a forced alignment (or TTS word timestamps in audio/vo/beat_NN.words.json) is available.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f"{HERE}/timing.json"))
S = {b["id"]: b for b in json.load(open(f"{HERE}/script.json"))["beats"]}
FPS = 30
beats = {}
for b in T["beats"]:
    text = S[b["id"]]["text"]
    toks = text.split()
    w = []
    for t in toks:
        core = re.sub(r"[^A-Za-z0-9']", "", t)
        weight = len(core) + 1.5
        pause = 6.0 if re.search(r"[.!?]$", t) else (3.0 if re.search(r"[,;:]$", t) else 0.0)
        w.append((t, weight, pause))
    total = sum(x[1] + x[2] for x in w)
    words, cur = [], 0.0
    real = b.get("word_times")
    for i, (t, wt, pa) in enumerate(w):
        if real and len(real) == len(w):                      # TTS-provided word timestamps win
            ws, we = real[i][1], real[i][2]
            words.append({"w": t, "t": round(ws, 3), "d": round(we - ws, 3)})
            continue
        d = b["speech"] * wt / total
        words.append({"w": t, "t": round(cur, 3), "d": round(d, 3)})
        cur += d + b["speech"] * pa / total
    beats[str(b["id"])] = {
        "narration": text, "start": b["start"], "end": round(b["start"] + b["speech"], 3),
        "duration": round(b["speech"], 3), "startFrame": round(b["start"] * FPS),
        "endFrame": round((b["start"] + b["speech"]) * FPS), "frames": round(b["speech"] * FPS), "words": words}
total_frames = round((T["total"] + 0.7) * FPS)
os.makedirs(f"{HERE}/overlay/vo", exist_ok=True)
json.dump({"voice": "ESTIMATE (no audio yet)", "rate": "n/a", "gap": 0.35, "fps": FPS, "totalDuration": T["total"],
           "totalFrames": total_frames, "beats": beats}, open(f"{HERE}/overlay/vo/timing.json", "w"), indent=1)
open(f"{HERE}/overlay/src/shared/meta.ts", "w").write(f"export const TOTAL_FRAMES = {total_frames};\n")
subprocess.check_call([sys.executable, f"{HERE}/../../skills/vox-skill/scripts/captions.py", "--words", "4", "--maxchars", "24"], cwd=f"{HERE}/overlay")
print("timing source:", {b['source'] for b in T['beats']}, "frames", total_frames)
