#!/usr/bin/env python3
"""
Converts classified_items.json into assets/latest-data.js, the file
the homepage (index.html) actually reads in the browser.

Keeps the newest N items only, so the data file doesn't grow forever --
but always keeps a handful of the newest videos and academy stories on
top of that, because the homepage's "United on Screen" and "The Next
Generation" sections are built from them and would otherwise go empty
on a busy news day when articles crowd them out of the newest N.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).parent
SITE_DATA_PATH = HERE.parent / "assets" / "latest-data.js"
MAX_ITEMS = 60
MAX_VIDEOS_IN_FEED = 12  # stops YouTube uploads swamping the written news in the wire
RESERVED_VIDEOS = 8    # newest videos always kept for "United on Screen"
RESERVED_ACADEMY = 6   # newest academy stories always kept for "The Next Generation"
CARRY_OVER_DAYS = 14   # if today's run finds none, reuse the previous file's (if this recent)


def guess_iso_date(raw: str) -> str:
    """Best-effort conversion of whatever date format a feed gave us.
    Tries ISO format first (YouTube-style), then RFC822 (RSS-style, which
    handles named timezones like GMT/BST correctly -- unlike strptime's
    %z, which only understands numeric offsets like +0000)."""
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass
    return datetime.now(timezone.utc).isoformat()


def load_previous_items() -> list[dict]:
    """Items from the current assets/latest-data.js, so a run where YouTube
    (say) is briefly unreachable doesn't blank the homepage video section."""
    try:
        text = SITE_DATA_PATH.read_text(encoding="utf-8")
        start = text.index("const LATEST_ITEMS = ") + len("const LATEST_ITEMS = ")
        end = text.index(";\nconst LATEST_UPDATED")
        return json.loads(text[start:end])
    except (OSError, ValueError):
        return []


def main():
    classified_path = HERE / "classified_items.json"
    items = json.loads(classified_path.read_text())

    # Videos are always shown in their own homepage section, whatever
    # category the classifier gave them. If classification didn't reach
    # some videos (e.g. it ran out of time), pull them straight from the
    # raw feed so the section still shows the latest ones.
    raw_path = HERE / "raw_items.json"
    if raw_path.exists():
        seen_urls = {item["url"] for item in items}
        for raw in json.loads(raw_path.read_text()):
            if raw.get("type") == "video" and raw.get("url") not in seen_urls:
                items.append({**raw, "category": "videos"})
                seen_urls.add(raw.get("url"))

    out_items = []
    for i, item in enumerate(items):
        # Python's built-in hash() is randomized per-process (PYTHONHASHSEED),
        # so it would give the same URL a different id on every run. Use a
        # stable hash instead so an item's id doesn't change day to day.
        url_digest = hashlib.md5(item["url"].encode("utf-8")).hexdigest()[:8]
        out_items.append({
            "id": f"item-{i}-{url_digest}",
            "title": item["title"],
            "source": item["source"],
            "category": item["category"],
            "published": guess_iso_date(item.get("published_raw", "")),
            "url": item["url"],
            "type": item.get("type", "article"),
            "image": item.get("image", ""),
        })

    out_items.sort(key=lambda x: x["published"], reverse=True)

    # Carry over the previous run's videos/academy stories if this run found
    # none (a source outage), as long as they're still reasonably recent.
    cutoff = (datetime.now(timezone.utc) - timedelta(days=CARRY_OVER_DAYS)).isoformat()
    previous = [p for p in load_previous_items() if p.get("published", "") >= cutoff]
    for is_wanted in (lambda x: x.get("type") == "video", lambda x: x.get("category") == "academy"):
        if not any(is_wanted(x) for x in out_items):
            out_items.extend(p for p in previous if is_wanted(p))
    out_items.sort(key=lambda x: x["published"], reverse=True)

    newest, video_count = [], 0
    for x in out_items:
        if len(newest) >= MAX_ITEMS:
            break
        if x.get("type") == "video":
            if video_count >= MAX_VIDEOS_IN_FEED:
                continue
            video_count += 1
        newest.append(x)
    kept_ids = {x["id"] for x in newest}
    videos = [x for x in out_items if x.get("type") == "video"][:RESERVED_VIDEOS]
    academy = [x for x in out_items if x.get("category") == "academy"][:RESERVED_ACADEMY]
    extras = [x for x in videos + academy if x["id"] not in kept_ids]
    for x in extras:
        kept_ids.add(x["id"])
    out_items = sorted(newest + list({x["id"]: x for x in extras}.values()),
                       key=lambda x: x["published"], reverse=True)

    updated_iso = datetime.now(timezone.utc).isoformat()
    js_content = (
        "// Auto-generated by automation/update_site_data.py -- do not edit by hand.\n"
        f"// Last updated: {updated_iso}\n"
        "const LATEST_ITEMS = " + json.dumps(out_items, indent=2, ensure_ascii=False) + ";\n"
        f"const LATEST_UPDATED = \"{updated_iso}\";\n"
    )

    SITE_DATA_PATH.write_text(js_content, encoding="utf-8")
    print(f"Wrote {len(out_items)} items -> {SITE_DATA_PATH}")


if __name__ == "__main__":
    main()
