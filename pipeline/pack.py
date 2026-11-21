#!/usr/bin/env python3
"""Assemble sellable digital packs from build/tracks and assets.

  pack.py            builds build/packs/{complete,old-testament,new-testament}/

Each pack holds audio/, icons/, cover.png, playlist.json, Parent-Guide.html
(printed to PDF by pipeline/guide_pdf.js), LICENCE.txt and NOTICES.txt.
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKS = {"complete": (1, 60, "Bible Stories: Creation to New Creation"),
         "old-testament": (1, 33, "Bible Stories: The Old Testament"),
         "new-testament": (34, 60, "Bible Stories: The New Testament")}

LICENCE = """LICENCE: PERSONAL AND HOUSEHOLD USE

You have bought a licence to use these recordings, not ownership of them.

You may:
- copy the files to devices and audio cards that belong to your own household;
- play them for your own family, as often as you like;
- keep a backup copy.

You may not:
- sell, give away, upload or share the files, or links to them, outside your
  household (this includes sharing a playlist link from an audio player app);
- use them in a church, school, nursery or other group setting without a
  group licence;
- edit, re-voice or republish the recordings or scripts.

For a group licence, contact the seller.
"""

NOTICES = """NOTICES

Scripts: original retellings written for this collection. No Bible translation
is quoted.

Voices and sound: the narration, character voices, sound effects and musical
stings are computer-generated (ElevenLabs). No human voice actors were used.

