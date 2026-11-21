// Lougha Online - slow English vlog at the mall. Vlog style: natural pace, jump cuts with quick punch-ins, zooms onto each item,
// English captions word by word (current word on a pink pill), NEW WORD stickers with the French translation, light synth music.
// assets/source.mp4 = the take with long gaps cut + camera moves (source/camera-zoom-expr.txt); mg.html maps cut time -> take time (keeps.json).
window.SPEC = {
  title: 'Slow English vlog - shopping',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 700], q: 1 },
  cut: [],
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 120, layer: 'over' }],
  music: { src: 'assets/music/vlog-bed.wav', offset: 0, breaks: [] },
  mix: { music: -27, duck: .45, ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0, extra: [[0.3, 'pop', 0.1], [5.45, 'pop', 0.08], [6.95, 'pop', 0.08], [10.45, 'pop', 0.08], [13.12, 'pop', 0.09], [17.32, 'pop', 0.09], [19.47, 'pop', 0.09], [22.52, 'pop', 0.09], [25.69, 'pop', 0.09], [27.24, 'pop', 0.09], [32.64, 'pop', 0.09], [35.14, 'pop', 0.09], [37.44, 'pop', 0.09], [45.0, 'pop', 0.09], [48.55, 'pop', 0.09], [49.78, 'pop', 0.09], [57.3, 'pop', 0.09], [61.35, 'pop', 0.09], [27.99, 'tap', 0.06], [30.29, 'tap', 0.06], [51.23, 'tap', 0.06], [52.55, 'tap', 0.06], [53.45, 'tap', 0.06], [63.45, 'bell', 0.1], [70.45, 'tap', 0.12], [70.47, 'bell', 0.1]] },   // short times
  captions: { hide: [[0, 999]] },
};
