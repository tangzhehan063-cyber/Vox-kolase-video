# exp01-tambora — "The Volcano Behind the Bicycle"

60-second 9:16 paper-collage explainer built with the vox-editorial engine (see `NOTES.md`).
**Video: `video/tambora_60s_TEMP_audio.mp4`** (placeholder music, no voice-over yet).

```bash
python3 build_assets.py          # draw sprites -> assets/sprites (7 s)
./make_temp_music.sh             # placeholder music bed
python3 timing.py                # clock from script.json (estimate) or audio/vo
python3 render.py --preview      # 540x960, ~30 s
python3 render.py --final        # 1080x1920, ~90 s on 4 cores
python3 assemble.py              # mux audio
python3 qc_grid.py out.png 1 5 9 # contact sheet of stills at those seconds
```
Docs: `RESEARCH.md` · `SCRIPT.md` · `STORYBOARD.md` · `NOTES.md`.
Fonts in `fonts/` (Anton, Figtree) are SIL Open Font License.
