# Experiment 01 — notes: process, render, evaluation

Output: `video/tambora_60s_TEMP_audio.mp4` (1080×1920, 30 fps, 63.1 s, H.264 + **placeholder** music, no voice-over).
Quick look: `video/preview_540x960.mp4`, `docs/overview_every_2s.jpg`, `docs/first_and_last_frame.jpg`.

## What was and was not touched
- New folder only: `experiments/exp01-tambora/`. No skill, example or repo file was edited or deleted.
- Nothing was written to `~/.claude/skills` (an attempt to put fonts there was refused, correctly — fonts live in `./fonts`).
- Engine code is **imported unchanged** (`library/paper.py`). Its font paths are redirected at import time in `paperkit.py`.
- No voice-over was generated (no Edge TTS, no other provider). No image-model credits were spent.

## 1. Audit — verified, not assumed
Environment: ffmpeg 6.1.1, Python 3.13, numpy 2.5, Pillow 13, 4 vCPU. `edge-tts` is not installed (not needed here).

| Item | Finding |
|---|---|
| Which engine? | `vox-editorial` (Python + ffmpeg, 1080×1920, paper collage, depth planes). `vox-skill` is Remotion, mostly 16:9 and macOS-only for its cut-out step. |
| `library/paper.py` | **Works** once fonts exist. Grounds, torn banners, tape, newsprint, confetti, word stickers are good and free. |
| Fonts | **Broken by default**: `paper.py` reads `~/.claude/skills/editorial-carousel/references/fonts/` (another skill, absent). Fixed locally with Anton + Figtree (SIL OFL) in `./fonts`. |
| Sprite pipeline (`sprite_sheets.py`, `chroma_sprites.py`) | **Not runnable here**: needs an external image model (`nano_banana_pro`). Not exercised. |
| `library/sprites` | 18 sprites, all from the infinite-scroll film (hands, phones, pages). None fit this topic. |
| `references/multiplane.py` | `render()` works, but every entrance happens in the first ~1 s and then layers only drift; one slow camera push; `__main__` needs a `scene` module and `audio/vo_durations.json` that are not in the repo. Cannot place events on narration cues → insufficient for this brief. |
| `kinetic_overlays.py`, `auto_elements.py`, `lift_cutouts.py`, `element_motion.py`, `real-subject-cutouts` | **Not exercised.** Overlays emit PNG sequences; cut-out lifting uses a macOS Swift tool. |
| `SKILL.md` mentions `fastcut-ad` | Not in this repo. |

Decision: reuse `paper.py` and the multiplane *model* (depth → parallax/drift/draw order, back-overshoot easing, per-layer phase), but add an **experiment-local timeline compositor** (`render.py`). This is the one place I went beyond "use what exists", and only because multiplane cannot do timed, keyframed scenes.

## 2. Topic and research
Tambora (1815) → year without a summer (1816) → fodder shortage → Drais's *Laufmaschine* (1817). Chosen for a built-in reversal (a bicycle owes something to a volcano), strong objects, and a hook that withholds the subject.
Claims, sources, and what was dropped: `RESEARCH.md`. Key honesty point: the causal chain is a hypothesis, so beat 9 says so.

## 3. Pipeline (all in this folder)
```
script.json ──► timing.py ──► timing.json ──► scenes.py (cues = beat + fraction) ──► render.py ──► out/tambora_silent.mp4
audio/vo/beat_NN.wav (later) ─┘                                                       assemble.py ──► video/*.mp4
```
| File | Role |
|---|---|
| `paperkit.py`, `sprites_a/b/c.py`, `build_assets.py` | locally drawn paper-cut subjects (supersampled polygons, grain, halftone shading, darker rim, white sticker border); 44 PNGs in `assets/sprites/`, built in ~7 s |
| `render.py` | timed layers, keyframes, pivots, scroll, dynamic layers, 5 transitions, 4-process frame ranges |
| `scenes.py` | 8 scenes, 288 layers, marker strokes / dotted route / thermometer / counter as per-frame layers |
| `timing.py` | the clock: estimate from word count **or** measured from audio |
| `assemble.py` | mux; with VO: beats placed at their start, music side-chain ducked, master −14 LUFS |

