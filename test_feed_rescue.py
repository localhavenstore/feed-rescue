#!/usr/bin/env python3
"""Feed Rescue verify (SPEC v0.1): 5 OPML styles -> every reddit.com feed found, expected mappings, output OPML parses,
non-Reddit feeds unchanged, no page requests beyond its own files, hostile titles stay text, 390 px layout, no JS errors.
Needs Python 3 + Playwright (pip install playwright && playwright install chromium)."""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

def is_sub_feed(u):   # mirrors the page: reddit host + /r/<sub>... and not a single-post feed
    x = urlparse(u or ""); return (x.hostname or "") in {"reddit.com", "www.reddit.com", "old.reddit.com", "np.reddit.com", "new.reddit.com"} \
        and re.match(r"^/r/[A-Za-z0-9_+]+(?:/(?:hot|new|top|rising|controversial|best))?(?:/\.rss|\.rss)/?$", x.path, re.I) is not None

H = pathlib.Path(__file__).resolve().parent; SITE = H / "site"; F = []
def check(name, ok):
    print(("ok   " if ok else "FAIL ") + name); ok or F.append(name)

OPML = {
 "feedly": '''<?xml version="1.0"?><opml version="1.0"><head><title>Feedly</title></head><body><outline text="Tech" title="Tech">
<outline type="rss" text="selfhosted" title="selfhosted" xmlUrl="https://www.reddit.com/r/selfhosted/.rss" htmlUrl="https://www.reddit.com/r/selfhosted"/>
<outline type="rss" text="Ars" title="Ars" xmlUrl="https://feeds.arstechnica.com/arstechnica/index" htmlUrl="https://arstechnica.com"/></outline></body></opml>''',
 "inoreader": '''<?xml version="1.0" encoding="UTF-8"?><opml version="2.0"><head><title>Inoreader</title></head><body>
<outline text="n8n" title="n8n" type="rss" xmlUrl="https://www.reddit.com/r/n8n/top/.rss?t=week"/>
<outline text="HN" type="rss" xmlUrl="https://hnrss.org/frontpage"/></body></opml>''',
 "freshrss": '''<?xml version="1.0" encoding="UTF-8"?><opml version="2.0"><head><title>FreshRSS</title></head><body><outline text="Linux">
<outline text="linux" type="rss" xmlUrl="https://old.reddit.com/r/linux/.rss?sort=new" htmlUrl="https://old.reddit.com/r/linux"/></outline></body></opml>''',
 "miniflux": '''<?xml version="1.0" encoding="UTF-8"?><opml version="2.0"><head><title>Miniflux</title></head><body><outline text="All">
<outline title="multi" text="multi" xmlUrl="https://reddit.com/r/LocalLLaMA+homeassistant/.rss" type="rss"/></outline></body></opml>''',
 "odd": '''<?xml version="1.0"?><opml version="2.0"><head><title>x</title></head><body>
<outline text="&lt;img src=x onerror=alert(1)&gt;" type="rss" xmlUrl="https://www.reddit.com/r/zzqqxxnonexistent/.rss"/>
<outline text="not reddit" type="rss" xmlUrl="https://example.org/reddit.com/r/fake.rss"/></body></opml>''',
 "edge": '''<?xml version="1.0"?><opml version="2.0"><head><title>edge</title></head><body>
<outline text="parent" type="rss" xmlUrl="https://www.reddit.com/r/linux/.rss"><outline text="child" type="rss" xmlUrl="https://example.net/child.xml" category="keep" htmlUrl="https://example.net"/></outline>
<outline text="proto" type="rss" xmlUrl="https://www.reddit.com/r/__proto__/.rss"/><outline text="ctor" type="rss" xmlUrl="https://www.reddit.com/r/constructor/.rss"/>
<outline text="port" type="rss" xmlUrl="https://www.reddit.com:8443/r/selfhosted/new/.rss"/>
<outline text="post" type="rss" xmlUrl="https://www.reddit.com/r/linux/comments/abc123/some_post/.rss"/>
<outline text="attrs" type="rss" xmlUrl="https://blog.example.com/feed" htmlUrl="https://blog.example.com" category="a,b" x-custom="1" description="d &amp; e"/></body></opml>''',
}
EXPECT = {"feedly": {"selfhosted": "lemmy.world"}, "inoreader": {"n8n": "community.n8n.io"}, "freshrss": {"linux": "lemmy.ml"},
          "miniflux": {"LocalLLaMA": "sh.itjust.works", "homeassistant": "community.home-assistant.io"}, "odd": {"zzqqxxnonexistent": "hnrss.org"},
          "edge": {"linux": "lemmy.ml", "__proto__": "hnrss.org", "constructor": "hnrss.org", "selfhosted": "lemmy.world"}}

