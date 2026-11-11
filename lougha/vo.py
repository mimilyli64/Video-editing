"""Voice first.

1. Generate two takes of the whole script as ONE flowing read.
   - ElevenLabs (bright upbeat young female voice) when ELEVENLABS_API_KEY is set,
   - otherwise a local neural TTS stand-in (Piper, fr_FR siwis) so the film
     can be built and timed offline.
   The read is in French (config.LANG); all anchors are scene seconds x config.TS.
2. Transcribe both takes (faster-whisper) and keep the word-perfect one.
3. Cut the take only at its own pauses (silence detection), one cut per phrase.
4. Place each phrase on its anchor (never earlier, never overlapping the previous
   phrase) and write build/vo.wav + build/vo_timing.json with the onset of every
   word that drives a picture hit.

Usage:  python3 -m lougha.vo
"""
import json
import os
import re
import subprocess
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from . import config as C

SR = 48000
PIPER_DIR = os.environ.get("PIPER_VOICES", os.path.join(C.BUILD, "voices"))
PIPER_VOICE = "en_US-hfc_female-medium" if C.LANG == "en" else "fr_FR-siwis-medium"
TAKES = [  # (name, length_scale, noise_scale, noise_w)
    ("take1", 0.92, 0.60, 0.75),
    ("take2", 0.88, 0.70, 0.85),
]
SENT_SIL = 0.42


def _read(path):
    sr, a = wavfile.read(path)
    a = a.astype(np.float32)
    if a.ndim > 1:
        a = a.mean(1)
    if np.abs(a).max() > 2:
        a /= 32768.0
    if sr != SR:
        a = resample_poly(a, SR, sr).astype(np.float32)
    return a


def _tts_text():
    return " ".join(p[2] for p in C.vo_script())


def take_piper(name, ls, ns, nw):
    out = os.path.join(C.BUILD, f"vo_{name}_raw.wav")
    model = os.path.join(PIPER_DIR, PIPER_VOICE + ".onnx")
    if not os.path.exists(model):
        os.makedirs(PIPER_DIR, exist_ok=True)
        base = ("https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/hfc_female/medium/" if C.LANG == "en"
                else "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/")
        for ext in (".onnx", ".onnx.json"):
            subprocess.run(["curl", "-sSL", "-o", os.path.join(PIPER_DIR, PIPER_VOICE + ext),
                            base + PIPER_VOICE + ext], check=True)
    subprocess.run([sys.executable, "-m", "piper", "-m", model, "-f", out,
                    "--length-scale", str(ls), "--noise-scale", str(ns), "--noise-w", str(nw),
                    "--sentence-silence", str(SENT_SIL)],
                   input=_tts_text().encode(), check=True, capture_output=True)
    return out


def take_elevenlabs(name, key):
    """Whole script, one request, one flowing read (eleven_multilingual_v2)."""
    import urllib.request
    voice = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    body = json.dumps({
        "text": _tts_text().replace("Lougha, onn laïne.", "Lougha Online.").replace("Loo-gah Online.", "Lougha Online."),
        "model_id": "eleven_multilingual_v2",
        "language_code": C.LANG,
        "voice_settings": {"stability": 0.38, "similarity_boost": 0.8, "style": 0.45,
                           "use_speaker_boost": True},
    }).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_44100",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    pcm = urllib.request.urlopen(req, timeout=120).read()
    a = np.frombuffer(pcm, dtype=np.int16)
    out = os.path.join(C.BUILD, f"vo_{name}_raw.wav")
    wavfile.write(out, 44100, a)
    return out


def transcribe(a):
    from faster_whisper import WhisperModel
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    m = WhisperModel("base", device="cpu", compute_type="int8")
    a16 = resample_poly(a, 16000, SR).astype(np.float32)
    segs, _ = m.transcribe(a16, word_timestamps=True, language=C.LANG,
                           condition_on_previous_text=False)
    words = []
    for s in segs:
        for w in s.words:
            words.append((w.start, w.end, w.word.strip()))
    return words


def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.findall(r"[a-z]+", s)


def word_perfect(words):
    """Word errors against the script; the brand name (last phrase) is checked by ear,
    since Whisper does not know the word "Lougha"."""
    got = norm(" ".join(w[2] for w in words))
    want = norm(" ".join(p[1] for p in C.vo_script()[:-1]))
    got = got[:len(want)]
    import difflib
    sm = difflib.SequenceMatcher(a=want, b=got)
    errs = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
    return errs, got


