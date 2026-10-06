# Feed Rescue

Reddit's RSS feeds stop on **13 November 2026** (Reddit: "there's no replacement" for following communities by RSS).
Feed Rescue takes your feed reader's OPML export, finds every subreddit feed in it (reddit.com/r/...; single-post feeds are
left as they are) and suggests open feeds on the same topic:

- the most active **Lemmy** community with the same name (large general instances, at least 50 monthly active users),
- the project's **official forum** (a hand-checked list - n8n, Home Assistant, Nextcloud, Docker, Fedora, Python, ...),
- a **Hacker News** keyword feed (hnrss.org) and a **news search** feed (Google News).

Then it gives you a new OPML to import. **Use it here: https://localhavenstore.github.io/feed-rescue/**

## Private by design
Everything runs in your browser. Your OPML is never uploaded, and the page makes no network requests while you use it
(the community list is part of the page). No analytics, no cookies.

## How the data is made
`build_data.py` reads the public [lemmyverse](https://data.lemmyverse.net/) community dataset (NSFW and flagged communities
excluded, instance allow-list in the script) and tests every official-forum feed (HTTP 200 + RSS) before it is published.
To rebuild: download https://data.lemmyverse.net/data/community.full.json into `raw/`, then `python3 build_data.py`
(writes `site/data.js`).
No Reddit data or API is used. Suggestions are alternatives on the same topic - not copies of the subreddit.

## Tests
`test_feed_rescue.py` (Playwright): OPML exports in Feedly / Inoreader / FreshRSS / Miniflux style and a hostile hand-written
one -> every subreddit feed found, expected mappings, output OPML parses, other feeds unchanged, no network requests,
hostile titles stay text, 390 px layout.

Not affiliated with Reddit, Lemmy or any project named. Made with AI assistance, checked by hand. MIT licence.
