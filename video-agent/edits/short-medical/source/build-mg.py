# builds source/mg.html: KEEPS + French captions timed on the English phrases (*word* = emphasised)
import json
tl = json.load(open('assets/timeline.json'))
keeps = [[round(a, 4), round(b, 4), round(c, 4)] for a, b, c in tl['keeps']]
# (source start of the English phrase, French text)
FR = [
 (0.90, "Bienvenue dans notre *nouvelle série,*"),
 (2.12, "*Scrub Talk !*"),
 (3.40, "Je m'appelle *Hadeel,*"),
 (4.64, "prof d'anglais médical chez *Lougha Online.*"),
 (6.72, "Aujourd'hui, on va lever"),
 (8.43, "une *confusion* très courante"),
 (9.60, "chez les *professionnels de santé,*"),
 (14.02, "qu'ils travaillent ou qu'ils *étudient,*"),
 (15.12, "entre *injury, wound et trauma.*"),
 (18.20, "Ils utilisent ces trois mots *indifféremment,*"),
 (20.70, "en pensant que c'est *la même chose,*"),
 (22.92, "mais en réalité,"),
 (23.80, "*ce n'est pas le cas.*"),
 (24.96, "Une *injury*, c'est toute *lésion,*"),
 (26.28, "*externe* ou *interne,*"),
 (28.10, "qui touche *le corps.*"),
 (30.44, "Une *wound*, c'est une ouverture"),
 (31.11, "de la *peau* ou des *tissus,*"),
 (32.94, "par exemple, *une lacération.*"),
 (36.86, "Un *trauma*, en revanche,"),
 (40.12, "c'est une *blessure physique*"),
 (41.98, "causée par une *force extérieure soudaine.*"),
 (46.72, "Si vous voulez améliorer"),
 (47.86, "votre *anglais médical,*"),
 (49.23, "*découvrez nos cours !*"),
]
END = 51.5
def parse(s):
    out, emph = [], False
    for tok in s.split(' '):
        st = tok.startswith('*'); en = tok.endswith('*') or tok.endswith('*,') or tok.endswith('*.')
        if st: emph = True
        w = tok.replace('*', '')
        out.append([w, emph or st])
        if en: emph = False
    return out
def kept_span(a, b):   # seconds of [a, b] that survive the cuts
    return sum(max(0, min(b, k[1]) - max(a, k[0])) for k in keeps)
def src_after(a, d):   # source time reached after d kept seconds from a
    for k in keeps:
        if k[1] <= a: continue
        s = max(a, k[0]); room = k[1] - s
        if d <= room: return s + d
        d -= room
    return keeps[-1][1]
caps = []
for i, (s, txt) in enumerate(FR):
    e = FR[i + 1][0] if i + 1 < len(FR) else END
    ws = parse(txt); span = kept_span(s, e)
    step = min(.32, span * .75 / max(1, len(ws)))
    caps.append([[round(src_after(s, j * step), 3), w, em] for j, (w, em) in enumerate(ws)])
s = open('source/mg.tpl.html').read().replace('/*KEEPS*/', json.dumps(keeps)).replace('/*CAPS*/', json.dumps(caps, ensure_ascii=False))
open('source/mg.html', 'w').write(s)
print(len(caps), 'chunks')
