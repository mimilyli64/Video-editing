// Lougha Online - Super Fast Track (allemand). Edited after the creator's reference (ruemedias-style ad): few cuts, each shot a fixed
// framing (wide / medium alternating, never a zoom move), stacked kinetic headlines at the top, 1-2 word bold-italic captions, glossy
// jewel tiles that stack, a light flash before the CTA. Lougha identity: purple / gold, logo, Loughaonline.com. French captions only on
// the phrases we understood (Darija voice). v2: the sit-down hook (0-1.15 s) is kept; « très intensif » passage captioned. assets/source.mp4 = cut take; mg.html maps cut time -> take time (keeps.json).
window.SPEC = {
  title: 'Lougha Online - Super Fast Track',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 640], q: 1 },
  cut: [],
  tighten: { gap: 99, lead: 5, tail: 5 },   // keep every frame of source.mp4 (the sit-down hook included)
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 70, layer: 'over' }],
  music: { src: 'assets/music/fasttrack-bed.wav', offset: 0, breaks: [] },
  mix: { music: -27, duck: .5, ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0, extra: [[1.55, 'pop', 0.08], [2.75, 'pop', 0.08], [4.56, 'thud', 0.4], [12.55, 'pop', 0.08], [13.75, 'pop', 0.08], [15.25, 'thud', 0.4], [17.55, 'pop', 0.1], [21.55, 'pop', 0.08], [23.95, 'thud', 0.35], [25.55, 'tap', 0.06], [27.71, 'pop', 0.08], [30.61, 'pop', 0.06], [32.11, 'pop', 0.06], [35.41, 'pop', 0.08], [37.81, 'pop', 0.08], [39.38, 'pop', 0.08], [39.88, 'pop', 0.08], [44.56, 'pop', 0.1], [48.26, 'tap', 0.12]] },   // short times
  captions: { hide: [[0, 99]] },
};
