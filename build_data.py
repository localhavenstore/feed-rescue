#!/usr/bin/env python3
"""Feed Rescue data (SPEC v0.1): lemmyverse community dump (raw/community.full.json, public data.lemmyverse.net) + a curated
map of official Discourse forums -> site/data.js. Every forum feed is checked live (HTTP 200 + RSS) at build time; a failing
one is left out (printed). Run by us weekly until 13 Nov. No Reddit data is used."""
import datetime as dt
import json
import pathlib
import sys
import time
import urllib.request

H = pathlib.Path(__file__).resolve().parent
MIN_MAU = 50
# general-purpose instances with topic communities (2026-10-06 activity ranking); political/unknown instances left out
ALLOW = ["lemmy.world", "lemmy.ml", "sh.itjust.works", "lemmy.ca", "lemmy.dbzer0.com", "sopuli.xyz", "lemmy.blahaj.zone",
         "programming.dev", "feddit.org", "lemmy.zip", "slrpnk.net", "feddit.uk", "lemmy.today", "ani.social", "beehaw.org",
         "discuss.online", "lemmy.sdf.org", "reddthat.com", "aussie.zone", "lemdro.id"]
# subreddit (lowercase) -> official Discourse forum of that project (latest.rss)
FORUMS = {"n8n": "community.n8n.io", "obsidianmd": "forum.obsidian.md", "docker": "forums.docker.com", "proxmox": "https://forum.proxmox.com/forums/-/index.rss",
          "homeassistant": "community.home-assistant.io", "nextcloud": "help.nextcloud.com", "openhab": "community.openhab.org",
          "letsencrypt": "community.letsencrypt.org", "rust": "users.rust-lang.org", "kde": "discuss.kde.org",
          "gnome": "discourse.gnome.org", "fedora": "discussion.fedoraproject.org", "ubuntu": "discourse.ubuntu.com", "nixos": "discourse.nixos.org",
          "pihole": "discourse.pi-hole.net", "syncthing": "forum.syncthing.net", "godot": "forum.godotengine.org", "blender": "blenderartists.org",
          "kicad": "forum.kicad.info", "python": "discuss.python.org", "golang": "forum.golangbridge.org", "rails": "discuss.rubyonrails.org",
          "julia": "discourse.julialang.org", "gitlab": "forum.gitlab.com", "grafana": "community.grafana.com", "firefox": "discourse.mozilla.org",
          "signal": "community.signalusers.org", "bitwarden": "community.bitwarden.com", "traefik": "community.traefik.io", "caddy": "caddy.community"}


def rss_ok(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "feed-rescue-build/0.1 (localhavenstore)"})
        with urllib.request.urlopen(req, timeout=25) as r:
            head = r.read(600).decode("utf-8", "replace")
            return r.status == 200 and "<rss" in head
    except Exception:
        return False


def main():
    raw = json.loads((H / "raw" / "community.full.json").read_text())
    allow = set(ALLOW); best = {}
    for c in raw:
        if c.get("nsfw") or c.get("isSuspicious") or c["baseurl"] not in allow:
            continue
        mau = (c.get("counts") or {}).get("users_active_month") or 0
        if mau < MIN_MAU:
            continue
        k = c["name"].lower()
        if k not in best or mau > best[k][3]:
            best[k] = [c["baseurl"], c["name"], (c.get("title") or c["name"])[:80], mau]
    forums, dead = {}, []
    for sub, host in FORUMS.items():
        url = host if host.startswith("https://") else f"https://{host}/latest.rss"     # Discourse default; others = full URL
        (forums.__setitem__(sub, url) if rss_ok(url) else dead.append(url)); time.sleep(0.5)
    out = {"built": dt.date.today().isoformat(), "min_mau": MIN_MAU, "instances": ALLOW, "lemmy": best, "forums": forums}
    js = "window.FR_DATA=" + json.dumps(out, separators=(",", ":"), ensure_ascii=False) + ";\n"
    (H / "site").mkdir(exist_ok=True); (H / "site" / "data.js").write_text(js)
    print(f"lemmy communities: {len(best)}, forums ok: {len(forums)}/{len(FORUMS)}, data.js {len(js) // 1024} KB")
    for d in dead:
        print("forum feed NOT ok (left out):", d)
    return 0 if len(js) < 1_500_000 else 1


if __name__ == "__main__":
    sys.exit(main())
