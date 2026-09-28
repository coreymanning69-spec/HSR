// Ambient voice lines for residents and intelligent monsters. Data plus a
// tiny picker; app.js uses it for the right-click card and the Examine/Talk
// dialog. Lines are flavor only: they never change host state.
//
// Pools per archetype: greet, idle, self, place, rumor, farewell (talk topics),
// taunt, bloodied, parley (monsters), observe (examine notes). Missing pools
// fall back to the generic person/monster archetype.

const V = {};

V.person = {kind: 'person', match: null,
  greet: [
    'Well met. You look like you came up out of somewhere unpleasant.',
    'Evening. Or morning. Hard to tell with the light the way it is.',
    'Ah — a new face. We get fewer of those than we used to.',
    'Keep your voice down, friend. Walls here have long memories.',
    'You\'re one of the well-walkers, aren\'t you? It\'s in how you stand.',
    'Hm? Oh. Sorry. I was listening for something.',
    'Welcome, I suppose. Mind the step, it bites.',
    'If you\'re selling, I\'m not buying. If you\'re asking, I might be telling.',
  ],
  idle: [
    'Rain again. Or ash. Same sound on the roof.',
    'My grandmother said the stars used to be closer. I think she meant it literally.',
    'I counted the bells this morning. There was one too many.',
    'Nobody sleeps well the night after someone goes down the well.',
    'You ever feel watched by the sky? No? Lucky.',
    'Bread\'s gone up again. Everything goes up but the people who go down.',
    'I had a dream I was a lantern. Someone kept carrying me into the dark.',
    'Some days the town hums. Like a held note. Today\'s one of them.',
    'Don\'t mind me. Just talking so the quiet doesn\'t.',
  ],
  self: [
    'Me? Nobody worth a ballad. I keep my head down and my door shut.',
    'Born here, likely die here. That\'s the plan, anyway.',
    'I used to want to go down there. Then I watched who came back.',
    'I mend what I can. People, pots, reputations. Pots are easiest.',
    'I\'ve a sister in the lower ward. We don\'t speak since the Quiet Winter.',
  ],
  place: [
    'The well was here before the town. The town\'s just what grew around the hole.',
    'The Reliquary\'s under us. All of us. Everything we build is a lid.',
    'Old folk say the streets were laid out to spell something from above.',
    'The sanctum doors open for some and not others. Nobody\'s sure what it wants.',
    'Every stone in the square was hauled up from below. Think on that when you sit.',
  ],
  rumor: [
    'Someone heard singing from the well last night. In a voice they swore was their own.',
    'A delver came back up with no shadow. Had it back by morning. Wrong shape, though.',
    'Merchants are paying double for anything that glows and doesn\'t burn.',
    'They say there\'s a door down there that only opens if you knock with a name.',
    'The guard captain\'s been buying rope. A lot of rope.',
    'Old Pell swears the third landing moved. Old Pell also swears at cats, so.',
    'There\'s a room below where the dead play cards. Winners get to stay dead.',
    'Something\'s eating the rats in the lower cellars. Nobody\'s complaining yet.',
    'A priest walked in the well without a light and walked out with one. It hasn\'t gone out.',
  ],
  farewell: [
    'Go careful. And if you hear your name down there, don\'t answer it.',
    'Come back up. That\'s all any of us ask.',
    'Luck to you. You\'ll want more than that, but it\'s what I\'ve got.',
    'Off you go, then. I\'ll keep a candle, if I remember.',
    'Safe roads. Or safe stairs. Whichever you\'re taking.',
  ],
  observe: [
    'Their hands are calloused in the places honest work leaves marks.',
    'They glance at the floor now and then, as if listening to something beneath it.',
    'Their clothes are patched with care — poor, but proud.',
    'A faint smell of woodsmoke and old bread follows them.',
    'They keep one foot angled toward the door.',
  ],
};

V.monster = {kind: 'monster', match: null,
  greet: [
    'More meat that walks. How thoughtful of the surface.',
    'You smell of sunlight. It will wash off.',
    'Turn back. Or don\'t. I am hungry either way.',
    'Another hero. The last one is still decorating the hallway.',
    'Stand still. It hurts less, and I dislike chasing.',
  ],
  taunt: [
    'Is that the best your little gods gave you?',
    'I have eaten braver things for breakfast. Literally.',
    'Your stance is wrong. You will die learning that.',
    'Swing again. I enjoyed the breeze.',
    'Ha! Your friends will make a fine matched set.',
    'Keep shouting. It brings the others.',
  ],
  bloodied: [
    'You... you cut me. You will regret that for a very short time.',
    'Blood for blood, then. I have more than you.',
    'Enough! ENOUGH!',
    'This is not how this was supposed to go.',
    'I will remember your face. I will wear it.',
  ],
  parley: [
    'Talk? Fine. Talk fast. My patience has teeth.',
    'Offer something worth more than your liver and we will see.',
    'You are not the first to bargain. You may be the first to survive it.',
    'What do you want, little light, that is worth walking this deep?',
  ],
  self: [
    'I was here before your town. I will be here after.',
    'I have a name. You have not earned it.',
    'I serve the dark. The dark pays better than you think.',
  ],
  place: [
    'This is our hall. You are standing in its mouth.',
    'The deeper you go, the less the stairs care where you meant to end up.',
    'Down here, the walls remember. Up there, you forget. Which is worse?',
  ],
  farewell: [
    'Go. Before I remember I am hungry.',
    'Leave. Come back with gold, or not at all.',
    'We will meet again. You will be smaller.',
  ],
  observe: [
    'Intelligence flickers behind its eyes — this one plans, not just hunts.',
    'It watches your weapon hand, not your face.',
    'Old scars cross its hide in careful, deliberate patterns.',
    'It speaks the common tongue with an accent like grinding stone.',
  ],
};

