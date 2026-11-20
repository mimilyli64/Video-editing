# builds source/mg.html: KEEPS + French captions timed on the English phrases (*word* = emphasised)
import json
tl = json.load(open('assets/timeline.json'))
keeps = json.load(open('source/keeps.json'))   # original take -> cut video (cuts done in source.mp4)
# (source start of the English phrase, French text)
FR = [
 (0.32, "Beaucoup de gens rêvent de partir *en Allemagne,*"),
 (1.95, "mais *tout le monde* n'y arrive pas."),
 (3.40, ""),
 (5.88, "Certains ont *le courage* d'apprendre l'allemand,"),
 (8.20, "*d'autres non.*"),
 (9.25, ""),
 (13.30, "C'est pour ça qu'on a créé *un programme exigeant :*"),
 (15.60, "*tout le monde* ne pourra pas suivre."),
 (17.90, ""),
 (23.25, "Une *pédagogie* qu'on ne trouve *nulle part ailleurs.*"),
 (25.65, ""),
 (30.05, "*Fini* les livres à remplir"),
 (31.90, "et les *PDF.*"),
 (33.80, ""),
 (34.30, "Le cours est *100 % interactif,*"),
 (36.50, "avec *ce livre* en plus."),
 (38.00, "Il contient *un résumé* de tout,"),
 (39.20, "des *activités* et des *exercices*"),
 (40.70, "à faire avec *le prof en direct.*"),
 (43.05, "Et on vous envoie le livre *chez vous.*"),
 (44.86, "Quand vous achetez le livre et payez,"),
 (47.04, "ce *QR code* vous ajoute"),
 (48.30, "*automatiquement* à votre groupe."),
 (49.50, ""),
 (51.25, "Si ça vous intéresse,"),
 (52.10, "découvrez *les avis* et *les résultats* de nos étudiants"),
 (55.15, "Tout est *sur notre site !*"),
]
END = 56.5
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
