#!/usr/bin/env python3
"""
Pre-publish check for United Roundup. Prints a plain-English list of problems
and exits 1 if there are any (exit 0 if clean).

Usage (from the repo root):
    python3 automation/pre_publish_check.py              # files staged for the next commit
    python3 automation/pre_publish_check.py FILE [FILE]  # specific files
    python3 automation/pre_publish_check.py --all        # every file in the repo (audit)
    python3 automation/pre_publish_check.py --hook       # read a Claude Code hook payload on stdin;
                                                         # only runs for "git commit" commands, and
                                                         # checks the whole working tree

FAILS on:
  1. any image over 200KB in a new or changed file
  2. a new article page that is missing from sitemap.xml
  3. the words "United Road" (not "United Roundup") in any checked file
  4. any checked file whose name contains "crest" or "manutd"
  5. a NEW article without byline "Laurie Sutcliffe", a date, an SEO title under
     60 characters, a meta description under 155 characters, or an Open Graph image
     (existing articles that are only being edited get these as warnings, not failures)
  6. any page that loads analytics (gtag / googletagmanager) outside the consent
     script, or a consent script that loads it without checking consent
  7. privacy.html not mentioning a tracker that is installed (checked site-wide, always)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}
TEXT_EXT = {".html", ".css", ".js", ".json", ".xml", ".md", ".txt", ".toml", ".py", ".yml", ".yaml"}
ARTICLE_RE = re.compile(r"^(briefings|whos-saying-what|the-big-story)/[^/]+/index\.html$")
MAX_IMAGE_BYTES = 200 * 1024
SELF = "automation/pre_publish_check.py"
BAD_PHRASE = "United " + "Road"  # built in two parts so this file never matches itself

# tracker -> (regex that shows it is installed, words privacy.html must contain one of)
TRACKERS = {
    "Google Analytics": (r"googletagmanager\.com|gtag\(", ["Google Analytics", "GA4"]),
    "X embeds": (r"platform\.(x|twitter)\.com/widgets\.js", ["X (formerly Twitter)", "embeds", "X’s", "X&rsquo;s"]),
    "Kit sign-up": (r"kit\.com|convertkit", ["Kit"]),
    "Meta/Facebook pixel": (r"connect\.facebook\.net|fbq\(", ["Facebook", "Meta"]),
    "Hotjar": (r"hotjar\.com", ["Hotjar"]),
    "Microsoft Clarity": (r"clarity\.ms", ["Clarity"]),
}

fails, warns = [], []


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def in_head(rel):
    return subprocess.run(["git", "cat-file", "-e", f"HEAD:{rel}"], cwd=ROOT,
                          capture_output=True).returncode == 0


def read(rel):
    try:
        return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def check_image(rel):
    size = (ROOT / rel).stat().st_size
    if size > MAX_IMAGE_BYTES:
        fails.append(f"Image too big: {rel} is {size // 1024}KB (limit 200KB). Compress it to WebP.")


def check_banned(rel, text):
    if rel != SELF and BAD_PHRASE.lower() in text.lower():
        fails.append(f"Wrong name: {rel} contains \"{BAD_PHRASE}\". The site is United Roundup.")


def check_filename(rel):
    low = Path(rel).name.lower()
    for bad in ("crest", "manutd"):
        if bad in low:
            fails.append(f"File name not allowed: {rel} contains \"{bad}\" "
                         "(no club crest or official branding).")


def check_article(rel, text, is_new):
    out = fails if is_new else warns
    tag = "" if is_new else " (existing article, not blocking)"
    sitemap = read("sitemap.xml")
    url = "https://unitedroundup.com/" + rel[: -len("index.html")]
    if is_new and url not in sitemap:
        fails.append(f"Sitemap: new article {rel} is not in sitemap.xml (expected {url}).")
    if "Laurie Sutcliffe" not in text:
        out.append(f"Byline: {rel} does not name Laurie Sutcliffe{tag}.")
    if not (re.search(r'"datePublished"\s*:\s*"\d{4}-\d{2}-\d{2}', text) or "<time" in text):
        out.append(f"Date: {rel} has no publish date{tag}.")
    m = re.search(r"<title>(.*?)</title>", text, re.S)
    if not m:
        out.append(f"SEO title: {rel} has no <title>{tag}.")
    elif len(m.group(1).strip()) >= 60:
        out.append(f"SEO title: {rel} is {len(m.group(1).strip())} characters (needs under 60){tag}.")
    m = re.search(r'<meta name="description" content="(.*?)">', text, re.S)
    if not m:
        out.append(f"Meta description: {rel} has none{tag}.")
    elif len(m.group(1)) >= 155:
        out.append(f"Meta description: {rel} is {len(m.group(1))} characters (needs under 155){tag}.")
    if not re.search(r'<meta property="og:image" content="https?://[^"]+"', text):
        out.append(f"Open Graph: {rel} has no og:image{tag}.")


def check_analytics(rel, text):
    if not re.search(r"googletagmanager|gtag\(", text):
        return
    if rel.endswith(".html"):
        fails.append(f"Analytics: {rel} loads gtag/googletagmanager directly. "
                     "It may only load from assets/cookie-consent.js after the visitor accepts.")
    elif rel.endswith(".js"):
        if "getConsent" not in text or '"accepted"' not in text:
            fails.append(f"Analytics: {rel} loads gtag/googletagmanager without checking cookie consent.")


def check_privacy():
    priv = read("privacy.html")
    if not priv:
        fails.append("privacy.html is missing.")
        return
    files = [p for p in ROOT.rglob("*") if p.suffix in {".html", ".js"} and p.is_file()
             and not any(part in {".git", "automation", "node_modules"} for part in p.parts)
             and p.name != "latest-data.js"]
    blob = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in files if p.name != "privacy.html")
    for name, (pattern, words) in TRACKERS.items():
        if re.search(pattern, blob) and not any(w in priv for w in words):
            fails.append(f"Privacy: {name} is installed but privacy.html does not mention it.")


def hook_wants_run():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return False
    cmd = (payload.get("tool_input") or {}).get("command", "")
    return bool(re.search(r"(^|[;&|]\s*|\s)git\s+(-\S+\s+)*commit\b", cmd))


def main():
    args = sys.argv[1:]
    hook = "--hook" in args
    if hook:
        if not hook_wants_run():
            return 0
        args = []
    if "--all" in args:
        files = [p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
                 if p.is_file() and ".git" not in p.parts]
    elif args:
        files = [str(Path(a).resolve().relative_to(ROOT)) if Path(a).is_absolute() else a for a in args]
    elif hook:
        # "git add -A && git commit" runs before anything is staged, so look at every
        # change in the working tree, not just the index.
        files = sorted({f for f in git("diff", "HEAD", "--name-only", "--diff-filter=ACMR").split("\n")
                        + git("ls-files", "--others", "--exclude-standard").split("\n") if f})
    else:
        files = [f for f in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").split("\n") if f]

    for rel in files:
        path = ROOT / rel
        if not path.is_file():
            continue
        check_filename(rel)
        ext = path.suffix.lower()
        if ext in IMAGE_EXT:
            check_image(rel)
        if ext in TEXT_EXT:
            text = read(rel)
            check_banned(rel, text)
            check_analytics(rel, text)
            if ARTICLE_RE.match(rel):
                check_article(rel, text, not in_head(rel))
    check_privacy()

    print(f"Pre-publish check: {len(files)} file(s) looked at.")
    if warns:
        print("\nWarnings (not blocking):")
        for w in warns:
            print("  - " + w)
    if fails:
        print("\nFAILED. Fix these before committing:")
        for f in fails:
            print("  - " + f)
        return 1
    print("\nPASSED. Nothing to fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