V.barkeep = {kind: 'person', match: /bar ?(keep|tender|staff|maid)|tavern|innkeep|patron|brewer|landlord/i,
  greet: [
    'What\'ll it be? Ale, stew, or a warm corner to bleed quietly in?',
    'Sit, sit. Delvers drink free on their first night back. Second night, not so much.',
    'Door\'s open, fire\'s lit, tap\'s flowing. That\'s the whole sermon.',
    'You look like you need a drink more than the drink needs you.',
    'Boots off the table, blades on the hook, coin on the bar. House rules.',
  ],
  idle: [
    'Someone carved a star into the bar again. I sand it down. It comes back.',
    'Keg in the back\'s been humming. I don\'t tap that one anymore.',
    'Good crowd tonight. Nobody\'s cried yet.',
    'I water the ale on weeknights. Don\'t tell anyone. Everyone knows.',
    'Heard a delver order a drink for a friend who wasn\'t there. Paid for it, too.',
  ],
  self: [
    'Twenty years behind this bar. Seen every face in town cry, laugh, and lie.',
    'My da ran this place before me. He went down the well on a bet. Lost it.',
    'I hear everything and repeat half. That\'s the trade.',
  ],
  place: [
    'Oldest tavern in town. The cellar\'s older still. Mind you don\'t go past the second door.',
    'This place was a waystation for delvers before it had a name. Before the town did, too.',
  ],
  rumor: [
    'Fellow in the corner paid in coins nobody\'s minted for three hundred years.',
    'A crew went down on the new moon. Their tab\'s still open. Draw your own conclusions.',
    'The guard drinks here off-shift. They\'re scared. Guards shouldn\'t drink like that.',
    'Somebody\'s been buying rounds with teeth. Human teeth. I turned them away. Mostly.',
  ],
  farewell: [
    'Come back and pay your tab. Living, preferably.',
    'Door\'s always open. Mostly for the draft.',
    'Tell the dark it owes me three customers.',
  ],
  observe: [
    'A rag over one shoulder, worn thin from years of wiping the same bar.',
    'They pour without looking and never spill a drop.',
    'Their eyes flick to every new arrival, pricing them in a heartbeat.',
    'A cudgel is tucked under the bar within easy reach.',
  ],
};

V.guard = {kind: 'person', match: /guard|watch(man)?|soldier|sentry|captain|warden|knight|sergeant/i,
  greet: [
    'Halt. State your business. Or don\'t — just don\'t make any.',
    'Weapons peace-bound in town. I\'m not asking twice.',
    'Well-walker, eh? Keep moving. And keep it quiet.',
    'Evening, citizen. Nothing to see. Move along.',
    'Your papers. Joking. Nobody\'s had papers since the archive flooded.',
  ],
  idle: [
    'Twelve hours on the gate and not one interesting thing. I pray it stays that way.',
    'The captain says stand tall. My knees say otherwise.',
    'Something walked past the well last night. Didn\'t leave footprints. Left a smell.',
    'Pay\'s late again. Still here, though. Where else would I go?',
    'Every time the bell rings twice, I check my sword. Habit.',
  ],
  self: [
    'Joined the watch to keep my family safe. Now I just keep the gate.',
    'Served eight years. Seen three things come up that well I won\'t talk about.',
    'I\'m not brave. I\'m just the one who didn\'t run fast enough when they handed out spears.',
  ],
  place: [
    'Curfew\'s at last bell. After that, the streets belong to whatever climbs up.',
    'The well-gate is barred at night. From the outside. Think about why.',
  ],
  rumor: [
    'Captain\'s been ordering chains. Heavy ones. Not for people.',
    'We lost a patrol on the lower steps. Found their lantern. Still lit.',
    'Nobody\'s supposed to know, but the sanctum doors opened on their own last week.',
  ],
  farewell: [
    'Stay out of trouble. Or at least out of my sight.',
    'Move along. Safely.',
    'If you see anything with too many knees, you run and you yell. In that order.',
  ],
  observe: [
    'Their armor is dented but carefully oiled.',
    'They stand with their back to a wall, always.',
    'A tally of small cuts is scratched into the haft of their spear.',
    'Their eyes are tired, but they never stop moving.',
  ],
};

