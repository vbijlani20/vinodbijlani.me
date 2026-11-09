#!/usr/bin/env python3
"""Pull new keynotes and blog posts from Google Drive into ./content.

Drive layout (create once, share the top folder with the service account's email as Viewer):

    Website/
      Keynotes/
        2026-11 HPE Discover Sydney/          <- one folder per talk, name starts with YYYY-MM or YYYY-MM-DD
          notes  (Google Doc or .txt)        <- optional, see below
          photo1.jpg, photo2.jpg ...         <- any number of photos
      Blog/
        <Google Docs>                        <- paste a LinkedIn post into a Doc; first line becomes the title

notes format (all lines optional; anything after the blank line is the description):

    Title: Building a secure, sovereign and agentic AI factory
    Role: Keynote
    City: Sydney
    LinkedIn: https://www.linkedin.com/posts/...

    Two or three lines about the talk.

Environment:
    GOOGLE_SERVICE_ACCOUNT_JSON   the service account key (JSON text)
    DRIVE_WEBSITE_FOLDER_ID       id of the Website folder
Run:  python scripts/sync_drive.py         (add --dry-run to only print what would change)
"""
import io, json, os, re, sys
from datetime import date, datetime
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
import textkit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
STATE = CONTENT / ".drive-sync.json"
DRY = "--dry-run" in sys.argv
PHOTO_MAX = 1800          # longest side in pixels
PHOTO_QUALITY = 82
MAX_PHOTOS_PER_TALK = 12  # keeps the repository well under GitHub Pages' 1 GB limit
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/heic", "image/heif")

try:  # HEIC photos straight from an iPhone
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def drive():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def children(svc, folder_id):
    out, token = [], None
    while True:
        r = svc.files().list(q=f"'{folder_id}' in parents and trashed = false", pageSize=200, pageToken=token,
                             fields="nextPageToken, files(id, name, mimeType, modifiedTime, createdTime)").execute()
        out += r.get("files", [])
        token = r.get("nextPageToken")
        if not token:
            return out


def find(items, name):
    return next((i for i in items if i["name"].strip().lower() == name.lower() and i["mimeType"].endswith("folder")), None)


def download(svc, f):
    from googleapiclient.http import MediaIoBaseDownload
    if f["mimeType"] == "application/vnd.google-apps.document":
        req = svc.files().export_media(fileId=f["id"], mimeType="text/plain")
    else:
        req = svc.files().get_media(fileId=f["id"])
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return buf.getvalue()


def save_photo(raw: bytes, dest: Path):
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    im.thumbnail((PHOTO_MAX, PHOTO_MAX))
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=PHOTO_QUALITY, optimize=True, progressive=True)


def parse_notes(text: str):
    text = textkit.clean(text)
    meta, desc = {}, []
    head, _, rest = text.partition("\n\n")
    for line in head.split("\n"):
        k, sep, v = line.partition(":")
        if sep and k.strip().lower() in ("title", "role", "city", "event", "linkedin", "date", "video"):
            meta[k.strip().lower()] = v.strip()
        else:
            desc.append(line)
    desc = "\n".join(desc + ([rest] if rest else [])).strip()
    return meta, desc


def folder_date(name):
    m = re.match(r"(\d{4})[-_. ](\d{1,2})(?:[-_. ](\d{1,2}))?", name)
    if not m:
        return None, name
    y, mo, d = m.group(1), int(m.group(2)), m.group(3)
    rest = name[m.end():].strip(" -_,")
    return (f"{y}-{mo:02d}-{int(d):02d}" if d else f"{y}-{mo:02d}"), rest


