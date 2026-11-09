#!/usr/bin/env python3
"""Static site generator for vinodbijlani.me (GitHub Pages).

    python build.py            # builds into ./_site
    python build.py out_dir    # builds somewhere else

Everything the site shows lives in ./content:
    profile.yml          who you are, links, the career route
    experience.yml       roles, each with its projects
    articles.yml         articles published elsewhere (Forbes, CDOTrends ...)
    books.yml, papers.yml, patents.yml
    keynotes/<slug>/index.md   one folder per talk; drop photos into keynotes/<slug>/photos/
    blog/<date>-<slug>.md      blog posts (from LinkedIn), each with an infographic in its front matter

No database, no server: the output is plain HTML that any static host can serve.
"""
import html, json, re, shutil, sys, datetime as dt
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "_site"
SITE_URL = "https://www.vinodbijlani.me"
e = html.escape
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


# ------------------------------------------------------------------ helpers
def load_yaml(name):
    return yaml.safe_load((CONTENT / name).read_text(encoding="utf-8")) or []


def read_md(path):
    text = path.read_text(encoding="utf-8")
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
    return meta, body


def md(text):
    return markdown.markdown(text or "", extensions=["extra", "sane_lists"])


def date_key(d):
    s = str(d or "")
    parts = (s.split("-") + ["0", "0"])[:3]
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return (0, 0, 0)


def date_display(d):
    y, m, day = date_key(d)
    if not y:
        return ""
    if m and day:
        return f"{day} {MONTHS[m-1]} {y}"
    if m:
        return f"{MONTHS[m-1]} {y}"
    return str(y)


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70]


class Page:
    """Knows its own depth so every link and asset path can be relative (works on any host)."""
    def __init__(self, path):
        self.path = path                       # e.g. "speaking/2026-10-x/index.html"
        self.depth = path.count("/")

    def rel(self, target):
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return target
        return "../" * self.depth + target


# ------------------------------------------------------------------ data
PROFILE = load_yaml("profile.yml")
EXPERIENCE = load_yaml("experience.yml")
ARTICLES = sorted(load_yaml("articles.yml"), key=lambda a: date_key(a.get("date")), reverse=True)
BOOKS = load_yaml("books.yml")
PAPERS = sorted(load_yaml("papers.yml"), key=lambda a: date_key(a.get("date")), reverse=True)
PATENTS = load_yaml("patents.yml")


def load_keynotes():
    items = []
    for d in sorted((CONTENT / "keynotes").glob("*/index.md")):
        meta, body = read_md(d)
        folder = d.parent
        photos = sorted(p for p in (folder / "photos").glob("*") if p.suffix.lower() in IMG_EXT) if (folder / "photos").exists() else []
        meta.update(slug=folder.name, body=body.strip(), photos=photos, folder=folder)
        items.append(meta)
    return sorted(items, key=lambda k: date_key(k.get("date")), reverse=True)


def load_posts():
    posts = []
    for f in sorted((CONTENT / "blog").glob("*.md")):
        meta, body = read_md(f)
        if meta.get("draft"):
            continue
        meta.setdefault("date", f.name[:10])
        meta["slug"] = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", f.stem)
        meta["body"] = body.strip()
        posts.append(meta)
    return sorted(posts, key=lambda p: date_key(p.get("date")), reverse=True)


KEYNOTES = load_keynotes()
POSTS = load_posts()
N_INVENTIONS = sum(len(g["inventions"]) for g in PATENTS)
N_FILINGS = sum(len(i["filings"]) for g in PATENTS for i in g["inventions"])
OFFICES = sorted({f[0] for g in PATENTS for i in g["inventions"] for f in i["filings"]})
OFFICE_NAMES = dict(US="United States", WO="WIPO (PCT)", EP="Europe", JP="Japan", CN="China", KR="Korea", GB="United Kingdom", DE="Germany")
YEARS = dt.date.today().year - int(PROFILE.get("career_start", 1998))
N_FORBES = sum(1 for a in ARTICLES if a.get("outlet") == "Forbes" and a.get("type") == "article")

URLS = {"home": "index.html", "experience": "experience.html", "speaking": "speaking/index.html", "blog": "blog/index.html",
        "publications": "publications.html", "books": "books.html", "papers": "papers.html", "patents": "patents.html"}
