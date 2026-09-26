# Press Room Watch — daily check playbook

This is the procedure the daily "Press Room Watch check" scheduled task follows.
It finds new Michael Carrick press conferences, drafts them into the data, and
asks Laurie to review before anything goes live. **Accuracy matters more than
speed:** every question and answer on Press Room Watch is quoted exactly from
the club's own published coverage. Never invent, paraphrase, tidy or guess.

Repo on Laurie's computer: `C:\Users\GGPC\Downloads\united-roundup-site\site`
(in device_bash: `$HOME/mnt/Downloads/united-roundup-site/site`).

## Hard rules
- **Never `git push`.** Commit locally only. Laurie approves by pushing in GitHub Desktop.
- **Never edit `press-room-watch.html`** and never run `rebuild_press_room.py` on the repo
  (it rewrites the HTML, which would cost a Netlify deploy). Only
  `automation/add_press_conference.py` changes the data.
- Only use text you have actually read on manutd.com in this run. If a page won't load
  or the Q&A can't be read clearly, skip that conference and say so in the summary.
- Question and answer wording must be copied **exactly** as published, including
  punctuation, curly quotes, square-bracket insertions and spelling.
- If anything is uncertain (section, tag, framing, which conference an article belongs
  to), make your best choice and **flag it** in the review page.
- If the repo has uncommitted changes to the three data files, or a git lock file,
  stop and report it rather than working around it.

## Step 1 — What's already in
Read `automation/press_room_conferences.json`. Note the latest `date` and every
`fixture|date|context` already present (including drafts committed but not yet pushed).

## Step 2 — Find candidate articles (cloud shell is fine for this)
The club's sitemaps are readable from anywhere:
`https://www.manutd.com/sitemaps/sitemap/0.xml` (also `1.xml`, `2.xml`).
List `/en/news/` URLs whose `<lastmod>` is after the latest registry date minus 2 days,
and whose slug suggests Carrick press-conference coverage, e.g. contains `carrick`,
`press-conference`, `told-reporters`, `every-word`, `everything-`…`-said`,
`what-carrick`, `carrick-says`, `carrick-on`. Ignore programme notes, team
line-ups, "how many changes" previews and podcast/video-only pages.

## Step 3 — Read them in the browser
manutd.com blocks servers, so read each candidate with the **built-in browser on
Laurie's computer** (`Claude_Browser__preview_start` then `Claude_Browser__get_page_text`
with a large `max_chars`). manutd.com is already allowed for the browser.
Keep only articles that publish press-conference questions with Carrick's answers
(question lines followed by quoted answers). Close tabs when done.

Work out which press conference each article belongs to:
- **fixture**: the opponent, spelt exactly as already used, e.g. `Arsenal`, `Aston Villa`,
  `Bournemouth`, `Brentford`, `Brighton and Hove Albion`, `Chelsea`, `Crystal Palace`,
  `Everton`, `Fulham`, `Hull City`, `Ipswich Town`, `Leeds United`, `Liverpool`,
  `Manchester City`, `Newcastle United`, `Nottingham Forest`, `Sabah FK`, `Sunderland`,
  `Tottenham Hotspur`, `West Ham United`. New opponents: full club name
  (e.g. `Atlético Madrid`, `Como`).
- **date**: the day the press conference took place (post-match = match day), `YYYY-MM-DD`.
- **context**: `pre_match` or `post_match`.
- **result**: `not_applicable` for pre-match; `win` / `draw` / `loss` (United's result) for post-match.
- Skip any conference already in the registry.
- A pre-match presser is often published in two parts: wait until you think both are out.
  If only the early part is out and the match is still 2+ days away, leave it for
  tomorrow's run. Otherwise draft what exists and flag that part may be missing.

## Step 4 — Draft each conference as JSON
One file per conference, in the format documented at the top of
`automation/add_press_conference.py`. For each question:
- **section**: `early` = the club's same-day early release; `embargoed` = the club's later
  (embargoed) release of the rest of the presser; `post` = post-match; `combined` = one
  article with the whole presser; `combined_partial` = one article with an unclear or
  partial selection. Match the most similar existing conference when unsure, and flag it.
- **question** / **response**: exact published wording. If one question has several
  answer paragraphs, join them with a single space. If no answer is published, use "".
- **topic** + **narrative_tag**: use one of these approved pairs (the script refuses others):
  Performance and standards → performance_standards · Fitness and availability →
  fitness_availability · Manager future → carrick_future · Opposition and match plan →
  opposition_match_plan · Tactics and selection → tactics_selection · Targets and Europe →
  champions_league_target · Targets and expectations → champions_league_target /
  board_expectations / pressure_mentality · Pressure and mentality → pressure_mentality ·
  Supporters and atmosphere → supporter_relationship · Transfers and squad planning →
  transfer_strategy · Leadership → leadership · Academy and development → academy_pathway ·
  Officials and decisions → officials_decisions · Ownership and club governance →
  ownership_governance · Ownership and hierarchy → hierarchy_relationship · External
  pressure → ex_player_commentary_pressure · Appointment and role → carrick_appointment.
  Most questions are Performance and standards; use a specific topic when the question
  is clearly about it.
- **framing**: `neutral` (plain question), `critical` (challenges Carrick/the team or implies
  failure), `premise-led` (builds in an assumption or outside claim, e.g. a pundit's view),
  `follow-up` (continues the previous question), `positive` (praises or invites a positive answer).
- **wording_status**: `article-verbatim` (always, for manutd.com text).
- **source_url**: the article's full URL.
- **response_count**: the number of quoted answer paragraphs across that conference's
  article(s), including answers not tied to a printed question.

## Step 5 — Add and check
In device_bash, from the repo root:
```
python3 automation/add_press_conference.py /path/to/draft.json
python3 automation/build_press_room_pages.py $HOME/prw-check
```
Both must succeed. If `add_press_conference.py` refuses something, fix the draft
(don't bypass it).

## Step 6 — Commit locally (never push)
```
git -c core.autocrlf=true add assets/press-room-data.js automation/press_room_conferences.json automation/press_room_response_counts.json
git commit -m "Press Room Watch: add <Fixture> <pre-match|post-match> (<date>) - awaiting review"
```

## Step 7 — Review page and summary
Publish (or update) a private artifact titled **"Press Room Watch review"** with, for each
new conference: fixture, date, context, result, section(s), source links, response count,
and a table of every question → answer (shortened is fine on the page), topic, tag and
framing, with anything flagged highlighted at the top. Say at the top:
- **To approve:** open GitHub Desktop and click **Push origin**. The live page updates
  within about 5 minutes, with no Netlify deploy.
- **To change or reject:** tell Claude in the United Roundup chat what's wrong.

End the run with a short summary: which conferences were drafted (or "No new press
conferences today"), anything flagged, and the review page link.
