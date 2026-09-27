// Doran's presentation clocks. Ordinary Cleaver tempo equals a normal sword;
// the mass is expressed in the arc and recoil, not a strength penalty.
export const DORAN_HITSTOP = 45;
export const DORAN_SWINGS = Object.freeze({
  chop: {ms: 530, contact: .56, hitstop: 45},
  cleave: {ms: 465, contact: .52, hitstop: 45},
  sweep: {ms: 585, contact: .55, hitstop: 45},
  rise: {ms: 435, contact: .5, hitstop: 45},
  grand_cleave: {ms: 640, contact: .5, hitstop: 65},
});
export const DORAN_DAGGER_TEMPO = .18;
export const DORAN_BEAT_TEMPO = Object.freeze({
  cleaver: {windup: 140, strike: 200, impact: 120, recover: 90},
  daggers: {windup: 55, strike: 120, impact: 70, recover: 55},
  grand_cleave: {windup: 230, strike: 280, impact: 170, recover: 170},
});
