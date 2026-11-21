// Lougha Online - Fast Track (allemand A1+A2 en 2 mois). Darija voice, French captions only on the phrases we understood.
// v2 (creator: « trop de cuts, zooms qui coupent le visage, ajoute une musique ») : fixed framing (no zoom at all), cuts only where the take
// already changes, each one a 0.2 s dissolve; graphics kept above her head (scaled .8); motivating music bed; « Inscris-toi maintenant » CTA.
// assets/source.mp4 = cut + dissolved take; mg.html maps cut time -> take time (keeps.json).
window.SPEC = {
  title: 'Lougha Online - Fast Track',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 500], q: 1 },
  cut: [],
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 70, layer: 'over' }],
  music: { src: 'assets/music/fasttrack-bed.wav', offset: 0, breaks: [] },
  mix: { music: -26, duck: .5, ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0, extra: [[0.4, 'pop', 0.1], [2.8, 'pop', 0.08], [5.7, 'thud', 0.4], [9.8, 'pop', 0.08], [12.75, 'thud', 0.4], [15.52, 'pop', 0.1], [17.72, 'bell', 0.1], [18.98, 'pop', 0.1], [22.21, 'thud', 0.3], [24.51, 'pop', 0.08], [31.72, 'thud', 0.4], [37.45, 'pop', 0.1], [40.2, 'pop', 0.1], [41.8, 'tap', 0.12]] },   // short times
  captions: { hide: [[0, 99]] },
};
