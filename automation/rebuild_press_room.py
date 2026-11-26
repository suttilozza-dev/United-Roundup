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

# Narrative tags were renamed when Press Room Watch moved from tracking one
# manager to tracking whichever manager is in post. Old names still resolve.
TAG_ALIASES = {"carrick_future": "manager_future", "carrick_appointment": "manager_appointment"}

# The manager a conference belongs to (registry field "manager").
MANAGER_CARRICK = "Carrick"
MANAGER_POCHETTINO = "Pochettino"


def load_supplemental(manager=None):
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
    if manager:
        registry = [c for c in registry if c.get("manager") == manager]
    resp_counts = {}
    if RESP_COUNTS_PATH.exists():
        resp_counts = json.loads(RESP_COUNTS_PATH.read_text(encoding="utf-8"))
    return registry, resp_counts


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def rate_per_conf(total, confs):
    """Responses-per-conference rate, used by both the Findings context
    panel and the Visual Analysis context-comparison columns."""
    return round(total / confs, 2) if confs else 0


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


def conference_managers():
    """(fixture, date, context) -> manager, from the conferences registry."""
    registry, _ = load_supplemental()
    return {(c["fixture"], c["date"], c["context"]): c.get("manager") for c in registry}


def normalize(records):
    out = []
    managers = conference_managers()
    required = ["manager", "fixture", "date", "context", "result", "section", "question",
                "topic", "framing", "narrative_tag", "wording_status", "source_url"]
    for i, r in enumerate(records):
        if not r.get("manager"):
            r = dict(r, manager=managers.get((r.get("fixture"), r.get("date"), r.get("context"))))
        missing = [k for k in required if k not in r or r[k] in (None, "")]
        # response is allowed to be empty; everything else must be present
        missing = [k for k in missing if k != "response"]
        if missing:
            sys.exit(f"FAIL: record {i} ({r.get('fixture','?')} {r.get('date','?')}) missing fields: {missing}")
        if r["context"] not in CONTEXT_LABELS:
            sys.exit(f"FAIL: record {i} has unknown context '{r['context']}' (want pre_match/post_match)")
        rr = dict(r)
        rr["narrative_tag"] = TAG_ALIASES.get(rr["narrative_tag"], rr["narrative_tag"])
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


def compute_stats(records, manager=None):
    """Tallies for `records` (already limited to one manager, or all of them).
    `manager` limits the conferences registry the same way."""
    topic_counts = Counter(r["topic"] for r in records)
    registry, resp_counts = load_supplemental(manager)

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

    # The narrative register is grouped by primary TOPIC, the same basis as the
    # Findings ranking and the Visual Analysis chart. It used to group by
    # narrative_tag and label each group with its most common topic, so a topic
    # that spans several tags (e.g. "Targets and expectations") showed different
    # totals in different sections under the same label.
    narr = defaultdict(list)
    for r in records:
        narr[r["topic"]].append(r)
    narr_rows = []
    for topic, rows in narr.items():
        confs = set((r["fixture"], r["date"]) for r in rows)
        dates = sorted(r["date"] for r in rows)
        narr_rows.append({
            "tag": Counter(r["narrative_tag"] for r in rows).most_common(1)[0][0],
            "topic": topic,
            "count": len(rows),
            "conferences": len(confs),
            "date_min": dates[0],
            "date_max": dates[-1],
        })

    # Evidence mix per context (for the Visual Analysis "Evidence mix" chart):
    # how many recovered QUESTIONS in each context are club-published
    # (article-verbatim) versus recovered from captions (transcript-derived).
    # Deliberately question-based, not response-based -- wording_status is a
    # property of a question record.
    wording_mix = defaultdict(Counter)
    for r in records:
        wording_mix[r["context"]][r["wording_status"]] += 1

    dates_all = sorted(r["date"] for r in records) or sorted(c["date"] for c in registry)
    return {
        "topic_counts": topic_counts,
        "n_conf": n_conf, "pre_conf": pre_conf, "post_conf": post_conf,
        "ctx_counts": ctx_counts, "ctx_confs": ctx_confs,
        "wording_mix": wording_mix,
        "narr_rows": narr_rows,
        "date_min": dates_all[0] if dates_all else None, "date_max": dates_all[-1] if dates_all else None,
        "n_questions": len(records),
    }