NAV = [("experience", "Experience"), ("speaking", "Speaking"), ("blog", "Blog"), ("publications", "Publications"),
       ("books", "Books"), ("papers", "Papers"), ("patents", "Patents")]


# ------------------------------------------------------------------ layout
def layout(pg, current, title, description, body, image=None):
    nav = "".join(
        f'<li><a href="{pg.rel(URLS[s])}"{" aria-current=\"page\"" if s == current else ""}>{e(label)}</a></li>'
        for s, label in NAV)
    full_title = PROFILE["name"] if current == "home" else f"{title} · {PROFILE['name']}"
    links = PROFILE["links"]
    canonical = SITE_URL + "/" + ("" if pg.path == "index.html" else pg.path.replace("index.html", "").replace(".html", ""))
    og_img = f'<meta property="og:image" content="{SITE_URL}/{image}">' if image else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{e(canonical)}">
{og_img}
<link rel="alternate" type="application/rss+xml" title="{e(PROFILE['name'])} blog" href="{pg.rel('feed.xml')}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{pg.rel('assets/site.css')}">
</head>
<body>
<nav class="site-nav" aria-label="Main">
  <div class="wrap">
    <a class="brand" href="{pg.rel('index.html')}">{e(PROFILE['name'])}<span>.</span></a>
    <ul>{nav}</ul>
  </div>
</nav>
{body}
<div class="wrap">
  <section class="contact" aria-label="Contact">
    <div>
      <h2>Invite {e(PROFILE['name'].split()[0])} to speak, write or advise.</h2>
      <p>Keynotes, panels and executive briefings on AI factories, sovereign AI and AI economics. {e(PROFILE['email'])}</p>
    </div>
    <div class="cta" style="margin-top:0">
      <a class="btn primary" href="mailto:{e(PROFILE['email'])}">Email</a>
      <a class="btn" href="{e(links['linkedin'])}">LinkedIn</a>
    </div>
  </section>
</div>
<footer>
  <div class="wrap">
    <span class="mono">© {dt.date.today().year} {e(PROFILE['name'])} · {e(PROFILE['location'].split(',')[0])}</span>
    <div class="links">
      <a href="{e(links['linkedin'])}">LinkedIn</a>
      <a href="{e(links['forbes'])}">Forbes Technology Council</a>
      <a href="{e(links['scholar'])}">Google Scholar</a>
      <a href="{e(links['researchgate'])}">ResearchGate</a>
      <a href="{pg.rel('feed.xml')}">RSS</a>
    </div>
  </div>
</footer>
<script src="{pg.rel('assets/site.js')}" defer></script>
</body>
</html>
"""


def page_head(num, title, intro, facts):
    f = "".join(f"<span><b>{e(str(n))}</b>{e(label)}</span>" for n, label in facts)
    return f"""<header class="page-head"><div class="wrap">
  <div class="crumb"><span class="stop">{num}</span><span class="mono">{e(PROFILE['name'])} · {e(title)}</span></div>
  <h1>{e(title)}</h1>
  <p class="intro">{intro}</p>
  <div class="facts">{f}</div>
