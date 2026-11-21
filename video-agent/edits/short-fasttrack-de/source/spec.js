// Lougha Online - Fast Track (allemand A1+A2 en 2 mois). Darija voice, French captions only on the phrases we understood.
// assets/source.mp4 = the take with silences cut + camera moves (source/camera-zoom-expr.txt); mg.html maps cut time -> take time (keeps.json).
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
  music: { breaks: [] },
  mix: { ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0, extra: [[0.4, 'pop', 0.1], [2.8, 'pop', 0.08], [5.7, 'thud', 0.45], [9.8, 'pop', 0.08], [12.51, 'thud', 0.45], [15.48, 'pop', 0.1], [17.68, 'bell', 0.1], [19.14, 'pop', 0.1], [22.57, 'thud', 0.35], [24.87, 'pop', 0.08], [32.48, 'thud', 0.45], [38.41, 'pop', 0.1], [41.06, 'pop', 0.1], [42.59, 'tap', 0.12]] },   // short times
  captions: { hide: [[0, 99]] },
};
