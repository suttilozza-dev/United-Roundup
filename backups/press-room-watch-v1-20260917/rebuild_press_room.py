#!/usr/bin/env python3
"""
Regenerates Press Room Watch's tally/leaderboard panels in press-room-watch.html
from the question data in assets/press-room-data.js.

assets/press-room-data.js (the PRESS_ROOM_QUESTIONS array) is the single source of
truth. To add new press conferences: append new question objects to that array
(or paste them in as JSON and merge), then run this script. It recomputes every
number and list on the page -- nothing about counts/leaderboards should ever be
hand-edited in the HTML again.

Required fields per question object:
  fixture, date (YYYY-MM-DD), context ("pre_match"|"post_match"),
  result ("not_applicable"|"win"|"draw"|"loss"), section, question, topic,
  framing, narrative_tag, wording_status, source_url, response (may be "")

date_disp / context_label are derived automatically -- don't hand-maintain them.

Usage: python3 automation/rebuild_press_room.py
Run from the site's repo root (where assets/ and press-room-watch.html live).
"""
import re, sys, json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "assets" / "press-room-data.js"
HTML_PATH = ROOT / "press-room-watch.html"
CONF_REGISTRY_PATH = ROOT / "automation" / "press_room_conferences.json"
RESP_COUNTS_PATH = ROOT / "automation" / "press_room_response_counts.json"

CONTEXT_LABELS = {"pre_match": "Pre-match", "post_match": "Post-match"}


def load_supplemental():
    """Optional supplemental evidence, keyed independently of the question array:
    - press_room_conferences.json: every known press conference (fixture,
      date, context, result), including ones where NO question wording was
      recovered at all (answer-only articles). Without this file, conference
      counts are derived purely from question records, which understates
      conferences that yielded zero recovered questions.
    - press_room_response_counts.json: {"fixture|date|context": count} giving
      the TOTAL number of preserved response records (paragraphs) for that
      conference -- every quoted answer recovered from official coverage,
      whether or not it could be linked to a specific captured question.
      This is the authoritative source for the RESPONSES tally and the
      "Before and after matches" panel; it is deliberately independent of
      the question array's per-record `response` text (which may join
      several response paragraphs into one question's display quote, or
      duplicate the same answer across two near-identical question wordings
      -- neither of which should be double-counted as separate responses).
    Both are optional -- if absent, the script still runs, just on a
    narrower (question-only) evidence base, and the RESPONSES total will
    undercount. When you add a new conference, add its entry to BOTH
    registries: fixture/date/context/result here, and its total response
    count in press_room_response_counts.json (count every response
    paragraph recovered for that conference, not just ones tied to a
    question).
    """
    registry = []
    if CONF_REGISTRY_PATH.exists():
        registry = json.loads(CONF_REGISTRY_PATH.read_text(encoding="utf-8"))
    resp_counts = {}
    if RESP_COUNTS_PATH.exists():
        resp_counts = json.loads(RESP_COUNTS_PATH.read_text(encoding="utf-8"))
    return registry, resp_counts


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def date_disp(iso):
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%-d %b %Y")


def kicker_range(date_min, date_max):
    """'15 JAN–4 SEP 2026' style range: drop the year from the start date
    when both ends fall in the same year, matching the page's own style."""
    start = datetime.strptime(date_min, "%Y-%m-%d")
    end = datetime.strptime(date_max, "%Y-%m-%d")
    start_str = start.strftime("%-d %b").upper()
    if start.year != end.year:
        start_str += f" {start.year}"
    return f"{start_str}–{end.strftime('%-d %b %Y').upper()}"


def load_questions():
    c = DATA_PATH.read_text(encoding="utf-8")
    m = re.search(r"const PRESS_ROOM_QUESTIONS = (\[.*?\]);", c, re.S)
    if not m:
        sys.exit("FAIL: could not find PRESS_ROOM_QUESTIONS array in " + str(DATA_PATH))
    return json.loads(m.group(1))


def normalize(records):
    out = []
    required = ["fixture", "date", "context", "result", "section", "question",
                "topic", "framing", "narrative_tag", "wording_status", "source_url"]
    for i, r in enumerate(records):
        missing = [k for k in required if k not in r or r[k] in (None, "")]
        # response is allowed to be empty; everything else must be present
        missing = [k for k in missing if k != "response"]
        if missing:
            sys.exit(f"FAIL: record {i} ({r.get('fixture','?')} {r.get('date','?')}) missing fields: {missing}")
        if r["context"] not in CONTEXT_LABELS:
            sys.exit(f"FAIL: record {i} has unknown context '{r['context']}' (want pre_match/post_match)")
        rr = dict(r)
        rr["date_disp"] = date_disp(rr["date"])
        rr["context_label"] = CONTEXT_LABELS[rr["context"]]
        rr.setdefault("response", "")
        out.append(rr)
    out.sort(key=lambda r: (r["date"], r["context"] != "pre_match"))
    return out


