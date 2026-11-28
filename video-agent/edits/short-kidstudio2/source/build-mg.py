# builds source/mg.html: KEEPS + French captions (whisper words, max 3 per chunk, key words in yellow)
import json, re
keeps = json.load(open('source/keeps.json'))
ws = [[w['start'], w['text'].strip()] for w in json.load(open('assets/words-scribe.json'))['words'] if w.get('type') == 'word']
out = []
for t, w in ws:
    if w in ('«', '»', '».'): continue
    if out and out[-1][1] == 'Kids' and w.startswith('Studio'): out[-1][1] = 'KidStudio' + w[6:]; continue
    if w == 'étudiés': w = 'étudient'
    if w == 'Beaucoup': t = 0.25
    if w == "d'enfants": t = 0.7
    out.append([t, w])
KEY = {"d'enfants", 'parler.', 'Pourquoi', 'envie,', 'confiance.', 'Imen,', 'KidStudio.', 'KidStudio', "l'anglais", 'deux', 'fois', 'vite.', 'programme', 'complet', 'quatre', 'compétences', 'Speaking,', 'Listening,', 'Reading', 'Writing', 'mémoriser', 'comprend,', 'parle,', 'lit', 'écrit', 'PDF', 'compliquées.', 'animés,', 'visuels', 'interactifs.', 'Jeux,', 'supports,', 'activités', 'participe', 'direct', 'Zoom,', 'maison,', 'personnalisé.', 'corrige,', "j'encourage", "j'adapte", 'rythme', 'Deux', 'séances', 'mois,', 'structuré', 'progrès', 'visible.', 'résultats', 'magnifiques,', 'osent', 'comprennent', 'refaire', 'base', 'solide', 'envie', "d'apprendre,", 'inscriptions', 'ouvertes', 'lien', 'bio.'}
chunks, cur = [], []
for t, w in out:
    cur.append([round(t, 2), w, w in KEY])
    if re.search(r'[.,!?:]$', w) or len(cur) >= 3: chunks.append(cur); cur = []
if cur: chunks.append(cur)
s = open('source/mg.tpl.html').read().replace('/*KEEPS*/', json.dumps(keeps)).replace('/*CAPS*/', json.dumps(chunks, ensure_ascii=False))
open('source/mg.html', 'w').write(s); print(len(chunks), 'chunks')
