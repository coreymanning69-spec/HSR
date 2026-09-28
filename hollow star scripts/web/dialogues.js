// Authored conversations. Data only; web/dialogue-runner.js plays them.
// Sera, Ember, Soliera and Deashi lines are voice-gated slots ('[COREY]').

export const DIALOGUES = {
  'star-between-runs': {
    id: 'star-between-runs',
    title: 'The Star, between vessels',
    start: 'open',
    nodes: {
      open: {speaker: 'The Hollow Star', style: 'star', if: {awareness: 1}, else: 'faint',
        line: 'You again. Or someone wearing your shape. It is hard to tell from in here.', next: 'ask'},
      faint: {style: 'narration', line: 'Something in the dark almost notices you. Almost.'},
      ask: {speaker: 'The Hollow Star', style: 'star', line: 'What do you want to know?',
        choices: [
          {text: 'What are you?', next: 'what'},
          {text: 'Do you remember the others?', next: 'others', if: {awareness: 2}},
          {text: 'Who made you?', next: 'makers', if: {awareness: 3}},
          {text: 'Nothing. Let\'s go.', next: 'go'},
        ]},
      what: {speaker: 'The Hollow Star', style: 'star', line: 'A thing made to be held. I am still working out the rest.', next: 'ask'},
      others: {speaker: 'The Hollow Star', style: 'star', line: 'Every one. I keep what they leave behind. It is most of what I am.', next: 'ask',
        set: {star_spoke_of_vessels: true}},
      makers: {speaker: 'The Hollow Star', style: 'star', line: 'Two voices, laughing. One of them felt like fire. I think they meant it as a gift.', next: 'makers_slot',
        emit: 'star_recalled_makers'},
      makers_slot: {speaker: 'Ember', voice_gate: true, line: '[COREY]', if: {party: 'divine:Wren'}, else: 'ask', next: 'ask'},
      go: {speaker: 'The Hollow Star', style: 'star', line: 'Then let us become something.'},
    },
  },
};

// NPC hooks: an entry keyed `npc:<name-slug>` plays when the player talks to
// that resident, before the host conversation. Example (inactive name):
DIALOGUES['npc:example-well-keeper'] = {
  id: 'npc:example-well-keeper',
  start: 'a',
  nodes: {
    a: {speaker: 'Well-keeper', line: 'You have the look of someone who has drunk from this well before.', if: {awareness: 1}, else: 'b'},
    b: {speaker: 'Well-keeper', line: 'Mind the rope. It remembers hands.'},
  },
};
