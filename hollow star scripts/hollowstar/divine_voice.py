"""Divine answers to Wren's cleric spells, plus Sera and Ember's general pools.

Presentation-only; never changes a roll or a result.

Theology (DM041_B2): Wren's cleric-side power is Ember's; her Divine Soul
source is Soliera, who routes and manages the whole system. Wren has no
Divine Intervention button — when something exceeds her she *asks*, and that
is a relationship, not a feature. Ember and Wren are both still learning how
this channel works, so Ember's answers are curious, compressed, sometimes
surprised that it worked (DM028_3b: question first, then quiet; vocabulary
still forming; does not understand dishonesty; child register, adult body).

Voice lock (DM000_3): Corey delegated Sera and Ember spoken dialogue for this
work. Soliera is NEVER voiced — no speech, thought or intent. She appears only
as presence/aftermath lines (speaker "Presence") describing what the channel
does. Sera (DM027_0 / DM030_2): joy first, singsong, exact, nicknames,
never hesitates, teasing with mortals, reverent about Soliera, cannot read.
"""
from __future__ import annotations

import hashlib

# ---------------------------------------------------------------------------
# General event pools (replace the old one-line-per-kind table). Each event
# draws one Sera line and/or one Ember line, rotated without quick repeats.
# ---------------------------------------------------------------------------
SERA = {
    "entry": [
        "Ooh, a new room. Let's see who lives here~",
        "Knock knock. Nobody? Rude.",
        "Pretty room. Shame about whatever's hiding in it.",
        "Shiny, you go first. You're the one they'll look at anyway.",
        "Birdie, what's it doing? Tell me it's doing something fun.",
        "It's quiet. I hate quiet. Somebody make a noise.",
    ],
    "combat": [
        "There we go! Finally, someone wants to play.",
        "Ooh, it swings like it means it. Cute.",
        "Hit it again, Shiny. It didn't learn yet.",
        "That one's counting on you being polite. Don't be.",
        "One, two... I'm keeping count, you know.",
        "Birdie, don't stand there. It's looking at you.",
        "Faster. It's thinking. Don't let it think.",
    ],
    "critical": [
        "OH. Did you see that? Do it again!",
        "Now THAT'S how you say hello.",
        "Mm. That one I felt from here.",
        "See? You CAN be scary. I knew it.",
        "Good boy, Shiny. Very good.",
    ],
    "blocked": [
        "It said no! How rude. Ask it differently.",
        "Aww, it has a trick. Break the trick.",
        "Wrong door, sweetheart. Try the other one.",
        "It's hiding behind something. Take the something away.",
    ],
    "reward": [
        "Shiny things! Gimme. ...Fine, they're yours.",
        "Gold, gold, gold~ Don't spend it all on boring stuff.",
        "See? Being scary pays.",
        "Is that a book? Don't make me read it.",
    ],
    "upgrade": [
        "Prettier! Stronger, too, I guess.",
        "A new toy. Don't break it on the first thing that bites.",
        "Ooh, it hums now. I like when they hum.",
    ],
    "danger": [
        "Uh oh~ Now it's interesting.",
        "Something's waking up. Be ready, both of you.",
        "Careful, Birdie. That one's not playing nice.",
        "Hm. That's the part that bites.",
    ],
    "terminal": [
        "Done already? Aww. Okay. You did good.",
        "Everyone's still in one piece! I'm impressed. A little.",
        "Go eat something, Shiny. You look hungry. You always look hungry.",
        "Next time, make it harder. For them, I mean.",
    ],
}

EMBER = {
    "entry": [
        "What was this room for? Before.",
        "It's hiding a rule. Which one?",
        "The Weave is thin here. Why?",
        "Someone left. Did they want to?",
        "Smells like old fire. Not mine.",
        "Doran, did you count the doors? How many?",
    ],
    "combat": [
        "Why does it want to hurt you? ...Oh. It's scared.",
        "That was on purpose. I saw.",
        "It moves like it learned from something bigger.",
        "Wren, the magic around it — it's knotted. Can you see?",
        "It keeps trying the same thing. Why?",
    ],
    "critical": [
        "That went all the way through. How?",
        "Oh. It stopped. Is it done?",
        "Big result. Small opening. I want to know how.",
    ],
    "blocked": [
        "It said no. How did it say no?",
        "There's a rule on it. I can feel the edges.",
        "Not that way. Some other way. Which?",
    ],
    "reward": [
        "Why does it pay us for asking questions?",
        "That one's warm. The others aren't. Why?",
        "More things. Where did they come from before here?",
    ],
    "upgrade": [
        "It changed. I can measure it. Good.",
        "Heavier now. Not heavy enough? ...It's fine.",
        "It remembers the fight. Can things remember?",
    ],
    "danger": [
        "Something's building. What does it do when it's full?",
        "It's getting hot. Not me. Something else.",
        "Wren. Look. Do you see it too?",
    ],
    "terminal": [
        "It's over. But the pattern isn't. What's next?",
        "Everyone's here. I counted. Twice.",
        "Can we do it again? Differently?",
    ],
}

