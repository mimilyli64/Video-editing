"""Lougha Online - "The Roots".  Single source of truth for timing, palette and copy.

Every time in this file is in seconds; frame(t) converts to a 60 fps frame index.
Picture hits that sit on spoken words are *not* hard-coded here: they are read from
build/vo_timing.json (written by vo.py) so the picture is locked to the voice.
"""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(ROOT, "out")
FONTS = os.path.join(ROOT, "assets", "fonts")

FPS = 60
FILM = 19.2          # main film
END = 2.0            # end card
DUR = FILM + END     # 21.2 s
NFRAMES = int(round(DUR * FPS))  # 1272


def frame(t):
    return int(round(t * FPS))


# ---------------------------------------------------------------- palette
def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


PAL = {
    "navy": "#17142B",     # stage
    "purple": "#542080",   # rich purple
    "violet": "#902FE8",   # vibrant violet
    "lav": "#C17AF5",      # lavender light
    "white": "#FFFFFF",
    "gold": "#FFD43B",     # open-book accent
    # derived shades (all purple family - no greens anywhere)
    "night": "#0E0B1E",
    "deep": "#221A44",
    "plum": "#331560",
    "lip": "#2A0F4C",
    "bark": "#3B1868",
    "mist": "#E9D6FF",
    "goldd": "#D99A12",
    "goldl": "#FFE88A",
}
RGB = {k: hex2rgb(v) for k, v in PAL.items()}

# ---------------------------------------------------------------- beat sheet
SECTIONS = [
    ("S1", "Hook", 0.00, 1.67),
    ("S2", "The root path", 1.67, 2.93),
    ("S3", "Lesson", 2.93, 4.80),
    ("S4", "Progress", 4.80, 7.20),
    ("S5", "Learning community", 7.20, 9.33),
    ("S6", "Talk", 9.33, 11.40),
    ("S7", "Languages and every skill", 11.40, 14.67),
    ("S8", "The message", 14.67, 16.50),
    ("S9", "Hero", 16.50, 19.20),
    ("S10", "End card", 19.20, 21.20),
]

# fixed (non-voice) hits
HIT = {
    "seed": 0.00,         # tiny root in darkness
    "slam": 0.17,         # tree slams in
    "wordmark": 0.62,     # root sweeps under the wordmark
    "book_glint": 1.10,
    "tree_gesture": 1.30,
    "dive": 1.50,
    "start_press": 2.40,
    "tiles": 3.30,        # first tile lifts
    "chime1": 4.23,       # original Lougha success sound #1
    "drop": 7.20,
    "rank1": 8.70,        # row reaches #1, success sound #2
    "pullback": 11.40,
    "breath": 16.50,
    "land": 16.80,
    "fanfare": 18.07,     # Lougha lesson-complete signature
    "endcard": 19.20,
}

# ---------------------------------------------------------------- voice-over
# (anchor, spoken text, tts text).  The script is read as one flowing take and cut
# only at its own pauses; each phrase starts on its anchor (or just after the
# previous phrase if the read runs long).
VO_SCRIPT = [
    (0.50, "Every language begins with a foundation.", "Every language begins with a foundation."),
    (2.95, "One word at a time,", "One word at a time."),
    (4.60, "strong roots that help you grow,", "Strong roots that help you grow."),
    (7.20, "real teachers who guide your journey,", "Real teachers who guide your journey."),
    (9.05, "and conversations that build your confidence.", "And conversations that build your confidence."),
    (11.67, "English,", "English."),
    (12.42, "French,", "French."),
    (12.98, "German...", "German."),
    (13.70, "speaking, listening, reading and writing.", "Speaking, listening, reading and writing."),
    (14.93, "Strong roots, endless possibilities.", "Strong roots, endless possibilities."),
    (17.33, "Lougha Online.", "Loo-gah Online."),   # respelt so TTS says LOO-gha
]
# The brief's script also contains "Because learning a language opens a world of
# possibilities." Between the 13.70 and 17.33 anchors there are 3.6 s for 22 words,
# which no natural read can fit, so by default it is left out of the timed cut.
# Set to True to include it (the phrases after it then slide later).
INCLUDE_BECAUSE_LINE = False
BECAUSE = (14.60, "Because learning a language opens a world of possibilities.",
           "Because learning a language opens a world of possibilities.")


def vo_script():
    s = list(VO_SCRIPT)
    if INCLUDE_BECAUSE_LINE:
        s.insert(9, BECAUSE)
    return s


# words whose spoken onset drives a picture hit
VO_WORD_HITS = {
    "every": "every", "one": "one_word", "strong": "strong_roots_1",
    "real": "real_teachers", "conversations": "conversations",
    "english": "en", "french": "fr", "german": "de",
    "speaking": "speaking", "listening": "listening", "reading": "reading",
    "writing": "writing", "lougha": "logo",
}
DEFAULT_WORD_TIMES = {
    "every": 0.50, "one_word": 2.95, "strong_roots_1": 4.60, "real_teachers": 7.20,
    "conversations": 9.30, "en": 11.67, "fr": 12.42, "de": 12.98, "speaking": 13.70,
    "listening": 14.05, "reading": 14.38, "writing": 14.62, "strong_roots_2": 14.93,
    "endless": 15.60, "logo": 17.33,
}


def word_times():
    p = os.path.join(BUILD, "vo_timing.json")
    t = dict(DEFAULT_WORD_TIMES)
    if os.path.exists(p):
        with open(p) as f:
            t.update(json.load(f).get("hits", {}))
    return t


# ---------------------------------------------------------------- copy (fictional data)
STUDENT = "Amira"
TEACHER = "Ms. Laila"
LESSON_PROMPT = "Translate this sentence."
LESSON_SRC = "Quiero un café, por favor."
LESSON_TILES = ["I", "would like", "a", "coffee,", "please."]
LESSON_BANK_ORDER = [3, 0, 4, 1, 2]   # shuffled order in the word bank
TILE_TIMES = [3.30, 3.44, 3.58, 3.72, 3.86]  # each tile lifts then snaps (+0.16 s)
COMMUNITY = [  # name, points (fictional)
    ("Lucas M.", 1480), ("Sofia R.", 1415), ("Yusuf A.", 1360), ("Hana K.", 1290),
    ("Elena P.", 1215), ("Omar T.", 1170), ("Amira S.", 1120),
]
AMIRA_FINAL_POINTS = 1525
VOCAB = {
    "en": ["hello", "friend", "journey", "grow"],
    "fr": ["bonjour", "ami", "voyage", "grandir"],
    "de": ["hallo", "Freund", "Reise", "wachsen"],
}
TEACHER_LINE = "¡Hola! ¿Qué tal tu día?"
STUDENT_LINE = "¡Muy bien! Pedí un café en español."
TAG1 = "Strong roots,"
TAG2 = "endless possibilities."
END_TAG = "Strong roots. Endless possibilities."
END_SUB = "Learn. Grow. Connect."