V.merchant = {kind: 'person', match: /merchant|trader|vendor|peddler|shop|smith|clerk|quartermaster|fence|pawn/i,
  greet: [
    'Customer! Come in, come in. Everything\'s for sale, some of it twice.',
    'Browse all you like. Touching costs extra. Joking. Mostly.',
    'Fresh from the depths? Show me what you found and I\'ll show you a fair price.',
    'Ah, a delver with full pockets and empty eyes. My favorite kind.',
    'Welcome! Today\'s special: everything you need and nothing you can afford.',
  ],
  idle: [
    'Glowing things sell well. Humming things sell better. Screaming things, not at all.',
    'Business is good when the well is hungry. That\'s the ugly truth of it.',
    'I had a sword that wouldn\'t stay in its scabbard. Sold it. Fine buyer. Very bloody.',
    'Inventory day. I\'m missing three rings and gained a skull. Nobody gains a skull.',
  ],
  self: [
    'Three generations of fair trading. Mostly fair. Fair-adjacent.',
    'I buy low, sell high, and never ask where it came from. That last part is key.',
    'I wanted to be a poet. Poetry doesn\'t pay. Relics do.',
  ],
  place: [
    'The market moves when the well does. Always has.',
    'Best prices this side of the Reliquary. Only prices, really.',
  ],
  rumor: [
    'Somebody\'s buying up every mirror in town. Paying in silver that\'s cold to the touch.',
    'A crown came up from the fourth landing. The fellow who carried it won\'t stop smiling.',
    'Don\'t buy the rope from Dell. It\'s been down there. It remembers the fall.',
  ],
  farewell: [
    'Come back with coin! Or treasure! Or both! Both is good!',
    'No refunds. On anything. Especially the cursed things.',
    'Pleasure doing business. It was business, wasn\'t it?',
  ],
  observe: [
    'Every finger wears a ring, and every ring is a different metal.',
    'Their scale is weighted — slightly, cleverly.',
    'They size up your gear before they meet your eyes.',
    'A ledger peeks from their coat, crammed with tiny, careful numbers.',
  ],
};

V.priest = {kind: 'person', match: /priest|cleric|acolyte|monk|nun|oracle|pilgrim|sister|brother|chaplain|templar|healer/i,
  greet: [
    'Light keep you, traveler. Though it seems it\'s had a rough time of it.',
    'Peace be on you. Sit, if your wounds allow.',
    'The gods see you. Whether they\'re pleased is another matter.',
    'Come for a blessing, or a bandage? We do both. The bandage works faster.',
  ],
  idle: [
    'The candles burn blue when someone dies below. They\'ve been blue all week.',
    'I pray every morning. Lately something prays back.',
    'The scriptures mention a star that fell and did not break. I used to think it was metaphor.',
    'Faith is a lantern. You still have to walk.',
  ],
  self: [
    'I took my vows the year the well opened. I think the two are connected.',
    'I tend the lamps and the dying. Some nights I can\'t tell which I\'m doing.',
    'My god is quiet. That doesn\'t mean absent. I tell myself that often.',
  ],
  place: [
    'This shrine was built to keep something in, not to let prayers out.',
    'The oldest altar here faces down. Not up. We don\'t speak of why.',
  ],
  rumor: [
    'The relics in the vault have been warm to the touch. All of them. All at once.',
    'A child recited a prayer nobody taught her. In a language nobody speaks.',
    'The Hollow Star — some think it\'s a god. Some think it\'s a wound. I think it\'s listening.',
  ],
  farewell: [
    'Go with light. And bring it back.',
    'May your gods walk with you — and may they walk in front.',
    'Return to us whole. Or at least mostly.',
  ],
  observe: [
    'Wax burns crust their fingertips.',
    'A holy symbol hangs at their throat, polished smooth by nervous thumbs.',
    'Their robes are clean at the hem and scorched at the cuffs.',
    'They murmur under their breath — a litany, or a count.',
  ],
};

