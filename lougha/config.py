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
FILM = 19.2          # main film, in SCENE seconds
END = 2.0            # end card, in SCENE seconds
DUR = FILM + END     # 21.2 scene seconds
# Global pacing: every scene time below is played TS x slower on screen.
# 4/3 -> 25.6 s film + 2.67 s end card = 28.27 s, music at 75 BPM (100 / TS).
TS = 4.0 / 3.0
REAL_DUR = DUR * TS
NFRAMES = int(round(REAL_DUR * FPS))  # 1696
LANG = "fr"


def frame(t):
    """Scene seconds -> delivered 60 fps frame index."""
    return int(round(t * TS * FPS))


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

# ---------------------------------------------------------------- voice-over (French)
# (anchor in scene seconds, displayed text, tts text, picture hit for the phrase onset)
# The script is read as one flowing take and cut only at its own pauses; each phrase
# starts on its anchor x TS (or just after the previous phrase if the read runs long).
VO_SCRIPT = [
    (0.50, "Chaque langue commence par des fondations.", "Chaque langue commence par des fondations.", "every"),
    (2.95, "Un mot à la fois,", "Un mot à la fois.", "one_word"),
    (4.60, "des racines solides qui vous font grandir,", "Des racines solides qui vous font grandir.", "strong_roots_1"),
    (7.20, "de vrais professeurs qui guident votre parcours,", "De vrais professeurs qui guident votre parcours.", "real_teachers"),
    (9.05, "et des conversations qui renforcent votre confiance.", "Et des conversations qui renforcent votre confiance.", "conversations"),
    (11.67, "Anglais,", "Anglais.", "en"),
    (12.42, "français,", "Français.", "fr"),
    (12.98, "allemand...", "Allemand.", "de"),
    (13.70, "parler, écouter, lire et écrire.", "Parler, écouter, lire et écrire.", "speaking"),
    (14.93, "Des racines solides, des possibilités infinies.", "Des racines solides, des possibilités infinies.", "strong_roots_2"),
    (17.33, "Lougha Online.", "Lougha, onn laïne.", "logo"),   # respelt so the French voice says LOO-ga on-LINE
]
# The brief's script also contains "Because learning a language opens a world of
# possibilities." ("Parce qu'apprendre une langue ouvre un monde de possibilités.").
# Between the 13.70 and 17.33 anchors there is no room for it at a natural pace, so by
# default it is left out of the timed cut. Set to True to include it.
INCLUDE_BECAUSE_LINE = False
BECAUSE = (14.60, "Parce qu'apprendre une langue ouvre un monde de possibilités.",
           "Parce qu'apprendre une langue ouvre un monde de possibilités.", None)
VO_DEADLINE = {14.93: 16.46}   # the tagline must clear the 16.50 breath (scene s)


def vo_script():
    s = list(VO_SCRIPT)
    if INCLUDE_BECAUSE_LINE:
        s.insert(9, BECAUSE)
    return s


# spoken words (inside phrases) whose onset drives a picture hit
VO_WORD_HITS = {"ecouter": "listening", "lire": "reading", "ecrire": "writing", "possibilites": "endless"}
DEFAULT_WORD_TIMES = {
    "every": 0.50, "one_word": 2.95, "strong_roots_1": 4.60, "real_teachers": 7.20,
    "conversations": 9.05, "en": 11.67, "fr": 12.42, "de": 12.98, "speaking": 13.70,
    "listening": 14.05, "reading": 14.38, "writing": 14.62, "strong_roots_2": 14.93,
    "endless": 15.60, "logo": 17.33,
}


def word_times():
    """Picture hits in SCENE seconds."""
    p = os.path.join(BUILD, "vo_timing.json")
    t = dict(DEFAULT_WORD_TIMES)
    if os.path.exists(p):
        with open(p) as f:
            t.update(json.load(f).get("hits", {}))
    return t


# ---------------------------------------------------------------- copy (French interface, fictional data)
# The lesson and the live class teach English (one of the three languages Lougha teaches).
STUDENT = "Amira"
TEACHER = "Mme Laila"
LESSON_LABEL = "Leçon 4  ·  Français vers anglais"
LESSON_PROMPT = "Traduisez cette phrase."
LESSON_SRC = "Je voudrais un café, s'il vous plaît."
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
TEACHER_LINE = "Hi Amira! How was your day?"
STUDENT_LINE = "Great! I ordered a coffee in English."
TAG1 = "Des racines solides,"
TAG2 = "des possibilités infinies."
END_TAG = "Des racines solides. Des possibilités infinies."
END_SUB = "Apprendre. Grandir. Se connecter."

UI = {
    "journey_title": "Le parcours d'Amira",
    "journey_sub": "Anglais  ·  du niveau A2 au B1",
    "journey_unit": "Unité 4  ·  Au café",
    "start": "COMMENCER",
    "excellent": "Excellent !",
    "correction_h": "Mme Laila : ordre des mots naturel, bravo.",
    "correction_v": "Mme Laila : ordre des mots naturel.",
    "every_lesson": "Chaque leçon",
    "helps_grow": "vous fait grandir.",
    "days_of": "jours de",
    "progress": "progrès",
    "illustrative": "Illustratif",
    "course_progress": "Progression du cours",
    "grow": "Grandir",
    "together": "ensemble.",
    "grow_together": "Grandir ensemble.",
    "real_line": "De vrais profs. De vrais progrès.",
    "group": "Anglais B1  ·  Groupe du soir",
    "week": "Progrès de la semaine",
    "pts": "pts",
    "call_title": "Anglais B1  ·  Cours en direct",
    "recorded": "Enregistré pour le replay",
    "teacher_tag": "Mme Laila  ·  Professeure",
    "reaction": "Excellent !",
    "langs": ["Anglais", "Français", "Allemand"],
    "langs_hdr": "Trois langues. Une seule fondation.",
    "langs_hdr_v": ["Trois langues.", "Une seule fondation."],
    "skills": ["Parler", "Écouter", "Lire", "Écrire"],
    "tag_v": ["Des racines", "solides, des", "possibilités", "infinies."],
    "end_v": ["Des racines solides.", "Des possibilités infinies."],
}
