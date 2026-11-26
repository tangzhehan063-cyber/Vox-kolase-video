#!/usr/bin/env python3
"""The clock. Writes timing.json from script.json.

* No audio yet  -> beat length = words / wps + pause   (ESTIMATE, flagged "estimate")
* audio/vo/beat_NN.(wav|mp3|m4a) present -> measured with ffprobe (flagged "audio")

Swap in the Gemini TTS files, run `python3 timing.py`, re-render. Scenes, cues and
transitions all derive from this file, so nothing else needs to change.
Per-word timestamps (if the TTS provides them) can be dropped in
audio/vo/beat_NN.words.json as [[word, start_s, end_s], ...]; cues use them when present.
"""
import glob, json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "default=nw=1:nk=1", path], text=True)
    return float(out.strip())


def build():
    s = json.load(open(f"{HERE}/script.json"))
    wps, pause = s["wps_estimate"], s["pause_between_beats_s"]
    t, beats, scenes = 0.0, [], {}
    for b in s["beats"]:
        words = re.findall(r"[A-Za-z']+", b["text"])
        hit = sorted(glob.glob(f"{HERE}/audio/vo/beat_{b['id']:02d}.*"))
        hit = [h for h in hit if h.split(".")[-1] in ("wav", "mp3", "m4a")]
        if hit:
            speech, src = probe(hit[0]), "audio"
        else:
            speech, src = len(words) / wps, "estimate"
        dur = speech + pause
        wj = f"{HERE}/audio/vo/beat_{b['id']:02d}.words.json"
        rec = dict(id=b["id"], scene=b["scene"], start=round(t, 3), dur=round(dur, 3),
                   speech=round(speech, 3), words=len(words), source=src,
                   word_times=json.load(open(wj)) if os.path.exists(wj) else None)
        beats.append(rec)
        sc = scenes.setdefault(b["scene"], dict(start=t, end=t + dur, beats=[]))
        sc["end"] = t + dur
        sc["beats"].append(b["id"])
        t += dur
    out = dict(total=round(t, 3), beats=beats,
               scenes={k: dict(v, start=round(v["start"], 3), end=round(v["end"], 3))
                       for k, v in scenes.items()})
    json.dump(out, open(f"{HERE}/timing.json", "w"), indent=1)
    return out


if __name__ == "__main__":
    o = build()
    print(f"total {o['total']:.1f}s", {b['id']: b['source'] for b in o['beats']})
    for k, v in o["scenes"].items():
        print(f"  {k}: {v['start']:6.2f} -> {v['end']:6.2f}  ({v['end']-v['start']:.1f}s) beats {v['beats']}")
