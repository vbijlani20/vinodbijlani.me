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
        order = [str(x) for x in (meta.get("order") or [])]
        if order:  # photos listed in 'order' come first, in that order
            photos.sort(key=lambda ph: order.index(ph.name) if ph.name in order else len(order))
        cover = [ph for ph in photos if ph.name == meta.get("cover")]
        photos = cover + [ph for ph in photos if ph not in cover]  # the cover is shown first everywhere
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


import hashlib
ASSET_V = hashlib.sha1((Path(__file__).parent / "assets" / "site.css").read_bytes() + (Path(__file__).parent / "assets" / "site.js").read_bytes()).hexdigest()[:8]
KEYNOTES = load_keynotes()
GALLERY = load_yaml("gallery.yml") if (CONTENT / "gallery.yml").exists() else []
GALLERY_GROUPS = {}
for _g in GALLERY:
    GALLERY_GROUPS.setdefault(_g.get("group") or "On stage", []).append(_g)
for _name, _items in GALLERY_GROUPS.items():
    _items.sort(key=lambda g: not g.get("cover"))
POSTS = load_posts()
N_INVENTIONS = sum(len(g["inventions"]) for g in PATENTS)
N_FILINGS = sum(len(i["filings"]) for g in PATENTS for i in g["inventions"])
OFFICES = sorted({f[0] for g in PATENTS for i in g["inventions"] for f in i["filings"]})
_FILING_YEARS = sorted(int(f[1][-4:]) for g in PATENTS for i in g["inventions"] for f in i["filings"])
FIRST_FILING, LAST_FILING = _FILING_YEARS[0], _FILING_YEARS[-1]
AI_SINCE = int(PROFILE.get("ai_since", FIRST_FILING))
OFFICE_NAMES = dict(US="United States", WO="WIPO (PCT)", EP="Europe", JP="Japan", CN="China", KR="Korea", GB="United Kingdom", DE="Germany")
YEARS = dt.date.today().year - int(PROFILE.get("career_start", 1998))
N_FORBES = sum(1 for a in ARTICLES if a.get("outlet") == "Forbes" and a.get("type") == "article")

URLS = {"home": "index.html", "experience": "experience.html", "speaking": "speaking/index.html", "blog": "blog/index.html",
        "publications": "publications.html", "books": "books.html", "papers": "papers.html", "patents": "patents.html"}
