#!/usr/bin/env python3
"""
Fetches new items from every source in sources.json.

Uses only Python's standard library (urllib + xml.etree) so it needs
no extra installs -- this matters because GitHub Actions runs a fresh
environment every time, and fewer dependencies means fewer things that
can break.

IMPORTANT: the URLs in sources.json are a starting point, not verified
fact. Run validate_sources.py first and fix anything it flags before
relying on this in production.
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).parent
UA = "Mozilla/5.0 (compatible; UnitedRoundupBot/1.0; +https://unitedroundup.com)"
MAX_AGE_DAYS = 14  # anything older than this is dropped -- this is a "latest news"
                    # page, not an archive, and Google News search has no recency
                    # window of its own so it happily returns 2014 alongside today


def is_recent(pub_date_raw: str) -> bool:
    """Returns True if we can't tell the age (benefit of the doubt -- most feeds
    are already current) OR if it's within MAX_AGE_DAYS. Returns False only when
    we can parse a date AND it's genuinely old."""
    if not pub_date_raw:
        return True
    try:
        pub_dt = parsedate_to_datetime(pub_date_raw)
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return True  # unparseable format -- don't punish the item for that
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    return pub_dt >= cutoff

# Only keep items that actually look United-related -- a general BBC
# Sport feed, for example, covers every team, so this filter matters.
UNITED_KEYWORDS = re.compile(
    r"manchester united|man utd|man united|old trafford|carrington",
    re.IGNORECASE,
)


def fetch_xml(url: str) -> ET.Element | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        return ET.fromstring(data)
    except Exception as exc:  # noqa: BLE001 -- we want to keep going on a bad source
        print(f"  [fetch failed] {url}: {exc}")
        return None


def parse_rss_items(root: ET.Element, source_name: str) -> list[dict]:
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = (item.findtext("description") or "").strip()
        haystack = f"{title} {desc}"
        if not UNITED_KEYWORDS.search(haystack):
            continue
        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "published_raw": pub,
            "type": "article",
            "raw_text": haystack[:600],
        })
    return items


def parse_google_news_items(root: ET.Element, source_name: str) -> list[dict]:
    """Google News search-feed items. Title comes as 'Headline - Outlet Name',
    so we strip the outlet suffix back off since we already know the source."""
    items = []
    for item in root.findall(".//item"):
        raw_title = (item.findtext("title") or "").strip()
        title = re.sub(r"\s*-\s*[^-]+$", "", raw_title).strip()
        if not UNITED_KEYWORDS.search(title):
            continue
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "published_raw": pub,
            "type": "article",
            "raw_text": raw_title,
            "via_google_news": True,  # flagged so the site can label these as aggregated
        })
    return items


def parse_youtube_feed(root: ET.Element, source_name: str) -> list[dict]:
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    items = []
    for entry in root.findall("a:entry", ns):
        title = (entry.findtext("a:title", namespaces=ns) or "").strip()
        link_el = entry.find("a:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        published = (entry.findtext("a:published", namespaces=ns) or "").strip()
        # Manchester United's own channel doesn't need the keyword filter --
        # everything from it is relevant by definition.
        if source_name != "Manchester United" and not UNITED_KEYWORDS.search(title):
            continue
        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "published_raw": published,
            "type": "video",
            "raw_text": title,
        })
    return items


def main():
    sources = json.loads((HERE / "sources.json").read_text())
    all_items = []

    print("Checking RSS sources...")
    for src in sources.get("rss_feeds", []):
        print(f" - {src['name']}")
        root = fetch_xml(src["url"])
        if root is not None:
            all_items.extend(parse_rss_items(root, src["name"]))

    print("Checking YouTube channels...")
    for src in sources.get("youtube_channels", []):
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={src['channel_id']}"
        print(f" - {src['name']}")
        root = fetch_xml(feed_url)
        if root is not None:
            all_items.extend(parse_youtube_feed(root, src["name"]))

    print("Checking Google News fallback sources (paywalled/blocked sites)...")
    for src in sources.get("google_news_search", []):
        query = urllib.parse.quote(src["query"])
        feed_url = f"https://news.google.com/rss/search?q={query}&hl=en-GB&gl=GB&ceid=GB:en"
        print(f" - {src['name']}")
        root = fetch_xml(feed_url)
        if root is not None:
            all_items.extend(parse_google_news_items(root, src["name"]))

    before_count = len(all_items)
    all_items = [item for item in all_items if is_recent(item.get("published_raw", ""))]
    dropped = before_count - len(all_items)
    if dropped:
        print(f"\nDropped {dropped} item(s) older than {MAX_AGE_DAYS} days.")

    out_path = HERE / "raw_items.json"
    out_path.write_text(json.dumps(all_items, indent=2, ensure_ascii=False))
    print(f"\nFound {len(all_items)} candidate items -> {out_path}")


if __name__ == "__main__":
    main()
