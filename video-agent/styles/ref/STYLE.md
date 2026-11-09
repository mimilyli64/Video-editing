# Style : ref

Copié de la vidéo de référence envoyée le 9 novembre 2026 (pub « Fast Track » Lougha Online, 21,7 s, 720×1280). S'applique par-dessus le style.md de short-editing : ce qui n'est pas ici reste comme là-bas.

Voix en darija marocaine, sous-titres traduits en français.

## Coupes
- 1 seule coupe franche en 21,7 s (à 2,5 s : plan debout → plan assis, avec un flou de mouvement d'une image). Le rythme vient des éléments graphiques, pas des coupes.
- Pas de fondu, pas de transition.
## Cadrage
- Caméra plein écran tout le long. Visage à 12 à 16 % de la hauteur du cadre (plan large, on voit le buste et les genoux).
- Pas de punch-in visible, pas de push. Le plan d'accroche est un peu plus serré et bouge (la personne se penche vers la caméra).
## Sous-titres
- Montserrat Bold, blanc, ombre douce, environ 52 px sur un cadre de 1080 px de large. Casse normale (pas de majuscules).
- Centrés au niveau de la poitrine (~52 % de la hauteur), 1 à 2 lignes, jusqu'à 6 mots par ligne.
- Les mots apparaissent un par un en fondu flou, de gauche à droite.
- Mot-clé en violet (#8A3FE0), sur sa propre ligne, plus gros (« parler anglais », « anglais »).
- Accroche (0 à 2,5 s) : serif blanc, chiffre clé énorme en magenta (#B50CE1, « 2 mois »).
## Éléments graphiques (un toutes les 1,5 à 3 s)
- 1,8 s : point d'interrogation violet en haut à droite (sticker 3D).
- 2,0 s : drapeau britannique qui monte depuis le bas.
- 3,2 s : pastille blanche translucide avec logo rond + « Lougha Online ».
- 4 à 7 s : « Fast Track » en blanc gras sur un arc, qui glisse depuis la gauche en haut du cadre.
- 4,5 à 6 s : pilules marron empilées « Rapide », « intensive » avec un interrupteur violet.
- 7,5 s : « EN ANGLAIS » entouré d'un trait violet dessiné à la main.
- 8 à 10,5 s : badges « A1 » « A2 » turquoise 3D lumineux qui tournent en entrant, en haut.
- 11 à 13 s : icônes carrées violettes (Reading, Speaking, Writing, Listening) qui s'empilent dans les coins hauts, une par compétence dite.
- 13,5 s+ : vrai produit (livre) tenu face caméra.
- 15,5 à 17 s : illustration flat (bureau, cahier, ampoule) sur « production écrite ».
- 19,5 s à la fin : CTA, pilule turquoise « Loughaonline.com » en bas + curseur qui clique.
## Son
- Pas de musique (le niveau tombe à -50 dB entre les phrases).
- 0 à 2,5 s : tons aigus qui s'empilent (tension), coupés net sur le changement de plan.
- 4,6 s : un « ding » à l'arrivée du logo.
- 7,4 s : un whoosh court quand les pilules glissent.
- Voix forte et sèche, mise à -14 LUFS (l'original est à -32 LUFS, trop bas).
## Étalonnage
- Naturel, couleurs riches (pièce violette néon). ffmpeg : eq=contrast=1.04:saturation=1.06
## Laissé de côté
- La tension tonale de l'accroche : remplacée par zhhh.mp3 sur la coupe (règle de la maison : pas de son de montée).
- Les clics d'entrée sur chaque élément : non copiés.
## Comment short-editing l'applique
- layout.keys : [[0, 0]] (plein écran tout le long).
- Chaque élément = un composant HTML (overlay alpha) posé sur le mot qui le nomme, hors du visage.
- Sons : zhhh.mp3 sur la coupe de l'accroche, pop sur le logo, pop-back.mp3 sur l'arrivée des pilules.

## Demandes de la créatrice (9 novembre 2026)
- Garder le logo Lougha Online, le site Loughaonline.com et la traduction darija → français.
- Ne PAS garder les couleurs de la référence : reprendre celles de sa propre vidéo.
- Même style, mais plus riche : beaucoup d'illustrations et de motion graphics animés.

## Rejeté
- 9 novembre 2026 : les micro-coupes de silence (24 coupes en 30 s) : « pas smooth, pas naturel ». Désormais la prise reste entière, sans aucune coupe.
- 9 novembre 2026 : le flou de mouvement sur les transitions (« vraiment nul »). Remplacé par des zooms nets : zoom avant à travers la coupe, dézoom après la coupe.
- 9 novembre 2026 : les blancs entre les phrases (« enlève complètement le côté naturel »). Coupés à ~0,2 s, pauses des virgules gardées.
