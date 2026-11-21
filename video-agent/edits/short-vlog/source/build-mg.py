# builds source/mg.html: KEEPS (orig take -> cut video) + English captions (3 words max, vocab words in yellow)
import json, re
keeps = json.load(open('source/keeps.json'))
ws = [[w['start'], w['text'].strip()] for w in json.load(open('assets/words-scribe.json'))['words'] if w.get('type') == 'word']
REP = {'Loha': 'Lougha'}
VOC = {'mall', 'shopping.', 'automatic', 'doors.', "women's", 'clothing', 'first', 'floor,', 'escalator', 'shoes,', 'slippers,', 'black', 'brown,', 'brown', 'boots.', 'handbag', 'wallet.', 'bag', 'winter', 'hat.', 'hat,', 'scarf', 'gloves.', 'clothes', 'coat.', 'Lougha', 'Online,', 'Online', 'slow', 'English', 'vlog.', 'vlogs,'}
chunks, cur = [], []
for t, w in ws:
    w = REP.get(w, w)
    cur.append([round(t, 2), w, w in VOC])
    if re.search(r'[.,!?]$', w) or len(cur) >= 3: chunks.append(cur); cur = []
if cur: chunks.append(cur)
# speech starts after the lead-in silence: the first word sits on the first kept frame
s = open('source/mg.tpl.html').read().replace('/*KEEPS*/', json.dumps(keeps)).replace('/*CAPS*/', json.dumps(chunks, ensure_ascii=False))
open('source/mg.html', 'w').write(s); print(len(chunks), 'chunks')
