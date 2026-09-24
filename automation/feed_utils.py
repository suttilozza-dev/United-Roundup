#!/usr/bin/env python3
"""
Shared fetch/parse helpers for RSS, Atom and YouTube XML feeds.

Both validate_sources.py (which only checks a feed is reachable and
well-formed) and fetch_sources.py (which parses out real items) hit the
same URLs the same way, so the request/parse logic lives here once
instead of as two copies that can silently drift apart.
"""
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "Mozilla/5.0 (compatible; UnitedRoundupBot/1.0; +https://unitedroundup.com)"


def fetch_xml(url: str, timeout: int = 15) -> ET.Element:
    """Fetches `url` and parses it as XML.

    Raises on any failure (network error, HTTP status, malformed XML) --
    callers decide how to handle that per source, since a single flaky
    source shouldn't take down the whole pipeline.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return ET.fromstring(data)


def youtube_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def google_news_feed_url(query: str) -> str:
    """Google News search feed URL for `query`, restricted to UK English
    results (hl/gl/ceid) to match the rest of the site's sourcing."""
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl=en-GB&gl=GB&ceid=GB:en"
