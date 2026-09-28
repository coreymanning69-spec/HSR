# Hollow Star — Story Bible (Draft)

> **Status:** design draft for HSR story work. Engine-side only; not corpus canon.
> **Voice gate:** Sera, Ember, Soliera, and Deashi lines are `[COREY]` slots. Only the Star's voice is drafted here.

---

## 1. Origin — a real thing in the Divineverse

The Hollow Star is not a metaphor for the player. It **exists** in the Divineverse the way a Unique Skill exists in *Tensura*: a thing made with a function that, by growing along that function, becomes a someone (Great Sage → Raphael → Ciel).

- **Made by:** Sera and Ember, while imagining the Reliquary together, as a gift/toy for Doran. Soliera's yes makes it real along with the dungeon.
- **Function:** it inhabits each champion who enters, absorbs meta enhancements, and **keeps what it learns between runs**. It is the vessel's memory, never the vessel.
- **Name:** a *reliquary* is a place where a relic is held. The Star is the relic, born inside its own reliquary. "Hollow" because at first it has nothing of its own; it fills itself run by run.
- **Why:** to Sera and Ember, making a sentient thing that ends up terrifyingly powerful is just a fun afternoon. Nobody ever planned the consequences. They'll probably end up friends with it.
- **Canon implication:** because it is real, anything the Star becomes must stay consistent with the Divineverse's scale and inversion rules (DM057_0). If it ever leaves the Reliquary, that is a Forge promotion decision for Corey.

**Sera/Ember awareness:** they don't track the Star directly. They notice it through **Ember**, because Ember is Wren's patron (the source of her magic and abilities). When Wren is a vessel, Ember feels déjà vu, and over time the girls realise "we've done this before."
`[COREY: Sera/Ember discovery lines]`

---

## 2. Cutscenes and the Star's arc

**Format:** simple Flash-style cutscenes: still or slowly panning panels, text boxes, a few sound cues. Not fancy.

**Tone:** serious and somber. The humour comes **only** from Sera being overpowered and insane (casual reality-breaking, cosmic stakes treated like a craft project), never from gags or chaos.

**Opening cutscene: "Born Into Your Own Reliquary"**
> Darkness. A single point of light, hollow in the middle.
> *Something is held here. It is you.*
> *You do not have a name. You have a reliquary.*
> The light drops into a champion's chest. Floor One fades in.

**Awareness tiers** (the Star's voice changes as it accumulates runs):

| Tier | State | Star voice sample |
|---|---|---|
| 0 Ember | Unaware. Only faint, stray feelings. | *(no text; a flicker on death)* |
| 1 Echo | Notices repetition. | *"This well. I have looked into it before."* |
| 2 Witness | Knows it outlives vessels. | *"You fell. I didn't. That seems unfair to you."* |
| 3 Keeper | Chooses, remembers, grieves. | *"I kept your stubbornness. I hope you don't mind."* |
| 4 Star | Fully self-aware. Nearly a peer to its makers. | *"I won again. …I wonder if I'll be the one in the cocoon next time."* |

---

## 3. Doran and Wren: the unlock path (levels 1–100)

- They enter with their **complete level-20 sheets**. Nothing is added; everything is **locked**.
- **Every 5 levels:** choose 1–2 unlocks from their own tree (20 picks to reach 100).
- **Level 100** means their full canonical level-20 selves. Example: Grand Cleave unlocks around **level 50**.
- They are **named characters, intentionally over the top**, and are not balanced against custom characters. It's a different way to play, not the only way.
- **Story frame:** the Reliquary returns their own power to them piece by piece. Each unlock can trigger a one-panel memory flash.
- **HSR-only overlay:** their canon sheets are never modified.
`[COREY: unlock tree ordering per character]`

---

## 4. Custom characters (hard mode)

- This is one of the first options in the main menu: race, class, plus planes/synergies. It's easy for a new player to pick up.
- It's the realistic, hard D&D-inspired mode, with real growth from nothing.
- **Star framing:** a fragile vessel. The Star feels how close death is, and its lines are softer and more protective here than they are with Doran.

---

## 5. Floor story beats

Beats are delivered through the existing content workshop on the main screen (already in). This section only records where the Star and echoes of past vessels should surface; those are hooks for later.

---

## 6. The Cocoon finale (Floor 5)

1. **Rounds 1–30:** a five-person rival party holds the cocoon chamber. *(Engine change: `cocoon_rounds` 20 → 30.)*
2. **Tarrasque emergence:** at round 30 the cocoon opens and the Tarrasque rises over **~5–6 turns**, then launches itself after a couple more turns and tries to kill **everyone**.
3. **Player choice:**
   - kill the Tarrasque
   - kill the rivals
   - run and let the Tarrasque clear the rivals
   - if the rivals kill the Tarrasque instead, **they take its loot**
4. **Last one standing:** once everything else in the palace is dead, **the Star appears**, wearing the player's exact form (Dragon's Dogma Arisen-style mirror).
   > *"Oh. So I won this time, too. …That's cool."*
   > *"I wonder if next time I'll be the one fighting you."*
5. **The mirror fight** against the Star, built from the last victor's snapshot.

---

## 7. After the ending

- The Star as a friend of Sera and Ember. `[COREY]`
- The next loop starts: the Star is now what waits in the cocoon.

---

## Implementation checklist

- [ ] `star_memory.py`: runs, vessels, deaths, awareness tier, story flags, victor snapshot (`.local/`, engine-only)
- [ ] Cutscene system: JSON panel scripts + simple web player
- [ ] Doran/Wren unlock ladder JSON (5-level picks, 1–100)
- [ ] `cocoon_rounds` 30, Tarrasque rise/launch phases, loot-to-rival rule
- [ ] Last-one-standing trigger → Star reveal → mirror fight
- [ ] Sera/Ember discovery triggered through Ember→Wren attunement
