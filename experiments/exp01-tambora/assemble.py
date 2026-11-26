#!/usr/bin/env python3
"""Mux audio onto the silent render.

  no VO files in audio/vo/   -> TEMPORARY music bed only  -> out/tambora_TEMP_audio.mp4   (placeholder, not final)
  audio/vo/beat_NN.* present -> each beat placed at its timing.json start, music ducked under it,
                                master -14 LUFS            -> out/tambora_final.mp4

The music bed (audio/music_temp.wav) is a synthesised placeholder from the vox-skill generator
(skills/vox-skill/scripts/score.py, run unmodified). Replace the file and re-run to swap it.
"""
import glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f"{HERE}/timing.json"))
video = sys.argv[1] if len(sys.argv) > 1 else f"{HERE}/out/tambora_silent.mp4"   # pass out/tambora_captioned.mp4 for the captioned cut
music = f"{HERE}/audio/music_temp.wav"
vo = []
for b in T["beats"]:
    hit = [h for h in sorted(glob.glob(f"{HERE}/audio/vo/beat_{b['id']:02d}.*")) if h.split(".")[-1] in ("wav", "mp3", "m4a")]
    if hit:
        vo.append((hit[0], b["start"]))
dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", video], text=True).strip()
dur = float(dur)
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", music]
for f, _ in vo:
    cmd += ["-i", f]
fade = f"afade=t=in:d=1.5,afade=t=out:st={dur-2.0:.2f}:d=2.0"
if vo:
    parts = []
    for i, (_, st) in enumerate(vo):
        parts.append(f"[{i+2}:a]adelay={int(st*1000)}|{int(st*1000)},apad[v{i}]")
    mix = "".join(f"[v{i}]" for i in range(len(vo)))
    parts.append(f"{mix}amix=inputs={len(vo)}:normalize=0:duration=longest,atrim=0:{dur:.2f}[vo]")
    parts.append("[vo]asplit=2[vo1][vo2]")
    parts.append(f"[1:a]volume=0.55,{fade}[m]")
    parts.append("[m][vo1]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md]")
    parts.append("[md][vo2]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    out = f"{HERE}/out/tambora_final.mp4" if "captioned" not in video else f"{HERE}/out/tambora_captions_final.mp4"
else:
    parts = [f"[1:a]volume=0.8,{fade},loudnorm=I=-16:TP=-1.5:LRA=11[a]"]
    out = f"{HERE}/out/tambora_TEMP_audio.mp4" if "captioned" not in video else f"{HERE}/out/tambora_captions_TEMP_audio.mp4"
cmd += ["-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]
subprocess.check_call(cmd)
print("wrote", out, "(VO beats:", len(vo), ")")