</div></header>"""


def row(url, side, h3, desc=""):
    inner = f'<div class="side">{side}</div><h3>{h3}{f"<span class=desc>{desc}</span>" if desc else ""}</h3>'
    if url:
        external = url.startswith("http")
        return f'<a class="row" href="{e(url)}">{inner}<span class="arrow" aria-hidden="true">{"↗" if external else "→"}</span></a>'
    return f'<div class="row">{inner}<span class="arrow"></span></div>'


def keynote_photo_rel(k, photo):
    return f"speaking/{k['slug']}/photos/{photo.name}"


# ------------------------------------------------------------------ infographic
def infographic(ig):
    """Renders the side panel for a blog post from its front-matter description."""
    if not ig:
        return ""
    kind = ig.get("type", "steps")
    parts = [f'<div class="ig-title mono">Infographic</div><h3>{e(ig.get("title", ""))}</h3>']
    if ig.get("lead"):
        parts.append(f'<p class="ig-lead">{e(ig["lead"])}</p>')
    if ig.get("stat"):
        s = ig["stat"]
        parts.append(f'<div class="ig-stat"><b>{e(str(s["value"]))}</b><span>{e(s["label"])}</span></div>')
    items = ig.get("items", [])
    if kind == "steps":
        parts.append('<ol class="ig-steps">' + "".join(
            f'<li><b>{e(str(i.get("label", "")))}</b><span>{e(str(i.get("text", "")))}</span></li>' for i in items) + "</ol>")
    elif kind == "stats":
        parts.append('<div class="ig-stats">' + "".join(
            f'<div><b>{e(str(i["value"]))}</b><span>{e(i["label"])}</span></div>' for i in items) + "</div>")
    elif kind == "compare":
        cols = []
        for c in ig.get("columns", []):
            cols.append(f'<div class="ig-col"><b>{e(c["heading"])}</b><span class="sub">{e(c.get("sub", ""))}</span><ul>'
                        + "".join(f"<li>{e(str(x))}</li>" for x in c.get("items", [])) + "</ul></div>")
        parts.append('<div class="ig-compare">' + '<div class="plus" aria-hidden="true">+</div>'.join(cols) + "</div>")
    elif kind == "bars":
        lo, hi = float(ig.get("min", 0)), float(ig.get("max", max([float(i["value"]) for i in items] or [1])))
        bars = []
        for i in items:
            v = float(i["value"])
            pct = max(2.0, min(100.0, (v - lo) / (hi - lo) * 100 if hi > lo else 100))
            bars.append(f'<li><span class="lbl">{e(i["label"])}</span><span class="track"><span class="bar" style="width:{pct:.1f}%"></span></span><b>{e(str(i.get("display", i["value"])))}</b></li>')
        parts.append('<ul class="ig-bars">' + "".join(bars) + "</ul>")
    if ig.get("foot"):
        parts.append(f'<p class="ig-foot">{e(ig["foot"])}</p>')
    return '<aside class="infographic" aria-label="Infographic">' + "".join(parts) + "</aside>"


# ------------------------------------------------------------------ pages
def build_home():
    pg = Page("index.html")
    route = "".join(f'<li><div class="yr">{e(str(r["year"]))}</div><div class="city">{e(r["city"])}</div><div class="what">{e(r["what"])}</div></li>' for r in PROFILE["route"])
    first, last = PROFILE["name"].split(" ", 1)

    talks = []
    for k in KEYNOTES[:3]:
        img = f'<img src="{pg.rel(keynote_photo_rel(k, k["photos"][0]))}" alt="" loading="lazy">' if k["photos"] else '<div class="ph" aria-hidden="true"></div>'
        talks.append(f'<a class="talk-card" href="{pg.rel("speaking/" + k["slug"] + "/index.html")}">{img}<div class="body"><span class="mono">{e(date_display(k.get("date")))} · {e(k.get("role", ""))}</span><h3>{e(k["title"])}</h3><p>{e(k["event"])}</p></div></a>')

    posts = "".join(f'<li>{row(pg.rel("blog/" + p["slug"] + "/index.html"), f"<span class=mono>{e(date_display(p["date"]))}</span>", e(p["title"]), e(p.get("summary", "")))}</li>' for p in POSTS[:3])
    forbes = [a for a in ARTICLES if a.get("type") == "article"][:4]
    writing = "".join(f'<li>{row(a["url"], f"<span class=mono>{e(a["outlet"])} · {e(date_display(a["date"]))}</span>", e(a["title"]))}</li>' for a in forbes)
    book = next((b for b in BOOKS if b.get("featured")), None)
    book_html = ""
    if book:
        bl = "".join(f'<a class="btn{" primary" if i == 0 else ""}" href="{e(l["url"])}">{e(l["label"])}</a>' for i, l in enumerate(book.get("links", [])))
        book_html = f"""<section class="block"><div class="wrap"><div class="book-feature">
  <div class="cover" aria-hidden="true"><span>OWN<br>YOUR<br>AI</span><small>The Sovereign Stack Playbook</small></div>
  <div><span class="mono">New book · {e(str(book["year"]))}</span><h2>{e(book["title"])}</h2><p class="muted">{e(book["authors"])}</p><p>{e(book["description"])}</p><div class="cta">{bl}</div></div>