def write_data_js(records):
    js = (
        "// Source of truth for Press Room Watch. Append new press-conference\n"
        "// question objects here, then run automation/rebuild_press_room.py.\n"
        f"// Last rebuilt: {datetime.now(timezone.utc).isoformat()}\n"
        "const PRESS_ROOM_QUESTIONS = " + json.dumps(records, indent=2, ensure_ascii=False) + ";\n"
    )
    DATA_PATH.write_text(js, encoding="utf-8")
    return js


def compute_stats(records):
    topic_counts = Counter(r["topic"] for r in records)
    registry, resp_counts = load_supplemental()

    # conf_meta: (fixture, date) -> (context, result), merged from question
    # records and the optional conferences registry (registry can add
    # conferences with zero recovered questions; it never overrides a
    # context/result actually seen in the question data).
    conf_meta = {}
    for c in registry:
        conf_meta[(c["fixture"], c["date"])] = (c["context"], c.get("result", "not_applicable"))
    for r in records:
        conf_meta[(r["fixture"], r["date"])] = (r["context"], r["result"])
    n_conf = len(conf_meta)
    pre_conf = sum(1 for ctx, _ in conf_meta.values() if ctx == "pre_match")
    post_conf = n_conf - pre_conf

    def bucket_for(context, result):
        if context == "pre_match":
            return "pre-match"
        return {"win": "post-win", "draw": "post-draw", "loss": "post-loss"}.get(result)

    # Response-record context stats: driven entirely by the per-conference
    # response_counts registry (total preserved response paragraphs for that
    # conference), NOT by counting question records. A conference's response
    # total belongs to the conference, independent of how many questions were
    # recovered for it or whether a paragraph could be linked to one.
    ctx_counts = Counter()
    ctx_confs = defaultdict(set)
    for (fixture, date), (context, result) in conf_meta.items():
        bucket = bucket_for(context, result)
        if not bucket:
            continue
        ctx_confs[bucket].add((fixture, date))
        key = f"{fixture}|{date}|{context}"
        ctx_counts[bucket] += resp_counts.get(key, 0)

    narr = defaultdict(list)
    for r in records:
        narr[r["narrative_tag"]].append(r)
    narr_rows = []
    for tag, rows in narr.items():
        confs = set((r["fixture"], r["date"]) for r in rows)
        dates = sorted(r["date"] for r in rows)
        narr_rows.append({
            "tag": tag,
            "topic": Counter(r["topic"] for r in rows).most_common(1)[0][0],
            "count": len(rows),
            "conferences": len(confs),
            "date_min": dates[0],
            "date_max": dates[-1],
        })

    dates_all = sorted(r["date"] for r in records)
    return {
        "topic_counts": topic_counts,
        "n_conf": n_conf, "pre_conf": pre_conf, "post_conf": post_conf,
        "ctx_counts": ctx_counts, "ctx_confs": ctx_confs,
        "narr_rows": narr_rows,
        "date_min": dates_all[0], "date_max": dates_all[-1],
        "n_questions": len(records),
    }


def build_fragments(stats):
    # 1. Topics <ol> (top 10)
    top10 = stats["topic_counts"].most_common(10)
    maxc = top10[0][1]
    li = []
    for i, (topic, count) in enumerate(top10, 1):
        pct = count / maxc * 100
        li.append(f'<li><span>{i:02d}</span><div><b>{esc(topic)}</b>'
                   f'<i><span style="width:{pct}%"></span></i></div><strong>{count}</strong></li>')
    topics_ol = "<ol>" + "".join(li) + "</ol>"

    # 2. Context/result panel
    order = ["pre-match", "post-win", "post-draw", "post-loss"]
    totals = {k: stats["ctx_counts"].get(k, 0) for k in order}
    maxtotal = max(totals.values()) or 1
    blocks = []
    for k in order:
        total = totals[k]
        confs = len(stats["ctx_confs"].get(k, []))
        rate = round(total / confs, 2) if confs else 0
        pct = round(total / maxtotal * 100)
        blocks.append(f'<div><span>{k}</span><strong>{total}</strong><i>{rate}<!-- --> per eligible conference</i>'
                       f'<div><span style="width:{pct}%"></span></div></div>')
    context_div = '<div class="prw-context-list">' + "".join(blocks) + "</div>"

    # 3. Narrative leaderboard (established: >=3 questions across >=2 conferences)
    established = [n for n in stats["narr_rows"] if n["count"] >= 3 and n["conferences"] >= 2]
    established.sort(key=lambda x: -x["count"])
    maxn = established[0]["count"] if established else 1
    li2 = []
    for i, n in enumerate(established, 1):
        pct = n["count"] / maxn * 100
        cls = ' class="top-1"' if i == 1 else (' class="top-2"' if i == 2 else (' class="top-3"' if i == 3 else ""))
        li2.append(f'<li{cls}><span class="prw-rank">{i:02d}</span><div class="prw-narrative-name">'
                    f'<div><i>T{i:02d}</i><small>Recurring topic</small></div>'
                    f'<h3>{esc(n["topic"])}</h3>'
                    f'<div class="prw-narrative-meter"><span style="width:{pct}%"></span></div>'
                    f'<p>{date_disp(n["date_min"])}<!-- --> &rarr; <!-- -->{date_disp(n["date_max"])}</p></div>'
                    f'<strong>{n["count"]}</strong><span class="prw-conference-count">{n["conferences"]}</span></li>')
    narrative_ol = "<ol>" + "".join(li2) + "</ol>"

    # 4. On the radar (emerging)
    emerging = [n for n in stats["narr_rows"] if not (n["count"] >= 3 and n["conferences"] >= 2)]
    emerging.sort(key=lambda x: -x["count"])
    arts = []
    for n in emerging:
        arts.append(f'<article><div><span>Emerging</span><i>{esc(n["topic"])}</i></div>'
                     f'<h4>{esc(n["topic"])}</h4>'
                     f'<small>{n["count"]}<!-- --> question{"s" if n["count"] != 1 else ""} &middot; '
                     f'<!-- -->{n["conferences"]}<!-- --> conference{"s" if n["conferences"] != 1 else ""}</small></article>')
    radar_div = "<div>" + "".join(arts) + "</div>"

    return {
        "topics_ol": topics_ol, "context_div": context_div,
        "narrative_ol": narrative_ol, "radar_div": radar_div,
        "established": established, "top_topic": top10[0],
    }


