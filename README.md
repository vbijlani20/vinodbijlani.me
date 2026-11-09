# vinodbijlani.me

Personal website of Vinod Bijlani, hosted free on GitHub Pages and updated automatically.

## How updates work

| You want to add… | Do this | Goes live |
|---|---|---|
| **A keynote or panel, with photos** | In Google Drive, open `Website/Keynotes`, create a folder named `2026-11 Event name, City`, and drop the photos in. Optionally add a Doc called `notes` (format below). | Next Tuesday morning, or straight away if you click **Run workflow** under *Actions → Sync from Google Drive* |
| **A blog post from LinkedIn** | Paste the post into a new Google Doc in `Website/Blog`. To link back to LinkedIn, make the first line `LinkedIn: <post URL>`. | Same as above. The infographic beside the post is built automatically from its bullet points and numbers. |
| **A Forbes or other article** | Add one line to `content/articles.yml` (copy the line above it). You can do this on github.com or in the GitHub phone app. | About 1 minute after saving |
| **Anything else** | Edit the matching file in `content/`. | About 1 minute after saving |

Or simply ask Claude: *"Add my keynote at X to the website, here are the photos"*. It edits these same files.

### `notes` Doc for a talk (every line is optional)

```
Title: Building a secure, sovereign and agentic AI factory
Role: Keynote
City: Taipei
LinkedIn: https://www.linkedin.com/posts/vinodbijlani_...
Video: https://www.youtube.com/watch?v=...

Two or three sentences about the talk. These appear on the talk's page.
```

Photos are resized to 1,800 px and compressed automatically (iPhone HEIC works too). Up to 12 per talk.

## What's where

```
content/
  profile.yml          name, title, bio, links, the career line on the home page
  experience.yml       roles, each with the projects delivered in it
  articles.yml         articles published elsewhere (Forbes, CDOTrends …)
  books.yml  papers.yml  patents.yml
  keynotes/<talk>/index.md      one folder per talk; photos in keynotes/<talk>/photos/
  blog/<date>-<title>.md        blog posts; `infographic:` in the header drives the side panel
assets/                site.css, site.js
build.py               turns content/ into the website (in _site/)
scripts/
  sync_drive.py               the weekly Google Drive import
  import_linkedin_export.py   one-off import of your LinkedIn data export as draft posts
.github/workflows/
  deploy.yml           builds and publishes on every change
  sync-drive.yml       weekly Drive import, then publish
```

Old Wix addresses (`/roles`, `/projects`, `/certifications`, `/letter-of-appreciation`) redirect to the new pages, and `/speaking`, `/publications`, `/papers`, `/books`, `/patents` keep their addresses.

### Blog infographics

Each post can describe its own side panel. Four layouts are available:

```yaml
infographic:
  type: steps        # steps | stats | compare | bars
  title: Four placements for hybrid AI
  stat: {value: "~120 kW", label: per rack}      # optional headline number
  items:
    - {label: Hyperscaler, text: The generalist}
```

`stats` takes `items: [{value, label}]`; `compare` takes `columns: [{heading, sub, items: []}]`; `bars` takes `items: [{label, value}]` with `min`/`max`.

## One-time setup

1. **Create the repository.** On github.com create a repository named `vinodbijlani.me` and upload these files (or push them with git).
2. **Turn on Pages.** *Settings → Pages → Build and deployment → Source: GitHub Actions.* The first build runs automatically.
3. **Custom domain.** *Settings → Pages → Custom domain:* `www.vinodbijlani.me`, then tick *Enforce HTTPS* once the certificate is ready. At your domain registrar set:
   - `www` → CNAME → `<your-github-username>.github.io`
   - apex `vinodbijlani.me` → A records `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`
4. **Google Drive sync** (optional but recommended):
   1. In Google Cloud Console create a project, enable the **Google Drive API**, create a **service account**, and download a JSON key.
   2. In Drive create `Website/Keynotes` and `Website/Blog`, and share the `Website` folder with the service account's email address as **Viewer**.
   3. In GitHub: *Settings → Secrets and variables → Actions → New repository secret*:
      - `GOOGLE_SERVICE_ACCOUNT_JSON` = the whole contents of the JSON key
      - `DRIVE_WEBSITE_FOLDER_ID` = the ID from the `Website` folder's URL (`drive.google.com/drive/folders/<ID>`)
   4. *Actions → Sync from Google Drive → Run workflow* to test.

## Build locally

```
pip install -r requirements.txt
python build.py
open _site/index.html
```