</div></div></section>"""

    explore = [
        ("experience", len(EXPERIENCE), "Experience", "Roles and the projects delivered in each, from Mumbai to Melbourne."),
        ("speaking", len(KEYNOTES), "Speaking", "Keynotes, panels and papers across Asia Pacific, the Middle East and the US."),
        ("blog", len(POSTS), "Blog", "Field notes on AI factories, token economics and governance, with infographics."),
        ("publications", len(ARTICLES), "Publications", f"Including {N_FORBES} Forbes Technology Council articles."),
        ("books", len(BOOKS), "Books", "Own Your AI, plus chapters with IGI Global and Nova Science."),
        ("patents", N_FILINGS, "Patents", f"{N_INVENTIONS} inventions filed in {len(OFFICES)} patent offices."),
    ]
    cards = "".join(f'<a href="{pg.rel(URLS[s])}"><b>{n}</b><h3>{e(t)}</h3><p>{e(d)}</p></a>' for s, n, t, d in explore)

    body = f"""<header class="hero" id="top"><div class="wrap">
  <div class="mono kicker">{e(PROFILE['kicker'])}</div>
  <h1>{e(first)}<span class="last">{e(last)}</span></h1>
  <p class="role"><strong>{e(PROFILE['title'])}, {e(PROFILE['company'])}.</strong> {e(PROFILE['headline'])}</p>
  <div class="cta">
    <a class="btn primary" href="{pg.rel(URLS['speaking'])}">Speaking</a>
    <a class="btn" href="{pg.rel(URLS['blog'])}">Read the blog</a>
    <a class="btn" href="mailto:{e(PROFILE['email'])}">Email</a>
  </div>
  <div class="route" aria-label="Career route"><ol>{route}</ol></div>
  <div class="stats">
    <div class="stat"><b>{YEARS}</b><span>years, since {PROFILE.get('career_start')}</span></div>
    <div class="stat"><b>{N_FORBES}</b><span>Forbes Technology Council articles</span></div>
    <div class="stat"><b>{len(KEYNOTES)}</b><span>keynotes, panels and talks</span></div>
    <div class="stat"><b>{N_FILINGS}</b><span>patent filings, {N_INVENTIONS} inventions</span></div>
  </div>
</div></header>
<main>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>Latest on stage</h2><div class="more"><a href="{pg.rel(URLS['speaking'])}">All {len(KEYNOTES)} talks →</a></div></div>
  <div class="talk-grid">{''.join(talks)}</div>
</div></section>
{book_html}
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>From the blog</h2><div class="more"><a href="{pg.rel(URLS['blog'])}">All posts →</a></div></div>
  <ul class="rows">{posts}</ul>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>Latest in Forbes</h2><div class="more"><a href="{pg.rel(URLS['publications'])}">All {len(ARTICLES)} publications →</a></div></div>
  <ul class="rows">{writing}</ul>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>The record</h2></div>
  <div class="explore">{cards}</div>
</div></section>
</main>"""
    first_photo = next((keynote_photo_rel(k, k["photos"][0]) for k in KEYNOTES if k["photos"]), None)
    return pg, layout(pg, "home", "Home", f"{PROFILE['name']}: {PROFILE['title']}, {PROFILE['company']}. {PROFILE['headline']}", body, first_photo)


def build_experience():
    pg = Page("experience.html")
    items = []
    for r in EXPERIENCE:
        projects = ""
        if r.get("projects"):
            cards = []
            for p in r["projects"]:
                meta = " · ".join(str(x) for x in [p.get("client", ""), p.get("when", "")] if x)
                cards.append(f"""<article class="card{' feature' if p.get('feature') else ''}">
  <div>{f'<span class="mono">{e(meta)}</span>' if meta else ''}<h3 style="margin-top:6px">{e(p['name'])}</h3></div>
  <p>{e(p['body'])}</p>
  <div class="outcome"><b>{e(str(p['big']))}</b><span>{e(p['small'])}</span></div>
</article>""")
            projects = f'<div class="grid2 projects">{"".join(cards)}</div>'
        items.append(f"""<li class="{'now' if r.get('now') else ''}">
  <div class="tl-head"><h3>{e(r['title'])}</h3><span class="tl-org">{e(r['org'])}</span></div>
  <div class="tl-meta">{e(r['years'])} · {e(r['place'])}</div>
  <p class="tl-body">{e(r['summary'])}</p>
  {projects}
