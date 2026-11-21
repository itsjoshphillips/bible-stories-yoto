#!/usr/bin/env python3
"""Render one short passage with several narrator treatments for A/B listening."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import storyteller as s

V = {"george": "JBFqnCBsd6RMkjVDRZzb", "alice": "Xb7hH8MSUJpSbSDYk0k2",
     "jessica": "cgSgspJ2msm6clMCkdW9", "disciple": "IKne3meq5aSn9XLyUdCD", "jesus": "cjVigY5qzO86Huf0OWal"}
PLAIN = [("n", "This is a story from God's book, the Bible. It is called: Jesus Calms the Storm."),
         ("n", "Then the wind began to blow. It blew harder, and harder. A great storm came roaring across the lake. The waves grew tall. They crashed against the boat. Crash! They broke right over the side. Splash! The boat was filling up with water."),
         ("n", "Jesus's friends were so afraid. And where was Jesus? [quietly] Still asleep, on the cushion."),
         ("disciple", "[shouting, frightened] Teacher! Wake up! Don't you care that we are going to drown?"),
         ("jesus", "[firm, with calm authority] Peace. Be still."),
         ("n", "[softly] And the wind stopped. The waves lay down flat. Everything was calm. And quiet. And still.")]
TAGGED = [("n", "[warm, bright, lively storyteller speaking to small children] This is a story from God's book, the Bible. It is called: Jesus Calms the Storm!"),
          ("n", "[building excitement] Then the wind began to blow. It blew harder, and harder! A great storm came roaring across the lake. The waves grew tall. They crashed against the boat. Crash! They broke right over the side. Splash! [worried] The boat was filling up with water."),
          ("n", "[wide-eyed] Jesus's friends were so afraid. And where was Jesus? [whispers, amused] Still asleep, on the cushion."),
          PLAIN[3], PLAIN[4],
          ("n", "[hushed, full of wonder] And the wind stopped. The waves lay down flat. Everything was calm. And quiet. And still.")]
VARIANTS = {  # name: (narrator voice, lines, stability or None)
    "A-george-tags": ("george", TAGGED, None),
    "B-george-tags-creative": ("george", TAGGED, 0.0),
    "C-alice-tags": ("alice", TAGGED, None),
    "D-jessica-tags": ("jessica", TAGGED, None),
}
out = s.BUILD / "auditions"
for name, (voice, lines, stab) in VARIANTS.items():
    if sys.argv[1:] and name[0] not in sys.argv[1:]:
        continue
    body = {"model_id": "eleven_v3",
            "inputs": [{"text": t, "voice_id": V[voice if k == "n" else k]} for k, t in lines]}
    if stab is not None:
        body["settings"] = {"stability": stab}
    raw = out / f"{name}.raw.mp3"
    raw.write_bytes(s.post_json("/v1/text-to-dialogue?output_format=mp3_44100_128", body))
    wav = out / f"{name}.wav"
    s.to_wav(raw, wav, -16.0, 1.0)
    s.ffmpeg("-i", wav, "-b:a", "128k", out / f"narrator-{name}.mp3")
    raw.unlink(); wav.unlink()
    print(name, round(s.duration(out / f"narrator-{name}.mp3"), 1), "s")
