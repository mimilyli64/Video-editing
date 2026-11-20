// Lougha Online - cours d'allemand (DEUTSCH A1+A2). Darija voice, French captions only on the phrases we understood.
// Green screen keyed onto the Lougha studio photo the creator sent (source/key.py), framed shins-up, zoom transitions on each cut.
// One overlay: source/mg.html -> assets/mg.mov (motion graphics + captions). All times are SOURCE seconds.
window.SPEC = {
  title: 'Lougha Online - Deutsch',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 560], q: 1 },
  cut: [[0, 0.25], [3.1, 3.37], [9.02, 9.22], [12.75, 13.24], [17.19, 18.14], [22.41, 23.21], [25.71, 26.77], [29.29, 29.98], [33.84, 34.22], [42.13, 43.01], [49.59, 51.21], [56.55, 99]],
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 70, layer: 'over' }],
  music: { breaks: [] },
  mix: { ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0,
    extra: [[1.6, 'pop', .1], [7.2, 'pop', .08], [10.2, 'pop', .08], [14.9, 'thud', .4], [23.6, 'bell', .1], [36.6, 'pop', .1], [44.2, 'pop', .08], [48.4, 'bell', .1], [56.0, 'tap', .12]] },
  captions: { hide: [[0, 99]] },
};