V.scholar = {kind: 'person', match: /scholar|sage|mage|wizard|archivist|librarian|scribe|alchemist|apprentice|historian|cartographer/i,
  greet: [
    'Ah! A primary source! Sit — tell me everything, and slowly.',
    'Mind the books. And the ink. And the thing in the jar.',
    'You\'ve been below. Did you see writing? Any writing? Symbols?',
    'Hmm? Yes, hello. One moment, I\'m nearly finished being wrong about something.',
  ],
  idle: [
    'The runes on the well rim have changed. I have sketches. Nobody believes the sketches.',
    'If the Reliquary is a vault, then what was stored? And more importantly — who is the key?',
    'I\'ve read every book in this town. Half of them twice. Three of them read me back.',
    'Arithmetic is a comfort. Numbers don\'t whisper. Usually.',
  ],
  self: [
    'I study the depths from up here. It\'s cowardly, and extremely comfortable.',
    'I was expelled from the Academy for asking the right question too loudly.',
    'I map the well. The well keeps disagreeing with my maps.',
  ],
  place: [
    'The town is built on a spiral. Aerial sketches confirm it. The question is: a spiral toward what?',
    'The stones below predate every culture I know. They also predate one I don\'t.',
  ],
  rumor: [
    'There\'s a book below whose pages are blank until you bleed on them. Purely theoretical, I\'m told.',
    'Someone found a map of the depths drawn in a hand identical to mine. I have never been down.',
    'The Hollow Star\'s makers — two voices, by the old texts. One fire, one laughter.',
  ],
  farewell: [
    'Take notes! Ideally not in blood, but I won\'t be picky.',
    'Bring me back a rubbing of anything with writing on it. Please.',
    'Off you go. Try not to become a footnote.',
  ],
  observe: [
    'Ink stains their fingers to the second knuckle.',
    'Spectacles perch on their head; a second pair hangs from their neck.',
    'Loose pages stuffed in every pocket rustle when they move.',
    'They squint at you as if you were an interesting marginal note.',
  ],
};

V.cook = {kind: 'person', match: /cook|chef|baker|butcher|kitchen|scullion/i,
  greet: [
    'You hungry? You look hungry. Everyone who comes up looks hungry.',
    'Stew\'s on. Don\'t ask what\'s in it. It\'s in it, and that\'s what matters.',
    'Out of my kitchen unless you\'re here to peel.',
  ],
  idle: [
    'The bread won\'t rise on days the well is loud.',
    'Salt keeps things out. I salt the doorways. I salt the stew. Same principle.',
    'Somebody keeps stealing onions. Somebody small. Somebody who isn\'t on the staff list.',
  ],
  self: ['I feed the living. Somebody has to.', 'I cooked for a lord once. He died. Not my fault. Probably.'],
  rumor: ['Meat from the lower market tastes sweet lately. I don\'t buy it anymore.', 'A delver brought back a mushroom that glows. We didn\'t eat it. It ate the cutting board.'],
  farewell: ['Eat something before you go down. Dying hungry is twice the tragedy.', 'Come back for seconds.'],
  observe: ['Their forearms are flecked with old burn scars.', 'A cleaver hangs at their hip, clean enough to see your face in.', 'They smell of onions, pepper, and patience.'],
};

V.child = {kind: 'person', match: /child|kid|urchin|orphan|boy|girl|youth|page/i,
  greet: [
    'Are you a hero? You don\'t look like one. That\'s okay.',
    'Did you go down the well? Was it scary? Did you see a monster? Did you KILL it?',
    'My mum says I\'m not supposed to talk to delvers. I\'m talking anyway.',
  ],
  idle: [
    'I dropped a stone in the well and counted. I got to a hundred and it hadn\'t landed.',
    'There\'s a lady who lives in my mirror. She\'s nice. She says I look like her.',
    'I\'m going to be a delver when I grow up. Or a baker. Probably a baker.',
  ],
  self: ['I\'m seven. And a half. The half is important.', 'I can climb anything. Almost anything. Not the well.'],
  rumor: ['The star talks to me at night. It asked what my name was. I didn\'t tell it.', 'Old Pell has a pet in his cellar that isn\'t a dog.'],
  farewell: ['Bring me back a monster tooth!', 'Bye! Don\'t die!'],
  observe: ['Scraped knees and bright, fearless eyes.', 'They clutch a carved wooden sword with serious intent.', 'Their pockets bulge with pebbles and stolen buttons.'],
};

V.noble = {kind: 'person', match: /noble|lord|lady|baron|count|duke|mayor|magistrate|envoy|heir/i,
  greet: [
    'You may approach. Slowly. And wipe your boots.',
    'Ah, the help. Or the heroes. I can never tell the difference.',
    'You have one minute of my time. You have already used ten seconds of it.',
  ],
  idle: [
    'The town council meets tomorrow. I will say wise things and they will nod.',
    'Taxes on relics fund the walls. The walls fund my peace of mind.',
    'My family\'s crest has a well on it. We are not proud of what that means.',
  ],
  self: ['My line has held this town since the first stone was laid. Or so the portraits claim.', 'I am a patron of the arts. And of the delvers. At a respectable distance.'],
  rumor: ['The king — well, the one that matters — has taken an interest in the Reliquary. A dangerous interest.', 'Several houses want what\'s below. Only one of us is honest enough to say so.'],
  farewell: ['You are dismissed.', 'Serve the town well. It remembers loyalty. So do I.'],
  observe: ['Rings of heavy gold, and not a single callus.', 'Perfume masks, poorly, the smell of fear-sweat.', 'Their smile does not reach their eyes and has no intention of trying.'],
};

