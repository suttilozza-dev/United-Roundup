# United Roundup — site files

This is a plain HTML/CSS/JS website. No build tools, no framework, no
server required — every page is a real file you can open directly.

## What's here

- `index.html` — homepage (rebuilt from your saved ChatGPT Sites capture,
  same design, colours, logo and layout)
- `press-room-watch.html` — live-built from your real `source-register.json`
  data: all 40 tracked Michael Carrick press conferences
- `about.html`, `sources.html`, `contact.html`, `briefings.html`,
  `editorial.html`, `privacy.html`, `terms.html` — placeholder pages so
  the nav/footer links don't break. Replace with real content whenever
  you're ready.
- `assets/style.css` — the original site's compiled stylesheet (colours,
  fonts, layout — untouched, so the look matches exactly)
- `assets/extra.css` — new styles added for the Press Room cards, using
  the same colour variables as the rest of the site
- `assets/main.js` — a small script for the mobile menu button
- `assets/img/` — all images and the logo

## Try it locally

Just open `index.html` in a browser — no setup needed. To click through
links properly (not just double-clicking the file), run a tiny local
server from this folder:

```
python3 -m http.server 8000
```

then visit `http://localhost:8000` in your browser.

## Not included yet

- The "Latest", "Briefing", "Academy", "Watch" and "Community" sections
  are still just anchor links on the homepage (as they were in the
  original) — not separate pages with real content.
- No live feed / auto-updating data. Anything dynamic will need to be
  added as a proper next step (Claude can help scope this once the
  static site is live).
- The `#top`/anchor links inside the homepage sections will need real
  content to link to as those sections are built out.

## Next steps

1. Push this folder to a new GitHub repo
2. Connect the repo to Netlify (free tier)
3. Point `unitedroundup.co.uk` at Netlify via DNS at your registrar
4. Come back here any time to add daily articles or new pages
