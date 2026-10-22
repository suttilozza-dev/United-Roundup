---
description: Read the "Press Room Watch review" artifact, copy the club's Q&A exactly, and add new conferences to the data (local commit only, never pushes)
argument-hint: [optional: name any "possibly missing" items to add]
---

Add new Carrick press conferences to Press Room Watch. Read `automation/PRESS_ROOM_PLAYBOOK.md` for the field rules and `automation/add_press_conference.py` for the JSON schema and the approved topic to narrative_tag pairs.

Hard rules: **never `git push`**; never edit `press-room-watch.html`; never run `rebuild_press_room.py`; only `automation/add_press_conference.py` changes the data. Never log in to anything. Never paraphrase, tidy, reorder or fill gaps in the club's wording. Do not enable or change any hook.

Arguments from Laurie: `$ARGUMENTS`

## Steps

**0. Check the repo is clean.** Run `git status --short`. If `automation/press_room_*.json` or `assets/press-room-data.js` have uncommitted changes, or there is a git lock file, stop and tell Laurie.

**a) Read the review and list what is on it.** Use the Artifact tool (`action: "list"`, then `"read"`) to open the artifact titled **"Press Room Watch review"** (most recently updated if there are several; say which you used). If you cannot find or read it, ask Laurie to paste its text and stop. List every conference on it (fixture, date, pre/post-match, whether it has proposed JSON). Read `automation/press_room_conferences.json` and skip any conference whose `fixture` + `date` + `context` is already there; say which you skipped.

**b) Read the club's articles.** For each remaining conference that has no proposed JSON (the page says "Club wording not read in the cloud"), open each manutd.com article link in a real browser and read the article text:
- Use the Claude in Chrome extension if it is connected.
- Otherwise use Playwright with the installed Chromium, headless (`PLAYWRIGHT_BROWSERS_PATH` is already set; do not run `playwright install`). Write any script outside the repo.
- Read-only: never log in, and never click anything except to dismiss a cookie banner.
- Copy each question and answer **exactly** as published: punctuation, curly quotes, square brackets, spelling. If one question has several answer paragraphs, join them with a single space. If no answer is published, use `""`.
- If you cannot read an article, **stop for that conference**, tell Laurie which one and why, and do not guess. Carry on with the others.

**c) Build the JSON and ask for the OK.** Build one JSON per conference in the format `add_press_conference.py` accepts (conference object, `response_count`, `questions`). Use only the approved topic/narrative_tag pairs from the script. `framing` is one of `neutral`, `critical`, `premise-led`, `follow-up`, `positive`. `wording_status` is `article-verbatim` for manutd.com text. Then show Laurie a table, one line per question: **question | topic | framing**, with the fixture, date, context and result above it, and flag anything uncertain (section, tag, framing, a part of a pre-match presser that may be missing). **Stop and wait for Laurie's OK before saving anything.**

**d) After the OK.** For each conference:
1. Save the JSON to a temp file outside the repo (`mktemp -d`).
2. Run `python3 automation/add_press_conference.py <that file>` from the repo root. If the script refuses, do not work around it: report the error and move on.
3. Run `python3 automation/build_press_room_pages.py public` to check the build. It writes a `public/` folder in the repo: delete it afterwards (unless it was already there before you started) and never stage it. If the build fails, report the error and do not commit.
4. Commit locally, staging only `automation/press_room_conferences.json`, `automation/press_room_response_counts.json` and `assets/press-room-data.js`, with the message:
   `Press Room Watch: add <fixture> <pre/post-match> (<date>) - awaiting review`
   End the message with the usual attribution lines. **Never push.**

**e) "Possibly missing" items.** Add one only if Laurie named it in `$ARGUMENTS`, and only with a reputable outlet's **direct quote** as the wording (named outlet, linked). Add it with `--add-to-existing`, `wording_status: "transcript-derived"` and that outlet's URL as `source_url`, and mark it as such in the table in step c. A paraphrase, an auto-caption or an unnamed source is not enough: say so and leave it out. Never add an item Laurie did not name.

**f) Finish.** List what was added (fixture, date, context, question count), what was skipped and why, anything uncertain, and end with the line:

YOUR MOVE: check the preview, then push in GitHub Desktop.