def split_on_pauses(a, n):
    """Return n (start, end) sample ranges, cutting only inside the take's own pauses."""
    hop = int(0.01 * SR)
    e = np.sqrt(np.convolve(a ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    db = 20 * np.log10(e + 1e-9)
    thr = db.max() - 38
    voiced = db > thr
    # silent runs
    runs, i = [], 0
    while i < len(voiced):
        if not voiced[i]:
            j = i
            while j < len(voiced) and not voiced[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    first = np.argmax(voiced)
    last = len(voiced) - np.argmax(voiced[::-1])
    inner = [r for r in runs if r[0] > first and r[1] < last]
    inner.sort(key=lambda r: r[1] - r[0], reverse=True)
    cuts = sorted(inner[: n - 1])
    if len(cuts) < n - 1:
        raise RuntimeError("take has fewer pauses than phrases")
    bounds = [first] + [x for c in cuts for x in c] + [last]
    rng = []
    for k in range(n):
        s, e2 = bounds[2 * k], bounds[2 * k + 1]
        rng.append((max(0, s * hop - int(0.015 * SR)), min(len(a), e2 * hop + int(0.06 * SR))))
    return rng


DEADLINE = {k: v for k, v in C.VO_DEADLINE.items()}


def tighten_pauses(seg, keep=0.09):
    """Shorten silent gaps longer than `keep` seconds inside a phrase."""
    hop = int(0.005 * SR)
    env = np.sqrt(np.convolve(seg ** 2, np.ones(hop) / hop, "same") + 1e-12)
    quiet = env < env.max() * 0.02
    out, i, n = [], 0, len(seg)
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if i > 0 and j < n and (j - i) > keep * SR:
                gap = int(keep * SR)
                fade = np.linspace(1, 0, gap // 2)
                out.append(seg[i:i + gap // 2] * fade)
                out.append(seg[j - gap // 2:j] * fade[::-1])
            else:
                out.append(seg[i:j])
            i = j
        else:
            j = i
            while j < n and not quiet[j]:
                j += 1
            out.append(seg[i:j])
            i = j
    return np.concatenate(out)


def stretch(seg, factor):
    """Speed a phrase up by `factor` (pitch kept) with ffmpeg atempo."""
    if factor <= 1.001:
        return seg
    tmp_in = os.path.join(C.BUILD, "_st_in.wav")
    tmp_out = os.path.join(C.BUILD, "_st_out.wav")
    wavfile.write(tmp_in, SR, (seg * 32767).astype(np.int16))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp_in, "-filter:a",
                    f"atempo={factor:.4f}", tmp_out], check=True)
    out = _read(tmp_out)
    os.remove(tmp_in)
    os.remove(tmp_out)
    return out


def main():
    os.makedirs(C.BUILD, exist_ok=True)
    key = os.environ.get("ELEVENLABS_API_KEY")
    engine = "elevenlabs" if key else "piper (stand-in)"
    script = C.vo_script()
    report = {"engine": engine, "takes": {}}
    best = None
    for name, ls, ns, nw in TAKES:
        path = take_elevenlabs(name, key) if key else take_piper(name, ls, ns, nw)
        a = _read(path)
        words = transcribe(a)
        errs, got = word_perfect(words)
        report["takes"][name] = {"errors": errs, "heard": " ".join(got), "dur": len(a) / SR}
        print(f"[vo] {name}: {len(a)/SR:.2f}s, word errors={errs}")
        if best is None or errs < best[1]:
            best = (name, errs, a)
    name, errs, a = best
    report["chosen"] = name
    print(f"[vo] keeping {name} (errors={errs})")

    rngs = split_on_pauses(a, len(script))
    total = int(C.REAL_DUR * SR)
    TS = C.TS
    out = np.zeros(total, np.float32)
    placed = []
    prev_end = 0.0
    for k, ((anchor, text, _, hitkey), (s, e)) in enumerate(zip(script, rngs)):
        seg = a[s:e]
        # onset inside the segment (first sample above -40 dB of peak)
        env = np.abs(seg)
        on = int(np.argmax(env > env.max() * 0.03))
        start = max(anchor * TS, prev_end + 0.10)
        nxt = script[k + 1][0] * TS if k + 1 < len(script) else C.REAL_DUR
        avail = nxt - start - 0.06
        if anchor in DEADLINE:
            avail = min(avail, DEADLINE[anchor] * TS - start)
        dur = (len(seg) - on) / SR
        factor = 1.0
        if dur > avail:
            # first tighten the read's own internal pauses (commas), then speed up
            seg = tighten_pauses(seg)
            on = int(np.argmax(np.abs(seg) > np.abs(seg).max() * 0.03))
            dur = (len(seg) - on) / SR
        if dur > avail and k + 1 < len(script):
            factor = min(1.30, dur / max(avail, 0.3))
            seg = stretch(seg, factor)
            on = int(on / factor)
        i0 = int(start * SR) - on
        i1 = min(total, i0 + len(seg))
        out[max(0, i0):i1] += seg[max(0, -i0): i1 - i0]
        prev_end = (i0 + len(seg)) / SR - 0.06
        placed.append({"anchor": anchor, "start": round(start, 3), "end": round(prev_end, 3),
                       "text": text, "tempo": round(factor, 3), "hit": hitkey})
        print(f"[vo] {anchor:6.2f} -> {start:6.2f}..{prev_end:6.2f}  x{factor:.2f}  {text}")
    report["phrases"] = placed

    # word timings on the placed VO -> picture hits (stored in SCENE seconds)
    words = transcribe(out)
    hits = {}
    for p in placed:
        if p["hit"]:
            hits[p["hit"]] = round(p["start"] / TS, 3)
    for (ws, we, w) in words:
        n = norm(w)
        if not n:
            continue
        key2 = C.VO_WORD_HITS.get(n[0])
        if key2 and key2 not in hits:
            hits[key2] = round(float(ws) / TS, 3)
    report["hits"] = hits
    report["words"] = [(round(float(s), 3), round(float(e), 3), w) for s, e, w in words]
    wavfile.write(os.path.join(C.BUILD, "vo.wav"), SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    with open(os.path.join(C.BUILD, "vo_timing.json"), "w") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print("[vo] hits:", hits)


if __name__ == "__main__":
    main()
