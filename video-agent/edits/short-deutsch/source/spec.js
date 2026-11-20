// Lougha Online - cours d'allemand (DEUTSCH A1+A2). Darija voice, French captions only on the phrases we understood.
// Green screen keyed onto the German study room the creator sent (plaque relabelled LOUGHA ONLINE), framed shins-up.
// assets/source.mp4 = keyed take with the silences cut + a camera move: smooth zooms in/out on key words and cuts, slow breathing.
// One overlay: source/mg.html -> assets/mg.mov (motion graphics + captions). All times are SOURCE seconds.
window.SPEC = {
  title: 'Lougha Online - Deutsch',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 560], q: 1 },
  cut: [],   // the silences are already cut in assets/source.mp4 (keeps in mg.html KEEPS)
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 70, layer: 'over' }],
  music: { breaks: [] },
  mix: { ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0,
    extra: [[0.75, 'pop', 0.1], [6.48, 'pop', 0.1], [8.08, 'thud', 0.35], [11.78, 'pop', 0.08], [13.69, 'thud', 0.5], [21.14, 'bell', 0.1], [27.89, 'thud', 0.45], [30.31, 'pop', 0.1], [31.51, 'bell', 0.1], [38.28, 'pop', 0.08], [40.03, 'pop', 0.1], [42.38, 'bell', 0.1], [47.61, 'pop', 0.1], [48.71, 'tap', 0.12]] },   // short times (source.mp4 is already cut)
  captions: { hide: [[0, 99]] },
};