V.thief = {kind: 'person', match: /thief|rogue|cutpurse|smuggler|spy|informant|beggar|scoundrel/i,
  greet: [
    'Psst. You. Yes, you. Not so loud.',
    'Nice purse. Heavy. You should keep it closer.',
    'Friends of the dark are friends of mine. Which kind are you?',
  ],
  idle: ['Locks are just puzzles with opinions.', 'Guards change shift at the third bell. Not that I noticed.', 'I don\'t steal from delvers. They\'ve got enough problems. Mostly.'],
  self: ['Name? I\'ve got several. Pick one you like.', 'I acquire things. Occasionally I acquire them back.'],
  rumor: ['There\'s a back way into the Reliquary. Costs more than money.', 'Someone\'s been fencing relics that shouldn\'t exist yet. Dated next year.'],
  farewell: ['You never saw me.', 'Check your pockets. Kidding. ...Check them.'],
  observe: ['Soft-soled boots, silent on the stones.', 'Their hands never stop moving — rolling a coin, testing a seam.', 'A thin blade shows at the wrist when they gesture.'],
};

V.bard = {kind: 'person', match: /bard|minstrel|singer|poet|musician|player|jester|storyteller/i,
  greet: [
    'A new verse walks in! Tell me, friend — how does your story end?',
    'Ah, an audience! Sit, and I\'ll sing of your deeds. Or make some up.',
    'You have a face made for tragedy. That\'s a compliment. Mostly.',
  ],
  idle: ['Every song about the well ends the same way. I\'m trying to write a new ending.', 'I sang a lullaby by the well once. Something hummed along.', 'Rhymes for "Reliquary" are shockingly scarce.'],
  self: ['I collect stories. Yours will do nicely, if you survive to finish it.', 'I played for kings. Well. One king. He was drunk. It counts.'],
  rumor: ['There\'s a ballad nobody wrote, and everybody knows. It\'s about you. I\'m sure of it.', 'The last bard to sing below came back with a voice that isn\'t hers.'],
  farewell: ['Go make a legend. I\'ll handle the rhymes.', 'Die dramatically, if you must. It helps the chorus.'],
  observe: ['Their lute is battered, its strings bright and new.', 'They hum constantly, a tune just shy of familiar.', 'Ribbons from a dozen towns are tied around their wrist.'],
};

V.adventurer = {kind: 'person', match: /adventurer|delver|mercenary|sellsword|hunter|ranger|scout|veteran|explorer/i,
  greet: [
    'Another crew for the well? Good. The more of us, the fewer of them.',
    'Don\'t take the left stair on the second landing. Trust me.',
    'You\'ve got the look. Went down, came up, still not sure which one counts.',
  ],
  idle: ['I dream of the fourth landing every night. It\'s never the same room twice.', 'Lost my partner on the last run. The well gave back her boots.', 'Gold\'s good. Being alive is better. Being alive with gold is best.'],
  self: ['Seven descents. Six returns. Math\'s getting uncomfortable.', 'I used to be the best on the stairs. Then I got older and the stairs didn\'t.'],
  place: ['First landing\'s safe-ish. Second\'s a coin toss. Third, you pay the toll in something you won\'t miss till later.'],
  rumor: ['There\'s a champion down there. Collects the ones who fall. Keeps them... organized.', 'A crew came back with an extra member. Nobody remembers them joining.'],
  farewell: ['Watch your flanks.', 'See you at the bottom. Or the top. Whichever\'s closer.'],
  observe: ['Their gear is mismatched, each piece chosen for survival rather than style.', 'A dozen small healing scars ladder up one arm.', 'They check exits the moment they enter anywhere.'],
};

// ── Intelligent monsters ─────────────────────────────────────────────────

V.goblin = {kind: 'monster', match: /goblin|hobgoblin|bugbear|gremlin|\bimp\b/i,
  greet: ['Oi! Shinies! Hand \'em over and maybe you keep your fingers!', 'Big-folk! Big-folk in the tunnels! Get the pointy sticks!', 'Oh, it\'s you. Boss said you\'d come. Boss is usually wrong.'],
  taunt: ['Missed me! Missed me! Now you gotta— OW.', 'You\'re slow as a sleeping mushroom!', 'I\'m gonna wear your boots. Both of \'em. On my hands.', 'Nyah! Can\'t catch Snikt!'],
  bloodied: ['Not fair! Not fair! I was winning!', 'Okay okay okay, maybe truce? Truce is a good word.', 'I\'m telling the Boss!'],
  parley: ['You got shinies? Shinies make friends.', 'We don\'t like the Boss neither. Pay us and we\'ll show you the back way.', 'Promise not to stab? Pinky promise? What\'s a pinky?'],
  self: ['I\'m Grubnik the Magnificent! Well. Grubnik the Adequate.', 'Third-best goblin in the warren. First two got eaten.'],
  place: ['This is our tunnel. We dug it. Well, we found it. Same thing.'],
  farewell: ['Bye! Don\'t come back! Or do, and bring snacks!'],
  observe: ['Its armor is a patchwork of stolen buckles and dented pots.', 'Its eyes dart between you and your belt pouch.', 'It clutches a knife far too clean to be its own.'],
};