def splice_html(html, stats, frags):
    def must(html, pattern, repl, label, flags=0):
        new_html, n = re.subn(pattern, repl, html, count=1, flags=flags)
        if n != 1:
            sys.exit(f"FAIL [{label}]: pattern did not match exactly once (matched {n})")
        return new_html

    # kicker date range
    html = must(html, r'<p class="prw-kicker">SOURCED TRACKER · [^<]*</p>',
                f'<p class="prw-kicker">SOURCED TRACKER · {kicker_range(stats["date_min"], stats["date_max"])}</p>',
                "kicker")

    # scoreboard
    html = must(html, r'<article><span>CONFERENCES</span><strong>\d+</strong><small>\d+<!-- --> pre · <!-- -->\d+<!-- --> post</small></article>',
                f'<article><span>CONFERENCES</span><strong>{stats["n_conf"]}</strong><small>{stats["pre_conf"]}<!-- --> pre · <!-- -->{stats["post_conf"]}<!-- --> post</small></article>',
                "scoreboard-conferences")
    html = must(html, r'<article><span>QUESTIONS</span><strong>\d+</strong><small>exact or source-verbatim</small></article>',
                f'<article><span>QUESTIONS</span><strong>{stats["n_questions"]}</strong><small>exact or source-verbatim</small></article>',
                "scoreboard-questions")
    total_responses = sum(stats["ctx_counts"].values())
    html = must(html, r'<article><span>RESPONSES</span><strong>\d+</strong><small>preserved records</small></article>',
                f'<article><span>RESPONSES</span><strong>{total_responses}</strong><small>preserved records</small></article>',
                "scoreboard-responses")
    html = must(html, r'<article><span>NARRATIVES</span><strong>\d+</strong><small>established patterns</small></article>',
                f'<article><span>NARRATIVES</span><strong>{len(frags["established"])}</strong><small>established patterns</small></article>',
                "scoreboard-narratives")

    # topics ol
    html = must(html, r'<span>Primary question count</span></div></div><ol>.*?</ol></article><article class="prw-context-panel">',
                '<span>Primary question count</span></div></div>' + frags["topics_ol"] + '</article><article class="prw-context-panel">',
                "topics-ol", flags=re.S)

    # context panel
    html = must(html, r'<div class="prw-context-list">.*?</div><p>These rates show the available source base\.',
                frags["context_div"] + '<p>These rates show the available source base.',
                "context-div", flags=re.S)

    # editorial paragraph
    top_topic, top_count = frags["top_topic"]
    html = must(html, r'Questions about .+? account for <!-- -->\d+<!-- --> turns—well ahead of any other topic\.',
                f'Questions about {esc(top_topic).lower()} account for <!-- -->{top_count}<!-- --> turns—well ahead of any other topic.',
                "editorial-paragraph")

    # narrative leaderboard
    html = must(html, r'<span>Conferences</span></div><ol>.*?</ol></div><aside class="prw-watchlist">',
                '<span>Conferences</span></div>' + frags["narrative_ol"] + '</div><aside class="prw-watchlist">',
                "narrative-ol", flags=re.S)

    # on the radar
    html = must(html, r'analytical lenses measure published responses rather than questions\.</p><div>.*?</div></aside></div></section>',
                'analytical lenses measure published responses rather than questions.</p>' + frags["radar_div"] + '</aside></div></section>',
                "radar-div", flags=re.S)

    return html


def main():
    records = normalize(load_questions())
    write_data_js(records)
    stats = compute_stats(records)
    frags = build_fragments(stats)
    html = HTML_PATH.read_text(encoding="utf-8")
    html = splice_html(html, stats, frags)
    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Rebuilt from {len(records)} questions across {stats['n_conf']} conferences "
          f"({stats['date_min']} -> {stats['date_max']}).")
    print(f"Established narratives: {len(frags['established'])}. "
          f"Top topic: {frags['top_topic'][0]} ({frags['top_topic'][1]}).")


if __name__ == "__main__":
    main()
