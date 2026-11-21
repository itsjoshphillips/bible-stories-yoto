# Bible stories for a Yoto card

**Recommendation: write 60 four-minute stories as plain-text scripts with
named speakers, render them with ElevenLabs' multi-voice dialogue model, and
load the result onto one Make Your Own card.** The scripts are the product;
the audio is a repeatable build from them, so any story can be reworded and
re-rendered in minutes for a few cents.

All 60 scripts are written and have been rendered on ElevenLabs' `eleven_v4`
model: 2.5 hours of audio in 60 tracks (145 MB), with every chunk checked
against its script by transcription and none flagged. The Yoto uploader has
not been run; dragging the MP3s into my.yotoplay.com is the tested-by-design
fallback.

## Why this shape

1. **Sixty stories fit one card and cover the whole arc.** The scripts average
   2.5 minutes as rendered, totalling 2.5 hours against Yoto's 5 hour, 100 track,
   500 MB limit. The list runs from creation to new creation and keeps the
   hard stories in. See [docs/STORY_PLAN.md](docs/STORY_PLAN.md).
2. **Fidelity is enforced by process, not by good intentions.** Every script
   carries fidelity notes listing each omission, compression and interpretive
   sentence against the passage, so a parent can audit a story in two minutes.
   See [docs/STYLE_GUIDE.md](docs/STYLE_GUIDE.md).
3. **A dialogue model beats stitching single voices together.** ElevenLabs'
   text-to-dialogue endpoint renders several voices in one pass, so characters
   react to each other, and it accepts delivery tags such as `[whispers]`.
   A fixed cast of ten voices keeps each character recognisable across stories.
4. **Machine-checked audio.** Expressive models occasionally skip or garble a
   line. With `--verify`, each chunk is transcribed and compared with the
   script; with `--takes 3`, the closest of three takes is kept. Mismatches are
   flagged for a human listen.
5. **Cheap to iterate.** Rendered chunks are cached by content, so changing one
   sentence re-renders one chunk, not the card.

## How it works

```
stories/NN-title.md ──► lint ──► dialogue TTS (cached, verified) ──► ffmpeg
   script + notes       budget     10-voice cast from cast.toml       trim, level,
                        checks                                        pauses, stings
                                                                          │
                              Yoto card ◄── yoto.py upload ◄── build/tracks/*.mp3
```

| Step | Command |
|------|---------|
| Check scripts and the card budget | `python3 pipeline/storyteller.py lint` |
| List voices on the account | `python3 pipeline/storyteller.py voices` |
| Hear each cast slot | `python3 pipeline/storyteller.py audition` |
| Dry run, no API calls | `python3 pipeline/storyteller.py build --mock` |
| Real render, best of three takes | `python3 pipeline/storyteller.py build --takes 3` |
| One story only | `python3 pipeline/storyteller.py build stories/25-david-and-goliath.md` |
| Send to Yoto | `python3 pipeline/yoto.py login`, then `python3 pipeline/yoto.py upload` |

Requirements: Python 3.11 or later and ffmpeg. No Python packages. Set
`ELEVENLABS_API_KEY` (and `YOTO_CLIENT_ID` for the uploader) in the environment
or in a `.env` file.

Audio treatment per track: edge silence trimmed from each chunk, speech
levelled to -16 LUFS, controlled pauses between chunks and scenes, optional intro and outro stings
from `assets/`, then a limiter and 128 kbps mono MP3.

## What is and is not verified

| Item | Status |
|------|--------|
| Parser, lint, chunking, caching, ffmpeg assembly, loudness | Run on all 60 stories |
| ElevenLabs dialogue, sound-effect and transcription calls | Run on all 60 stories |
| Measured cost | About 0.23 credits per character; about 32,000 credits for one full pass |
| Voice IDs in `cast.toml` | Confirmed present on the account |
| How the audio sounds | Judged by ear on stories 1, 25, 40 and 53 only |
| Yoto uploader | Written from Yoto's published flow; never run |

## Decisions needed

1. **Hard stories.** Listen to the 15 weighty stories (marked W in the plan)
   before they reach the card.
2. **Narrator.** British, Australian or other accent; male or female.
3. **ElevenLabs account.** A paid plan with API access and its key.
4. **Interpretive sentences.** Keep or strike the glosses flagged in each script's fidelity notes.