# ---------------------------------------------------------------------------
# Wren's divine spells. Each entry lists Ember's answer (first-time discovery
# lines vs. later casts), optional Sera lines, and optional Presence lines —
# the channel's behaviour where Soliera's routing shows. Presence lines state
# only what is observed: never her words, thoughts or intent.
# ---------------------------------------------------------------------------
DIVINE = {
    # -- asking upward (the spells that literally contact a god) ---------------
    "Augury": {
        "ember_first": ["Wren asked me if it's good or bad. ...I don't know yet. Weal? Woe? Both?",
                        "You asked. I looked. It's... mostly okay? Is 'mostly' an answer?"],
        "ember": ["Weal. I think. Don't go left.", "Woe. A little woe. Bring Doran.",
                  "Both. It's both. Is that allowed?", "I looked. Nothing looked back. That's good, right?",
                  "It's good. Probably. I'm getting better at this."],
        "presence": ["The omen settles cleanly, as if the question had been straightened on its way up."],
    },
    "Divination": {
        "ember_first": ["You're asking ME? Okay. Okay. Ask slowly.",
                        "I heard you. I don't know the answer. I'm going to go find it. Wait."],
        "ember": ["I found it. It's true. Mostly true. The true part is the important part.",
                  "Ask better, Wren. I mean — ask smaller. The big ones are hard to hold.",
                  "The answer is yes. The question was bigger than you asked, though.",
                  "I asked someone who knows. They knew."],
        "presence": ["The answer arrives already sorted, cleaner than a question that size should allow."],
    },
    "Commune": {
        "ember_first": ["Wren? You're talking to me. Directly. Is this what praying is?",
                        "Three questions? Only three? I have more than three for YOU."],
        "ember": ["Yes. No. ...Ask the third one again, I wasn't ready.",
                  "Yes. Yes. I don't know — I'll know after. Is that okay?",
                  "No. And why do you want to know? You don't have to answer. I'm curious.",
                  "Yes. That one's easy. The next one isn't.",
                  "I like when you ask me things. Ask more things."],
        "sera": ["Birdie's calling home! Tell her I said hi~",
                 "Don't keep her on too long, Birdie. She gets distracted."],
        "presence": ["For a moment the line is very quiet and very wide, and every answer lands in order."],
    },
    "Planar Ally": {
        "ember_first": ["You want help? From... someone? I'll ask who's awake.",
                        "Nobody's ever asked me to send someone before. Hold on."],
        "ember": ["Someone's coming. I asked nicely. Be nice back.",
                  "I found one who said yes. They want something after. Is that fair?",
                  "I sent the one who asks the fewest questions. You're welcome."],
        "sera": ["Borrowing help? Cute. You could've just asked me.",
                 "If it gives you trouble, Birdie, tell me. I'll have a talk with it."],
        "presence": ["The summons is accepted before the words are finished, like the door was already open."],
    },
    "Word of Recall": {
        "ember_first": ["Home? Now? Okay — hold on to Doran, he's heavy."],
        "ember": ["Pulling you back. Don't let go of anyone.", "Home! Did you bring me anything?",
                  "Recall. I like this one. You come back every time."],
        "sera": ["Welcome home~ Wipe your feet, Shiny."],
        "presence": ["The road home is simply there — no drift, no delay — and the Sanctum is under your feet."],
    },
    "Gate": {
        "ember_first": ["You opened a hole in the world. Where does it go? Can I look?"],
        "ember": ["The Gate's awake. Who are you calling? Say their name right.",
                  "Careful what comes through. Things that come through remember who opened it."],
        "presence": ["The Gate holds its shape perfectly. Something far above is keeping its edges straight."],
    },
    "Divine Word": {
        "ember_first": ["You said a word that makes the world listen. Where did you learn that? ...From me?"],
        "ember": ["It heard you. Everything heard you.", "Loud. Good loud."],
        "sera": ["Ooh, Birdie said a bad word. Say it again!"],
    },
    "Conjure Celestial": {
        "ember_first": ["You want a whole celestial? I'll ask. They're very tall."],
        "ember": ["One's coming. It's polite. Be polite.", "It said yes. It always says yes to you. Why?"],
        "presence": ["The celestial arrives already facing you, as if it had been told exactly where to stand."],
    },
    # -- the dead and the returning ---------------------------------------------
    "Revivify": {
        "ember_first": ["They were leaving. You caught them. How did you know to catch them?"],
        "ember": ["Back! They came back. Good.", "Their light was going out. It's lit now.",
                  "I held the door. You pulled. That's how it works?"],
        "sera": ["Nope, nobody leaves early. Good catch, Birdie."],
        "presence": ["The soul comes back without resistance, as though the way out had been quietly closed."],
    },
    "Raise Dead": {
        "ember_first": ["You want them back. ...Do they want to come back? I'll ask."],
        "ember": ["They said yes. They're coming.", "It took a while. They were far. They're back."],
        "presence": ["The return is slow and complete. Nothing is lost on the way."],
    },
    "Resurrection": {
        "ember_first": ["That was a long way to go and get someone. I didn't know I could."],
        "ember": ["Whole. All of them. Every piece.", "I went and got them. It was far. It was fine."],
        "presence": ["The body remakes itself around the soul, every detail exactly where it was."],
    },
    "True Resurrection": {
        "ember_first": ["There wasn't anything left. I made them from — from the idea of them. Is that them?"],
        "ember": ["All the way back. Even the parts that were gone.", "Made again. It's them. I checked twice."],
        "presence": ["Where nothing remained, someone stands. The making is flawless."],
    },
    "Speak with Dead": {
        "ember": ["They can talk! Ask them what it's like.", "They don't have to tell the truth. But near me, it's hard not to."],
    },
    # -- blessings, guardians, holy light ---------------------------------------
    "Bless": {
        "ember": ["Blessed. I think I did it right.", "There. Warm. Everyone feels warm?"],
        "sera": ["Aww, Birdie's sharing. Cute."],
    },
    "Guidance": {
        "ember": ["A little help. Just a little.", "Here. Lean on this."],
    },
    "Spirit Guardians": {
        "ember_first": ["You want spirits around you? I'll send the kind ones. ...Mostly kind."],
        "ember": ["They're circling. They like you.", "Guardians up. They bite things that bite you."],
        "sera": ["Pretty! Scary AND pretty. My favorite."],
    },
    "Spiritual Weapon": {
        "ember": ["A floating sword? Okay. I'll hold it up.", "It hits what you point at. Point well."],
    },
    "Guardian of Faith": {
        "ember": ["I put someone at the door. They don't move. Ever."],
    },
    "Sacred Flame": {
        "ember": ["Fire from nowhere. Mine, sort of.", "Burn it. Gently. No, not gently."],
    },
    "Holy Aura": {
        "ember_first": ["You're glowing. Everyone's glowing. Did I do that?"],
        "ember": ["Bright. They can't look straight at you.", "Everyone's safe inside the light."],
        "sera": ["Ooh, shiny! Now you all match Shiny."],
        "presence": ["The light is steady and even, as if its source never had to strain."],
    },
    "Death Ward": {
        "ember": ["If it tries to take you, it gets me instead. I don't let go.",
                  "Warded. Death has to ask first now."],
    },
    "Sanctuary": {
        "ember": ["Nobody's allowed to hit you. I said so.", "Safe. Stay safe."],
        "sera": ["Hiding, Birdie? Smart. I'll hit them for you."],
    },
    "Beacon of Hope": {
        "ember": ["Hope. That's a funny thing to give. Here.", "Everyone breathes easier now. I can hear it."],
    },
    "Heroes' Feast": {
        "ember_first": ["You made food out of prayer? Can I have some?"],
        "ember": ["Feast! Doran's going to eat all of it.", "Nobody gets sick after this. I promise."],
        "sera": ["Shiny, save some for the rest of us. SHINY."],
    },
    "Hallow": {
        "ember": ["This place is ours now. It feels different. Does it feel different to you?"],
    },
    "Forbiddance": {
        "ember": ["Nobody comes in without knocking. Nobody."],
    },
    # -- healing ------------------------------------------------------------------
    "Heal": {
        "ember": ["All better. All of it.", "Fixed. Every cut."],
        "sera": ["See, Shiny? Birdie takes care of you."],
    },
    "Mass Heal": {
        "ember_first": ["Everyone at once? That's a lot of hurting to take away. ...Okay. Done."],
        "ember": ["Everyone. All at once. Easy."],
        "presence": ["Every wound in reach closes at the same instant, as though counted in advance."],
    },
    "Prayer of Healing": {
        "ember": ["I heard the prayer. Here.", "Rest. It'll close while you rest."],
    },
    "Mass Healing Word": {
        "ember": ["Heal, heal, heal. There."],
    },
    "Cure Wounds": {
        "ember": ["There. Closed.", "That one was deep. It's shut now."],
    },
    "Healing Word": {
        "ember": ["Quick one. Here.", "Still standing? Good."],
    },
    "Greater Restoration": {
        "ember": ["Whatever was stuck in you, it's gone.", "Unknotted. You feel lighter?"],
    },
    # -- Liberation / Portal doctrine -------------------------------------------
    "Freedom of Movement": {
        "ember": ["Nothing can hold you now. I checked.", "Unstuck. Stay unstuck."],
    },
    "Banishment": {
        "ember": ["Go away! ...Where did it go? I want to know where it went."],
        "sera": ["Bye bye~ Don't come back."],
    },
    "Plane Shift": {
        "ember_first": ["Another world? Which one? Can I pick?"],
        "ember": ["Hold hands. Everyone. Now."],
        "presence": ["The crossing is seamless, as if the worlds had been lined up beforehand."],
    },
    "Astral Projection": {
        "ember": ["You're so small up here. And silver. Don't cut the cord."],
    },
    "Dispel Evil and Good": {
        "ember": ["It doesn't belong here. It's going home now."],
    },
}