Icons and cover artwork: derived from Noto Emoji, copyright Google LLC,
licensed under the Apache License, Version 2.0
(https://www.apache.org/licenses/LICENSE-2.0).

Yoto is a trademark of Yoto Limited. This product is independent and is not
affiliated with, endorsed by or sponsored by Yoto.
"""

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font: 11pt/1.5 Georgia, 'DejaVu Serif', serif; color: #1c2333; }
h1 { font: 700 26pt/1.15 'DejaVu Sans', Helvetica, sans-serif; color: #16224a; margin: 0 0 4pt; }
h2 { font: 700 14pt 'DejaVu Sans', Helvetica, sans-serif; color: #16224a; margin: 20pt 0 6pt;
     border-bottom: 2px solid #f0c95c; padding-bottom: 3pt; break-after: avoid; }
p.lead { font-size: 12.5pt; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; }
th, td { text-align: left; padding: 3.5pt 6pt; border-bottom: 1px solid #dfe3ee; vertical-align: top; }
th { font-family: 'DejaVu Sans', Helvetica, sans-serif; background: #eef1f8; }
td.n, td.t { white-space: nowrap; text-align: right; color: #56607a; }
tr { break-inside: avoid; }
.w { color: #a2401c; font-weight: 700; }
ol li, ul li { margin-bottom: 4pt; }
.small { font-size: 9pt; color: #56607a; }
"""


def meta(path):
    text = path.read_text(encoding="utf-8")
    get = lambda k: (re.search(rf"^{k}:\s*(.+)$", text, re.M) or [None, ""])[1].strip()
    notes = [l[1:].strip() for l in text.splitlines() if l.startswith("#") and "Fidelity notes" not in l]
    return {"stem": path.stem, "number": int(path.stem[:2]), "title": get("title"),
            "refs": get("refs"), "weighty": get("weighty") == "true", "notes": notes}


def guide(name, stories, total_s):
    e = html.escape
    rows = "".join(
        f"<tr><td class=n>{s['number']}</td><td>{e(s['title'])}"
        f"{' <span class=w>W</span>' if s['weighty'] else ''}</td>"
        f"<td>{e(s['refs'])}</td><td class=t>{int(s['seconds'] // 60)}:{int(s['seconds'] % 60):02d}</td></tr>"
        for s in stories)
    weighty = "".join(f"<li><b>{s['number']}. {e(s['title'])}</b> ({e(s['refs'])})</li>"
                      for s in stories if s["weighty"])
    n = len(stories)
    return f"""<!doctype html><html lang="en-GB"><meta charset="utf-8"><title>{e(name)}</title>
<style>{CSS}</style><body>
<h1>{e(name)}</h1>
<p class=lead>{n} Bible stories for children aged three to five, told in order,
with a cast of voices. {total_s / 3600:.1f} hours of audio, ready for a Yoto
Make Your Own card or any MP3 player.</p>

<h2>What is in this pack</h2>
<ul>
<li><b>audio/</b>: {n} MP3 files, numbered in story order.</li>
<li><b>icons/</b>: one 16 by 16 pixel picture per story, with the same name as its MP3, for the player's display.</li>
<li><b>cover.png</b>: artwork for the playlist.</li>
<li><b>playlist.json</b>: titles, passages and file names, for anyone who wants to automate the upload.</li>
<li><b>LICENCE.txt</b> and <b>NOTICES.txt</b>.</li>
</ul>

<h2>Putting it on a Yoto card</h2>
<ol>
<li>Sign in at my.yotoplay.com on a computer and choose Make Your Own, then add a playlist.</li>
<li>Drag every file from the <b>audio</b> folder into the playlist. They sort into story order by name.</li>
<li>Click the playlist picture and upload <b>cover.png</b>.</li>
<li>For each track, click its small icon, choose upload, and pick the picture from <b>icons</b> with the same number. Allow about ten minutes. This step is optional.</li>
<li>Save. In the Yoto app on your phone, open the playlist, choose link to card, and hold a blank Make Your Own card on the player.</li>
</ol>
<p class=small>One card holds up to 100 tracks and 5 hours, so this pack fits on a single card.
The files are ordinary MP3s and also play on any phone, tablet, car stereo or other children's audio player.</p>

<h2>How the stories are told</h2>
<ul>
<li><b>The Bible sets the events.</b> Nothing is invented: no extra characters, events or motives. What God and Jesus say is a close paraphrase of the passage.</li>
<li><b>Plain, not graphic.</b> Sin is called disobeying God and death is called death. Hard things are said once, in a short sentence, without lingering detail.</li>
<li><b>No tacked-on morals.</b> Each story ends with what the passage itself shows about God.</li>
<li><b>Written for the ear.</b> Short sentences, repeated refrains, and a narrator who always says who is speaking.</li>
<li><b>One story.</b> The collection runs in order, so a child hears the promise made, kept waiting, and kept.</li>
</ul>

<h2>The stories</h2>
<p class=small><span class=w>W</span> marks a weighty story: it includes death, judgement or real danger. You may want to listen first.</p>
<table><tr><th>#</th><th>Story</th><th>Bible passage</th><th>Length</th></tr>{rows}</table>

<h2>Weighty stories in this pack</h2>
<ul>{weighty}</ul>

<h2>How this was made</h2>
<p>The scripts are original retellings written for this collection and checked against the Bible passages listed above.
The narrator, the character voices, the sound effects and the short guitar phrases are computer-generated; no human
voice actors were used. Every recording was checked against its script.</p>

<h2>Licence in brief</h2>
<p>For your own household: copy the files to your own devices and cards and play them as often as you like.
Please do not share, resell or upload the files or playlist links. Churches, schools and nurseries need a group licence.
The full terms are in LICENCE.txt.</p>
<p class=small>Yoto is a trademark of Yoto Limited. This product is independent and is not affiliated with or endorsed by Yoto.</p>
</body></html>"""


def main():
    stories = [meta(p) for p in sorted((ROOT / "stories").glob("*.md"))]
    for s in stories:
        rep = ROOT / "build" / "reports" / f"{s['stem']}.json"
        s["seconds"] = json.loads(rep.read_text())["seconds"]
    for slug, (lo, hi, name) in PACKS.items():
        out = ROOT / "build" / "packs" / slug
        shutil.rmtree(out, ignore_errors=True)
        (out / "audio").mkdir(parents=True)
        (out / "icons").mkdir()
        chosen = [s for s in stories if lo <= s["number"] <= hi]
        for s in chosen:
            shutil.copy(ROOT / "build" / "tracks" / f"{s['stem']}.mp3", out / "audio")
            shutil.copy(ROOT / "assets" / "icons" / f"{s['stem']}.png", out / "icons")
        shutil.copy(ROOT / "assets" / "cover.png", out / "cover.png")
        total = sum(s["seconds"] for s in chosen)
        (out / "playlist.json").write_text(json.dumps({"title": name, "cover": "cover.png", "chapters": [
            {"number": s["number"], "title": s["title"], "passage": s["refs"], "weighty": s["weighty"],
             "seconds": s["seconds"], "audio": f"audio/{s['stem']}.mp3", "icon": f"icons/{s['stem']}.png"}
            for s in chosen]}, indent=2, ensure_ascii=False))
        (out / "LICENCE.txt").write_text(LICENCE)
        (out / "NOTICES.txt").write_text(NOTICES)
        (out / "Parent-Guide.html").write_text(guide(name, chosen, total))
        print(f"{slug}: {len(chosen)} stories, {total / 3600:.2f} h")


if __name__ == "__main__":
    main()
