#!/usr/bin/env python3
"""Turn a LinkedIn data export into blog-post drafts.

1. On LinkedIn: Settings → Data privacy → Get a copy of your data → choose "Posts" (or the full archive).
2. Unzip it and run:   python scripts/import_linkedin_export.py path/to/Shares.csv [--min-words 120] [--since 2025-01-01]
3. Each substantial post becomes content/blog/<date>-<slug>.md with `draft: true`.
   Read it, edit if you like, delete `draft: true`, commit. Posts already imported are skipped.

It also writes linkedin-talks.csv listing posts that mention a keynote, panel or summit, so their
LinkedIn links can be added to the matching talk in content/keynotes/<talk>/index.md (field: linkedin).
"""
import argparse, csv, re, sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import textkit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BLOG = ROOT / "content" / "blog"
TALK_WORDS = re.compile(r"\b(keynote|panel|summit|conference|convention|webinar|fireside|discover more|ai days|spoke|speaking)\b", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--min-words", type=int, default=120)
    ap.add_argument("--since", default="2000-01-01")
    args = ap.parse_args()
    since = date.fromisoformat(args.since)

    existing = {p.read_text(encoding="utf-8").split("linkedin: ")[-1].split("\n")[0].strip() for p in BLOG.glob("*.md") if "linkedin: " in p.read_text(encoding="utf-8")}
    made, talks = 0, []
    with open(args.csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            text = r.get("ShareCommentary") or ""
            link = r.get("ShareLink") or ""
            when = date.fromisoformat((r.get("Date") or "")[:10])
            if when < since:
                continue
            if TALK_WORDS.search(text):
                talks.append({"date": when.isoformat(), "linkedin": link, "first_line": textkit.clean(text).split("\n")[0][:120]})
            if len(textkit.clean(text).split()) < args.min_words or link in existing:
                continue
            name, content = textkit.blog_post(text.replace('""', '"'), when, link, draft=True)
            (BLOG / name).write_text(content, encoding="utf-8")
            made += 1
    with open(ROOT / "linkedin-talks.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "linkedin", "first_line"])
        w.writeheader()
        w.writerows(talks)
    print(f"{made} draft posts written to content/blog/, {len(talks)} talk-related posts listed in linkedin-talks.csv")


if __name__ == "__main__":
    main()