### Render notes
- 1893 frames, 30 fps. Preview 540×960: **28 s**. Final 1080×1920: **~90 s** on 4 processes, x264 CRF 17 (33 MB silent).
- Frame ranges render independently, so cost scales with cores.
- Review loop: stills per scene → contact sheets → fixes → full preview → per-second motion energy and cut-spike scan → transition frames → 1:1 crops of the final.
- I reviewed stills, sheets, transition frames and metrics; I did **not** watch it as live playback or listen to the audio.

### Verified behaviours
- Swap-in test: 10 fake VO files with random durations → `timing.py` re-clocked every scene (total 62.4 → 63.9 s), stills rendered, `assemble.py` built the ducked mix. Test files removed and `timing.json` restored.
- Final loudness of the temporary mix: −14.1 LUFS, peak −1.5 dBFS (placeholder music only).

## 4. Swapping in Gemini TTS
1. One file per beat: `audio/vo/beat_01.wav … beat_10.wav` (optional `beat_NN.words.json` as `[[word, start, end], …]`).
2. `python3 timing.py`
3. `python3 render.py --final`  (re-render is required: scene lengths and cues change)
4. `python3 assemble.py`  → `out/tambora_final.mp4`
Cues are fractions of each beat, so a slower or faster read just stretches the scenes. If Gemini's total differs a lot (> ~10 %), re-check the end of S6 (the ride) and S8 (the counter) first.
Replace the music by overwriting `audio/music_temp.wav` (regenerate with `./make_temp_music.sh`).

## 5. Evaluation — honest
**Works well**
- The depth/parallax model reads as space; `paper.py` pieces (grain, torn banner, tape, clippings) give the right register for free.
- The assembly beat (S6: frame drops, wheels spin in, rider lands, marker rings the wheels, crossed-out pedal, then the road scrolls at three speeds) is the strongest sequence: it explains a mechanism instead of showing a picture.
- Staged exits carry meaning (S5: horses sink out of the stalls, leaving empty openings, then the thinker walks in).
- Variety: 8 grounds/compositions, 5 transition types, motion vocabulary changes per scene. No scene is a zoom on a still.
- Hook has a visual in the first 0.1 s and the eruption lands within 0.5 s.
- Speed: a full 1080×1920 render in 90 s makes iteration cheap.

**Weak in this video**
- Subjects are flat geometric paper shapes. Horse heads, the horse and Drais are charming but plain next to image-model illustrations or real photographs; this is the biggest quality gap.
- Globe continents are coarse (hand-simplified outlines); Europe/Indonesia read, details do not.
- The eruption plume is a stack of the same cloud shapes; it reads as a column, not a convincing plume.
- Rider and machine are approximate: stiff legs, hands not exactly on the arm cushion.
- Some scenes have a dead lower third (S3, parts of S4/S7) and long calm holds; motion metrics show ~0.5–1 (of 12) energy in those seconds, driven only by drift/breath.
- No captions, no sound design: sound is placeholder music only.
- Timing is an estimate. Cues near the end of a beat can fall inside the 0.6–0.8 s transition and be hidden; I moved a few earlier, but real audio may need the same check.

**Engine: good / lacking / next**
- *Good:* paper elements, depth model, library/manifest idea, per-beat clock design.
- *Lacking:* sprite stage depends on an unavailable model; fonts path points to a missing skill; multiplane has no timed events; example `__main__` not self-contained; no transition library; no captions step for this skill; docs describe more than runs offline.
- *Next:*
  1. Promote the compositor (`render.py`) into the skill as `timeline.py` with the transitions, once a second film confirms the API.
  2. Add a local sprite fallback kit (`paperkit.py`) so films can be built without an image model, and let it feed `library/`.
  3. Word-level cues from TTS timestamps instead of beat fractions.
  4. Caption PNGs from the same timing file.
  5. Try real public-domain photo cut-outs for people/places (not attempted here).
  6. A leaner plume/crowd generator, and a figure rig with proper limbs.
  7. A `--check` that flags cues inside transition windows and dead zones from the motion metric.
