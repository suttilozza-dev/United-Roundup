#!/usr/bin/env python3
"""
Checks every source in sources.json is real and actually returns a feed.

Run this FIRST, before trusting fetch_sources.py. Anything that fails
here needs a corrected URL -- this script does not guess or invent one,
it only reports what it finds.
"""
import json
import urllib.error
from pathlib import Path

from feed_utils import fetch_xml, google_news_feed_url, youtube_feed_url

HERE = Path(__file__).parent


def check(url: str) -> tuple[bool, str]:
    try:
        root = fetch_xml(url)
        count = len(root.findall(".//item")) or len(
            root.findall(".//{http://www.w3.org/2005/Atom}entry")
        )
        if count == 0:
            return False, "Reachable, but no items found -- feed format may be unexpected"
        return True, f"OK -- {count} items found"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main():
    sources = json.loads((HERE / "sources.json").read_text())
    results = []

    for src in sources.get("rss_feeds", []):
        ok, msg = check(src["url"])
        results.append((src["name"], src["url"], ok, msg))

    for src in sources.get("youtube_channels", []):
        feed_url = youtube_feed_url(src["channel_id"])
        ok, msg = check(feed_url)
        results.append((src["name"], feed_url, ok, msg))

    for src in sources.get("google_news_search", []):
        feed_url = google_news_feed_url(src["query"])
        ok, msg = check(feed_url)
        results.append((f"{src['name']} (via Google News)", feed_url, ok, msg))

    print(f"{'STATUS':<8}{'SOURCE':<28}{'DETAIL'}")
    print("-" * 70)
    fail_count = 0
    for name, url, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        if not ok:
            fail_count += 1
        print(f"{status:<8}{name:<28}{msg}")

    print(f"\n{len(results) - fail_count}/{len(results)} sources verified working.")
    if fail_count:
        print("Fix or replace the FAILed sources before relying on this pipeline.")


if __name__ == "__main__":
    main()
