#!/usr/bin/env python3
"""Turn story scripts into multi-voice audio tracks for a Yoto card.

Python standard library plus ffmpeg/ffprobe only.

  storyteller.py lint                 check scripts, word counts, card budget
  storyteller.py voices               list voices on the ElevenLabs account
  storyteller.py audition             render one sample line per voice slot
  storyteller.py build [files...]     render tracks into build/tracks/
      --mock        no API calls: tones stand in for speech (tests the assembly)
      --verify      transcribe each chunk and compare it with the script
      --takes N     render N takes per chunk and keep the closest (implies --verify)
      --no-sfx      replace [SFX] cues with a pause
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
CACHE = BUILD / "cache"
TRACKS = BUILD / "tracks"
API = "https://api.elevenlabs.io"

SPEAKER_RE = re.compile(r"^([A-Z][A-Z0-9_]*):\s*(.*)$")
DIRECTIVE_RE = re.compile(r"^\[(PAUSE|SFX|SCENE)\b:?\s*(.*?)\]$")
TAG_RE = re.compile(r"\[[^\]]*\]")

# Yoto Make Your Own limits (support.yotoplay.com): 100 tracks, 5 hours and
# 500 MB per card; 60 minutes and 100 MB per track.
YOTO_MAX_TRACKS, YOTO_MAX_HOURS, YOTO_MAX_MB = 100, 5.0, 500
WORDS_PER_MINUTE = 135  # planning estimate for unhurried narration


# ---------------------------------------------------------------- scripts

@dataclass
class Item:
    kind: str            # "line" | "pause" | "sfx"
    speaker: str = ""
    text: str = ""
    seconds: float = 0.0


@dataclass
class Story:
    path: Path
    meta: dict
    items: list

    @property
    def slug(self):
        return self.path.stem

    def spoken(self):
        return " ".join(TAG_RE.sub(" ", i.text) for i in self.items if i.kind == "line")


def parse(path, cfg):
    raw = path.read_text(encoding="utf-8").splitlines()
    meta, i = {}, 0
    if raw and raw[0].strip() == "---":
        i = 1
        while raw[i].strip() != "---":
            key, _, value = raw[i].partition(":")
            meta[key.strip()] = value.strip()
            i += 1
        i += 1
    items, cur = [], None
    for n, line in enumerate(raw[i:], start=i + 1):
        s = line.strip()
        if s.startswith("#"):
            continue
        if not s:
            cur = None
            continue
        m = DIRECTIVE_RE.match(s)
        if m:
            cur = None
            kind, arg = m.group(1), m.group(2)
            if kind == "PAUSE":
                items.append(Item("pause", seconds=float(arg)))
            elif kind == "SCENE":
                items.append(Item("pause", seconds=cfg["audio"]["scene_pause"]))
            else:
                desc, _, secs = arg.partition("|")
                items.append(Item("sfx", text=desc.strip(), seconds=float(secs or 3)))
            continue
        m = SPEAKER_RE.match(s)
        if m:
            cur = Item("line", speaker=m.group(1), text=m.group(2).strip())
            items.append(cur)
        elif cur is None:
            sys.exit(f"{path.name}:{n}: text with no SPEAKER: prefix")
        else:
            cur.text += " " + s
    return Story(path, meta, items)


def sequence(story, max_chars):
    """Group consecutive lines into dialogue requests; directives split groups."""
    seq, cur, size = [], [], 0
    for it in story.items:
        if it.kind != "line":
            if cur:
                seq.append(("speech", cur))
                cur, size = [], 0
            seq.append((it.kind, it))
            continue
        if cur and size + len(it.text) > max_chars:
            seq.append(("speech", cur))
            cur, size = [], 0
        cur.append(it)
        size += len(it.text)
    if cur:
        seq.append(("speech", cur))
    return seq


def load_config():
    with open(ROOT / "cast.toml", "rb") as f:
        return tomllib.load(f)


def voice_id(cfg, speaker):
    slot = cfg["characters"].get(speaker)
    if slot is None or slot not in cfg["voices"]:
        sys.exit(f"speaker {speaker} has no voice: add it to [characters] in cast.toml")
    return cfg["voices"][slot]["voice_id"]


def story_files(args_files):
    files = [Path(f) for f in args_files] or sorted((ROOT / "stories").glob("*.md"))
    if not files:
        sys.exit("no story scripts found")
    return files


# ------------------------------------------------------------------ lint

def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def cmd_lint(args):
    cfg = load_config()
    total_min, total_chars, problems = 0.0, 0, 0
    print(f"{'story':<34}{'words':>6}{'min':>6}{'voices':>7}{'chars':>7}  notes")
    files = story_files(args.files)
    for f in files:
        st = parse(f, cfg)
        notes = []
        lines = [i for i in st.items if i.kind == "line"]
        for sp in sorted({i.speaker for i in lines}):
            if cfg["characters"].get(sp) not in cfg["voices"]:
                notes.append(f"NO VOICE for {sp}")
        for i in lines:
            if len(i.text) > cfg["model"]["max_chars"]:
                notes.append(f"line over {cfg['model']['max_chars']} chars ({i.speaker})")
        words = len(st.spoken().split())
        sents = sentences(st.spoken())
        longest = max((len(s.split()) for s in sents), default=0)
        if longest > 24:
            notes.append(f"longest sentence {longest} words")
        mean = words / max(len(sents), 1)
        if mean > 11:
            notes.append(f"mean sentence {mean:.1f} words")
        slots = {cfg["characters"].get(i.speaker) for i in lines}
        if len(slots) > 5:
            notes.append(f"{len(slots)} voices is a lot for under-fives")
        pauses = sum(i.seconds for i in st.items if i.kind != "line")
        minutes = words / WORDS_PER_MINUTE + pauses / 60 + 0.25
        if not 2.0 <= minutes <= 6.0:
            notes.append("outside the 2 to 6 minute range")
        chars = sum(len(i.text) for i in lines)
        total_min += minutes
        total_chars += chars
        problems += sum(1 for n in notes if n.startswith(("NO VOICE", "line over")))
        print(f"{st.slug[:33]:<34}{words:>6}{minutes:>6.1f}{len(slots):>7}{chars:>7}  {'; '.join(notes)}")
    n = len(files)
    print(f"\n{n} stories, about {total_min:.0f} min, {total_chars:,} billable characters per take")
    if n:
        per = total_min / n
        print(f"projected for 60 stories at this average: {per * 60 / 60:.1f} h "
              f"(Yoto card limit {YOTO_MAX_HOURS:.0f} h, {YOTO_MAX_TRACKS} tracks, {YOTO_MAX_MB} MB)")
    if n > YOTO_MAX_TRACKS or total_min / 60 > YOTO_MAX_HOURS:
        print("OVER the Yoto card limit")
        problems += 1
    return 1 if problems else 0


# ----------------------------------------------------------------- audio

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.exit(f"command failed: {' '.join(map(str, cmd))}\n{p.stderr[-1500:]}")
    return p.stdout


def ffmpeg(*a):
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *map(str, a)])


def duration(path):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                      "-of", "csv=p=0", str(path)]).strip())


def to_wav(src, dst, loudness, tempo=1.0, trim=True):
    """Trim edge silence, normalise loudness, convert to 44.1 kHz mono WAV."""
    cut = "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05"
    chain = [cut, "areverse", cut, "areverse"] if trim else []
    chain += ["highpass=f=70", f"loudnorm=I={loudness}:TP=-1.5:LRA=11"]
    if abs(tempo - 1.0) > 1e-3:
        chain.append(f"atempo={tempo}")
    ffmpeg("-i", src, "-af", ",".join(chain), "-ar", 44100, "-ac", 1, dst)


def silence(seconds, dst):
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{seconds:.3f}", dst)


# ------------------------------------------------------------ ElevenLabs

def api_key():
    key = os.environ.get("ELEVENLABS_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        sys.exit("set ELEVENLABS_API_KEY (environment or .env), or use --mock")
    return key


def http(method, url, headers, data=None):
    for attempt in range(5):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = e.read()[:600].decode(errors="replace")
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(2 ** attempt * 2)
                continue
            sys.exit(f"{method} {url} failed with {e.code}: {body}")
        except urllib.error.URLError as e:
            if attempt < 4:
                time.sleep(2 ** attempt * 2)
                continue
            sys.exit(f"{method} {url} failed: {e.reason}")


def post_json(path, body):
    return http("POST", API + path, {"xi-api-key": api_key(), "Content-Type": "application/json"},
                json.dumps(body).encode())


def dialogue_body(cfg, items):
    body = {"model_id": cfg["model"]["id"],
            "inputs": [{"text": i.text, "voice_id": voice_id(cfg, i.speaker)} for i in items]}
    if "stability" in cfg["model"]:
        body["settings"] = {"stability": cfg["model"]["stability"]}
    if "seed" in cfg["model"]:
        body["seed"] = cfg["model"]["seed"]
    return body


def cached(kind, payload, take, suffix, make):
    """Content-addressed cache: unchanged chunks are never paid for twice."""
    key = hashlib.sha256(json.dumps([kind, payload, take], sort_keys=True).encode()).hexdigest()[:20]
    path = CACHE / f"{kind}-{key}{suffix}"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".part" + suffix)
        make(tmp)
        tmp.rename(path)
    return path


def render_speech(cfg, items, take, mock):
    body = dialogue_body(cfg, items)
    if mock:
        chars = sum(len(TAG_RE.sub("", i.text)) for i in items)
        hz = 160 + int(hashlib.md5(body["inputs"][0]["voice_id"].encode()).hexdigest(), 16) % 160

        def make(p):
            ffmpeg("-f", "lavfi", "-i", f"sine=frequency={hz}:sample_rate=44100",
                   "-t", f"{max(chars / 15, 0.5):.2f}", "-af", "volume=0.2", p)
        return cached("mock", body, take, ".mp3", make)
    fmt = cfg["model"]["output_format"]

    def make(p):
        p.write_bytes(post_json(f"/v1/text-to-dialogue?output_format={fmt}", body))
    return cached("speech", [body, fmt], take, ".mp3", make)


def render_sfx(item, mock):
    if mock:
        def make(p):
            ffmpeg("-f", "lavfi", "-i", "anoisesrc=color=pink:amplitude=0.1:sample_rate=44100",
                   "-t", item.seconds, p)
        return cached("mocksfx", [item.text, item.seconds], 0, ".mp3", make)
    body = {"text": item.text, "duration_seconds": item.seconds, "prompt_influence": 0.4}

    def make(p):
        p.write_bytes(post_json("/v1/sound-generation", body))
    return cached("sfx", body, 0, ".mp3", make)


def transcribe(path):
    boundary = uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="model_id"\r\n\r\nscribe_v1\r\n'.encode(),
             f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="chunk.mp3"\r\n'
             f'Content-Type: audio/mpeg\r\n\r\n'.encode(), path.read_bytes(),
             f'\r\n--{boundary}--\r\n'.encode()]
    out = http("POST", API + "/v1/speech-to-text",
               {"xi-api-key": api_key(), "Content-Type": f"multipart/form-data; boundary={boundary}"},
               b"".join(parts))
    return json.loads(out).get("text", "")


def words(text):
    return re.findall(r"[a-z0-9']+", TAG_RE.sub(" ", text).lower())


def similarity(expected, heard):
    return difflib.SequenceMatcher(None, words(expected), words(heard), autojunk=False).ratio()


# ----------------------------------------------------------------- build

def build_story(story, cfg, args):
    au = cfg["audio"]
    work = BUILD / "work" / story.slug
    work.mkdir(parents=True, exist_ok=True)
    parts, report, flagged = [], [], 0

    def add(path):
        parts.append(path)

    def add_silence(seconds):
        if seconds > 0:
            p = work / f"{len(parts):03d}-silence.wav"
            silence(seconds, p)
            add(p)

    def add_asset(key):
        src = ROOT / au.get(key, "")
        if au.get(key) and src.is_file():
            p = work / f"{len(parts):03d}-{key}.wav"
            to_wav(src, p, au["loudness"] - 4, trim=False)
            add(p)
            add_silence(0.6)

    add_silence(au["lead_in"])
    add_asset("intro")
    previous = None
    for kind, payload in sequence(story, cfg["model"]["max_chars"]):
        if kind == "pause":
            add_silence(payload.seconds)
        elif kind == "sfx" and args.no_sfx:
            add_silence(au["scene_pause"])
        elif kind == "sfx":
            p = work / f"{len(parts):03d}-sfx.wav"
            to_wav(render_sfx(payload, args.mock), p, au["sfx_loudness"], trim=False)
            add(p)
            add_silence(0.3)
        else:
            if previous == "speech":
                add_silence(au["gap"])
            expected = " ".join(i.text for i in payload)
            best, best_score, heard = None, -1.0, ""
            for take in range(args.takes):
                src = render_speech(cfg, payload, take, args.mock)
                score = 1.0
                if args.verify and not args.mock:
                    heard = transcribe(src)
                    score = similarity(expected, heard)
                if score > best_score:
                    best, best_score, best_heard = src, score, heard
            p = work / f"{len(parts):03d}-speech.wav"
            to_wav(best, p, au["loudness"], au["tempo"])
            add(p)
            secs = duration(p)
            rate = len(TAG_RE.sub("", expected)) / max(secs, 0.1)
            entry = {"chunk": len(report) + 1, "seconds": round(secs, 1),
                     "chars_per_second": round(rate, 1), "similarity": round(best_score, 3),
                     "source": best.name, "starts": expected[:60]}
            bad_rate = not args.mock and not 7 <= rate <= 24
            if best_score < au["verify_threshold"] or bad_rate:
                entry["FLAG"] = "pace" if bad_rate else "transcript mismatch"
                entry["heard"] = best_heard
                flagged += 1
            report.append(entry)
        previous = kind
    add_silence(0.8)
    add_asset("outro")
    add_silence(au["tail"])

    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    TRACKS.mkdir(parents=True, exist_ok=True)
    out = TRACKS / f"{story.slug}.mp3"
    ffmpeg("-f", "concat", "-safe", 0, "-i", listing, "-af", "alimiter=limit=0.89",
           "-ar", 44100, "-ac", 1, "-b:a", "128k",
           "-metadata", f"title={story.meta.get('title', story.slug)}",
           "-metadata", f"track={story.meta.get('number', '')}",
           "-metadata", "album=Bible Stories", out)
    secs = duration(out)
    (BUILD / "reports").mkdir(exist_ok=True)
    (BUILD / "reports" / f"{story.slug}.json").write_text(
        json.dumps({"track": out.name, "seconds": round(secs, 1), "chunks": report}, indent=2))
    flag = f"  {flagged} chunk(s) FLAGGED, see build/reports/{story.slug}.json" if flagged else ""
    print(f"{out.relative_to(ROOT)}  {secs / 60:.1f} min  {len(report)} chunks{flag}")
    return secs, out.stat().st_size, flagged


def cmd_build(args):
    cfg = load_config()
    if args.takes > 1:
        args.verify = True
    total_s = total_b = flagged = 0
    for f in story_files(args.files):
        s, b, fl = build_story(parse(f, cfg), cfg, args)
        total_s, total_b, flagged = total_s + s, total_b + b, flagged + fl
    print(f"total {total_s / 3600:.2f} h, {total_b / 1e6:.0f} MB"
          + (f", {flagged} chunk(s) need a listen" if flagged else ""))
    return 1 if flagged else 0


def cmd_voices(_):
    data = json.loads(http("GET", API + "/v1/voices", {"xi-api-key": api_key()}))
    for v in sorted(data.get("voices", []), key=lambda v: v.get("name", "")):
        labels = v.get("labels") or {}
        print(f"{v['voice_id']}  {v.get('name', ''):<28} "
              f"{labels.get('accent', ''):<12} {labels.get('gender', ''):<8} {labels.get('description', '')}")


def cmd_audition(_):
    cfg = load_config()
    out = BUILD / "auditions"
    out.mkdir(parents=True, exist_ok=True)
    line = "Long, long ago, God made a promise. [gently] And God always keeps his promises."
    for slot, v in cfg["voices"].items():
        body = {"model_id": cfg["model"]["id"], "inputs": [{"text": line, "voice_id": v["voice_id"]}]}
        (out / f"{slot}.mp3").write_bytes(post_json("/v1/text-to-dialogue", body))
        print(out / f"{slot}.mp3")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lint")
    p.add_argument("files", nargs="*")
    p.set_defaults(fn=cmd_lint)
    p = sub.add_parser("build")
    p.add_argument("files", nargs="*")
    p.add_argument("--mock", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--no-sfx", action="store_true", help="replace [SFX] cues with a pause")
    p.add_argument("--takes", type=int, default=1)
    p.set_defaults(fn=cmd_build)
    sub.add_parser("voices").set_defaults(fn=cmd_voices)
    sub.add_parser("audition").set_defaults(fn=cmd_audition)
    args = ap.parse_args()
    sys.exit(args.fn(args) or 0)


if __name__ == "__main__":
    main()
