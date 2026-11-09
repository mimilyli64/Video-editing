// Short: "Lougha Online, la formation de français 100% interactive". All times are SOURCE seconds (files/words.md).
// Style "ref" (copied from the Lougha Online Fast Track reel) with the take's own palette: terracotta, cream, caramel, gold, espresso.
// Beats (one motion-graphics overlay, source/mg.html -> assets/mg.mov, keyed on source time):
//   A 0-3.55   hook: serif "Vous comprenez / le français" + flag + check, reversal "mais à l'oral..." -> "?" + bubble "euh..."
//   B 3.66-7.4 word tiles + magnifier ("cherchez vos mots"), sentence with a red squiggle under "allé", "correcte ?" flipping
//   C 7.5-10.9 bulb lights on "simple", speaking head -> ear waves ("communiquer"), the "2" badge + two empty slots
//   D 10.9-14  slots fill: Grammaire + bricks "solide", Oral + mic levels + week ticked ("régulière")
//   E 14.1-17.4 Lougha Online pill (logo), 100% counter, arc "interactive", orbiting icons
//   F 17.5-21  toggles "La grammaire" / "La communication" switched on, gold ring on "vraiment besoin"
//   G 21-24.9  three tiles: Les temps (clock running), Les phrases (words assembling), Expressions (coffee steaming)
//   H 25-28.4  chat bubbles (échanges) + chips Au café / Au marché / Au travail (situations réelles)
//   I 28.5-end CTA: logo + name, Loughaonline.com pill, cursor click
window.SPEC = {
  title: 'Lougha Online - français à l\'oral',
  media: {
    mg: { src: 'assets/mg.mov', width: 1080, alpha: true },
  },
  cam: { crop: [0, 0, 1080, 1920], eyes: [540, 495] },   // assets/source.mp4 = the take with zoom transitions on its own jump cuts (alternating 1 / 1.12 framing: ease-in push-in through the cut toward a tight shot, zoom-out settle after the cut toward a wide shot, 0.5 %/s drift, NO blur)
  // the dead air between sentences (where the take switches takes) cut to a short breath; commas keep their pause
  cut: [[0, 0.58], [3.45, 4.08], [7.11, 7.9], [10.89, 11.38], [13.9, 14.51], [20.73, 21.49], [24.7, 25.22], [28.24, 28.81], [31.5, 99]],
  tighten: { gap: 99 },   // no automatic micro-cut (rejected: « pas naturel »)

  layout: { keys: [[0, 0]] },
  zoom: { keys: [[0, 1]] },

  actors: [],
  scenes: [
    { type: 'overlay', media: 'mg', from: 0, to: 32, layer: 'over' },   // mg.html maps short time -> source time itself (KEEPS)
  ],

  music: { breaks: [] },
  sfx: {
    swish: 0, accents: 0,
    extra: [[1.05, 'pop', .1], [2.93, 'thud', .5], [10.25, 'thud', .5], [14.52, 'bell', .12], [16.62, 'pop', .1], [30.15, 'tap', .12]],
    files: [
      { at: 4.08, src: 'assets/sfx/zhhh.mp3', peak: true, gain: -10 },
      { at: 17.55, src: 'assets/sfx/pop-back.mp3', gain: -14 },
    ],
  },

  captions: {
    yKeys: [[0, 1420]],
    replace: [['mais qui dit l\'or,', 'mais à l\'oral,'], ['l\'oral online,', 'Lougha Online,'], ['de description', 'd\'inscription'], ['La raison', 'La raison']],
    emph: ['hésitez.', 'mots', 'correcte.', 'simple,', 'deux', 'choses', 'grammaire', 'solide', 'régulière', 'l\'oral.', 'Lougha', 'Online,', '100%', 'interactive,', 'communication', 'besoin.', 'temps,', 'phrases', 'quotidien.', 'échanges', 'réelles.', 'bio.'],
    hide: [[0, 99]],   // captions are drawn in mg.html (word by word, key words big and gold, like the reference)
  },
};
