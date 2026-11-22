// Lougha Online - Super Fast Track (allemand). Edited after the creator's reference (ruemedias-style ad): few cuts, each shot a fixed
// framing (wide / medium alternating, never a zoom move), stacked kinetic headlines at the top, 1-2 word bold-italic captions, glossy
// jewel tiles that stack, a light flash before the CTA. Lougha identity: purple / gold, logo, Loughaonline.com. French captions only on
// the phrases we understood (Darija voice). assets/source.mp4 = cut take; mg.html maps cut time -> take time (keeps.json).
window.SPEC = {
  title: 'Lougha Online - Super Fast Track',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 640], q: 1 },
  cut: [],
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 70, layer: 'over' }],
  music: { src: 'assets/music/fasttrack-bed.wav', offset: 0, breaks: [] },
  mix: { music: -27, duck: .5, ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0, extra: [[0.4, 'pop', 0.08], [1.6, 'pop', 0.08], [11.4, 'pop', 0.08], [12.6, 'pop', 0.08], [14.1, 'thud', 0.4], [16.4, 'pop', 0.1], [20.4, 'pop', 0.08], [22.8, 'thud', 0.35], [24.4, 'tap', 0.06], [26.56, 'pop', 0.08], [29.46, 'pop', 0.06], [30.96, 'pop', 0.06], [34.26, 'pop', 0.08], [36.66, 'pop', 0.08], [38.23, 'pop', 0.08], [38.73, 'pop', 0.08], [43.41, 'pop', 0.1], [47.11, 'tap', 0.12]] },   // short times
  captions: { hide: [[0, 99]] },
};
