# builds source/mg.html: KEEPS + French captions timed on the English phrases (*word* = emphasised)
import json
tl = json.load(open('assets/timeline.json'))
keeps = json.load(open('source/keeps.json'))   # original take -> cut video (cuts done in source.mp4)
# (source start of the English phrase, French text)
FR = [
 (1.19, "Le programme *le plus rapide* et *le plus intense*"),
 (2.55, "pour apprendre *l'allemand* au monde."),
 (3.70, ""),
 (9.06, "Au lieu d'avancer *petit à petit,*"),
 (11.09, "ce programme te fait passer"),
 (12.60, "*deux niveaux* en seulement *deux mois.*"),
 (13.36, "Tu fais *l'A1* et *l'A2* en *2 mois.*"),
 (17.95, ""),
 (18.71, "C'est le *Super Fast Track*"),
 (20.40, "de *Lougha Online.*"),
 (21.87, "Spécialement pour ceux qui veulent"),
 (23.40, "*l'A2* avant *la fin de l'année.*"),
 (25.71, "*5 séances* par semaine,"),
 (27.20, "au lieu de *2 ou 3.*"),
 (28.90, ""),
 (29.74, "Et tu reçois *ce livre*"),
 (31.30, "à suivre avec le programme,"),
 (33.06, "avec des *exercices*"),
 (34.60, "et de la place pour écrire *ton vocabulaire.*"),
 (36.85, ""),
 (37.53, "Et nos étudiants auront *une offre spéciale*"),
 (40.47, "pour étudier *en Allemagne :*"),
 (42.25, ""),
 (43.16, "le *B1* et le *B2*,"),
 (44.40, "si tu suis toutes les étapes,"),
 (45.40, "tu les feras *en Allemagne.*"),
 (47.40, ""),
 (48.39, "Si ça t'intéresse, *le lien* est dans *la bio.*"),
 (51.22, "Tu y trouveras *les avis* et *les résultats.*"),
]
END = 53.7
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
