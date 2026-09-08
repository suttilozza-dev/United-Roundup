#!/usr/bin/env python3
"""
Classifies raw items (from fetch_sources.py) into the site's categories.

Two modes:
  --dry-run   Uses simple keyword rules. Free, instant, no API key needed.
              Good enough to prove the pipeline's plumbing works end to end,
              but not as accurate as the real thing.
  (default)   Calls the Claude API (Haiku 4.5 -- cheap, fast, plenty
              capable for a tagging task like this). Needs ANTHROPIC_API_KEY
              set as an environment variable.

Categories match the tabs already built into latest.html:
  transfers, team, academy, interviews, club, videos
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
CATEGORIES = ["transfers", "team", "academy", "interviews", "club", "videos"]

SYSTEM_PROMPT = """You classify Manchester United news items for United Roundup, a fan news site.

Given a headline and short text, respond with ONLY the raw JSON object itself,
nothing else -- no markdown code fences, no ```json wrapper, no explanation
before or after. Just the object, like this:
{"category": "transfers", "confidence": "high"}

Categories, in priority order when more than one could apply:
- transfers: signings, sales, loans, contract talks, transfer rumours
- team: injuries, fitness updates, squad news, team news ahead of a match
- academy: youth teams, U21/U18, academy graduates, women's team
- interviews: press conferences, one-on-one interviews, podcast appearances
- club: official club statements, ownership, finances, non-match club news
- videos: use only if the item is a video AND doesn't fit another category better

Respond with confidence "low" if you are genuinely unsure -- do not guess
confidently. This output is reviewed, not published blind."""


def classify_dry_run(item: dict) -> dict:
    """Free, offline, rule-based classification -- for testing the pipeline only."""
    text = item.get("raw_text", "").lower()
    rules = [
        ("transfers", ["transfer", "signing", "loan", "£", "fee", "bid", "deal"]),
        ("team", ["injury", "injured", "fitness", "out for", "return to training", "sidelined"]),
        ("academy", ["academy", "u21", "u18", "youth", "women's"]),
        ("interviews", ["press conference", "interview", "carrick said", "asked about"]),
        ("club", ["statement", "ownership", "club has", "announced"]),
    ]
    for category, keywords in rules:
        if any(k in text for k in keywords):
            return {"category": category, "confidence": "low (dry-run rule match)"}
    if item.get("type") == "video":
        return {"category": "videos", "confidence": "low (dry-run fallback)"}
    return {"category": "club", "confidence": "low (dry-run fallback)"}


def classify_with_api(item: dict, client, usage_totals: dict) -> dict:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Title: {item['title']}\n\nText: {item.get('raw_text', '')[:500]}",
        }],
    )
    usage_totals["input_tokens"] += message.usage.input_tokens
    usage_totals["output_tokens"] += message.usage.output_tokens
    raw = message.content[0].text.strip()
    # Models sometimes wrap JSON in a markdown code fence even when told not to.
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"category": "club", "confidence": f"low (unparseable model output: {raw[:80]!r})"}
    if result.get("category") not in CATEGORIES:
        result["category"] = "club"
    return result


def main():
    import time
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Use free rule-based classification, no API calls")
    parser.add_argument("--time-budget", type=float, default=150.0,
                         help="Stop after this many seconds and checkpoint (real API mode only)")
    args = parser.parse_args()

    items_path = HERE / "raw_items.json"
    if not items_path.exists():
        print("raw_items.json not found -- run fetch_sources.py first (or use sample data).")
        sys.exit(1)

    items = json.loads(items_path.read_text())
    checkpoint_path = HERE / "classify_checkpoint2.json"

    classified = []
    usage_totals = {"input_tokens": 0, "output_tokens": 0}
    start_index = 0

    if not args.dry_run and checkpoint_path.exists():
        ckpt = json.loads(checkpoint_path.read_text())
        classified = ckpt["classified"]
        usage_totals = ckpt["usage_totals"]
        start_index = len(classified)
        print(f"Resuming from checkpoint: {start_index}/{len(items)} already done.")

    client = None
    if not args.dry_run:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("No ANTHROPIC_API_KEY set. Add --dry-run to test without one.")
            sys.exit(1)
        import anthropic  # imported here so --dry-run never needs this installed
        client = anthropic.Anthropic(api_key=api_key)

    start_time = time.monotonic()
    stopped_early = False
    for idx in range(start_index, len(items)):
        if not args.dry_run and (time.monotonic() - start_time) > args.time_budget:
            stopped_early = True
            break
        item = items[idx]
        result = classify_dry_run(item) if args.dry_run else classify_with_api(item, client, usage_totals)
        item["category"] = result["category"]
        item["classification_confidence"] = result["confidence"]
        classified.append(item)
        print(f"  [{result['category']:<10}] {item['title'][:70]}")

        if not args.dry_run:
            checkpoint_path.write_text(json.dumps(
                {"classified": classified, "usage_totals": usage_totals}, ensure_ascii=False
            ))

    if stopped_early:
        print(f"\nTime budget reached -- {len(classified)}/{len(items)} done, checkpoint saved. "
              f"Re-run the same command to continue.")
        return

    out_path = HERE / "classified_items.json"
    out_path.write_text(json.dumps(classified, indent=2, ensure_ascii=False))
    print(f"\nClassified {len(classified)} items -> {out_path}")

    if not args.dry_run:
        in_tok = usage_totals["input_tokens"]
        out_tok = usage_totals["output_tokens"]
        cost = (in_tok / 1_000_000 * 1.0) + (out_tok / 1_000_000 * 5.0)
        print(f"\n--- USAGE (real API run) ---")
        print(f"Input tokens:  {in_tok}")
        print(f"Output tokens: {out_tok}")
        print(f"Estimated cost (Haiku 4.5 @ $1/$5 per MTok): ${cost:.4f}")
        (HERE / "classify_usage_totals.json").write_text(json.dumps(usage_totals))


if __name__ == "__main__":
    main()
