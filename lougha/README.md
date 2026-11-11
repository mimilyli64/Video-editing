# Lougha Online — "The Roots"

A brand film built entirely in code: a Python renderer (NumPy, Pillow, OpenCV) with a real perspective camera.
It runs 19.2 s plus a 2 s end card at 60 fps, in 16:9 (1920×1080) and a rebuilt 9:16 (1080×1920).
The camera flies continuously through the whole film, with no hard cuts.

## Deliverables (`out/`)

| File | |
|---|---|
| `Lougha_TheRoots_16x9_60fps.mp4` | 1920×1080, 60 fps, H.264 + AAC 320k |
| `Lougha_TheRoots_9x16_60fps.mp4` | 1080×1920, 60 fps, re-laid-out vertical |
| `mix.wav` | master, 48 kHz / 24-bit, −14 LUFS integrated, ≤ −1.25 dBTP |
| `cue_sheet.csv` | every sound cue with its time and 60 fps frame |
| `BRIEF_FRAMES.md` | the beat sheet, fixed hits and voice-locked hits in frames |

## Build

```bash
pip install numpy pillow opencv-python-headless scipy fonttools pyloudnorm piper-tts faster-whisper
python3 -m lougha.vo                 # 1. voice first: 2 takes, keep the word-perfect one, cut at its pauses
python3 -m lougha.render --fmt h     # 2. picture 16:9  (locked to build/vo_timing.json)
python3 -m lougha.render --fmt v     #    picture 9:16
python3 -m lougha.audio              # 3. music + sound design + mix/master
python3 -m lougha.master             # 4. mux + BRIEF_FRAMES.md
# previews
python3 -m lougha.render --fmt h --scale .5 --stills 0.2,4.3,8.7,16.8
python3 -m lougha.render --fmt v --scale .5 --preview
```

## How it is built

- **One root renderer.** `engine/world.py: Root.draw` is the only function that draws a root. That covers the seed root, the path through the world, the underlines, the progress roots, the tree's own roots, the voice waveform, the language and skill branches, and the tagline baseline. Each root is three braided purple strands with tube shading, curling rootlets, a lavender glow, travelling light pulses and a bright growing tip.
- **The mascot.** `engine/tree.py` rebuilds the logo's tree in 3D from the logo's own pixel layout. It keeps the six flag fruits, gets purple, violet and lavender modelled leaves, a purple bark trunk with golden bounce light, and the golden open book at its base. Every branch bends on its own damped spring. That drives the squash-and-stretch landings, the delayed whip of the branches, leaf flutter, the gesture before the dive, and the happy bounce on the beat.
- **Stations.** Each educational station is a flat textured plane with a home pose that maps 1:1 onto the screen, so type is pixel-sharp when the camera arrives. In between, the camera flies a Catmull-Rom path, with depth of field, adaptive temporal motion blur (1–6 samples per frame from on-screen speed), bloom, vignette and grain.
- **9:16** is a re-layout, not a crop. Every station has its own vertical composition: stacked video tiles, a 2×2 skill grid, three-line tagline, flags in a triangle, the tree above the progress card. The camera is reframed for the vertical format.
- **Voice first.** `vo.py` generates two takes of the whole script as one read, transcribes both and keeps the word-perfect take. It cuts only at the take's own pauses, places each phrase on its anchor, and writes the onset of every picture-driving word to `build/vo_timing.json`. The renderer and the cue sheet read their language, skill, tagline and logo hits from that file.
- **Music** is original and synthesized in code: 100 BPM in D major, with mallet plucks, felt keys and a round sub. It follows the brief's arc, including the kick/clap/shaker drop at 7.20, a softer bed under the call, the lift at 11.40, a breath at 16.50 with only a reversed swell, and a full chord with a low hit at 16.80 ringing under the end card.
- **Lougha sonic identity**, all original:
  - `lougha_success` (4.23 and 8.70): a warm A5→D6 bell lift.
  - `lougha_signature` (17.33): one root note, three rising branch notes and a bright leaf on top (D3 · D5 F♯5 A5 · D6).
  - An extended version as the lesson-complete fanfare at 18.07.
- **Mix.** Voice is at −16 LUFS. The music is sidechain-ducked, then checked word by word, and any word under 12 dB of separation gets more ducking; the minimum margin is logged. The music also dips under the hero brand sounds. The master is two-pass loudnorm to −14 LUFS and −1.25 dBTP.

## Notes and deviations

- **Voice engine.** The pipeline calls ElevenLabs (`eleven_multilingual_v2`) when `ELEVENLABS_API_KEY` is set (voice choice: `ELEVENLABS_VOICE_ID`). This build had no key and no access to the ElevenLabs API, so the voice is a local neural TTS stand-in (Piper `en_US-hfc_female`), run through the same two-take, word-perfect and cut-at-pauses process. To swap in ElevenLabs, re-run `vo.py` → `render` → `audio` → `master`. The picture re-locks to the new word timings automatically.
- **Script length.** The brief's script includes "Because learning a language opens a world of possibilities." There are 3.6 s between the 13.70 and 17.33 anchors, and the 22 words there cannot fit at a natural pace, so that sentence is left out of the timed cut. To restore it, set `INCLUDE_BECAUSE_LINE = True` in `config.py`; the later phrases then slide.
- To land the anchors, two phrases are read 1.3× faster and some comma pauses are tightened ("speaking, listening, reading and writing" and "Strong roots, endless possibilities"). The last word of the tagline runs into the 16.50 breath and ends just as the tree lands at 16.80.
- **Illustrative data.** The "365 days of progress" counter is labelled *Illustrative*. Every student name, score and lesson is fictional. There are no prices, dates, schedules or offers.
- **Fonts.** Nunito (SIL OFL, `assets/fonts/`) is the rounded sans for every Lougha string.
- A layered Resolve project is not included. The stems are written to `build/stem_{vo,music,sfx}.wav` for that.