def build_fragments(stats):
    # 1. Topics <ol> (top 10)
    top10 = stats["topic_counts"].most_common(10)
    maxc = top10[0][1] if top10 else 1
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
        rate = rate_per_conf(total, confs)
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

    # 5. Visual Analysis: question-mix donut (top 5 topics + "Other")
    donut_palette = ["#d65432", "#f08a5d", "#e2b173", "#63748d", "#9b7b88", "#d8d1c8"]
    top5 = top10[:5]
    other_count = stats["n_questions"] - sum(c for _, c in top5)
    slices = top5 + [("Other topics", other_count)]
    cursor = 0.0
    stops, donut_li = [], []
    for (label, val), color in zip(slices, donut_palette):
        pct = val / stats["n_questions"] * 100 if stats["n_questions"] else 0
        start = cursor
        cursor += pct
        stops.append(f"{color} {start}% {cursor}%")
        donut_li.append(f'<li><i style="background:{color}"></i><span>{esc(label)}</span>'
                         f'<b>{val}</b><small>{round(pct)}%</small></li>')
    donut_bg = f"conic-gradient({','.join(stops)})"
    donut_ol = "<ol>" + "".join(donut_li) + "</ol>"
    top_pct = round(top10[0][1] / stats["n_questions"] * 100) if top10 and stats["n_questions"] else 0

    # 6. Visual Analysis: context-comparison bar columns (reuses the same
    #    per-conference rates as the Findings context panel).
    max_rate = max((totals[k] / len(stats["ctx_confs"].get(k, [])) if stats["ctx_confs"].get(k) else 0
                     for k in order), default=1) or 1
    columns = []
    for k in order:
        total = totals[k]
        confs = len(stats["ctx_confs"].get(k, []))
        rate = rate_per_conf(total, confs)
        height = round((rate / max_rate) * 100) if max_rate else 0
        label = k.replace("post-", "")
        columns.append(f'<div><div class="prw-column-value">{rate}</div><div class="prw-column-track">'
                        f'<i style="height:{height}%"></i></div><b>{label}</b>'
                        f'<small>{confs} conference{"s" if confs != 1 else ""}</small></div>')
    columns_html = "".join(columns)

    # 7. Visual Analysis: evidence-mix bars (article-verbatim vs
    #    transcript-derived), one bar per context.
    evidence_bars = []
    for ctx, label in (("pre_match", "Pre-match"), ("post_match", "Post-match")):
        mix = stats["wording_mix"].get(ctx, {})
        verbatim = mix.get("article-verbatim", 0)
        transcript = mix.get("transcript-derived", 0)
        total = verbatim + transcript
        vw = round(verbatim / total * 100) if total else 0
        tw = 100 - vw
        evidence_bars.append(
            f'<div><b>{label}</b><div><i class="verbatim" style="width:{vw}%" title="Official article: {verbatim}"></i>'
            f'<i class="transcript" style="width:{tw}%" title="Transcript-derived: {transcript}"></i></div><span>{total}</span></div>')
    evidence_bars_html = "".join(evidence_bars)

    return {
        "topics_ol": topics_ol, "context_div": context_div,
        "narrative_ol": narrative_ol, "radar_div": radar_div,
        "established": established, "top_topic": top10[0] if top10 else ("no topic yet", 0),
        "donut_bg": donut_bg, "donut_ol": donut_ol, "top_pct": top_pct,
        "columns_html": columns_html, "evidence_bars_html": evidence_bars_html,
    }


POCHETTINO_FIRST_CONFERENCE = "2026-11-20"   # his first United press conference; nothing earlier counts
SEASON_START = "2026-07-01"                  # the 2026-27 season

