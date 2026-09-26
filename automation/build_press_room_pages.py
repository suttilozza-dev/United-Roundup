#!/usr/bin/env python3
"""
Builds the Press Room Watch files that are published to GitHub Pages, so the
live page can update without a Netlify deploy.

Reads the source of truth in the repo (assets/press-room-data.js plus the two
automation/press_room_*.json registries), recomputes every tally with the same
code as rebuild_press_room.py, and writes to an output folder (default
"public/"):

  press-room-data.js       the question data the page's search/filter uses
  press-room-sections.json the four computed sections of press-room-watch.html
                           (hero scoreboard, findings, visual analysis,
                           narratives), which the live page swaps in on load
  press-room-summary.js    headline numbers for the homepage promo

Nothing in the repo is modified. Run from the repo root:
  python3 automation/build_press_room_pages.py [output_dir]
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_press_room as prw  # noqa: E402

# CSS selector on the live page -> class that opens the matching <section>.
SECTIONS = {
    ".prw-dashboard-hero": "prw-dashboard-hero",
    "#findings": "prw-findings",
    ".prw-visuals": "prw-visuals",
    "#narratives": "prw-narratives",
}


def extract_section(html, cls):
    """Return the full <section class="cls" ...>...</section>, allowing nesting."""
    m = re.search(r'<section class="%s"[^>]*>' % re.escape(cls), html)
    if not m:
        sys.exit(f"FAIL: section .{cls} not found in press-room-watch.html")
    i, depth = m.end(), 1
    while depth:
        n = re.search(r"<(/?)section\b", html[i:])
        if not n:
            sys.exit(f"FAIL: section .{cls} is not closed")
        i += n.end()
        depth += -1 if n.group(1) else 1
    return html[m.start():html.index(">", i) + 1]


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "public")
    out.mkdir(parents=True, exist_ok=True)

    records = prw.normalize(prw.load_questions())
    stats = prw.compute_stats(records)
    frags = prw.build_fragments(stats)
    html = prw.splice_html(prw.HTML_PATH.read_text(encoding="utf-8"), stats, frags)

    now = datetime.now(timezone.utc).isoformat()
    (out / "press-room-data.js").write_text(
        "// Published copy of Press Room Watch data (built by automation/build_press_room_pages.py).\n"
        f"// Built: {now}\n"
        "const PRESS_ROOM_QUESTIONS = " + json.dumps(records, ensure_ascii=False) + ";\n",
        encoding="utf-8")

    sections = {sel: extract_section(html, cls) for sel, cls in SECTIONS.items()}
    (out / "press-room-sections.json").write_text(json.dumps(sections, ensure_ascii=False), encoding="utf-8")

    summary = {
        "conferences": stats["n_conf"],
        "questions": stats["n_questions"],
        "responses": sum(stats["ctx_counts"].values()),
        "narratives": len(frags["established"]),
        "latest": stats["date_max"],
        "built": now,
    }
    (out / "press-room-summary.js").write_text(
        "const PRESS_ROOM_SUMMARY = " + json.dumps(summary) + ";\n", encoding="utf-8")
    print(f"Press Room Watch: {summary['questions']} questions, {summary['conferences']} conferences, "
          f"{summary['responses']} responses, {summary['narratives']} narratives -> {out}/")


if __name__ == "__main__":
    main()