V.kobold = {kind: 'monster', match: /kobold|dragonborn-?kin|lizardfolk|troglodyte/i,
  greet: ['Trespasser! The Great Scale will hear of this!', 'Stop! You walk on trap-floor! ...Is joke. Or is it.', 'Softskins! Quick — to the murder holes!'],
  taunt: ['Our traps are better than your sword!', 'You step there? Good. Good good good.', 'Tiny but clever! You big but dumb!'],
  bloodied: ['Retreat! Tactical retreat! Brave retreat!', 'You break Kib\'s tail. Kib very upset.'],
  parley: ['You fight the dragon-that-sleeps? Then maybe we help. Maybe.', 'Tribute! You bring tribute, we let you pass.'],
  self: ['Kib is trap-master of Clan Ashscale! Very important!'],
  farewell: ['Go! And do not touch the third stone!'],
  observe: ['Its scales are painted with crude, precise draconic runes.', 'Tiny tools jangle from its belt: wire, hooks, clamps.', 'It watches the floor as closely as it watches you.'],
};

V.orc = {kind: 'monster', match: /\borc|ogre|gnoll|troll|half-?orc|warlord|berserker/i,
  greet: ['FIGHT ME.', 'You smell weak. Prove me wrong.', 'Finally. Something worth breaking.'],
  taunt: ['Hit harder! My mother hits harder!', 'Is that a sword or a butter knife?', 'You fight like you\'re already dead.', 'GRAAAH!'],
  bloodied: ['Good! GOOD! Now we fight properly!', 'Blood! Finally, a real fight!', 'You... are strong. I will honor your skull.'],
  parley: ['You want to talk? Talk with steel.', 'Strength respects strength. Show me yours and maybe we drink instead.', 'My chief is a coward. Kill him and I follow you.'],
  self: ['I am Kraag, Skull-Taker, Third Son of the Burning Axe.', 'I have killed forty-three. You would be forty-four.'],
  farewell: ['Next time, we finish this.', 'Go. Get stronger. Then come back.'],
  observe: ['Trophies of bone and braided hair hang from its harness.', 'Its tusks are capped in beaten iron.', 'Every muscle is coiled, eager. It wants this fight.'],
};

V.undead = {kind: 'monster', match: /lich|vampire|wight|wraith|ghost|specter|spectre|revenant|skeleton|zombie|ghoul|banshee|mummy|death ?knight|shade|undead|dead/i,
  greet: ['Another warm one... how long it has been since I felt warmth.', 'You walk in the halls of the dead. You are only early.', 'Welcome, mortal. Sit. We have eternity to talk.'],
  taunt: ['Your heart beats so loudly. Let me quiet it.', 'I was a king when your ancestors ate dirt.', 'Death is patient. So am I.', 'Strike me again. I have forgotten pain.'],
  bloodied: ['You cannot kill what is already dead... but you can make it very angry.', 'This body is only a vessel. I have others.', 'The grave will not have me. Nor will you.'],
  parley: ['I remember a name. Bring me the one who bore it, and you may pass.', 'Speak the words of the old rite and I will let you go.', 'I want nothing you can give. Except, perhaps, your time.'],
  self: ['I was a priest once. I prayed for life eternal. The gods have a cruel sense of humor.', 'I have forgotten my name. I have not forgotten who killed me.', 'Once I loved. Now I only remember that I did.'],
  place: ['These halls were a cathedral. Now they are a tomb. The prayers are still here — listen.', 'The Star took us in. It keeps what is left behind.'],
  farewell: ['Go. Live. It is so very brief.', 'Return when you are ready to stay.'],
  observe: ['A chill radiates from it that no fire could warm.', 'Its eyes hold a pinprick of cold light — not quite life, not quite nothing.', 'Burial finery rots on its frame, still fastened with care.', 'It does not breathe, and yet it speaks.'],
};

V.dragon = {kind: 'monster', match: /dragon|drake|wyrm|wyvern/i,
  greet: ['Ahh. Tiny, bright things have come to my hoard. How... bold.', 'Kneel, and I may yet find you interesting.', 'You are in my home, morsel. Speak quickly.'],
  taunt: ['I have burned cities for less insolence.', 'Your blade is a toothpick. Your armor, a wrapper.', 'Do you know how many heroes are in my bedding?'],
  bloodied: ['You DARE—', 'Impressive. I have not bled in a century.', 'You will be remembered — as ash.'],
  parley: ['Offer me a riddle I cannot answer, and your life is yours.', 'Gold. Secrets. Songs. I collect them all. What do you bring?', 'I am old enough to be reasonable. Do not test how old.'],
  self: ['I was old when your gods were young.', 'Names have power. You will not have mine.'],
  place: ['Every coin here has a story. Every story ends with me.'],
  farewell: ['Go, little flame. Before I decide you are part of my hoard.', 'We shall meet again. I am very patient.'],
  observe: ['Every scale is the size of a shield and scored with old battle-scars.', 'Heat shimmers off its body like a forge at rest.', 'Its eyes track you with ancient, amused intelligence.', 'Gems are embedded in its belly, pressed there by centuries of sleep on gold.'],
};