# Club-level topics for the "2026-27 season, all managers" section: the
# narrative tags that describe the club rather than one manager's job.
CLUB_LEVEL_TAGS = [
    ("ownership_governance", "Ownership and club governance"),
    ("hierarchy_relationship", "Ownership and hierarchy"),
    ("board_expectations", "Board expectations"),
    ("transfer_strategy", "Transfers and squad planning"),
    ("supporter_relationship", "Supporters and atmosphere"),
    ("officials_decisions", "Officials and decisions"),
]


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def build_hero(stats, frags):
    n = stats["n_conf"]
    total_responses = sum(stats["ctx_counts"].values())
    return (
        '<section class="prw-dashboard-hero">'
        '<div class="prw-dashboard-intro">'
        '<p class="prw-kicker">PRESS ROOM WATCH &middot; COUNTED FROM 20 NOVEMBER 2026</p>'
        f'<h1>Mauricio Pochettino &middot; <em>conferences so far: {n}</em></h1>'
        '<p>Every recovered question from Mauricio Pochettino&rsquo;s Manchester United press conferences, '
        'classified under an approved editorial framework and kept beside its original wording. '
        'His count starts with his first press conference as United head coach, on 20 November 2026.</p>'
        '<p class="prw-thin-note"><b>Early numbers are thin.</b> With so few conferences in the record, '
        'no pattern is established yet, and questions about his appointment are likely to dominate at first.</p>'
        '</div>'
        '<div class="prw-scoreboard" aria-label="Evidence summary">'
        f'<article><span>CONFERENCES</span><strong>{n}</strong><small>{stats["pre_conf"]}<!-- --> pre &middot; <!-- -->{stats["post_conf"]}<!-- --> post</small></article>'
        f'<article><span>QUESTIONS</span><strong>{stats["n_questions"]}</strong><small>exact or source-verbatim</small></article>'
        f'<article><span>RESPONSES</span><strong>{total_responses}</strong><small>preserved records</small></article>'
        f'<article><span>NARRATIVES</span><strong>{len(frags["established"])}</strong><small>established patterns</small></article>'
        '</div></section>')


def build_season_section(all_records):
    """2026-27 season, all managers: club-level topics only."""
    rows = []
    season = [r for r in all_records if r["date"] >= SEASON_START]
    for tag, label in CLUB_LEVEL_TAGS:
        rs = [r for r in season if r["narrative_tag"] == tag]
        by_mgr = Counter(r["manager"] for r in rs)
        confs = {(r["fixture"], r["date"], r["context"]) for r in rs}
        rows.append((label, len(rs), by_mgr, len(confs)))
    rows.sort(key=lambda x: -x[1])
    maxc = max((r[1] for r in rows), default=0) or 1
    li = []
    for i, (label, n, by_mgr, nconf) in enumerate(rows, 1):
        split = " &middot; ".join(f"{esc(m)} {c}" for m, c in sorted(by_mgr.items(), key=lambda kv: (-kv[1], kv[0]))) or "none yet"
        li.append(f'<li><span>{i:02d}</span><div><b>{esc(label)}</b>'
                  f'<small style="display:block;opacity:.7">{split} &middot; {plural(nconf, "conference")}</small>'
                  f'<i><span style="width:{n / maxc * 100}%"></span></i></div><strong>{n}</strong></li>')
    n_conf = len({(r["fixture"], r["date"], r["context"]) for r in season})
    managers = sorted({r["manager"] for r in season})
    return (
        '<section class="prw-season" id="season">'
        '<div class="prw-section-title"><div><p>04 &middot; 2026-27 SEASON</p><h2>The club-level questions.</h2></div>'
        '<p>Only topics about the club rather than one manager&rsquo;s job: ownership and governance, the hierarchy, board expectations, '
        'transfers, supporters and officials. Counted across every manager this season, so the split by manager is shown.</p></div>'
        '<div class="prw-finding-grid"><article class="prw-topic-panel">'
        '<div class="prw-panel-head"><div><b>Club-level topics</b>'
        f'<span>{plural(len(season), "question")} in {plural(n_conf, "conference")} &middot; {esc(" and ".join(managers) if managers else "no manager yet")}</span></div></div>'
        '<ol>' + "".join(li) + '</ol></article></div></section>')


