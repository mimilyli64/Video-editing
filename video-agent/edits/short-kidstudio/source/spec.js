// KidStudio: "Le meilleur investissement, c'est votre enfant". All times are SOURCE seconds (files/words.md).
// Style "ref" changed for KidStudio: rounded Fredoka, the logo's colors (navy, sky blue, green, yellow, orange), sticker cards.
// One overlay (source/mg.html -> assets/mg.mov) holds every motion graphic and the captions, mapped short -> source with KEEPS.
// assets/source.mp4 = the take with zoom transitions on each cut (no blur), see source/transitions-zoom-expr.txt.
window.SPEC = {
  title: 'KidStudio - anglais pour enfants',
  media: { mg: { src: 'assets/mg.mov', width: 1080, alpha: true } },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 640] },
  // dead air between sentences cut to a short breath; the two silences after « comme ça » / « ou ça » are kept for the Macron clips
  cut: [[0, 0.38], [3.86, 4.54], [6.98, 7.97], [12.0, 12.28], [23.9, 24.1], [27.93, 28.23], [32.93, 33.51], [37.33, 37.81], [44.25, 44.88], [47.3, 99]],
  tighten: { gap: 99 },
  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },
  actors: [],
  scenes: [{ type: 'overlay', media: 'mg', from: 0, to: 60, layer: 'over' }],
  music: { breaks: [] },
  sfx: {
    swish: 0, accents: 0,
    extra: [[2.88, 'thud', .5], [3.5, 'bell', .1], [11.1, 'pop', .1], [16.95, 'bell', .12], [23.4, 'thud', .4], [24.32, 'pop', .1], [29.2, 'pop', .1], [38.7, 'pop', .1], [46.0, 'tap', .12]],
    files: [
      { at: 13.05, src: 'assets/sfx/macron-b.mp3', gain: -2 },
      { at: 14.80, src: 'assets/sfx/macron-a.mp3', gain: -2 },
    ],
  },
  captions: { hide: [[0, 99]] },   // drawn in mg.html
};
