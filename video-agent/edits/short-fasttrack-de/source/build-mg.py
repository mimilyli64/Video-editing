# builds source/mg.html: KEEPS + French captions timed on the English phrases (*word* = emphasised)
import json
tl = json.load(open('assets/timeline.json'))
keeps = json.load(open('source/keeps.json'))   # original take -> cut video (cuts done in source.mp4)
# (source start of the English phrase, French text)
FR = [
 (0.60, ""),
 (2.65, "Tu ne connais pas encore *Lougha Online ?*"),
 (5.36, "Ou notre nouveau programme : *Fast Track ?*"),
 (7.47, "Il te permet d'enchaîner les niveaux"),
 (9.30, "*sans interruption.*"),
 (11.40, "Plus besoin d'attendre qu'un groupe"),
 (12.90, "*se remplisse.*"),
 (14.83, "Avec Fast Track, tu fais"),
 (16.40, "*l'A1 et l'A2 en 2 mois.*"),
 (19.55, ""),
 (20.48, "Et tu as *ce livre,*"),
 (21.90, "avec *tous les détails.*"),
 (23.57, "Ce livre, tu ne l'étudies *pas seul :*"),
 (26.29, "tu l'étudies *avec le prof*"),
 (27.00, "et tu y fais *les exercices.*"),
 (27.80, ""),
 (31.49, "Chez Lougha Online,"),
 (33.20, "on teste les étudiants *à chaque niveau.*"),
 (37.60, ""),
 (40.29, "Il y a plein de vidéos"),
 (42.00, "avec *les résultats* de nos étudiants."),
 (44.00, ""),
]
END = 47.1
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
    if not txt: caps.append([[s, '', False]]); continue
    ws = parse(txt); span = kept_span(s, e)
    step = min(.32, span * .75 / max(1, len(ws)))
    caps.append([[round(src_after(s, j * step), 3), w, em] for j, (w, em) in enumerate(ws)])
s = open('source/mg.tpl.html').read().replace('/*KEEPS*/', json.dumps(keeps)).replace('/*CAPS*/', json.dumps(caps, ensure_ascii=False))
open('source/mg.html', 'w').write(s)
print(len(caps), 'chunks')