def build_carrick_record(all_records, frags_c, stats_c):
    """Michael Carrick: final record. Frozen totals read from the data."""
    total_responses = sum(stats_c["ctx_counts"].values())
    first, last = stats_c["date_min"], stats_c["date_max"]
    top5 = stats_c["topic_counts"].most_common(5)
    maxc = top5[0][1] if top5 else 1
    li = "".join(f'<li><span>{i:02d}</span><div><b>{esc(t)}</b><i><span style="width:{c / maxc * 100}%"></span></i></div><strong>{c}</strong></li>'
                 for i, (t, c) in enumerate(top5, 1))
    return (
        '<section class="prw-carrick-record" id="carrick-record">'
        '<div class="prw-section-title"><div><p>05 &middot; FINAL RECORD</p><h2>Michael Carrick: final record.</h2></div>'
        '<p>Michael Carrick&rsquo;s tracked press conferences ran from '
        f'{date_disp(first)} to {date_disp(last)}. The club announced his departure, and this record is now closed: these totals will not change.</p></div>'
        '<div class="prw-finding-grid"><article class="prw-topic-panel">'
        '<div class="prw-scoreboard" aria-label="Carrick final record">'
        f'<article><span>CONFERENCES</span><strong>{stats_c["n_conf"]}</strong><small>{stats_c["pre_conf"]}<!-- --> pre &middot; <!-- -->{stats_c["post_conf"]}<!-- --> post</small></article>'
        f'<article><span>QUESTIONS</span><strong>{stats_c["n_questions"]}</strong><small>exact or source-verbatim</small></article>'
        f'<article><span>RESPONSES</span><strong>{total_responses}</strong><small>preserved records</small></article>'
        f'<article><span>NARRATIVES</span><strong>{len(frags_c["established"])}</strong><small>established patterns</small></article>'
        '</div>'
        f'<div class="prw-panel-head"><div><b>Most discussed topics</b><span>First tracked {date_disp(first)} &middot; last tracked {date_disp(last)}</span></div></div>'
        f'<ol>{li}</ol></article></div></section>')