V.fiend = {kind: 'monster', match: /demon|devil|fiend|succubus|incubus|hellhound|pit fiend|balor|cambion|rakshasa/i,
  greet: ['Ah, a soul with an appetite for adventure. Let us discuss terms.', 'Welcome, mortal. You look like someone who wants something.', 'Bow, or burn. Either pleases me.'],
  taunt: ['Your gods are not listening, little one. I am.', 'Such rage! I could bottle it.', 'Pray louder. I enjoy the harmonies.'],
  bloodied: ['You think this body is all I am?', 'Pain! Delicious!', 'I will remember the flavor of this defeat — and yours.'],
  parley: ['Everything has a price. Yours is so very reasonable.', 'Sign here, and here, and here. Just a formality.', 'I can give you what you want. The question is what you\'ll give me.'],
  self: ['I have a thousand names and use none of them twice.', 'I was invited. They always forget they invited me.'],
  farewell: ['Until our contract is due.', 'Go. You will call on me again. They always do.'],
  observe: ['Its smile is too wide, its teeth too many.', 'The air around it tastes of sulfur and old promises.', 'Its shadow moves a heartbeat after it does.'],
};

V.fey = {kind: 'monster', match: /fey|fae|fairy|faerie|sprite|pixie|dryad|nymph|hag|satyr|redcap|changeling/i,
  greet: ['Oh! A visitor! Would you like to play a game? You have to.', 'Mind your name, traveler. It is the most valuable thing you carry.', 'Iron? How rude.'],
  taunt: ['Catch me, catch me! Oh, you can\'t.', 'You smell of clocks and salt. How dull.', 'I\'ll turn your hair to moss. It would be an improvement.'],
  bloodied: ['You broke our bargain!', 'Iron! Cold iron! Cheater!'],
  parley: ['A riddle for a riddle. A favor for a favor. A name for a name.', 'Give me the color of your eyes and I\'ll give you safe passage.', 'Promises bind. Speak carefully.'],
  self: ['I am the dew on the ninth leaf. That\'s all you need to know.', 'I am older than your language and younger than your worries.'],
  farewell: ['Don\'t eat anything on your way out.', 'Farewell, dear. I\'ll keep your shadow safe.'],
  observe: ['It flickers at the edge of your vision, never quite in focus.', 'The air smells of crushed flowers and thunder.', 'Its eyes are the color of a season you can\'t name.'],
};

V.giant = {kind: 'monster', match: /giant|ettin|cyclops|titan|colossus|golem|construct|sentinel|automaton/i,
  greet: ['SMALL THING. WHY ARE YOU IN MY HALL?', 'YOU. STOP.', 'Intruder detected. State purpose.'],
  taunt: ['I HAVE STEPPED ON BIGGER.', 'YOU ARE LIKE ANTS. ANNOYING ANTS.', 'Resistance noted. Resistance irrelevant.'],
  bloodied: ['OW. OW! THAT WAS RUDE.', 'Structural integrity compromised. Rage protocol engaged.'],
  parley: ['BRING ME SHEEP. TEN SHEEP. THEN WE TALK.', 'Directive: guard. Directive does not specify you. Clarify.'],
  self: ['I GUARD. I HAVE ALWAYS GUARDED.', 'Built for purpose. Purpose forgotten. Guarding continues.'],
  farewell: ['GO AWAY NOW.', 'Resuming watch.'],
  observe: ['The ground shivers faintly with each of its breaths.', 'Moss grows in the cracks of its skin — or its stone.', 'It is slow, but it has never needed to be fast.'],
};

V.aberration = {kind: 'monster', match: /aberration|mind ?flayer|illithid|beholder|aboleth|\beye tyrant|tentacle|horror|void|star-?spawn|hollow ?(one|thing|spawn)/i,
  greet: ['...we have been expecting you... we have been expecting everything...', 'Your thoughts are so loud. Let me quiet them.', 'Hello, little mind. Open.'],
  taunt: ['We see your fear. It is delicious.', 'Your shape is an error. We will correct it.', 'Every step you take, we took first.'],
  bloodied: ['Pain. A novel sensation. We will study it... on you.', 'This vessel falters. There are others. There are always others.'],
  parley: ['We could share. Everything. You would never be alone again.', 'Give us one memory. A small one. You won\'t miss it.'],
  self: ['We are the space between stars. We are what the Hollow Star forgot.', 'I was a thought once. Now I am thinking you.'],
  place: ['This is the underside of your world. It has always been here, looking up.'],
  farewell: ['We will be in your dreams.', 'Go. We already know how this ends.'],
  observe: ['Looking at it too long makes the edges of the room bend.', 'Its voice arrives inside your head before your ears.', 'It moves in ways your eyes refuse to agree on.'],
};

