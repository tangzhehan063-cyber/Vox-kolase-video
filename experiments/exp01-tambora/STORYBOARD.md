# Storyboard — "The Volcano Behind the Bicycle" (9:16, 1080×1920, 30 fps, ~63 s)

Durations are **estimates** (words ÷ 2.7 wps + 0.35 s pause). They come from `timing.json`;
every cue below is expressed as a fraction of a beat so it moves when real audio replaces the estimate.
Eight scenes for ten beats: scenes 5 and 6 each carry two beats and evolve inside one composition.

Depth planes follow the engine (0.05 ground … 1.15 headline): BG = 0.05–0.45, MID = 0.5–0.8, FG = 0.9–1.15.

| # | Time (est.) | Beat(s) / narration | Ground | Main visual | Supporting objects | Depth layers | Main motion | Transition out |
|---|---|---|---|---|---|---|---|---|
| S1 | 0.0–7.8 | 1 · "A volcano erupts in one corner of the world. Two years later, in another, a man gives up on horses." | cobalt | Paper globe (orthographic, Indonesia lower-right, Germany upper-left) with a volcano erupting on it **in the first 0.3 s** | ash plume, flying rocks, flash star, tiny stable + horse at Germany, "2 YEARS LATER" tag, dashed arc + "?" card | BG clippings/tape · MID globe · FG volcano, plume, confetti | eruption pop + camera shake; globe slow push; red marker X over the horse; dashed arc grows between the two corners | torn-paper diagonal wipe |
| S2 | 7.8–13.7 | 2 · "April, eighteen fifteen. Tambora, in Indonesia, blows apart. The most powerful eruption in recorded history." | coral | Giant paper volcano rising from the bottom edge, plume stacking upward | "APRIL 1815" torn banner, "VEI 7" numeral, "TAMBORA · INDONESIA" tag, lava, rocks | BG ridge clippings · MID volcano · FG plume puffs, rocks | camera tilts **up** with the plume; plume puffs grow in a staggered cascade | ash-cloud rise (grey cloud edge sweeps up) |
| S3 | 13.7–18.5 | 3 · "Ash and sulphur wrap the whole Earth. Sunlight dims. The planet cools." | steel grey | Globe wrapped by ash-cloud bands (some in front, some behind) | sun that dims and is eaten by a cloud, falling thermometer | BG sun · MID globe · FG cloud bands, thermometer | clouds orbit/slide across the globe; sun cross-fades to dim; mercury drops | push left (torn strip edge) |
| S4 | 18.5–23.3 | 4 · "Eighteen sixteen becomes the year without a summer. Harvests fail across Europe." | cream | Torn desk calendar "1816", JUN/JUL/AUG | snowflakes land on each month, "NO SUMMER" banner slapped across, dim sun, dead oat sheaves | BG dim sun, clippings · MID calendar · FG banner, oat sheaves | calendar drops in with bounce; snowflakes stamp one by one; dead sheaves slide in | page-drop (A falls away) |
| S5 | 23.3–36.9 | 5+6 · oats run short, horses starve, **Drais looks at the empty stables and asks "what if you didn't need a horse?"** | marigold | Barn front with 3 stalls, horse heads peeking out → heads sink away leaving dark empty stalls; then Drais steps in from the left | healthy oat sheaf → grey dead sheaf, bucket, "OATS" banner, "KARL DRAIS" banner, thought bubble with "?" then a **wheel** | BG clippings · MID stable, bucket, sheaf · FG Drais, bubble | heads sink in stagger; sheaf swaps state; Drais enters + stable shrinks back; wheel pops into bubble and spins | **iris** opening from the wheel |
| S6 | 36.9–50.2 | 7+8 · "In eighteen seventeen he builds a wooden machine. Two wheels. No pedals. You push the ground away with your feet. He rides it out of Mannheim, faster than anyone can walk. No oats required." | teal | The machine is **assembled from parts** (frame drops, two wheels spin in, rider lands), marker rings the wheels, a crossed-out pedal; then rides away on a scrolling road | "1817" numeral, legs pushing, hills + pines scrolling at three speeds, "MANNHEIM" signpost passing, walker left behind, crossed-out oat bucket | BG hills · MID pines, sign · FG machine, dust, road dashes | parts fly in; legs swing; wheels roll; world scrolls left at depth-dependent speeds | torn-paper wipe from the left |
| S7 | 50.2–55.7 | 9 · "Historians still argue about the famine's role. But the timing is hard to ignore." | cream | Three paper tags 1815 / 1816 / 1817 on a zig-zag, each with a mini icon (volcano, snowflake, wheel) | two "?" cards wobbling (the argument), red marker line linking the tags, big marker loop | BG clippings · MID tags · FG ? cards, marker | tags stamp in; marker connects them then loops all three | iris from the 1817 tag |
| S8 | 55.7–62.4 (+0.6 hold) | 10 · "That machine is the ancestor of every bicycle. A reply to a volcano, twelve thousand kilometres away." | cobalt | Draisine → arrow → modern bicycle rolling in; globe above with a dashed route Tambora → Mannheim and a **12,000 KM** counter | "FROM ASH TO WHEELS" banner, pins | BG clippings · MID globe · FG draisine, bicycle, banner | bicycle rolls in; route draws; counter climbs; final hold | — |

## Variety check (anti-slideshow)
- Eight different compositions; grounds rotate cobalt → coral → steel → cream → marigold → teal → cream → cobalt.
- Motion vocabulary changes per scene: marker drawing (S1, S6, S7), camera tilt (S2), orbiting layers (S3), stamp/drop (S4), staged exit + entrance (S5), assembly + scrolling parallax (S6), tag zig-zag (S7), route + counter (S8).
- Five transition types: torn wipe, ash-cloud rise, push, page drop, iris.
- Typography is a composition element: ≤ 1–2 torn banners per scene, never a subtitle strip. Captions are intentionally **not** burned in yet (they depend on the final Gemini timing).

## Swap-in plan for Gemini TTS
1. Put `beat_01.wav … beat_10.wav` in `audio/vo/` (optional `beat_NN.words.json`).
2. `python3 timing.py` rewrites `timing.json` from the real durations.
3. `python3 render.py --final` re-renders; then `./assemble.sh` muxes VO + the (temporary) music bed.
