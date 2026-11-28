// KidStudio - Imen, programme d'anglais (4 compétences). French voice and captions. Filter glitch: the face filter is not yet
// aligned on the first frames (0-0.15 s); the edit starts at 0.17 s, before her first word, so it never shows.
// Fixed framing per take (1 / 1.12 alternating, no zoom move), silences between sentences cut, KidStudio look (Fredoka, logo colours),
// graphics on the ceiling above her head, captions on her sweater. assets/source.mp4 = cut take; mg.html maps cut -> take time.
window.SPEC = {
  title: 'KidStudio - Imen',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 900], q: 1 },
  cut: [],
  tighten: { gap: 99, lead: 5, tail: 5 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 120, layer: 'over' }],
  music: { src: 'assets/music/vlog-bed.wav', offset: 0, breaks: [] },
  mix: { music: -28, duck: .5, ceil: -2.2 },
  grade: false,
  sfx: { swish: 0, accents: 0, extra: [[2.68, 'thud', 0.35], [3.58, 'pop', 0.08], [9.03, 'bell', 0.1], [14.49, 'pop', 0.1], [21.22, 'pop', 0.08], [22.17, 'pop', 0.08], [23.17, 'pop', 0.08], [24.07, 'pop', 0.08], [25.77, 'thud', 0.3], [27.17, 'pop', 0.06], [28.27, 'pop', 0.06], [29.07, 'pop', 0.06], [29.67, 'pop', 0.06], [31.87, 'thud', 0.3], [34.75, 'pop', 0.08], [35.2, 'pop', 0.08], [35.9, 'pop', 0.08], [42.6, 'pop', 0.1], [49.35, 'pop', 0.08], [56.1, 'pop', 0.08], [59.18, 'bell', 0.12], [63.88, 'pop', 0.1], [71.53, 'thud', 0.45], [74.55, 'tap', 0.12]] },   // short times
  captions: { hide: [[0, 999]] },
};
