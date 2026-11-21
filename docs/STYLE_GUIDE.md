# Style guide: writing for the ear of a three-year-old

**Every script must pass two tests: a careful adult can check each sentence
against the passage, and a three-year-old can follow it with no pictures.**
The rules below serve one test or the other. `storyteller.py lint` enforces
the measurable ones.

## 1. Fidelity: the text sets the events, we only choose the words

- **No invented events, characters or motives.** If the passage does not say
  someone was tired, sad or small, neither do we. Sensory colour is allowed
  only where the text implies it (a storm is loud; nails hurt).
- **Speech is paraphrase, never invention.** Every line God or Jesus speaks
  must map to a verse. Other characters speak only where the passage gives
  them speech.
- **Plain, not graphic.** Sin is called disobeying God. Death is called death.
  Judgement is not skipped. Each hard fact is stated once, in a short sentence,
  with no lingering description. What we cut is gore (Goliath's head), never
  the event (Goliath dies).
- **No tacked-on moral.** A story ends with one sentence about what God is
  like or what God did, taken from the passage's own emphasis. Never "so we
  should be kind".
- **Glosses are flagged.** Any sentence of interpretation (why Jesus died,
  who alone commands the sea) is listed under "Fidelity notes" with its
  supporting references, so a parent can strike it.
- **Every script carries fidelity notes**: what was compressed, what was
  omitted and why, and any harmonising of parallel accounts.
- **Own wording throughout.** Scripts paraphrase from the passage and quote no
  modern translation at length.

## 2. Language: short, concrete, rhythmic

- **Length**: 300 to 550 spoken words, which is 2.5 to 4.5 minutes.
- **Sentences**: mean of 11 words or fewer; none over 24. One idea each.
- **Words a small child owns.** Hard words that matter are kept and explained
  once in passing: "a tomb: a cave, cut into the rock".
- **Repetition is a feature.** Refrains ("And God saw that it was good"),
  triples ("calm, and quiet, and still") and sound words ("Splash!") give
  small listeners something to anticipate and join in with.
- **Fixed frame.** Every story opens "This is a story from God's book, the
  Bible. It is called: ..." and closes "You can find this story in the Bible,
  in the book of ..., chapter ...". The ritual tells a child where they are
  and teaches that the stories come from somewhere.
- **Never end in fear.** Weighty stories close on God's character or promise,
  using words the Bible itself supplies.

## 3. Voices: theatrical, never frightening

- **Narrator carries about 70 per cent.** Characters speak the lines that
  matter; the narrator names the speaker first ("So David went to King Saul")
  because the child cannot see who is talking.
- **Five voices or fewer per story** where the passage allows.
- **One voice per character across the whole card.** David sounds like David
  in story 24 and story 25. The mapping lives in `cast.toml`.
- **God and Jesus are calm, warm and unhurried.** No echo, no boom. Authority
  comes from stillness.
- **Villains are loud or proud, never monstrous.** Goliath shouts; he does not
  growl. Bedtime is a likely listening slot.
- **Delivery tags are sparse**: one short tag in square brackets at the start
  of a line, only where the default reading would be wrong. `[gently]`,
  `[whispers]`, `[shouting, frightened]`, `[awed]`.
- **Sound effects: at most two per story**, between lines and never under
  speech. Under-fives separate speech from background noise poorly, so
  clarity beats atmosphere.

## 4. Script format

```
---
number: 40
title: Jesus Calms the Storm
refs: Mark 4:35-41
weighty: false
---
# Fidelity notes (lines starting with # are never spoken)

NARRATOR: One paragraph per speaker turn. A blank line ends the turn.

JESUS: [firm, with calm authority] Peace. Be still.

[PAUSE 1.2]
[SCENE]
[SFX: wind rising over open water | 4]
```

`[PAUSE n]` inserts n seconds of silence, `[SCENE]` a standard scene break,
and `[SFX: description | seconds]` a generated sound effect. Every speaker
name must be mapped to a voice slot in `cast.toml`.
