#!/usr/bin/env python3
"""Upload build/tracks/*.mp3 to Yoto as one Make Your Own playlist.

  yoto.py login     device-code sign-in; stores tokens in build/yoto-token.json
  yoto.py upload    upload every track, then create (or update) the playlist

Needs YOTO_CLIENT_ID (a public client created at yoto.dev). After the first
upload, link the playlist to a blank card in the Yoto app; later uploads update
the same playlist, so the card never needs relinking.

STATUS: written from Yoto's published flow (yoto.dev/myo/uploading-to-cards)
but NOT yet run against the live API, because this build environment could not
reach Yoto's hosts. Expect to adjust field names on first use. The manual
fallback always works: drag build/tracks/*.mp3 into my.yotoplay.com.
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
TOKEN = BUILD / "yoto-token.json"
STATE = BUILD / "yoto-playlist.json"
AUTH = "https://login.yotoplay.com"
API = "https://api.yotoplay.com"
TITLE = "Bible Stories"


def call(method, url, headers=None, data=None, ok_errors=()):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            body = r.read()
            return json.loads(body) if body.strip().startswith((b"{", b"[")) else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        if e.code in ok_errors:
            return json.loads(body)
        sys.exit(f"{method} {url} failed with {e.code}: {body[:600]}")


def form(url, **fields):
    return call("POST", url, {"Content-Type": "application/x-www-form-urlencoded"},
                urllib.parse.urlencode(fields).encode(), ok_errors=(400, 403))


def client_id():
    cid = os.environ.get("YOTO_CLIENT_ID")
    if not cid:
        sys.exit("set YOTO_CLIENT_ID (create a public client at yoto.dev)")
    return cid


def login():
    d = form(f"{AUTH}/oauth/device/code", client_id=client_id(),
             scope="profile offline_access", audience=API)
    print(f"Open {d.get('verification_uri_complete', d.get('verification_uri'))}"
          f" and confirm code {d.get('user_code')}")
    while True:
        time.sleep(d.get("interval", 5))
        t = form(f"{AUTH}/oauth/token", client_id=client_id(), device_code=d["device_code"],
                 grant_type="urn:ietf:params:oauth:grant-type:device_code")
        if "access_token" in t:
            break
        if t.get("error") not in ("authorization_pending", "slow_down"):
            sys.exit(f"login failed: {t}")
    BUILD.mkdir(exist_ok=True)
    TOKEN.write_text(json.dumps(t))
    TOKEN.chmod(0o600)
    print("signed in")


def bearer():
    if not TOKEN.exists():
        sys.exit("run: yoto.py login")
    t = json.loads(TOKEN.read_text())
    if t.get("refresh_token"):
        new = form(f"{AUTH}/oauth/token", client_id=client_id(), grant_type="refresh_token",
                   refresh_token=t["refresh_token"])
        if "access_token" in new:
            t.update(new)
            TOKEN.write_text(json.dumps(t))
    return {"Authorization": f"Bearer {t['access_token']}", "Accept": "application/json"}


def upload_track(path, auth):
    data = path.read_bytes()
    q = urllib.parse.urlencode({"sha256": hashlib.sha256(data).hexdigest(), "filename": path.name})
    up = call("GET", f"{API}/media/transcode/audio/uploadUrl?{q}", auth)["upload"]
    if up.get("uploadUrl"):  # absent when Yoto already holds identical bytes
        call("PUT", up["uploadUrl"], {"Content-Type": "audio/mpeg"}, data)
    for _ in range(60):
        t = call("GET", f"{API}/media/upload/{up['uploadId']}/transcoded?loudnorm=false", auth)
        t = t.get("transcode", {})
        if t.get("transcodedSha256"):
            return t
        time.sleep(2)
    sys.exit(f"transcode timed out for {path.name}")


def upload():
    auth = bearer()
    tracks = sorted((BUILD / "tracks").glob("*.mp3"))
    if not tracks:
        sys.exit("nothing in build/tracks; run storyteller.py build first")
    chapters, total_s, total_b = [], 0, 0
    for n, path in enumerate(tracks, start=1):
        t = upload_track(path, auth)
        info = t.get("transcodedInfo", {})
        title = path.stem.split("-", 1)[1].replace("-", " ").capitalize()
        if (ROOT / "stories" / f"{path.stem}.md").exists():
            for line in (ROOT / "stories" / f"{path.stem}.md").read_text().splitlines():
                if line.startswith("title:"):
                    title = line.split(":", 1)[1].strip()
        key = f"{n:02d}"
        track = {"key": key, "title": title, "trackUrl": f"yoto:#{t['transcodedSha256']}",
                 "duration": info.get("duration"), "fileSize": info.get("fileSize"),
                 "channels": info.get("channels"), "format": info.get("format"),
                 "type": "audio", "overlayLabel": str(n)}
        chapters.append({"key": key, "title": title, "overlayLabel": str(n), "tracks": [track]})
        total_s += info.get("duration") or 0
        total_b += info.get("fileSize") or 0
        print(f"uploaded {n}/{len(tracks)} {title}")
    body = {"title": TITLE, "content": {"chapters": chapters},
            "metadata": {"media": {"duration": total_s, "fileSize": total_b}}}
    if STATE.exists():
        body["cardId"] = json.loads(STATE.read_text())["cardId"]
    res = call("POST", f"{API}/content", {**auth, "Content-Type": "application/json"},
               json.dumps(body).encode())
    card_id = (res.get("card") or res).get("cardId")
    if card_id:
        STATE.write_text(json.dumps({"cardId": card_id}))
    print(f"playlist '{TITLE}' saved ({len(chapters)} stories, {total_s / 3600:.2f} h). "
          "Link it to a blank card in the Yoto app.")


if __name__ == "__main__":
    {"login": login, "upload": upload}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