</li>""")
    orgs = []
    for r in EXPERIENCE:
        if r["org"] not in orgs:
            orgs.append(r["org"])
    n_projects = sum(len(r.get("projects", [])) for r in EXPERIENCE)
    body = page_head("01", "Experience", f"{YEARS} years from server administration to leading AI practice across Asia Pacific, with the projects delivered along the way.",
                     [(YEARS, "years"), (len(EXPERIENCE), "roles"), (n_projects, "featured projects"), (len(orgs), "organisations")]) + \
        f'<main class="inner"><div class="wrap"><ul class="logos" aria-label="Organisations">{"".join(f"<li>{e(o)}</li>" for o in orgs)}</ul><ol class="timeline">{"".join(items)}</ol></div></main>'
    return pg, layout(pg, "experience", "Experience", f"Career and projects of {PROFILE['name']}: HPE, IBM, Kroger, Northwestern Mutual, Citibank and Kvaerner.", body)


def build_speaking():
    pg = Page("speaking/index.html")
    by_year = {}
    for k in KEYNOTES:
        by_year.setdefault(str(date_key(k.get("date"))[0]), []).append(k)
    parts = []
    for y, talks in by_year.items():
        lis = []
        for k in talks:
            thumb = f'<img class="thumb" src="{pg.rel(keynote_photo_rel(k, k["photos"][0]))}" alt="" loading="lazy">' if k["photos"] else ""
            badges = "".join([f'<span class="chip hot">{len(k["photos"])} photo{"s" if len(k["photos"]) > 1 else ""}</span>' if k["photos"] else "",
                              '<span class="chip">LinkedIn</span>' if k.get("linkedin") else ""])
            lis.append(f"""<li><a class="talk-row" href="{pg.rel('speaking/' + k['slug'] + '/index.html')}">
  <div><div class="tl-head"><h3>{e(k['title'])}</h3></div>
  <div class="tl-meta">{e(date_display(k.get('date')))} · {e(k.get('role', ''))}{(' · ' + e(k['city'])) if k.get('city') else ''}</div>
  <p class="tl-body">{e(k['event'])}</p><div class="chips">{badges}</div></div>{thumb}</a></li>""")
        parts.append(f'<div class="year-mark">{y}</div><ol class="timeline" style="margin-bottom:12px">{"".join(lis)}</ol>')
    years = sorted(by_year)
    cities = []
    for k in KEYNOTES:
        c = (k.get("city") or "").replace("ICC ", "")
        if c and c != "Online" and c not in cities:
            cities.append(c)
    body = page_head("02", "Speaking", "Keynotes, panels, papers and executive round tables on AI factories, sovereign AI, AI economics and smart cities.",
                     [(len(KEYNOTES), "talks"), (f"{years[0]}–{years[-1]}", ""), (len(cities), "cities")]) + \
        f'<main class="inner"><div class="wrap">{"".join(parts)}</div></main>'
    return pg, layout(pg, "speaking", "Speaking", f"Keynotes and talks by {PROFILE['name']} on AI factories, sovereign AI and agentic AI.", body)


def build_keynote(k):
    pg = Page(f"speaking/{k['slug']}/index.html")
    gallery = ""
    if k["photos"]:
        figs = "".join(f'<a class="g-item" href="photos/{e(p.name)}" data-lightbox><img src="photos/{e(p.name)}" alt="{e(k["event"])} photo {i+1}" loading="lazy"></a>' for i, p in enumerate(k["photos"]))
        gallery = f'<div class="gallery g-{min(len(k["photos"]), 4)}">{figs}</div>'
    links = list(k.get("links") or [])
    if k.get("linkedin"):
        links.insert(0, {"label": "Read the LinkedIn post", "url": k["linkedin"]})
    btns = "".join(f'<a class="btn{" primary" if i == 0 else ""}" href="{e(l["url"])}">{e(l["label"])}</a>' for i, l in enumerate(links))
    related = [p for p in POSTS if k["slug"] in (p.get("keynotes") or [])]
    rel_html = ""
    if related:
        rel_html = '<h2 class="sub-h">Related blog posts</h2><ul class="rows">' + "".join(
            f'<li>{row(pg.rel("blog/" + p["slug"] + "/index.html"), f"<span class=mono>{e(date_display(p["date"]))}</span>", e(p["title"]))}</li>' for p in related) + "</ul>"
    body = f"""<header class="page-head"><div class="wrap">
  <div class="crumb"><a class="stop" href="{pg.rel(URLS['speaking'])}" aria-label="Back to all talks">←</a><span class="mono">{e(k.get('role', ''))} · {e(date_display(k.get('date')))}{(' · ' + e(k['city'])) if k.get('city') else ''}</span></div>
  <h1 class="h1-sm">{e(k['title'])}</h1>
  <p class="intro">{e(k['event'])}</p>
  {f'<div class="cta">{btns}</div>' if btns else ''}
