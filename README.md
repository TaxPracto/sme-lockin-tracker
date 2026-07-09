# 🔓 Unlock Radar — SME IPO Anchor Lock-in Tracker

A self-hosted tracker for **30-day and 90-day anchor investor lock-in expiries** on Indian SME IPOs
(BSE SME + NSE Emerge), with mainboard as an optional toggle.

Every morning at **07:00 IST**, GitHub Actions:
1. pulls the latest lock-in dates (`scraper.py`, source: Chittorgarh report #156)
2. rebuilds the dashboard, calendar feed and raw JSON (`build_site.py` → `docs/`)
3. commits the refreshed site (served free by GitHub Pages)
4. emails the morning digest to you (`send_email.py`, via your Gmail app password)

**Cost: ₹0.** Runs entirely on GitHub's free tier (~1 min/day of the 2,000 free minutes/month).

---

## One-time setup (~15 minutes)

### 1. Create the repo
- Log in to github.com → **New repository**
- Name: `sme-lockin-tracker` (anything works) · Visibility: **Public** (required for free GitHub Pages)
- Upload every file in this folder (drag & drop works: "uploading an existing file" link).
  Keep the folder structure — especially `.github/workflows/daily.yml`.

### 2. Turn on GitHub Pages
- Repo → **Settings → Pages**
- "Build and deployment" → Source: **GitHub Actions**
- (that is all — no branch/folder to pick)
- Your dashboard URL: `https://<username>.github.io/sme-lockin-tracker/` (live in ~2 min; shareable with anyone)

### 3. Create a Gmail app password (for the digest email)
- Google Account → Security → turn on **2-Step Verification** (if not already on)
- Visit **myaccount.google.com/apppasswords** → create one named `unlock-radar` → copy the 16-char password

### 4. Add the secrets
- Repo → **Settings → Secrets and variables → Actions → New repository secret**, add:

| Secret name | Value |
|---|---|
| `GMAIL_ADDRESS` | your@gmail.com |
| `GMAIL_APP_PASSWORD` | the 16-char app password |
| `DIGEST_TO` | *(optional)* comma-separated recipients; defaults to GMAIL_ADDRESS |

### 5. First run
- Repo → **Actions** tab → enable workflows if prompted
- Open **daily-unlock-radar** → **Run workflow** → wait ~1 min
- Check: dashboard URL updates, digest lands in your inbox 📬
- From tomorrow it runs automatically at 07:00 IST. If a run ever fails, GitHub emails you the failure notice automatically.

### Bonus: lock-ins inside Google Calendar
Google Calendar → Other calendars → **+ → From URL** →
`https://<username>.github.io/sme-lockin-tracker/lockins.ics`
Every future unlock shows up as an all-day event and refreshes automatically.

---

## Files

| File | Role |
|---|---|
| `scraper.py` | Fetches current + previous year lock-in data → `data/lockins.json` |
| `build_site.py` | Renders `docs/index.html` (dashboard), `docs/lockins.ics`, `docs/data.json` |
| `send_email.py` | Sends the morning digest (`--preview` writes `email_preview.html` instead) |
| `.github/workflows/daily.yml` | The 07:00 IST daily schedule |
| `make_sample.py`, `sample_raw/` | Dev-only: offline sample data from 2026-07-08 capture (safe to delete) |

## Notes & caveats
- **50% of anchor shares** release at each of the two dates; ₹ values are **estimated at issue price**, not market price.
- Dates come from Chittorgarh's published expiry dates (computed off basis-of-allotment); the odd ±1-day
  shift around exchange holidays is possible — treat dates as strong guidance, verify before acting.
- Very new IPOs can briefly show "—" for shares/value until the source fills in anchor details.
- If Chittorgarh changes their API shape, the scraper fails loudly (and GitHub emails you) instead of
  publishing wrong data.
- For research & information only — **not investment advice**.