NAV = [("experience", "Experience"), ("speaking", "Thought Leadership"), ("blog", "Blog"), ("publications", "Publications"),
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
<link rel="stylesheet" href="{pg.rel('assets/site.css')}?v={ASSET_V}">
</head>
<body>
<nav class="site-nav" aria-label="Main">
  <div class="wrap">
    <a class="brand" href="{pg.rel('index.html')}">{e(PROFILE['name'])}<span class="dash" aria-hidden="true"></span></a>
    <ul>{nav}</ul>
  </div>
</nav>
{body}
<div class="wrap">
  <section class="contact" aria-label="Contact">
    <div>
      <h2>Invite {e(PROFILE['name'].split()[0])} to speak, write or advise.</h2>
      <p>Keynotes, panels and executive briefings on AI factories, sovereign AI and AI economics. Send a message on LinkedIn.</p>
    </div>
    <div class="cta" style="margin-top:0">
      <a class="btn primary" href="{e(links['linkedin'])}">Connect on LinkedIn</a>
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
<script src="{pg.rel('assets/site.js')}?v={ASSET_V}" defer></script>
</body>
</html>
"""


def page_art(pg, key):
    """Right-hand header image for a section page, from profile.yml page_photos."""
    ph = (PROFILE.get("page_photos") or {}).get(key)
    if not ph:
        return ""
    pos = f' style="object-position:{e(ph["pos"])}"' if ph.get("pos") else ""
    img = f'<img src="{pg.rel(ph["src"])}" alt="{e(ph.get("alt", ""))}"{pos} fetchpriority="high">'
    if ph.get("link"):
        href = ph["link"] if ph["link"].startswith("http") else pg.rel(ph["link"])
        img = f'<a href="{e(href)}">{img}</a>'
    cls = "head-art natural" if ph.get("fit") == "natural" else "head-art"
    return f'<figure class="{cls}">{img}</figure>'


def page_head(num, title, intro, facts, art="", note=""):
    f = "".join(f"<span><b>{e(str(n))}</b>{e(label)}</span>" for n, label in facts)
    text = f"""<div class="head-text">
  <div class="crumb"><span class="stop">{num}</span><span class="mono">{e(PROFILE['name'])} · {e(title)}</span></div>
  <h1>{e(title)}</h1>
  <p class="intro">{intro}</p>
  {f'<div class="facts">{f}</div>' if f else ''}
</div>"""
    if art:
        # numbers sit under the title and intro, in the same style as the home page
        nums = "".join(f'<div class="stat"><b>{e(str(n))}</b><span>{e(label)}</span></div>' for n, label in facts)
        if f:
            text = text.replace(f'<div class="facts">{f}</div>', f'<div class="stats compact head-stats">{nums}</div>' + (f'<p class="head-note">{note}</p>' if note else ""))
        return f'<header class="page-head with-art"><div class="wrap head-grid">{text}<div class="head-side">{art}</div></div></header>'
    return f'<header class="page-head"><div class="wrap">{text}</div></header>'



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

    seen, with_photos = set(), []
    for k in KEYNOTES:  # one session per event on the home page
        if k["photos"] and k["event"] not in seen:
            seen.add(k["event"]); with_photos.append(k)
    featured = with_photos[:3] or KEYNOTES[:3]
    # Photo strip: one photo each from six other presentations, each linking to its event page
    strip = []
    for k in with_photos[3:9]:
        cap = (k.get("captions") or {}).get(k["photos"][0].name) or k["event"]
        strip.append(f'<a href="{pg.rel("speaking/" + k["slug"] + "/index.html")}" title="{e(k["event"])}"><img src="{pg.rel(keynote_photo_rel(k, k["photos"][0]))}" alt="{e(cap)}" loading="lazy"><span>{e(k["event"])}</span></a>')
    stage_strip = f'<div class="stage-strip">{"".join(strip)}</div>' if strip else ""
    talks = []
    for k in featured:
        img = f'<img src="{pg.rel(keynote_photo_rel(k, k["photos"][0]))}" alt="" loading="lazy">' if k["photos"] else '<div class="ph" aria-hidden="true"></div>'
        talks.append(f'<a class="talk-card" href="{pg.rel("speaking/" + k["slug"] + "/index.html")}">{img}<div class="body"><span class="mono">{e(date_display(k.get("date")))} · {e(k.get("role", ""))}</span><h3>{e(k["title"])}</h3><p>{e(k["event"])}</p></div></a>')

    posts = "".join(
        f'<a class="talk-card" href="{pg.rel("blog/" + p["slug"] + "/index.html")}">'
        + (f'<img class="ig-thumb" src="{pg.rel("blog/" + p["image"])}" alt="" loading="lazy">' if p.get("image") else post_visual(pg, p))
        + f'<div class="body"><span class="mono">{e(date_display(p["date"]))}</span><h3>{e(p["title"])}</h3><p>{e(p.get("summary", ""))}</p></div></a>'
        for p in POSTS[:3])
    forbes = [a for a in ARTICLES if a.get("type") == "article"][:4]
    writing = "".join(f'<li>{row(a["url"], f"<span class=mono>{e(a["outlet"])} · {e(date_display(a["date"]))}</span>", e(a["title"]))}</li>' for a in forbes)
    book = next((b for b in BOOKS if b.get("featured")), None)
    book_html = ""
    if book:
        bl = "".join(f'<a class="btn{" primary" if i == 0 else ""}" href="{e(l["url"])}">{e(l["label"])}</a>' for i, l in enumerate(book.get("links", [])))
        book_html = f"""<section class="block"><div class="wrap"><div class="book-feature">
  <a class="cover-link" href="{e(book["links"][0]["url"])}"><img class="cover-img" src="{pg.rel("assets/img/own-your-ai-cover.webp")}" alt="Own Your AI book cover"></a>
  <div><span class="mono">New book · {e(str(book["year"]))}</span><h2>{e(book["title"])}</h2><p class="muted">{e(book["authors"])}</p><p>{e(book["description"])}</p><div class="cta">{bl}</div></div>
</div></div></section>"""

    explore = [
        ("experience", len(EXPERIENCE), "Experience", "Roles and the projects delivered in each, from Mumbai to Melbourne.", "roles"),
        ("speaking", len(KEYNOTES), "Thought leadership", "Keynotes, panels and papers across Asia Pacific, the Middle East and the US.", "talks"),
        ("blog", len(POSTS), "Blog", "Field notes on AI factories, token economics and governance, with infographics.", "posts"),
        ("publications", len(ARTICLES), "Publications", f"Including {N_FORBES} Forbes Technology Council articles.", "publications"),
        ("books", len(BOOKS), "Books", "Own Your AI, plus chapters with Springer, Elsevier, IGI Global and Nova Science.", "titles"),
        ("patents", N_FILINGS, "Patents", f"{N_INVENTIONS} inventions filed in {len(OFFICES)} patent offices.", "filings"),
    ]
    cards = "".join(f'<a href="{pg.rel(URLS[s])}"><h3>{e(t)} <span aria-hidden="true">→</span></h3><p>{e(d)}</p><span class="mono">{n} {e(u)}</span></a>' for s, n, t, d, u in explore)

    hero_img = ""
    if PROFILE.get("stage_photo"):
        hero_img = f'<figure class="stage-photo"><img src="{pg.rel(PROFILE["stage_photo"])}" alt="{e(PROFILE["name"])} presenting a keynote on stage" width="1100" height="732" fetchpriority="high"></figure>'
    elif PROFILE.get("photo"):
        hero_img = f'<img class="portrait" src="{pg.rel(PROFILE["photo"])}" alt="{e(PROFILE["name"])}" width="240" height="298">'
    body = f"""<header class="hero" id="top"><div class="wrap">
  <div class="hero-top">
    <div class="hero-text"><div class="mono kicker">{e(PROFILE['kicker'])}</div>
    <h1>{e(first)}<span class="last">{e(last)}</span></h1>
    <p class="role"><strong>{e(PROFILE['title'])}, {e(PROFILE['company'])}.</strong> {e(PROFILE['headline'])}</p>
    <div class="cta">
      <a class="btn primary" href="{pg.rel(URLS['speaking'])}">Thought leadership</a>
      <a class="btn" href="{pg.rel(URLS['blog'])}">Read the blog</a>
      <a class="btn" href="{e(PROFILE['links']['linkedin'])}">LinkedIn</a>
    </div></div>
    <div class="hero-side">{hero_img}
      <div class="stats compact">
        <div class="stat"><b>{YEARS}</b><span>years since {PROFILE.get('career_start')}</span></div>
        <div class="stat"><b>{len(KEYNOTES)}</b><span>keynotes, panels and talks</span></div>
        <div class="stat"><b>{len(ARTICLES)}</b><span>articles and expert panels</span></div>
        <div class="stat"><b>{len(BOOKS)}</b><span>books and chapters</span></div>
        <div class="stat"><b>{N_FILINGS}</b><span>patent filings</span></div>
      </div>
    </div>
  </div>
</div></header>
<main>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>Thought leadership</h2><div class="more"><a href="{pg.rel(URLS['speaking'])}">All keynotes, panels and talks →</a></div></div>
  <div class="talk-grid">{''.join(talks)}</div>
  {stage_strip}
</div></section>
{book_html}
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>From the blog</h2><div class="more"><a href="{pg.rel(URLS['blog'])}">All posts →</a></div></div>
  <div class="talk-grid">{posts}</div>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>Latest publications</h2><div class="more"><a href="{pg.rel(URLS['publications'])}">All {len(ARTICLES)} publications →</a></div></div>
  <ul class="rows">{writing}</ul>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>Explore further</h2></div>
  <div class="explore subtle">{cards}</div>
</div></section>
<section class="block"><div class="wrap">
  <div class="sec-head"><span class="stop">→</span><h2>From Mumbai to Melbourne</h2></div>
  <div class="route" aria-label="Career route"><ol>{route}</ol></div>
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
    body = page_head("01", "Experience", f"{YEARS} years from server administration to leading AI practice across Asia Pacific. Building AI solutions since {AI_SINCE}, with the projects delivered along the way.",
                     [(YEARS, "years"), (len(EXPERIENCE), "roles"), (f"Since {AI_SINCE}", "building AI solutions")], page_art(pg, "experience")) + \
        f'<main class="inner"><div class="wrap"><ul class="logos" aria-label="Organisations">{"".join(f"<li>{e(o)}</li>" for o in orgs)}</ul><ol class="timeline">{"".join(items)}</ol></div></main>'
    return pg, layout(pg, "experience", "Experience", f"Career and projects of {PROFILE['name']}: HPE, IBM, Kroger, Northwestern Mutual, Citibank and Kvaerner.", body)


def talk_kinds(k):
    r = (k.get("role") or "").lower()
    kinds = [x for x, words in (("keynote", ("keynote",)), ("panel", ("panel", "moderat")), ("webinar", ("webinar", "online"))) if any(w in r for w in words)]
    if "webinar" in (k.get("event") or "").lower() or (k.get("city") or "") == "Online":
        kinds.append("webinar")
    return sorted(set(kinds)) or ["talk"]


def first_para(text, limit=260):
    para = re.sub(r"\s+", " ", (text or "").strip().split("\n\n")[0])
    para = re.sub(r"[*_`#>\[\]]|\(https?://[^)]*\)", "", para)
    return para if len(para) <= limit else para[:limit].rsplit(" ", 1)[0] + "…"


def photo_figure(pg, src, caption, event, credit=None, credit_url=None):
    cred = ""
    if credit:
        cred = f'<a class="credit" href="{e(credit_url)}">{e(credit)} ↗</a>' if credit_url else f'<span class="credit">{e(credit)}</span>'
    return (f'<figure class="ph"><a href="{pg.rel(src)}" data-lightbox aria-label="Enlarge: {e(caption)}">'
            f'<img src="{pg.rel(src)}" alt="{e(caption)}" loading="lazy"></a>'
            f'<figcaption><strong>{e(event)}</strong><span>{e(caption)}</span>{cred}</figcaption></figure>')


GROUP_BLURB = {
    "Technical presentations": "Sessions on AI platforms, sovereign AI and the AI factory, presented with Red Hat and HPE.",
    "Conference photographs": "With colleagues and partners at conferences and HPE exhibits.",
}


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def captioned_grid(pg, photos):
    """photos: list of (src, caption, event, credit_label, credit_url)."""
    n = len(photos)
    cls = n if n <= 4 else "many"
    return f'<div class="photo-grid detail n{cls}">' + "".join(photo_figure(pg, *ph) for ph in photos) + "</div>"


def build_photo_group(name, items):
    pg = Page(f"speaking/photos/{slugify(name)}/index.html")
    grid = captioned_grid(pg, [("gallery/" + g["file"], g.get("caption", ""), name, None, None) for g in items])
    art = f'<figure class="head-art"><img src="{pg.rel("gallery/" + items[0]["file"])}" alt="{e(items[0].get("caption", ""))}" fetchpriority="high"></figure>'
    body = f"""<header class="page-head with-art"><div class="wrap head-grid"><div class="head-text">
  <div class="crumb"><a class="stop" href="{pg.rel(URLS['speaking'])}" aria-label="Back to thought leadership">←</a><span class="mono">Photo archive · {len(items)} photos</span></div>
  <h1 class="h1-sm">{e(name)}</h1>
  <p class="intro">{e(GROUP_BLURB.get(name, ''))}</p>
</div>{art}</div></header>
<main class="inner"><div class="wrap">{grid}</div></main>"""
    return pg, layout(pg, "speaking", name, f"{name}: photos of {PROFILE['name']}.", body, "gallery/" + items[0]["file"])


def build_speaking():
    pg = Page("speaking/index.html")
    years = sorted({str(date_key(k.get("date"))[0]) for k in KEYNOTES})
    cities = []
    for k in KEYNOTES:
        c = (k.get("city") or "").replace("ICC ", "")
        if c and c != "Online" and c not in cities:
            cities.append(c)
    n_photos = sum(len(k["photos"]) for k in KEYNOTES) + len(GALLERY)
    counts = {}
    for k in KEYNOTES:
        for kind in talk_kinds(k):
            counts[kind] = counts.get(kind, 0) + 1
    labels = [("all", "All", len(KEYNOTES)), ("keynote", "Keynotes", counts.get("keynote", 0)), ("panel", "Panels", counts.get("panel", 0)),
              ("webinar", "Webinars", counts.get("webinar", 0)), ("talk", "Other talks", counts.get("talk", 0))]
    chips = "".join(f'<button type="button" data-kind="{k}" aria-pressed="{"true" if k == "all" else "false"}">{e(l)}<span>{n}</span></button>' for k, l, n in labels if n)
    finder = f"""<div class="finder" role="search">
  <label for="tl-q">Search talks, events, cities and topics</label>
  <input id="tl-q" type="search" placeholder="Try: sovereign, Sydney, panel, 2021" autocomplete="off" aria-controls="tl-results">
  <div class="filters" role="group" aria-label="Filter by format">{chips}</div>
  <p id="tl-status" class="mono" role="status"></p>
</div>"""

    # Events in pictures: one cover photo per event, linking to the event page with every photo
    events = []
    for k in KEYNOTES:
        if not k["photos"]:
            continue
        page = pg.rel("speaking/" + k["slug"] + "/index.html")
        cover = k["photos"][0]
        alt = (k.get("captions") or {}).get(cover.name) or k["event"]
        n = len(k["photos"])
        meta = " · ".join(x for x in (date_display(k.get("date")), (k.get("city") or "").replace("ICC ", ""), k.get("role", "")) if x)
        li = f'<a class="ev-li" href="{e(k["linkedin"])}">LinkedIn post ↗</a>' if k.get("linkedin") else ""
        events.append(f"""<article class="ev-card" data-record data-kind="{' '.join(talk_kinds(k))}">
  <a class="ev-cover" href="{page}"><img src="{pg.rel(keynote_photo_rel(k, cover))}" alt="{e(alt)}" loading="lazy"><span class="ev-count mono">{n} photo{'s' if n != 1 else ''}</span></a>
  <div class="ev-body"><span class="mono">{e(meta)}</span>
    <h3><a href="{page}">{e(k['title'])}</a></h3>
    <p class="event-name">{e(k['event'])}</p>
    <p class="ev-sum">{e(first_para(k['body'], 170))}</p>
    <div class="ev-foot"><a class="ev-more" href="{page}">View event and {n} photo{'s' if n != 1 else ''} →</a>{li}</div>
  </div>
</article>""")

    # Archive photos without a specific event: one cover per group, linking to the group page
    archive = []
    for name, items in GALLERY_GROUPS.items():
        page = pg.rel("speaking/photos/" + slugify(name) + "/index.html")
        g0 = items[0]
        archive.append(f"""<article class="ev-card" data-record data-kind="talk keynote panel webinar">
  <a class="ev-cover" href="{page}"><img src="{pg.rel('gallery/' + g0['file'])}" alt="{e(g0.get('caption', ''))}" loading="lazy"><span class="ev-count mono">{len(items)} photos</span></a>
  <div class="ev-body"><span class="mono">Photo archive</span><h3><a href="{page}">{e(name)}</a></h3>
    <p class="ev-sum">{e(GROUP_BLURB.get(name, ''))}</p>
    <div class="ev-foot"><a class="ev-more" href="{page}">View {len(items)} photos →</a></div></div>
</article>""")

    # Full archive of talks by year
    by_year = {}
    for k in KEYNOTES:
        by_year.setdefault(str(date_key(k.get("date"))[0]), []).append(k)
    parts = []
    for y, talks in by_year.items():
        lis = []
        for k in talks:
            kinds = talk_kinds(k)
            if k["photos"]:
                thumb = f'<img class="thumb" src="{pg.rel(keynote_photo_rel(k, k["photos"][0]))}" alt="" loading="lazy">'
            else:  # designed tile until a photo is added to the talk's folder
                place = (k.get("city") or "").replace("ICC ", "") or ("Online" if "webinar" in kinds else "")
                fmt = {"keynote": "Keynote", "panel": "Panel", "webinar": "Webinar"}.get(next((x for x in kinds if x != "talk"), ""), "Talk")
                thumb = (f'<div class="thumb tile" aria-hidden="true"><span class="t-fmt">{e(fmt)}</span>'
                         f'<b>{e(str(date_key(k.get("date"))[0]))}</b><span class="t-line"></span><span class="t-place">{e(place)}</span></div>')
            badges = "".join([f'<span class="chip">{e(x.capitalize())}</span>' for x in kinds if x != "talk"]
                             + [f'<span class="chip hot">{len(k["photos"])} photo{"s" if len(k["photos"]) > 1 else ""}</span>' if k["photos"] else "",
                                '<span class="chip">LinkedIn</span>' if k.get("linkedin") else ""])
            summ = first_para(k["body"], 180)
            lis.append(f"""<li data-record data-kind="{' '.join(kinds)}"><a class="talk-row" href="{pg.rel('speaking/' + k['slug'] + '/index.html')}">
  <div><div class="tl-head"><h3>{e(k['title'])}</h3></div>
  <div class="tl-meta">{e(date_display(k.get('date')))} · {e(k.get('role', ''))}{(' · ' + e(k['city'])) if k.get('city') else ''}</div>
  <p class="tl-body">{e(k['event'])}</p>{f'<p class="tl-sum">{e(summ)}</p>' if summ else ''}<div class="chips">{badges}</div></div>{thumb}</a></li>""")
        parts.append(f'<div class="year-group" data-group><div class="year-mark">{y}</div><ol class="timeline" style="margin-bottom:12px">{"".join(lis)}</ol></div>')

    jump = '<nav class="jump mono" aria-label="On this page"><a href="#all-talks">All talks</a><a href="#events">Events in pictures</a><a href="#archive">Photo archive</a></nav>'
    body = page_head("02", "Thought Leadership", "Keynotes, panels, papers and executive round tables on AI factories, sovereign AI, AI economics and smart cities. Each event lists the date, city, role, what was discussed and where to read more.",
                     [], page_art(pg, "speaking")) + f"""
<main class="inner"><div class="wrap">{jump}
<div id="tl-results">
<div class="sec-head" id="all-talks"><span class="stop">→</span><h2>All keynotes, panels and talks</h2></div>
{"".join(parts)}
<div class="sec-head" id="events" style="margin-top:64px"><span class="stop">→</span><h2>Events in pictures</h2></div>
<div class="ev-grid" data-group>{"".join(events)}</div>
<div class="sec-head" id="archive" style="margin-top:64px"><span class="stop">→</span><h2>Photo archive</h2></div>
<div class="ev-grid" data-group>{"".join(archive)}</div>
<p class="empty" hidden>No talks match. Try a different word or clear the search.</p>
</div></div></main>"""
    return pg, layout(pg, "speaking", "Thought Leadership", f"Keynotes, panels and talks by {PROFILE['name']} on AI factories, sovereign AI and agentic AI, with photos and event details.", body)


def build_keynote(k):
    pg = Page(f"speaking/{k['slug']}/index.html")
    gallery = ""
    if k["photos"]:
        caps = k.get("captions") or {}
        cred = k.get("photo_credit") or ({"label": "Vinod Bijlani on LinkedIn", "url": k["linkedin"]} if k.get("linkedin") else {})
        n = len(k["photos"])
        gallery = (f'<h2 class="sub-h">Photos <span class="mono">· {n}</span></h2>'
                   + captioned_grid(pg, [(keynote_photo_rel(k, ph), caps.get(ph.name) or k["event"], k["event"], cred.get("label"), cred.get("url")) for ph in k["photos"]]))
    links = list(k.get("links") or [])
    if k.get("linkedin"):
        links.insert(0, {"label": "Read the LinkedIn post", "url": k["linkedin"]})
    btns = "".join(f'<a class="btn{" primary" if i == 0 else ""}" href="{e(l["url"])}">{e(l["label"])}</a>' for i, l in enumerate(links))
    related = [p for p in POSTS if k["slug"] in (p.get("keynotes") or [])]
    rel_html = ""
    if related:
        rel_html = '<h2 class="sub-h">Related blog posts</h2><ul class="rows">' + "".join(
            f'<li>{row(pg.rel("blog/" + p["slug"] + "/index.html"), f"<span class=mono>{e(date_display(p["date"]))}</span>", e(p["title"]))}</li>' for p in related) + "</ul>"
    art = ""
    if k["photos"]:
        cap = (k.get("captions") or {}).get(k["photos"][0].name) or k["event"]
        art = f'<figure class="head-art"><img src="photos/{e(k["photos"][0].name)}" alt="{e(cap)}" fetchpriority="high"></figure>'
    body = f"""<header class="page-head{' with-art' if art else ''}"><div class="wrap{' head-grid' if art else ''}"><div class="head-text">
  <div class="crumb"><a class="stop" href="{pg.rel(URLS['speaking'])}" aria-label="Back to thought leadership">←</a><span class="mono">{e(k.get('role', ''))} · {e(date_display(k.get('date')))}{(' · ' + e(k['city'])) if k.get('city') else ''}</span></div>
  <h1 class="h1-sm">{e(k['title'])}</h1>
  <p class="intro">{e(k['event'])}</p>
  {f'<div class="cta">{btns}</div>' if btns else ''}
</div>{art}</div></header>
<main class="inner"><div class="wrap"><div class="prose">{md(k['body'])}</div>{gallery}{rel_html}</div></main>"""
    img = keynote_photo_rel(k, k["photos"][0]) if k["photos"] else None
    return pg, layout(pg, "speaking", k["title"], f"{k['event']}: {k['title']}", body, img)


SERIES_NAME = "Data centre and AI factory leadership"
STRANDS = [
    ("buildout", "The global buildout", "Where data centre capacity sits today, where it is heading by 2030, and how much of the pipeline will actually be delivered."),
    ("factory", "Inside the AI factory", "From data halls to rack-scale AI: power, cooling, orchestration and the move to the edge."),
    ("economics", "The economics of AI factories", "What a token, a FLOP and a megawatt really cost, and where each workload should run."),
]


def post_visual(pg, p):
    """Infographic image if the post has one, otherwise a tile built from its infographic headline."""
    if p.get("image"):
        return f'<img class="pv" src="{pg.rel("blog/" + p["image"])}" alt="" loading="lazy">'
    ig = p.get("infographic") or {}
    stat = (ig.get("stat") or {}).get("value")
    if stat:
        inner = f'<span class="mono">{e(ig.get("title", "Infographic"))}</span><b>{e(str(stat))}</b>'
    else:
        inner = f'<span class="mono">Infographic</span><b class="sm">{e(ig.get("title", ""))}</b>'
    return f'<div class="pv pv-tile" aria-hidden="true">{inner}<span class="pv-line"></span></div>'


def build_blog_index():
    pg = Page("blog/index.html")
    series = [p for p in POSTS if p.get("series") == "dc"]
    strands = []
    for key, name, blurb in STRANDS:
        ps = sorted([p for p in series if p.get("strand") == key], key=lambda p: date_key(p["date"]))
        if not ps:
            continue
        cards = "".join(
            f'<a class="dc-card" href="{pg.rel("blog/" + p["slug"] + "/index.html")}">{post_visual(pg, p)}'
            f'<div class="body"><span class="mono">{e(date_display(p["date"]))}</span><h4>{e(p["title"])}</h4><p>{e(p.get("summary", ""))}</p></div></a>'
            for p in ps)
        strands.append(f'<div class="strand"><div class="strand-head"><h3>{e(name)}</h3><p>{e(blurb)}</p></div><div class="dc-grid">{cards}</div></div>')
    cats = []
    for i, (key, name, blurb) in enumerate(STRANDS):
        ps = sorted([p for p in series if p.get("strand") == key], key=lambda p: date_key(p["date"]), reverse=True)
        if not ps:
            continue
        lis = "".join(f'<li><a href="{pg.rel("blog/" + p["slug"] + "/index.html")}"><span class="mono">{e(date_display(p["date"]))}</span>{e(p["title"])}</a></li>' for p in ps)
        cats.append(f"""<article class="focus-card{' dark' if i == 0 else ''}">
  <div class="focus-top"><span class="focus-num mono">0{i + 1}</span><span class="mono">{len(ps)} posts</span></div>
  <h3>{e(name)}</h3><p>{e(blurb)}</p>
  <ul class="focus-list">{lis}</ul>
</article>""")
    hub = f"""<section id="data-centres">
  <div class="sec-head"><span class="stop">→</span><h2>{e(SERIES_NAME)}</h2></div>
  <p class="focus-note">Notes on the shift from data centres to AI factories, in three parts.</p>
  <div class="focus-grid three">{"".join(cats)}</div>
</section>"""
    rows = "".join(
        f'<li><a class="post-row" href="{pg.rel("blog/" + p["slug"] + "/index.html")}">'
        + f'<div><span class="mono">{e(date_display(p["date"]))}</span><h3>{e(p["title"])}</h3><p>{e(p.get("summary", ""))}</p>'
        + '<div class="chips">' + "".join(f"<span class=chip>{e(t)}</span>" for t in (p.get("tags") or [])[:3]) + '</div></div>'
        + post_visual(pg, p) + '</a></li>' for p in POSTS)
    body = page_head("03", "Blog", "Field notes from customer conversations, conferences and the AI infrastructure build-out, each with an infographic summary.",
                     [(len(POSTS), "posts"), (len([q for q in POSTS if q.get("series") == "dc"]), "on data centres and AI factories")], page_art(pg, "blog"),
                     '<span class="mono">Themes</span>' + " · ".join(f'<a href="#data-centres">{e(name)}</a>' for _, name, _ in STRANDS)) + \
        f'<main class="inner"><div class="wrap">{hub}<div class="sec-head" style="margin-top:64px"><span class="stop">→</span><h2>All posts</h2></div><ul class="post-list">{rows}</ul></div></main>'
    return pg, layout(pg, "blog", "Blog", f"Blog posts by {PROFILE['name']} on data centres, AI factories, token economics, sovereign AI and governance.", body)


def build_post(p):
    pg = Page(f"blog/{p['slug']}/index.html")
    tags = "".join(f'<span class="chip">{e(t)}</span>' for t in (p.get("tags") or []))
    related = list(p.get("related") or [])
    if p.get("linkedin"):
        related.insert(0, {"label": "Discuss on LinkedIn", "url": p["linkedin"]})
    rel = ""
    if related:
        rel = '<div class="post-links"><span class="mono">Read more</span>' + "".join(f'<a href="{e(l["url"])}">{e(l["label"])} ↗</a>' for l in related) + "</div>"
    side_image = ""
    if p.get("image"):
        src = pg.rel("blog/" + p["image"])
        side_image = (f'<figure class="ig-figure"><a href="{src}" data-lightbox><img src="{src}" alt="{e(p.get("image_alt", p["title"]))}"></a>'
                      f'<figcaption class="mono">Infographic · tap to enlarge</figcaption></figure>')
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
  {f'<a class="series-link" href="{pg.rel(URLS["blog"])}#data-centres">Part of the series: {e(SERIES_NAME)} →</a>' if p.get("series") == "dc" else ''}
</div></header>
<main class="inner"><div class="wrap"><div class="post-grid">
  <article class="prose">{md(p['body'])}{rel}</article>
  <div class="side-col{' has-image' if p.get('image') else ''}">{side_image}{infographic(p.get('infographic'))}</div>
</div>{pager}</div></main>"""
    return pg, layout(pg, "blog", p["title"], p.get("summary", p["title"]), body, ("blog/" + p["image"]) if p.get("image") else None)


FEATURED_OUTLETS = ["World Economic Forum", "Forbes", "The Business Times (Singapore)", "Singapore Business Review", "CDOTrends", "Forbes Brasil"]


def build_publications():
    pg = Page("publications.html")
    topics = {}
    for a in ARTICLES:
        topics[a["topic"]] = topics.get(a["topic"], 0) + 1
    topics = dict(sorted(topics.items(), key=lambda t: -t[1]))
    buttons = f'<button type="button" aria-pressed="true" data-topic="all">All<span>{len(ARTICLES)}</span></button>' + "".join(
        f'<button type="button" aria-pressed="false" data-topic="{e(t)}">{e(t)}<span>{n}</span></button>' for t, n in topics.items())
    label = {"article": "Article", "panel": "Expert panel", "interview": "Interview", "whitepaper": "Whitepaper"}
    rows = "".join(
        f'<li data-topic="{e(a["topic"])}">' + row(a.get("url", ""),
            f'<span class="mono">{e(a["outlet"])} · {e(date_display(a["date"]))}</span><span class="chips"><span class="chip{" hot" if a.get("type") == "article" and a["outlet"].startswith("Forbes") else ""}">{label.get(a.get("type"), "Article")}</span></span>',
            e(a["title"]), e(a.get("note", ""))) + "</li>" for a in ARTICLES)
    outlets = len({a["outlet"] for a in ARTICLES})
    # Spotlight: AI factories and sovereign AI, the two themes of the body of work
    forbes_all = [a for a in ARTICLES if a["outlet"] == "Forbes"]
    forbes_articles = [a for a in forbes_all if a.get("type") == "article"]
    focus_defs = [
        ("ai-factories", "AI Factories", "How enterprises build, run and pay for AI factories: architecture, hybrid placement, security and the economics of tokens, data and FLOPs."),
        ("sovereign-ai", "Sovereign AI", "Why nations and enterprises want control over their data, models and AI operations, and a practical path from AI dependence to AI sovereignty."),
    ]
    cards = []
    for i, (key, name, blurb) in enumerate(focus_defs):
        items = [a for a in ARTICLES if a.get("focus") == key]
        lis = "".join(f'<li><a href="{e(a["url"])}"><span class="mono">{e(a["outlet"])} · {e(date_display(a["date"]))}</span>{e(a["title"])}</a></li>' for a in items[:6])
        if len(items) > 6:
            lis += f'<li class="more"><a href="#all-publications">{len(items) - 6} more in the full list ↓</a></li>'
        cards.append(f"""<article class="focus-card{' dark' if i == 0 else ''}">
  <div class="focus-top"><span class="focus-num mono">0{i + 1}</span><span class="mono">{len(items)} publications</span></div>
  <h3>{e(name)}</h3><p>{e(blurb)}</p>
  <ul class="focus-list">{lis}</ul>
</article>""")
    spotlight = (f'<div class="sec-head"><span class="stop">→</span><h2>Focus areas</h2></div>'
                 f'<p class="focus-note">Most of this writing appears in Forbes, where Vinod is a member of the Forbes Technology Council: {len(forbes_articles)} articles and {len(forbes_all) - len(forbes_articles)} expert panels. '
                 f'<a href="{e(PROFILE["links"]["forbes"])}">Forbes profile ↗</a></p>'
                 f'<div class="focus-grid two">{"".join(cards)}</div>')
    for wp in [a for a in ARTICLES if a.get("type") == "whitepaper"]:
        spotlight += (f'<article class="wp-card"><div><span class="mono">Whitepaper · {e(wp["outlet"])} · {e(date_display(wp["date"]))}</span>'
                      f'<h3>{e(wp["title"])}</h3><p class="wp-authors">{e(wp.get("authors", ""))}</p><p>{e(wp.get("summary", ""))}</p></div>'
                      f'<div class="wp-side"><ul>' + "".join(f"<li>{e(x)}</li>" for x in wp.get("covers", [])) + '</ul>'
                      f'<div class="cta" style="margin-top:0"><a class="btn primary" href="{e(wp["url"])}">Read the whitepaper ↗</a>'
                      + (f'<a class="btn" href="{e(wp["related"]["url"])}">Read on CDOTrends ↗</a>' if wp.get("related") else "") + '</div></div></article>')
    body = page_head("04", "Publications", "Articles and expert panels on AI factories and sovereign AI for the Forbes Technology Council, CDOTrends, The Business Times and more.",
                     [(len(ARTICLES), "publications"), (N_FORBES, "Forbes articles")], page_art(pg, "publications"),
                     '<span class="mono">Published in</span>' + " · ".join(e(o) for o in FEATURED_OUTLETS) + f" and {outlets - len(FEATURED_OUTLETS)} more") + \
        f'<main class="inner"><div class="wrap">{spotlight}<div class="sec-head" id="all-publications" style="margin-top:64px"><span class="stop">→</span><h2>All publications</h2></div><p class="note" style="margin:0 0 24px"><strong>Looking for the blog?</strong> Posts written for this site are on the <a href="{pg.rel(URLS["blog"])}">blog</a>.</p><div class="filters" role="group" aria-label="Filter by topic">{buttons}</div><ul class="rows" data-filterable>{rows}</ul></div></main>'
    return pg, layout(pg, "publications", "Publications", f"Articles by {PROFILE['name']} for the World Economic Forum, Forbes, CDOTrends and more.", body)


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
    body = page_head("05", "Books", "A playbook on sovereign AI, and invited chapters on smart and sustainable buildings, resilient smart cities, health and STEM education.",
                     [(n_books, "book"), (len(BOOKS) - n_books, "chapters"), (len({b["publisher"] for b in BOOKS if b.get("publisher") and "Self" not in b["publisher"]}), "academic publishers")], f'<figure class="head-art natural"><a href="https://www.amazon.com/dp/B0GS7C6DN4"><img src="{pg.rel("assets/img/own-your-ai-cover.webp")}" alt="Own Your AI: The Sovereign Stack Playbook for Nations and Enterprises, by Prem Naraindas and Vinod Bijlani"></a></figure>') + \
        f'<main class="inner"><div class="wrap"><div class="grid2">{"".join(cards)}</div></div></main>'
    return pg, layout(pg, "books", "Books", f"Books and chapters by {PROFILE['name']}, including Own Your AI.", body)


def build_papers():
    pg = Page("papers.html")
    rows = "".join(f'<li>{row(p.get("url", ""), f"<span class=mono>{e(date_display(p["date"]))}</span>", e(p["title"]), e(p["venue"]))}</li>' for p in PAPERS)
    body = page_head("06", "Papers", "Conference and journal papers on smart buildings, net zero, 5G traffic management and intelligent transport.",
                     [(len(PAPERS), "papers"), (sum(1 for q in PAPERS if "IEEE" in q["venue"]), "IEEE"), (len({str(q["date"])[:4] for q in PAPERS}), "years published")], page_art(pg, "papers")) + \
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
    body = page_head("07", "Patents", f"AI, machine learning and data analytics inventions since {AI_SINCE}: smart transportation, retail, interactive media and networks, filed with IBM from {FIRST_FILING} to {LAST_FILING}. IBM Master Inventor.",
                     [], f'<figure class="head-art patent-art" aria-hidden="true"><div class="pa-lead"><b>Since {AI_SINCE}</b><span>inventing in AI, machine learning and analytics</span></div><div><b>{N_FILINGS}</b><span>patent filings</span></div><div><b>{N_INVENTIONS}</b><span>inventions</span></div><div><b>{len(OFFICES)}</b><span>patent offices</span></div><p class="mono">IBM Master Inventor · {" · ".join(OFFICES)}</p></figure>') + \
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
    body = page_head("?", "Page not found", f'The page you were looking for has moved. Try <a href="/speaking/">Thought Leadership</a>, the <a href="/blog">blog</a> or <a href="/">the home page</a>.', [])
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
    pages += [build_photo_group(n, items) for n, items in GALLERY_GROUPS.items()]
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

    if (CONTENT / "gallery").exists():
        shutil.copytree(CONTENT / "gallery", OUT / "gallery", dirs_exist_ok=True)
    if (CONTENT / "blog" / "media").exists():
        shutil.copytree(CONTENT / "blog" / "media", OUT / "blog" / "media", dirs_exist_ok=True)
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
