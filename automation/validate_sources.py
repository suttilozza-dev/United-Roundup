#!/usr/bin/env python3
"""
Checks every source in sources.json is real and actually returns a feed.

Run this FIRST, before trusting fetch_sources.py. Anything that fails
here needs a corrected URL -- this script does not guess or invent one,
it only reports what it finds.
"""
import json
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
UA = "Mozilla/5.0 (compatible; UnitedRoundupBot/1.0; +https://unitedroundup.com)"


def check(url: str) -> tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        root = ET.fromstring(data)
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
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={src['channel_id']}"
        ok, msg = check(feed_url)
        results.append((src["name"], feed_url, ok, msg))

    for src in sources.get("google_news_search", []):
        import urllib.parse
        query = urllib.parse.quote(src["query"])
        feed_url = f"https://news.google.com/rss/search?q={query}&hl=en-GB&gl=GB&ceid=GB:en"
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