</div></header>
<main class="inner"><div class="wrap">{gallery}<div class="prose">{md(k['body'])}</div>{rel_html}</div></main>"""
    img = keynote_photo_rel(k, k["photos"][0]) if k["photos"] else None
    return pg, layout(pg, "speaking", k["title"], f"{k['event']}: {k['title']}", body, img)


def build_blog_index():
    pg = Page("blog/index.html")
    rows = "".join(f'<li>{row(pg.rel("blog/" + p["slug"] + "/index.html"), f"<span class=mono>{e(date_display(p["date"]))}</span><span class=chips>" + "".join(f"<span class=chip>{e(t)}</span>" for t in (p.get("tags") or [])[:2]) + "</span>", e(p["title"]), e(p.get("summary", "")))}</li>' for p in POSTS)
    body = page_head("03", "Blog", "Field notes from customer conversations, conferences and the AI infrastructure build-out, each with an infographic summary.",
                     [(len(POSTS), "posts"), ("RSS", "feed available")]) + \
        f'<main class="inner"><div class="wrap"><ul class="rows">{rows}</ul></div></main>'
    return pg, layout(pg, "blog", "Blog", f"Blog posts by {PROFILE['name']} on AI factories, token economics, sovereign AI and governance.", body)


def build_post(p):
    pg = Page(f"blog/{p['slug']}/index.html")
    tags = "".join(f'<span class="chip">{e(t)}</span>' for t in (p.get("tags") or []))
    related = list(p.get("related") or [])
    if p.get("linkedin"):
        related.insert(0, {"label": "Discuss on LinkedIn", "url": p["linkedin"]})
    rel = ""
    if related:
        rel = '<div class="post-links"><span class="mono">Read more</span>' + "".join(f'<a href="{e(l["url"])}">{e(l["label"])} ↗</a>' for l in related) + "</div>"
    idx = POSTS.index(p)
    nxt = POSTS[idx - 1] if idx > 0 else None
    prv = POSTS[idx + 1] if idx + 1 < len(POSTS) else None
    pager = '<nav class="pager" aria-label="More posts">' + \
        (f'<a href="../{e(prv["slug"])}/index.html"><span class="mono">← Older</span>{e(prv["title"])}</a>' if prv else "<span></span>") + \
        (f'<a class="next" href="../{e(nxt["slug"])}/index.html"><span class="mono">Newer →</span>{e(nxt["title"])}</a>' if nxt else "<span></span>") + "</nav>"
    body = f"""<header class="page-head"><div class="wrap">
  <div class="crumb"><a class="stop" href="{pg.rel(URLS['blog'])}" aria-label="Back to the blog">←</a><span class="mono">{e(date_display(p['date']))} · {e(PROFILE['name'])}</span></div>
  <h1 class="h1-sm">{e(p['title'])}</h1>
  {f'<p class="intro">{e(p["summary"])}</p>' if p.get('summary') else ''}
  <div class="chips" style="margin-top:16px">{tags}</div>
</div></header>
<main class="inner"><div class="wrap"><div class="post-grid">
  <article class="prose">{md(p['body'])}{rel}</article>
  {infographic(p.get('infographic'))}
