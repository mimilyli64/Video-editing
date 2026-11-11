# builds source/mg.html from mg.tpl.html: KEEPS (timeline), CAPS (caption chunks from files/words.md), clip frames
import json, re, os
toks = [[w['start'], w['text'].strip()] for w in json.load(open('assets/words-scribe.json'))['words'] if w.get('type') == 'word']
REP = {"l'ordre": "l'or"}
EMPH = {"investissement", "l'or", "l'immobilier,", "enfant.", "l'anglais", "l'âge", "adulte,", "l'apprentissage", "prononciation", "Macron.", "KidStudio,", "écouter,", "recopier", "cœur", "15", "minutes,", "décroche.", "l'inverse,", "passivement", "rien.", "interactive,", "participe,", "réagit", "parle.", "animés", "visuels.", "direct", "Zoom,", "compétences,", "lire,", "écrire", "communiquer.", "bio.", "Comme", "ça,", "ça."}
# merge "Kid" "Studio," -> "KidStudio,"
out = []
for t, w in toks:
    w = REP.get(w, w)
    if out and out[-1][1] == 'Kid' and w.startswith('Studio'): out[-1][1] = 'Kid' + w; continue
    out.append([t, w])
chunks, cur = [], []
for t, w in out:
    cur.append([round(t, 2), w, w in EMPH])
    if re.search(r'[.,!?:]$', w) or len(cur) >= 5:
        chunks.append(cur); cur = []
if cur: chunks.append(cur)
# a lone short word joins the next chunk
merged = []
for c in chunks:
    if merged and len(merged[-1]) == 1 and len(merged[-1][0][1]) <= 4 and not re.search(r'[.!?]$', merged[-1][0][1]): merged[-1] += c
    else: merged.append(c)
tl = json.load(open('assets/timeline.json'))
keeps = [[round(a, 4), round(b, 4), round(c, 4)] for a, b, c in tl['keeps']]
fr = ''.join(f'<img class="fa" src="clips/a/{f}" style="display:none">' for f in sorted(os.listdir('source/clips/a'))) + \
     ''.join(f'<img class="fb" src="clips/b/{f}" style="display:none">' for f in sorted(os.listdir('source/clips/b')))
s = open('source/mg.tpl.html').read().replace('/*KEEPS*/', json.dumps(keeps)).replace('/*CAPS*/', json.dumps(merged, ensure_ascii=False)).replace('<!--FRAMES-->', fr)
open('source/mg.html', 'w').write(s)
for c in merged: print(' '.join(('*' if e else '') + w for _, w, e in c), end=' | ')
