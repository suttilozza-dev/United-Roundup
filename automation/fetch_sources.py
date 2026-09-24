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
import html
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from feed_utils import fetch_xml as _fetch_xml, google_news_feed_url, youtube_feed_url

HERE = Path(__file__).parent
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
    """Thin per-source wrapper around feed_utils.fetch_xml: a single bad
    source should not stop the rest of the pipeline from running, so any
    failure here is logged and treated as "no items from this source"."""
    try:
        return _fetch_xml(url)
    except Exception as exc:  # noqa: BLE001 -- we want to keep going on a bad source
        print(f"  [fetch failed] {url}: {exc}")
        return None


def clean_text(value: str | None) -> str:
    """Some publishers (e.g. talkSPORT) double-encode punctuation in their
    feeds, so a headline arrives as '&#8216;weak&#8217;' instead of 'weak'
    in curly quotes. Decode any leftover HTML entities so the wire shows
    the real characters. Unescape before stripping -- an entity-encoded
    space (e.g. '&nbsp;' at the edges) only becomes literal whitespace
    after decoding, so stripping first would miss it."""
    return html.unescape(html.unescape(value or "")).strip()


# Media RSS is published under both an http and an https namespace URI
# (the Daily Mail uses the https one), so look for thumbnails under both.
MEDIA_NS = ("http://search.yahoo.com/mrss/", "https://search.yahoo.com/mrss/")
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
IMG_SRC = re.compile(r"""<img[^>]+?src=["']([^"']+)["']""", re.IGNORECASE)
IMAGE_EXT = re.compile(r"\.(jpe?g|png|webp|gif)(\?|$)", re.IGNORECASE)


def _usable_image(url: str | None) -> str:
    """Only keep absolute https image URLs -- the site is served over https,
    so an http image would be blocked as mixed content."""
    url = html.unescape((url or "").strip())
    if url.startswith("//"):
        url = "https:" + url
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]
    # Sky Sports links full 1920px originals; its image server also has a
    # 768px version at the same path, which is plenty for a homepage card.
    url = re.sub(r"(\.365dm\.com/\d+/\d+/)\d+x\d+/", r"\g<1>768x432/", url)
    return url if url.startswith("https://") else ""


def extract_rss_image(item: ET.Element) -> str:
    """Best thumbnail for an RSS <item>, or "" if the feed doesn't give one.
    Feeds differ a lot: BBC uses media:thumbnail, the Guardian media:content
    (several sizes), Sky enclosure, and WordPress sites like talkSPORT only
    put an <img> inside the article body (content:encoded)."""
    candidates = []  # (width, url)
    for ns in MEDIA_NS:
        for tag in ("thumbnail", "content"):
            for el in item.iter(f"{{{ns}}}{tag}"):
                url = el.get("url")
                medium = (el.get("medium") or "").lower()
                mime = (el.get("type") or "").lower()
                if tag == "content" and medium not in ("", "image") and not mime.startswith("image"):
                    continue
                if tag == "content" and not medium and not mime.startswith("image") and not IMAGE_EXT.search(url or ""):
                    continue
                try:
                    width = int(el.get("width") or 0)
                except ValueError:
                    width = 0
                if _usable_image(url):
                    candidates.append((width, _usable_image(url)))
    if candidates:
        # Prefer a reasonably sized image: the largest one up to ~1200px wide,
        # otherwise whichever is smallest above that.
        fitting = [c for c in candidates if c[0] <= 1200]
        pool = fitting or candidates
        return max(pool, key=lambda c: c[0])[1] if fitting else min(pool, key=lambda c: c[0])[1]
    for el in item.findall("enclosure"):
        mime = (el.get("type") or "").lower()
        url = el.get("url")
        if (mime.startswith("image") or IMAGE_EXT.search(url or "")) and _usable_image(url):
            return _usable_image(url)
    for text in (item.findtext(f"{{{CONTENT_NS}}}encoded"), item.findtext("description")):
        match = IMG_SRC.search(text or "")
        if match and _usable_image(match.group(1)):
            return _usable_image(match.group(1))
    return ""


def youtube_thumbnail(entry: ET.Element, ns: dict) -> str:
    video_id = (entry.findtext("yt:videoId", namespaces=ns) or "").strip()
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    for thumb in entry.iter(f"{{{MEDIA_NS[0]}}}thumbnail"):
        if _usable_image(thumb.get("url")):
            return _usable_image(thumb.get("url"))
    return ""


def parse_rss_items(root: ET.Element, source_name: str) -> list[dict]:
    items = []
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title"))
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        desc = clean_text(item.findtext("description"))
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
            "image": extract_rss_image(item),
        })
    return items


def parse_google_news_items(root: ET.Element, source_name: str) -> list[dict]:
    """Google News search-feed items. Title comes as 'Headline - Outlet Name',
    so we strip the outlet suffix back off since we already know the source."""
    items = []
    for item in root.findall(".//item"):
        raw_title = clean_text(item.findtext("title"))
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


def parse_youtube_feed(root: ET.Element, source_name: str, united_only: bool = False) -> list[dict]:
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    items = []
    for entry in root.findall("a:entry", ns):
        title = clean_text(entry.findtext("a:title", namespaces=ns))
        link_el = entry.find("a:link", ns)
        link = link_el.get("href") if link_el is not None else ""
        published = (entry.findtext("a:published", namespaces=ns) or "").strip()
        # Channels that only cover United (the club's own channel and the
        # dedicated fan channels, flagged "united_only" in sources.json) skip
        # the keyword filter -- their titles often say "Carrick" or "United"
        # rather than "Manchester United", but everything they post is relevant.
        if not united_only and source_name != "Manchester United" and not UNITED_KEYWORDS.search(title):
            continue
        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "published_raw": published,
            "type": "video",
            "raw_text": title,
            "image": youtube_thumbnail(entry, ns),
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
        feed_url = youtube_feed_url(src["channel_id"])
        print(f" - {src['name']}")
        root = fetch_xml(feed_url)
        if root is not None:
            all_items.extend(parse_youtube_feed(root, src["name"], src.get("united_only", False)))

    print("Checking Google News fallback sources (paywalled/blocked sites)...")
    for src in sources.get("google_news_search", []):
        feed_url = google_news_feed_url(src["query"])
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
