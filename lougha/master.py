"""Mux picture + mix into the deliverables and write the frame-exact brief.

  python3 -m lougha.master
"""
import csv
import json
import os
import subprocess

from . import config as C


def brief():
    wt = C.word_times()
    L = ["# Lougha Online - \"The Roots\": frame-exact brief", "",
         f"60 fps · French · pacing x{C.TS:.3f} (music 75 BPM) · film 0-{C.FILM * C.TS:.2f}s "
         f"(frames 0-{C.frame(C.FILM) - 1}) + end card {C.FILM * C.TS:.2f}-{C.REAL_DUR:.2f}s "
         f"(frames {C.frame(C.FILM)}-{C.NFRAMES - 1}) · {C.NFRAMES} frames", "",
         "Times below are delivered seconds; frames are 60 fps frame indices.", "",
         "## Beats", "", "| Beat | | Start s | Frame | End s | Frame |", "|---|---|---|---|---|---|"]
    for k, name, a, b in C.SECTIONS:
        L.append(f"| {k} | {name} | {a * C.TS:.2f} | {C.frame(a)} | {b * C.TS:.2f} | {C.frame(b)} |")
    L += ["", "## Fixed picture/sound hits", "", "| Hit | s | Frame |", "|---|---|---|"]
    for k, v in sorted(C.HIT.items(), key=lambda x: x[1]):
        L.append(f"| {k} | {v * C.TS:.2f} | {C.frame(v)} |")
    L += ["", "## Voice-locked hits (word onsets measured on the chosen take)", "", "| Word hit | s | Frame |", "|---|---|---|"]
    for k, v in sorted(wt.items(), key=lambda x: x[1]):
        L.append(f"| {k} | {v * C.TS:.3f} | {C.frame(v)} |")
    p = os.path.join(C.BUILD, "vo_timing.json")
    if os.path.exists(p):
        r = json.load(open(p))
        L += ["", f"## Voice-over ({r['engine']}, kept {r['chosen']})", "", "| Anchor s | Placed s | End s | Tempo | Line |",
              "|---|---|---|---|---|"]
        for ph in r["phrases"]:
            L.append(f"| {ph['anchor'] * C.TS:.2f} | {ph['start']:.2f} | {ph['end']:.2f} | x{ph['tempo']} | {ph['text']} |")
        L += ["", "Takes:"] + [f"- {k}: {v['errors']} word errors" for k, v in r["takes"].items()]
    cs = os.path.join(C.OUT, "cue_sheet.csv")
    if os.path.exists(cs):
        n = sum(1 for _ in open(cs)) - 1
        L += ["", f"## Sound: {n} cues, see `out/cue_sheet.csv` (time, frame, cue)."]
    with open(os.path.join(C.ROOT, "BRIEF_FRAMES.md"), "w") as f:
        f.write("\n".join(L) + "\n")


def mux(pic, out):
    mix = os.path.join(C.OUT, "mix.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", pic, "-i", mix, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-shortest",
                    "-movflags", "+faststart", out], check=True)
    print("wrote", out)


def main():
    brief()
    for tag in ("16x9", "9x16"):
        pic = os.path.join(C.OUT, f"picture_{tag}.mp4")
        if os.path.exists(pic):
            mux(pic, os.path.join(C.OUT, f"Lougha_TheRoots_{tag}_60fps.mp4"))


if __name__ == "__main__":
    main()
