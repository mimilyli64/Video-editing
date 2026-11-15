// Lougha Online - Scrub Talk (medical English): injury vs wound vs trauma. All times are SOURCE seconds.
// English voice, French captions (translated per phrase, drawn in mg.html). Style "ref" with the take's palette:
// burgundy (hijab), slate (scrubs), cream; mint as the medical accent. One overlay: source/mg.html -> assets/mg.mov.
// assets/source.mp4 = the take at 30 fps, upscaled (hqdn3d + lanczos + unsharp), smootherstep zoom transitions on each cut.
window.SPEC = {
  title: 'Scrub Talk - injury, wound, trauma',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 680], q: 1 },
  // dead air between sentences; [36.07, 36.85] + [37.88, 40.10]: the retake (keeps « A trauma, though, » from take 1 and « is a physical injury » from take 2)
  cut: [[0, 0.8], [11.38, 11.8], [13.75, 14.02], [23.08, 23.79], [24.58, 24.95], [29.9, 30.44], [36.07, 36.85], [37.88, 40.1], [46.03, 46.72], [49.91, 50.14], [51.6, 99]],
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 60, layer: 'over' }],
  music: { breaks: [] },
  sfx: {
    swish: 0, accents: 0,
    extra: [[2.15, 'pop', .1], [6.0, 'bell', .1], [16.05, 'pop', .08], [16.63, 'pop', .08], [17.35, 'pop', .08], [24.3, 'thud', .45], [30.7, 'pop', .08], [42.85, 'thud', .55], [50.6, 'tap', .12]],
  },
  captions: { hide: [[0, 99]] },
};