# Ember-voiced flavour for Wren's Channel Divinity and Divine Soul features.
FEATURES = {
    "dimensional_shift": {"ember": ["Blink! Where'd you go? Oh, there.", "You slipped through a crack. I saw."]},
    "indomitable_spirit": {"ember": ["It tried to hold you. It can't. Nothing can.", "Free. That's the whole point."]},
    "unearthly_recovery": {"presence": ["Wren's strength floods back all at once, more than the wound took."],
                           "sera": ["Up you get, Birdie. No lying around."]},
    "favored_by_the_gods": {"presence": ["The miss bends into a hit, as if the odds had been adjusted by a steady hand."]},
}

SERA_CHANCE = 0.35
RECENT = 20


def _roll(*parts) -> float:
    return int.from_bytes(hashlib.sha256(":".join(map(str, parts)).encode()).digest()[:8], "big") / 2**64


def _choose(pool, memory, salt):
    if not pool:
        return None
    recent = memory.setdefault("recent", [])
    fresh = [line for line in pool if line not in recent] or pool
    text = fresh[int(_roll(salt) * len(fresh))]
    recent.append(text)
    del recent[:-RECENT]
    return text


def general(kind: str, turn: int, state: dict, seed="") -> list[dict]:
    """One Sera and/or one Ember line for a general event kind."""
    memory = state.setdefault("voices", {})
    lines = []
    roll = _roll(seed, turn, kind, "who")
    speakers = ("Sera", "Ember") if roll < 0.45 else ("Sera",) if roll < 0.75 else ("Ember",)
    for speaker in speakers:
        pool = (SERA if speaker == "Sera" else EMBER).get(kind)
        text = _choose(pool, memory, f"{seed}:{turn}:{kind}:{speaker}")
        if text:
            lines.append({"speaker": speaker, "text": text, "trigger": kind,
                          "priority": "high" if kind in {"critical", "terminal"} else "normal",
                          "register": "commentary"})
    return lines