with sync_playwright() as pw:
    b = pw.chromium.launch(); ctx = b.new_context(accept_downloads=True, viewport={"width": 390, "height": 900})
    for name, opml in OPML.items():
        pg = ctx.new_page(); reqs, errs, dialogs = [], [], []
        pg.on("request", lambda r: reqs.append(r.url)); pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        pg.goto((SITE / "index.html").as_uri()); pg.fill("#t", opml); pg.click("#go")
        summary = pg.text_content("#sum")
        with pg.expect_download() as dl:
            pg.click("#dl")
        out = pathlib.Path(dl.value.path()).read_text()
        root = ET.fromstring(out)
        urls = [o.get("xmlUrl") for o in root.iter("outline") if o.get("xmlUrl")]
        for sub, host in EXPECT[name].items():
            check(f"{name}: r/{sub} -> a feed on {host}", any(host in u for u in urls))
        check(f"{name}: reddit.com subreddit feeds removed (default)", not any(is_sub_feed(u) for u in urls))
        orig = [o.get("xmlUrl") for o in ET.fromstring(opml.encode()).iter("outline") if o.get("xmlUrl") and not is_sub_feed(o.get("xmlUrl"))]
        check(f"{name}: other feeds unchanged ({len(orig)})", all(u in urls for u in orig))
        check(f"{name}: only its own files requested", all(u.startswith("file://") or u.startswith("blob:") for u in reqs))
        check(f"{name}: no JS errors / dialogs", not errs and not dialogs)
        check(f"{name}: no horizontal scroll at 390 px", pg.evaluate("document.documentElement.scrollWidth") <= 390)
        if name == "edge":
            outs = {o.get("xmlUrl"): o.attrib for o in root.iter("outline") if o.get("xmlUrl")}
            check("edge: feed nested under a removed reddit outline is kept", "https://example.net/child.xml" in outs and outs["https://example.net/child.xml"].get("category") == "keep")
            check("edge: single-post feed is not treated as a subreddit feed (kept)", any("/comments/abc123/" in u for u in urls))
            src = {o.get("xmlUrl"): o.attrib for o in ET.fromstring(opml.encode()).iter("outline")}
            check("edge: all attributes of an other feed preserved", outs.get("https://blog.example.com/feed") == src["https://blog.example.com/feed"])
            check("edge: 4 subreddit feeds found (2 hostile names, 1 port; the post feed not)", "4 reddit.com feed" in summary)
        if name == "odd":
            check("odd: hostile title shown as text, no <img> injected", pg.locator("#res img").count() == 0)
            check("odd: example.org URL with 'reddit.com/r/' in its path is NOT treated as reddit", "1 reddit.com feed" in summary)
        pg.close()
    pg = ctx.new_page(); pg.goto((SITE / "index.html").as_uri()); pg.fill("#t", "not xml at all"); pg.click("#go")
    check("garbage input -> clear message", "not an OPML" in pg.text_content("#sum")); b.close()
print(f"\n{len(F)} failed" if F else "\nALL PASSED"); sys.exit(1 if F else 0)