def splice_html(html, stats, frags, all_records=None, carrick=None):
    """Splice the computed fragments into press-room-watch.html. `stats`/`frags`
    describe the live manager (Pochettino); `all_records` feeds the season
    section; `carrick` is (stats, frags) for his final record."""
    def must(html, pattern, repl, label, flags=0):
        # The page's HTML is pretty-printed (indented, one tag per line), so
        # allow any whitespace between adjacent tags in every pattern.
        pattern = pattern.replace("><", r">\s*<")
        new_html, n = re.subn(pattern, lambda _m: repl, html, count=1, flags=flags)
        if n != 1:
            sys.exit(f"FAIL [{label}]: pattern did not match exactly once (matched {n})")
        return new_html

    # hero (kicker, headline, thin-numbers note and scoreboard)
    html = must(html, r'<section class="prw-dashboard-hero">.*?</section>', build_hero(stats, frags),
                "hero", flags=re.S)

    # the hand-written "narrative right now" panel lives in its own file
    now_path = Path(__file__).resolve().parent / "press_room_now.html"
    if now_path.exists():
        html = must(html, r'<section class="prw-now" id="now">.*?</section>', now_path.read_text(encoding="utf-8").strip(),
                    "now-panel", flags=re.S)

    # topics ol
    html = must(html, r'<span>Primary question count</span></div></div><ol>.*?</ol></article><article class="prw-context-panel">',
                '<span>Primary question count</span></div></div>' + frags["topics_ol"] + '</article><article class="prw-context-panel">',
                "topics-ol", flags=re.S)

    # context panel
    html = must(html, r'<div class="prw-context-list">.*?</div><p>These rates show the available source base\.',
                frags["context_div"] + '<p>These rates show the available source base.',
                "context-div", flags=re.S)

    # editorial paragraph: generated, never a claim the numbers can't carry
    top_topic, top_count = frags["top_topic"]
    n_conf = stats["n_conf"]
    if top_count:
        editorial = (f'The most common topic so far is {esc(top_topic).lower()}, with <!-- -->{top_count}<!-- --> of '
                     f'<!-- -->{stats["n_questions"]}<!-- --> questions. With only {plural(n_conf, "conference")} in the record this is an early count, '
                     'not a pattern, and it will move as more press conferences are added.')
    else:
        editorial = 'No questions are in the record yet. This section fills in as press conferences are added.'
    html = must(html, r'<p>[^<]*(?:<!--[^>]*-->[^<]*)*</p>(?=<a href="#narratives">)',
                f'<p>{editorial}</p>', "editorial-paragraph")

    # narrative leaderboard
    html = must(html, r'<span>Conferences</span></div><ol>.*?</ol></div><aside class="prw-watchlist">',
                '<span>Conferences</span></div>' + frags["narrative_ol"] + '</div><aside class="prw-watchlist">',
                "narrative-ol", flags=re.S)

    # on the radar
    html = must(html, r'analytical lenses measure published responses rather than questions\.</p><div>.*?</div></aside></div></section>',
                'analytical lenses measure published responses rather than questions.</p>' + frags["radar_div"] + '</aside></div></section>',
                "radar-div", flags=re.S)

    # visual analysis: donut + caption
    if top_count:
        donut_caption = (f'<p><strong>{esc(top_topic)} accounts for {frags["top_pct"]}% so far.</strong> '
                         'Counts this small move quickly; read the shape, not the exact figures.</p>')
    else:
        donut_caption = '<p>No questions yet.</p>'
    html = must(html, r'<div class="prw-donut-layout">.*?</div><p>.*?</p></article>',
                '<div class="prw-donut-layout"><div class="prw-donut" style="background:'
                + frags["donut_bg"] + f'"><div><strong>{stats["n_questions"]}</strong><span>questions</span></div></div>'
                + frags["donut_ol"] + '</div>' + donut_caption + '</article>',
                "visuals-donut", flags=re.S)

    # visual analysis: context comparison columns (caption generated)
    html = must(html, r'<div class="prw-columns">.*?</div>\s*<p>[^<]*</p>',
                '<div class="prw-columns">' + frags["columns_html"] + '</div><p>Early counts: with '
                + plural(n_conf, "conference") + ' in the record, per-conference rates are not yet comparable across match contexts, '
                'and incomplete or answer-only sources prevent a claim about total room length.</p>',
                "visuals-columns", flags=re.S)

    # visual analysis: evidence mix bars (caption generated)
    mix = Counter()
    for v in stats["wording_mix"].values():
        mix.update(v)
    verbatim, transcript = mix.get("article-verbatim", 0), mix.get("transcript-derived", 0)
    html = must(html, r'<div class="prw-style-bars">.*?</div>\s*<p>[^<]*(?:&[a-z]+;[^<]*)*</p>',
                '<div class="prw-style-bars">' + frags["evidence_bars_html"] + '</div>'
                f'<p>{verbatim} of {verbatim + transcript} recovered questions use the club&rsquo;s own published wording. '
                f'{transcript} are transcript-derived: auto-caption text checked as far as the source permits, never presented as club-verbatim.</p>',
                "visuals-evidence-bars", flags=re.S)

    if all_records is not None:
        html = must(html, r'<section class="prw-season" id="season">.*?</section>', build_season_section(all_records),
                    "season", flags=re.S)
    if carrick is not None:
        html = must(html, r'<section class="prw-carrick-record" id="carrick-record">.*?</section>',
                    build_carrick_record(all_records, carrick[1], carrick[0]), "carrick-record", flags=re.S)
    return html


def split_by_manager(records):
    """(pochettino_records, carrick_records)"""
    p = [r for r in records if r["manager"] == MANAGER_POCHETTINO]
    c = [r for r in records if r["manager"] == MANAGER_CARRICK]
    return p, c


def compute_all(records):
    """Everything the page and the Pages build need, in one place."""
    p_recs, c_recs = split_by_manager(records)
    p_stats = compute_stats(p_recs, MANAGER_POCHETTINO)
    c_stats = compute_stats(c_recs, MANAGER_CARRICK)
    return {"records": records,
            "p": (p_stats, build_fragments(p_stats)),
            "c": (c_stats, build_fragments(c_stats))}


def main():
    records = normalize(load_questions())
    write_data_js(records)
    a = compute_all(records)
    html = HTML_PATH.read_text(encoding="utf-8")
    html = splice_html(html, a["p"][0], a["p"][1], all_records=records, carrick=a["c"])
    HTML_PATH.write_text(html, encoding="utf-8")
    ps, pf = a["p"]
    cs, cf = a["c"]
    print(f"Rebuilt: Pochettino {ps['n_questions']} questions in {ps['n_conf']} conferences; "
          f"Carrick final record {cs['n_questions']} questions in {cs['n_conf']} conferences "
          f"({cs['date_min']} -> {cs['date_max']}).")


if __name__ == "__main__":
    main()