def _spell_name(spell_id) -> str:
    return str(spell_id or "").split("@", 1)[0].strip()


def divine(run, event: dict, turn: int, state: dict, caster_name: str | None, seed="") -> list[dict]:
    """Answer a divine spell or feature Wren just used. Empty list if not divine."""
    if str(caster_name or "").lower() != "wren":
        return []
    spell = _spell_name(event.get("spell"))
    entry = DIVINE.get(spell)
    feature = None
    if entry is None:
        feature = str(event.get("feature") or event.get("kind") or event.get("type") or "").lower()
        entry = FEATURES.get(feature)
    if entry is None:
        return []
    key = spell or feature
    memory = state.setdefault("voices", {})
    counts = memory.setdefault("divine_counts", {})
    counts[key] = int(counts.get(key, 0)) + 1
    first = counts[key] == 1
    lines = []
    ember_pool = entry.get("ember_first") if first and entry.get("ember_first") else entry.get("ember")
    text = _choose(ember_pool, memory, f"{seed}:{turn}:{key}:ember")
    if text:
        lines.append({"speaker": "Ember", "text": text, "trigger": f"divine:{key}", "priority": "high",
                      "register": "divine", "first_time": first})
    if entry.get("presence") and (first or _roll(seed, turn, key, "presence") < 0.4):
        lines.append({"speaker": "Presence", "text": _choose(entry["presence"], memory, f"{seed}:{turn}:{key}:p"),
                      "trigger": f"divine:{key}", "priority": "normal", "register": "presence"})
    if entry.get("sera") and _roll(seed, turn, key, "sera") < SERA_CHANCE:
        lines.append({"speaker": "Sera", "text": _choose(entry["sera"], memory, f"{seed}:{turn}:{key}:sera"),
                      "trigger": f"divine:{key}", "priority": "normal", "register": "commentary"})
    return lines