def sync_keynotes(svc, folder, state, log):
    for talk in children(svc, folder["id"]):
        if not talk["mimeType"].endswith("folder"):
            continue
        when, name = folder_date(talk["name"])
        if not when:
            log.append(f"skip keynote folder without a date prefix: {talk['name']}")
            continue
        known = state["keynotes"].get(talk["id"], {})
        slug = known.get("slug") or f"{when[:7]}-{textkit.slugify(name, 50)}"
        kdir = CONTENT / "keynotes" / slug
        files = children(svc, talk["id"])
        notes = next((f for f in files if f["mimeType"] == "application/vnd.google-apps.document" or f["name"].lower().endswith((".txt", ".md"))), None)

        index = kdir / "index.md"
        notes_stamp = notes["modifiedTime"] if notes else ""
        if not index.exists() or known.get("notes") != notes_stamp:
            meta, desc = parse_notes(download(svc, notes).decode("utf-8", "replace")) if notes else ({}, "")
            city = meta.get("city", "")
            if not city and "," in name:
                name, city = [x.strip() for x in name.rsplit(",", 1)]
            fm = {"title": meta.get("title") or name, "event": meta.get("event") or name, "date": meta.get("date") or when,
                  "city": city, "role": meta.get("role", "Speaker")}
            if meta.get("linkedin"):
                fm["linkedin"] = meta["linkedin"]
            if meta.get("video"):
                fm["links"] = [{"label": "Watch the session", "url": meta["video"]}]
            log.append(f"{'update' if index.exists() else 'new'} talk: {slug}")
            if not DRY:
                kdir.mkdir(parents=True, exist_ok=True)
                index.write_text(textkit.front_matter(fm, desc), encoding="utf-8")

        have = set(known.get("photos", []))
        photos = [f for f in files if f["mimeType"] in IMAGE_TYPES][:MAX_PHOTOS_PER_TALK]
        n_existing = len(list((kdir / "photos").glob("*.jpg"))) if (kdir / "photos").exists() else 0
        for f in photos:
            if f["id"] in have:
                continue
            n_existing += 1
            dest = kdir / "photos" / f"{n_existing:02d}.jpg"
            log.append(f"  + photo {dest.relative_to(ROOT)} ({f['name']})")
            if not DRY:
                save_photo(download(svc, f), dest)
            have.add(f["id"])
        state["keynotes"][talk["id"]] = {"slug": slug, "notes": notes_stamp, "photos": sorted(have)}


def sync_blog(svc, folder, state, log):
    files = children(svc, folder["id"])
    # An image with the same name as a Doc (e.g. "Datanomics.gif" next to the Doc "Datanomics") becomes that post's infographic
    images = {Path(f["name"]).stem.strip().lower(): f for f in files if f["mimeType"] in IMAGE_TYPES + ("image/gif",)}
    for f in files:
        if f["mimeType"] != "application/vnd.google-apps.document" and not f["name"].lower().endswith((".txt", ".md")):
            continue
        if f["id"] in state["blog"]:
            continue  # imported once; after that the Markdown file in GitHub is the master copy
        text = download(svc, f).decode("utf-8", "replace")
        linkedin = ""
        m = re.search(r"https://www\.linkedin\.com/posts/vinodbijlani\S+", text)
        if m and text.strip().lower().startswith("linkedin:"):
            linkedin, text = m.group(0), text.split("\n", 1)[1]
        when = datetime.fromisoformat(f["createdTime"].replace("Z", "+00:00")).date()
        name, content = textkit.blog_post(text, when, linkedin)
        img = images.get(Path(f["name"]).stem.strip().lower())
        if img:
            ext = ".gif" if img["mimeType"] == "image/gif" else ".jpg"
            media = CONTENT / "blog" / "media" / (name[:-3] + ext)
            log.append(f"  + infographic {media.relative_to(ROOT)}")
            if not DRY:
                media.parent.mkdir(parents=True, exist_ok=True)
                raw = download(svc, img)
                media.write_bytes(raw) if ext == ".gif" else save_photo(raw, media)
            content = content.replace("\ntags:", f"\nimage: media/{media.name}\ntags:", 1)
        dest = CONTENT / "blog" / name
        log.append(f"new post: {dest.relative_to(ROOT)}")
        if not DRY:
            dest.write_text(content, encoding="utf-8")
        state["blog"][f["id"]] = name


def main():
    state = json.loads(STATE.read_text()) if STATE.exists() else {"keynotes": {}, "blog": {}}
    svc = drive()
    top = children(svc, os.environ["DRIVE_WEBSITE_FOLDER_ID"])
    log = []
    if (k := find(top, "Keynotes")):
        sync_keynotes(svc, k, state, log)
    if (b := find(top, "Blog")):
        sync_blog(svc, b, state, log)
    if not DRY:
        STATE.write_text(json.dumps(state, indent=2, sort_keys=True))
    print("\n".join(log) or "Nothing new in Drive.")
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a") as fh:
            fh.write("### Drive sync\n\n" + ("\n".join(f"- {l}" for l in log) or "Nothing new.") + "\n")


if __name__ == "__main__":
    main()