V.cultist = {kind: 'monster', match: /cult|fanatic|zealot|acolyte of|heretic|warlock|necromancer|sorcerer|witch|druid/i,
  greet: ['The Star has seen you. It told us you would come.', 'Join us, or kneel to us. Either way, you serve.', 'Blessed are the ones who descend. Doubly blessed are the ones who don\'t come back.'],
  taunt: ['Your death is holy. Your screams are hymns.', 'We have prayed for this!', 'The Star will take you whole!'],
  bloodied: ['My blood is an offering! Take it! TAKE IT!', 'I am not afraid! I am not—'],
  parley: ['The Star wants a vessel. Why not you?', 'Lay down your blade and learn the truth.'],
  self: ['I was lost. Then the voice in the well called my name.', 'I have given the Star my sleep, my name, and my left eye. I would give more.'],
  place: ['This is the Star\'s throat. We sing down it.'],
  farewell: ['We will pray for you. You won\'t like how.'],
  observe: ['A crude star is branded into the back of one hand.', 'Their eyes shine with a dreadful, peaceful certainty.', 'Candle wax and dried blood crust their sleeves.'],
};

V.bandit = {kind: 'monster', match: /bandit|brigand|raider|pirate|outlaw|thug|cutthroat|highwayman|marauder/i,
  greet: ['Your gold or your life. Honestly, we\'ll take both.', 'Nice gear. Shame to scratch it.', 'Well, well. Look who wandered off the path.'],
  taunt: ['Is that your best? I\'ve seen farmers swing harder.', 'Surround them, lads!', 'Pretty sword. It\'ll look better on me.'],
  bloodied: ['Run! RUN! It\'s not worth it!', 'Nobody said they\'d fight BACK!'],
  parley: ['Toll\'s ten gold a head. Cheap, compared to the alternative.', 'We\'re just trying to eat. Like anyone else.'],
  self: ['Used to be a farmer. Then the well took the farm.'],
  farewell: ['Pleasure robbing you.', 'Next time, bring more coin.'],
  observe: ['A mismatched blade, clearly taken from someone who died holding it.', 'Hunger shows in the hollows of their cheeks.', 'They glance at their allies before each move — unsure, looking for a leader.'],
};

const ORDER = ['dragon', 'undead', 'fiend', 'aberration', 'fey', 'giant', 'goblin', 'kobold', 'orc', 'cultist', 'bandit',
  'barkeep', 'guard', 'merchant', 'priest', 'scholar', 'cook', 'child', 'noble', 'thief', 'bard', 'adventurer'];

export const VOICE_TOPICS = {
  person: [{id: 'self', label: 'Ask about them'}, {id: 'place', label: 'Ask about this place'}, {id: 'rumor', label: 'Any rumors?'}, {id: 'idle', label: 'Make small talk'}, {id: 'farewell', label: 'Say farewell'}],
  monster: [{id: 'parley', label: 'Parley'}, {id: 'self', label: 'Who are you?'}, {id: 'place', label: 'What is this place?'}, {id: 'taunt', label: 'Provoke it'}, {id: 'farewell', label: 'Back away'}],
};

function haystack(entity = {}) {
  return [entity.name, entity.display_name, entity.role, entity.kind, entity.species, entity.creature_type,
    entity.family, entity.archetype, entity.class_name, ...(entity.tags || [])].filter(Boolean).join(' ');
}

// Resolve the archetype for a resident/foe row. `hostile` biases unknowns to monster.
export function voiceOf(entity = {}, {hostile = false} = {}) {
  const text = haystack(entity);
  const key = ORDER.find(id => V[id].match.test(text));
  if (key) return {key, ...V[key]};
  return hostile ? {key: 'monster', ...V.monster} : {key: 'person', ...V.person};
}

function hash(text) { let h = 2166136261; for (const ch of String(text)) h = Math.imul(h ^ ch.charCodeAt(0), 16777619); return h >>> 0; }
const spoken = new Map();

// Pick a line from a pool, avoiding immediate repeats per entity+pool.
export function voiceLine(entity = {}, pool = 'greet', opts = {}) {
  const voice = voiceOf(entity, opts);
  const base = V[voice.kind];
  const lines = voice[pool]?.length ? voice[pool] : base[pool] || base.greet;
  const key = `${entity.id || entity.name}:${pool}`;
  const last = spoken.get(key);
  let index = (hash(key) + Math.floor(Math.random() * lines.length)) % lines.length;
  if (lines.length > 1 && index === last) index = (index + 1) % lines.length;
  spoken.set(key, index);
  return lines[index];
}

// Two or three stable examine notes for an entity (same ones each look).
export function voiceObservations(entity = {}, opts = {}) {
  const voice = voiceOf(entity, opts);
  const pool = [...(voice.observe || []), ...V[voice.kind].observe.slice(0, 2)];
  const seed = hash(entity.id || entity.name || voice.key);
  const picks = [];
  for (let i = 0; picks.length < Math.min(3, pool.length); i++) {
    const line = pool[(seed + i * 7) % pool.length];
    if (!picks.includes(line)) picks.push(line);
  }
  return picks;
}

export const VOICE_LIBRARY = V;
