# United Roundup — source tracking automation

This is the pipeline that checks your sources for new content, sorts it
into categories, and updates the Latest page automatically.

## What's proven to work right now

- `classify.py --dry-run` — tested against 6 realistic sample headlines,
  all 6 correctly sorted into transfers/team/academy/interviews/club/videos
- `update_site_data.py` — tested, correctly writes `site/assets/latest-data.js`
  in the exact format `latest.html` expects
- `latest.html` — the actual page, with working filter tabs, already live

## What still needs real-world testing

- `fetch_sources.py` and `validate_sources.py` — written correctly, but
  never actually run against the internet (this environment couldn't
  reach it). **Run `validate_sources.py` first, on your own machine or
  via Cowork, before trusting any of the URLs in `sources.json`.**
- The real (non-dry-run) classification — the logic is the same as the
  dry-run version proved, but it hasn't made a real API call yet.

## Recommended order to test this yourself

```bash
cd automation
python3 validate_sources.py       # check which sources actually work
python3 fetch_sources.py          # pull real current headlines
python3 classify.py --dry-run     # classify them for free, check the results look sane
python3 update_site_data.py       # write them into the site
```

Open `site/latest.html` locally afterwards and check the results look
right. Only once you're happy with that should you consider setting up
`ANTHROPIC_API_KEY` and running `classify.py` for real (no `--dry-run`),
which is the only step that costs anything.

## Files

- `sources.json` — the source list. **The RSS URLs and YouTube channel
  IDs in here are a starting point, not verified.** Fix anything
  `validate_sources.py` flags as failing.
- `fetch_sources.py` — pulls new items from every source
- `validate_sources.py` — checks sources actually work, before you trust them
- `classify.py` — sorts items into categories (dry-run or real API)
- `update_site_data.py` — writes results into the site's data file
- `.github-workflow-source-tracking.yml` — move this into
  `.github/workflows/source-tracking.yml` once you're ready to automate
  on a schedule
