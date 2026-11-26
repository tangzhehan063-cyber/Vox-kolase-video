#!/bin/sh
# Placeholder music bed (NOT final). Uses the vox-skill generator unmodified; ~11 MB wav, so it is git-ignored.
cd "$(dirname "$0")" && python3 ../../skills/vox-skill/scripts/score.py audio/music_temp.wav --seconds 64 --key D --bpm 72