</div>{pager}</div></main>"""
    return pg, layout(pg, "blog", p["title"], p.get("summary", p["title"]), body)


def build_publications():
    pg = Page("publications.html")
    topics = {}
    for a in ARTICLES:
        topics[a["topic"]] = topics.get(a["topic"], 0) + 1
    topics = dict(sorted(topics.items(), key=lambda t: -t[1]))
    buttons = f'<button type="button" aria-pressed="true" data-topic="all">All<span>{len(ARTICLES)}</span></button>' + "".join(
        f'<button type="button" aria-pressed="false" data-topic="{e(t)}">{e(t)}<span>{n}</span></button>' for t, n in topics.items())
    label = {"article": "Article", "panel": "Expert panel", "interview": "Interview"}
    rows = "".join(
        f'<li data-topic="{e(a["topic"])}">' + row(a.get("url", ""),
            f'<span class="mono">{e(a["outlet"])} · {e(date_display(a["date"]))}</span><span class="chips"><span class="chip{" hot" if a.get("type") == "article" and a["outlet"].startswith("Forbes") else ""}">{label.get(a.get("type"), "Article")}</span></span>',
            e(a["title"]), e(a.get("note", ""))) + "</li>" for a in ARTICLES)
    outlets = len({a["outlet"] for a in ARTICLES})
    body = page_head("04", "Publications", "Articles and expert panels for the Forbes Technology Council, CDOTrends, the World Economic Forum, The Business Times and more.",
                     [(len(ARTICLES), "publications"), (N_FORBES, "Forbes articles"), (outlets, "outlets")]) + \
        f'<main class="inner"><div class="wrap"><p class="note" style="margin:0 0 24px"><strong>Looking for the blog?</strong> Posts written for this site are on the <a href="{pg.rel(URLS["blog"])}">blog</a>.</p><div class="filters" role="group" aria-label="Filter by topic">{buttons}</div><ul class="rows" data-filterable>{rows}</ul></div></main>'
    return pg, layout(pg, "publications", "Publications", f"Articles by {PROFILE['name']} in Forbes, CDOTrends, the World Economic Forum and more.", body)


def build_books():
    pg = Page("books.html")
    cards = []
    for b in BOOKS:
        if not b.get("publisher") and not b.get("description"):
            cards.append(f'<article class="card"><span class="mono">{e(b["kind"])}</span><h3>{e(b["title"])}</h3></article>')
            continue
        meta = " · ".join(str(x) for x in [b.get("publisher"), b.get("year")] if x)
        links = "".join(f'<a class="btn{" primary" if i == 0 else ""}" href="{e(l["url"])}">{e(l["label"])} ↗</a>' for i, l in enumerate(b.get("links") or []))
        cards.append(f"""<article class="card{' feature' if b.get('featured') else ''}">
  <div><span class="mono">{e(b['kind'])} · {e(meta)}</span><h3 style="margin-top:6px">{e(b['title'])}</h3>{f'<p class="role-line">{e(b["book"])}</p>' if b.get('book') else ''}{f'<p class="role-line">{e(b["authors"])}</p>' if b.get('authors') else ''}</div>
  <p>{e(b.get('description', ''))}</p>
  {f'<div class="cta" style="margin-top:auto">{links}</div>' if links else ''}
</article>""")
    n_books = sum(1 for b in BOOKS if b["kind"] == "Book")
    body = page_head("05", "Books", "A playbook on sovereign AI, and invited chapters on sustainable buildings, resilient smart cities and health.",
                     [(n_books, "book"), (len(BOOKS) - n_books, "chapters"), ("IGI Global · Nova Science", "")]) + \
        f'<main class="inner"><div class="wrap"><div class="grid2">{"".join(cards)}</div></div></main>'
    return pg, layout(pg, "books", "Books", f"Books and chapters by {PROFILE['name']}, including Own Your AI.", body)


def build_papers():
    pg = Page("papers.html")
    rows = "".join(f'<li>{row(p.get("url", ""), f"<span class=mono>{e(date_display(p["date"]))}</span>", e(p["title"]), e(p["venue"]))}</li>' for p in PAPERS)
    body = page_head("06", "Papers", "Conference and journal papers on smart buildings, net zero, 5G traffic management and intelligent transport.",
                     [(len(PAPERS), "papers"), ("Springer · IEEE", "")]) + \
        f'<main class="inner"><div class="wrap"><ul class="rows">{rows}</ul></div></main>'
    return pg, layout(pg, "papers", "Papers", f"Papers by {PROFILE['name']}.", body)


def build_patents():
    pg = Page("patents.html")
    parts = []
    for g in PATENTS:
        cards = []
        for inv in g["inventions"]:
            fl = "".join(f'<a href="https://patentscope.wipo.int/search/en/detail.jsf?docId={e(d)}" title="{e(OFFICE_NAMES.get(o, o))}"><b>{e(o)}</b><span>{e(str(dt_))}</span></a>' for o, dt_, d in inv["filings"])
            n = len(inv["filings"])
            cards.append(f'<article class="patent"><h3>{e(inv["title"])}</h3><div class="count">{n}<small>{"filing" if n == 1 else "filings"}</small></div><div class="filings">{fl}</div></article>')
        parts.append(f'<div class="group-title">{e(g["group"])} <span class="mono">{len(g["inventions"])} inventions</span></div><div class="grid2">{"".join(cards)}</div>')
    body = page_head("07", "Patents", "Inventions in data analytics for smart transportation, retail, interactive media and networking. IBM Master Inventor.",
                     [(N_INVENTIONS, "inventions"), (N_FILINGS, "filings"), (len(OFFICES), "patent offices"), (" · ".join(OFFICES), "")]) + \
        f'<main class="inner"><div class="wrap">{"".join(parts)}<p class="note">Each filing links to its record on WIPO Patentscope.</p></div></main>'
    return pg, layout(pg, "patents", "Patents", f"Patents by {PROFILE['name']}, IBM Master Inventor.", body)


def redirect(path, target, label):
    pg = Page(path)
    t = pg.rel(target)
    return pg, f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{e(label)} · {e(PROFILE['name'])}</title>
<meta http-equiv="refresh" content="0; url={e(t)}"><link rel="canonical" href="{SITE_URL}/{target.replace('.html', '')}"><meta name="robots" content="noindex"></head>
<body><p>This page has moved to <a href="{e(t)}">{e(label)}</a>.</p></body></html>"""


