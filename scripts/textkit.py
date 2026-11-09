"""Shared helpers for turning raw text (LinkedIn posts, Drive notes) into site content."""
import re
import unicodedata
from datetime import date

import yaml

BULLET = re.compile(r"^\s*(?:[•\-\*→➜➤▶✅✔️☑️🔹🔸▪️◆]|\d{1,2}[.)])\s*")
FIGURE = re.compile(r"(?<![\w.])(~?[$€£]?\d[\d,.]*\s?(?:%|x|×|[KMB]\b|kW|MW|GW|GWh|ms|nm|bn|million|billion)?)", re.I)
HASHTAGS = re.compile(r"(?:^|\s)#\w+")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿️]")


def clean(text: str) -> str:
    """LinkedIn 'bold' letters are Unicode maths symbols; NFKC turns them back into normal text."""
    text = unicodedata.normalize("NFKC", text.replace("﻿", ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def strip_noise(line: str) -> str:
    line = EMOJI.sub("", line)
    return line.strip(" *_")


def slugify(s: str, n: int = 60) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n].rstrip("-") or "post"


def split_post(text: str):
    """Split a LinkedIn post into (title, body, links). Comments/links after the main post are kept as links."""
    text = clean(text)
    links = re.findall(r"https?://\S+", text)
    # drop lines that are only hashtags or a call to follow
    lines = [l for l in text.split("\n") if not re.fullmatch(r"\s*(#\w+\s*)+", l)
             and not re.match(r"\s*(follow @|follow me|♻️|repost)", l, re.I)]
    paras = [p.strip() for p in "\n".join(lines).split("\n\n") if p.strip()]
    title = strip_noise(paras[0].split("\n")[0]) if paras else "Untitled"
    title = re.sub(r"\s+", " ", title).rstrip(":")
    if len(title) > 110:
        title = title[:107].rsplit(" ", 1)[0] + "…"
    body = "\n\n".join(paras[1:] if len(paras) > 1 else paras)
    body = HASHTAGS.sub("", body)
    body = re.sub(r"https?://\S+", "", body)
    return title, body.strip(), links


def to_markdown(body: str) -> str:
    """LinkedIn uses one line per thought; turn bullet-ish lines into Markdown lists, keep the rest as paragraphs."""
    out = []
    for para in body.split("\n\n"):
        lines = [l for l in para.split("\n") if l.strip()]
        if lines and sum(bool(BULLET.match(l)) for l in lines) >= max(2, len(lines) // 2):
            out.append("\n".join("- " + strip_noise(BULLET.sub("", l)) for l in lines))
        else:
            out.append(" ".join(strip_noise(l) if i == 0 else l.strip() for i, l in enumerate(lines)))
    return "\n\n".join(out)


def auto_infographic(title: str, body: str):
    """Build a side-panel infographic from the post itself: list items become steps, the first figure becomes the headline stat."""
    items = []
    for line in body.split("\n"):
        if BULLET.match(line):
            t = strip_noise(BULLET.sub("", line))
            if 3 <= len(t) <= 140:
                label, _, rest = t.partition(":")
                if rest and len(label) <= 32:
                    items.append({"label": label.strip(), "text": rest.strip()})
                else:
                    words = t.split()
                    items.append({"label": " ".join(words[:3]), "text": " ".join(words[3:])})
    stat = None
    for line in body.split("\n"):
        m = FIGURE.search(line)
        if m and len(m.group(1).strip()) > 1 and not re.fullmatch(r"\d{4}", m.group(1).strip()):
            stat = {"value": m.group(1).strip(), "label": strip_noise(line)[:90]}
            break
    if not items and not stat:
        return None
    ig = {"type": "steps", "title": "At a glance", "items": items[:6]}
    if stat:
        ig["stat"] = stat
    if not items:
        ig = {"type": "stats", "title": "At a glance", "items": [stat]}
    return ig


def front_matter(meta: dict, body: str) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000) + "---\n\n" + body.strip() + "\n"


def summary_of(body: str, n: int = 180) -> str:
    first = re.sub(r"\s+", " ", body.split("\n\n")[0]).strip(" -")
    return first if len(first) <= n else first[: n - 1].rsplit(" ", 1)[0] + "…"


def blog_post(text: str, when: date, linkedin: str = "", draft: bool = False):
    """Return (filename, file content) for a blog post made from a LinkedIn post."""
    title, body, links = split_post(text)
    md = to_markdown(body)
    meta = {"title": title, "date": when.isoformat(), "summary": summary_of(md), "tags": []}
    if linkedin:
        meta["linkedin"] = linkedin
    related = [{"label": "Forbes Technology Council article", "url": u} for u in links if "forbes.com" in u]
    if related:
        meta["related"] = related[:3]
    ig = auto_infographic(title, body)
    if ig:
        meta["infographic"] = ig
    if draft:
        meta["draft"] = True
    return f"{when.isoformat()}-{slugify(title)}.md", front_matter(meta, md)
