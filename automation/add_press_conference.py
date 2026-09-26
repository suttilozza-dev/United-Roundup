#!/usr/bin/env python3
"""
Adds ONE press conference to Press Room Watch's source data, safely.

Input is a JSON file:
{
  "conference": {"fixture": "Tottenham Hotspur", "date": "2026-10-09",
                 "context": "pre_match", "result": "not_applicable"},
  "response_count": 18,
  "questions": [
    {"section": "early", "question": "...", "response": "...",
     "topic": "Fitness and availability", "narrative_tag": "fitness_availability",
     "framing": "neutral", "wording_status": "article-verbatim",
     "source_url": "https://www.manutd.com/en/news/..."}
  ]
}

It checks every field against the approved taxonomy (the topic/tag pairs and
framings already used on the page), refuses duplicates, then updates:
  assets/press-room-data.js, automation/press_room_conferences.json,
  automation/press_room_response_counts.json
It does NOT touch press-room-watch.html (so no Netlify deploy is needed);
the live page's tallies are rebuilt on GitHub Pages after the data is pushed.

Usage (from the repo root):  python3 automation/add_press_conference.py draft.json

To add questions to a conference that is ALREADY in the data (e.g. a question
Laurie approved from the cross-check, or the second part of a pre-match presser):
    python3 automation/add_press_conference.py --add-to-existing draft.json
Here "response_count" is the number of EXTRA answer paragraphs being added,
and "conference" must match the existing entry exactly (including result).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rebuild_press_room as prw  # noqa: E402

TOPIC_TAGS = {
    "Performance and standards": ["performance_standards"],
    "Fitness and availability": ["fitness_availability"],
    "Manager future": ["carrick_future"],
    "Opposition and match plan": ["opposition_match_plan"],
    "Tactics and selection": ["tactics_selection"],
    "Targets and Europe": ["champions_league_target"],
    "Targets and expectations": ["champions_league_target", "board_expectations", "pressure_mentality"],
    "Pressure and mentality": ["pressure_mentality"],
    "Supporters and atmosphere": ["supporter_relationship"],
    "Transfers and squad planning": ["transfer_strategy"],
    "Leadership": ["leadership"],
    "Academy and development": ["academy_pathway"],
    "Officials and decisions": ["officials_decisions"],
    "Ownership and club governance": ["ownership_governance"],
    "Ownership and hierarchy": ["hierarchy_relationship"],
    "External pressure": ["ex_player_commentary_pressure"],
    "Appointment and role": ["carrick_appointment"],
}
FRAMINGS = {"neutral", "critical", "premise-led", "follow-up", "positive"}
SECTIONS = {"early", "embargoed", "post", "combined", "combined_partial"}
WORDING = {"article-verbatim", "transcript-derived"}
RESULTS = {"pre_match": {"not_applicable"}, "post_match": {"win", "draw", "loss"}}


def fail(msg):
    sys.exit("REFUSED: " + msg)


def main():
    args = sys.argv[1:]
    add_to_existing = "--add-to-existing" in args
    args = [a for a in args if a != "--add-to-existing"]
    if len(args) != 1:
        fail("usage: add_press_conference.py [--add-to-existing] draft.json")
    draft = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    conf = draft.get("conference") or fail("missing 'conference'")
    for k in ("fixture", "date", "context", "result"):
        if not conf.get(k):
            fail(f"conference is missing '{k}'")
    if conf["context"] not in RESULTS:
        fail(f"context must be pre_match or post_match, not {conf['context']!r}")
    if conf["result"] not in RESULTS[conf["context"]]:
        fail(f"result {conf['result']!r} is not valid for {conf['context']}")
    prw.date_disp(conf["date"])  # raises if the date isn't YYYY-MM-DD

    registry = json.loads(prw.CONF_REGISTRY_PATH.read_text(encoding="utf-8"))
    match = [c for c in registry
             if (c["fixture"], c["date"], c["context"]) == (conf["fixture"], conf["date"], conf["context"])]
    if add_to_existing:
        if not match:
            fail(f"{conf['fixture']} {conf['date']} {conf['context']} isn't in Press Room Watch yet "
                 "(run without --add-to-existing to add it as a new conference)")
        if match[0]["result"] != conf["result"]:
            fail(f"result {conf['result']!r} doesn't match the existing entry ({match[0]['result']!r})")
    elif match:
        fail(f"{conf['fixture']} {conf['date']} {conf['context']} is already in Press Room Watch "
             "(use --add-to-existing to add questions to it)")

    count = draft.get("response_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        fail("response_count must be a whole number (count every quoted answer paragraph)")

    questions = draft.get("questions") or []
    existing = prw.load_questions()
    seen = {(q["question"].strip(), q["date"]) for q in existing}
    new = []
    for i, q in enumerate(questions, 1):
        for k in ("section", "question", "topic", "narrative_tag", "framing", "wording_status", "source_url"):
            if not q.get(k):
                fail(f"question {i} is missing '{k}'")
        if q["topic"] not in TOPIC_TAGS:
            fail(f"question {i}: unknown topic {q['topic']!r}")
        if q["narrative_tag"] not in TOPIC_TAGS[q["topic"]]:
            fail(f"question {i}: tag {q['narrative_tag']!r} doesn't belong to topic {q['topic']!r}")
        if q["framing"] not in FRAMINGS:
            fail(f"question {i}: unknown framing {q['framing']!r}")
        if q["section"] not in SECTIONS:
            fail(f"question {i}: unknown section {q['section']!r}")
        if q["wording_status"] not in WORDING:
            fail(f"question {i}: unknown wording_status {q['wording_status']!r}")
        if not q["source_url"].startswith("https://"):
            fail(f"question {i}: source_url must be a full https link")
        if (q["question"].strip(), conf["date"]) in seen:
            fail(f"question {i} is already in the data: {q['question'][:60]!r}")
        rec = {"fixture": conf["fixture"], "date": conf["date"], "context": conf["context"],
               "result": conf["result"], "section": q["section"], "question": q["question"].strip(),
               "topic": q["topic"], "framing": q["framing"], "narrative_tag": q["narrative_tag"],
               "wording_status": q["wording_status"], "source_url": q["source_url"],
               "response": (q.get("response") or "").strip()}
        new.append(rec)

    records = prw.normalize(existing + new)
    prw.write_data_js(records)

    if not add_to_existing:
        registry.append({"fixture": conf["fixture"], "date": conf["date"],
                         "context": conf["context"], "result": conf["result"]})
        registry.sort(key=lambda c: (c["date"], c["context"] != "pre_match"))
        prw.CONF_REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    counts = json.loads(prw.RESP_COUNTS_PATH.read_text(encoding="utf-8"))
    key = f"{conf['fixture']}|{conf['date']}|{conf['context']}"
    if add_to_existing:
        count = counts.get(key, 0) + count
    counts[key] = count
    prw.RESP_COUNTS_PATH.write_text(json.dumps(counts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    verb = "Added to" if add_to_existing else "Added"
    print(f"{verb} {conf['fixture']} {conf['context']} ({conf['date']}): {len(new)} questions, "
          f"{count} response paragraphs in total. Press Room Watch now has {len(records)} questions.")


if __name__ == "__main__":
    main()