def build_404():
    pg = Page("404.html")
    body = page_head("?", "Page not found", f'The page you were looking for has moved. Try <a href="/speaking">Speaking</a>, the <a href="/blog">blog</a> or <a href="/">the home page</a>.', [])
    return pg, layout(pg, "", "Not found", "Page not found", body)


def build_feed():
    items = "".join(f"""<item><title>{e(p['title'])}</title><link>{SITE_URL}/blog/{p['slug']}</link><guid>{SITE_URL}/blog/{p['slug']}</guid>
<pubDate>{dt.date(*date_key(p['date'])).strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate><description>{e(p.get('summary', ''))}</description></item>""" for p in POSTS)
    return f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{e(PROFILE['name'])}</title><link>{SITE_URL}</link>
<description>{e(PROFILE['headline'])}</description>{items}</channel></rss>"""


def build_sitemap(paths):
    urls = "".join(f"<url><loc>{SITE_URL}/{p.replace('index.html', '').replace('.html', '')}</loc></url>" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>'


# ------------------------------------------------------------------ main
def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    for f in (ROOT / "assets").iterdir():
        if f.is_file():
            shutil.copy(f, OUT / "assets" / f.name)
        elif f.is_dir():
            shutil.copytree(f, OUT / "assets" / f.name)

    pages = [build_home(), build_experience(), build_speaking(), build_blog_index(), build_publications(),
             build_books(), build_papers(), build_patents(), build_404()]
    pages += [build_keynote(k) for k in KEYNOTES]
    pages += [build_post(p) for p in POSTS]
    # Old Wix addresses keep working
    pages += [redirect("roles.html", "experience.html", "Experience"), redirect("projects.html", "experience.html", "Experience"),
              redirect("certifications.html", "experience.html", "Experience"), redirect("letter-of-appreciation.html", "index.html", "Home")]

    for pg, content in pages:
        out = OUT / pg.path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(content, encoding="utf-8")
    for k in KEYNOTES:
        if k["photos"]:
            dest = OUT / "speaking" / k["slug"] / "photos"
            dest.mkdir(parents=True, exist_ok=True)
            for p in k["photos"]:
                shutil.copy(p, dest / p.name)

    (OUT / "feed.xml").write_text(build_feed(), encoding="utf-8")
    public = [pg.path for pg, _ in pages if pg.path not in ("404.html", "roles.html", "projects.html", "certifications.html", "letter-of-appreciation.html")]
    (OUT / "sitemap.xml").write_text(build_sitemap(public), encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", OUT / "CNAME")
    (OUT / ".nojekyll").write_text("")
    print(f"Built {len(pages)} pages into {OUT}: {len(KEYNOTES)} talks, {len(POSTS)} posts, {len(ARTICLES)} publications, "
          f"{sum(len(k['photos']) for k in KEYNOTES)} photos")


if __name__ == "__main__":
    main()
