# CLAUDE.md — living context for the SME IPO Unlock Radar

> THIS FILE IS THE CURRENT STATE OF THE PROJECT. Any Claude session working on this repo:
> (1) read this file FIRST, (2) after shipping changes, UPDATE this file in the same session
> (new rules, new pitfalls, new pages/features, backlog changes) and commit it alongside the code.
> Pushing .md files does NOT trigger the daily workflow or the email — safe to commit anytime.

# SME IPO Unlock Radar — project brain

Self-owned, Rs.0-cost tracker of SME IPO lock-in expiries (anchor 30D/90D, pre-IPO 6M, promoter 1Y/2Y).
Runs itself daily at 07:00 IST via GitHub Actions: scrape -> registry -> prices -> outcomes -> build 3-page site -> deploy to GitHub Pages -> email digest.

- Live site: https://taxpracto.github.io/sme-lockin-tracker/ (+ anchors.html, backtest.html, lockins.ics, data.json)
- Repo: https://github.com/TaxPracto/sme-lockin-tracker (account: TaxPracto)
- Email digest goes ONLY to ashwani.adac@gmail.com. NEVER add other recipients.

## Non-negotiable security rules
1. Claude NEVER sees or handles the Gmail app password. It lives only in GitHub Actions secrets (GMAIL_ADDRESS, GMAIL_APP_PASSWORD, DIGEST_TO). If it must change, Ashwani pastes it himself at github.com/TaxPracto/sme-lockin-tracker/settings/secrets/actions.
2. No HTTP fetching from the sandbox via bash/python (curl, requests etc. are blocked policy). Use web_fetch tool, or better: remember the RUNNER fetches everything — Claude usually only edits code.
3. Not investment advice — every page keeps that disclaimer.

## Architecture (all files in repo root)
| file | role |
|---|---|
| scraper.py | Chittorgarh report 156 (anchor lock-in dates, years Y-2..Y) + per-IPO meta (shareholding regex, cap 250/run, cached data/ipo_meta.json). Builds events A30/A90/PRE6M/PX1Y/PX2Y -> data/lockins.json |
| registry_feed.py | fund-house registry crawl 133 -> 190 -> 134 (SME variant). Writes data/registry.json {houses: {name: {id, deals: {slug: {inv,sh,lg,cg}}, years}}}. Report 190 entity id goes in the LAST URL segment. Past years (2024-25) capped at top-5 per year by source paywall — cannot fix free, documented as Coverage note on anchors page |
| price_feed.py | BSE/NSE UDiFF bhavcopies by ISIN, walk back <=6 days, rolling 30 sessions -> data/prices.json {isin: [[date, close, vol]]} |
| backfill.py | one-shot price history from 2024-06-01 -> data/history.json. Re-trigger by pushing any edit to backfill.py (workflow paths filter) |
| outcomes.py | per past event: pre_close, ret1/ret5/ret20, runup20, dov_ev, pl_at_unlock -> data/outcomes.json keyed "slug|TYPE" |
| build_site.py | THE BIG ONE. Generates docs/index.html (radar), docs/anchors.html, docs/backtest.html, lockins.ics, data.json. Python head computes merges + stats; giant HTML template with placeholders __DATA__ __STATS__ __OUTS__ __FUNDS__ __REG__ __GENERATED__; anchors/backtest pages are f-strings (DOUBLE braces for CSS) + _ANCH_JS plain string (single braces, has __FD__ placeholder) |
| send_email.py | Gmail SMTP 465, strips spaces from app password, --preview mode exists |
| .github/workflows/daily.yml | cron 30 1 * * * (=07:00 IST) + workflow_dispatch + push paths ['*.py', '.github/workflows/*.yml']. Steps: scraper->registry->prices->outcomes->build->git commit data/+docs (git pull --rebase || true)->deploy-pages->email. Pages source = GitHub Actions, concurrency group "pages" |
| .github/workflows/backfill.yml | dispatch + push paths ['backfill.py'] |

## Locked product rules (do not re-litigate)
- SEBI ICDR: anchor 50% @30d + 50% @90d; SME 20% MPC locked 3yr; promoter excess: listings >= 2025-03-08 phased 50% @1yr + 50% @2yr, older 100% @1yr (REGIME_CUTOFF); pre-IPO non-promoter 6M from allotment. est. dates = computed, flagged "est."
- Issue price derived: anchor_investment_cr*1e7 / anchor_shares.
- dov (days-of-volume) = unlocking shares / avg daily volume. Buckets: <1x green, 1-5x amber, >5x red.
- Fund score = 50 + 2.5*clamp(medRet5,+/-10) - 0.3*(pctNeg-50) - 1.2*max(avgDov-3,0) - 0.05*max(avgRunup-25,0) + min(deals,10)*0.5. STICKY >=60, FLIPPER <45, min 3 measured unlocks to grade. Components exposed per fund in FDATA (anchors overlay).
- Score replay (anchors page, added 2026-07-15): each fund's score is rebuilt after every measured unlock in date order via _replay(); experience bonus held CONSTANT at today's value so the trail's last point equals the table score exactly. Per-unlock "points" = delta vs the previous replay point (first event = "start"). Momentum ("trend 90d") = last replay score minus replay score as of (today - 90 days); funds with zero events before the cutoff show "new", |mom| < 0.05 shows 0.0. Movers strip = top-5 risers / top-5 slippers with |mom| >= 0.5, "new" funds excluded. FDATA per fund carries ev[{d,co,t,r5,sc,dl}], mom, nw, pend[] (registry deals with no measured unlock yet, names via _slug_pretty).
- Language: plain non-math English everywhere ("typical move", "fell how often", "out of 100"). Percentages carry % signs. Every stats page shows its date window (_WINDOW) and the "more events watched = more trust, under ~20 = hint" rule.
- UI: light theme (#F7F5F0 bg, Fraunces headings, Instrument Sans body, IBM Plex Mono numbers). Wide layout 1360px; anchors = movers strip (2 cards, click -> fund history) + table + sticky right rail of explainer cards; backtest = 2-col grid of 4 question-framed tables. Radar: This week -> Pressure board (top-6 dov <=90d) -> Just passed (last 30d with ret5 chips, opens modal on History tab) -> Horizon slider 15-180d -> ledger. Company modal: stats grid, capital bar, timeline, anchor chips (x n serial tags), UPCOMING/HISTORY tabs (history = close-before + ret1/5/20 boxes + benchmark-vs-typical line from STATS), QTY/DATE math per upcoming event. Anchors page: sortable headers (click, gold arrows; "trend 90d" is the last column, "new"/em-dash sort as null), search box, verdict pills, "only well-tested 10+" checkbox, fund-name click -> overlay with TWO TABS: "how the score is built" (srow breakdown + stot) and "IPO history & trend" (score-trail SVG sparkline w/ dashed line at 50, newest-first unlock rows date·IPO·30D/90D·week-after·score·points-delta, pending-deals fnote, momentum line).
- Trend column cells format "+4.2 ▲" / "-3.1 ▼" (ASCII minus, arrow AFTER number) so the existing val() parseFloat sort keeps working.

## Change workflow (proven, follow exactly)
1. Work in sandbox: /sessions/<session>/mnt/outputs/sme-lockin-tracker/ (bash heredocs / python replace with assert count==1; the Write tool often fails on this nested path).
2. If sandbox copy missing: fetch raw.githubusercontent.com/TaxPracto/sme-lockin-tracker/main/build_site.py etc. via web_fetch (large files land in a tool-results txt — delegate byte-exact reconstruction to a general-purpose subagent: it Reads the tool-results file in chunks, strips the 4-line web_fetch header + line-number prefixes, writes via quoted heredocs, verifies ast.parse + line count. Watch chunk-boundary blank lines and keep literal backslash-u sequences as-is). Data files in sandbox are STALE STUBS — real data lives on the runner; never conclude "data missing" from local files.
3. After every edit: python3 -c "import ast; ast.parse(open('build_site.py').read())" then python3 build_site.py and probe docs/*.html with asserts. For JS changes, ALSO smoke-test with jsdom in the sandbox (npm install jsdom; JSDOM(html, {runScripts:'dangerously'}), simulate clicks, assert overlay/tab/sort behaviour) — python probes cannot catch JS runtime errors.
4. Deploy via Chrome (no git in sandbox): navigate github.com/TaxPracto/sme-lockin-tracker/upload/main -> read_page -> file_upload with the WINDOWS path C:\Users\ASHWANI\...\outputs\sme-lockin-tracker\build_site.py -> form_input commit summary -> submit via javascript: [...document.querySelectorAll('button[type=submit]')].find(b=>b.textContent.trim()==='Commit changes') then btn.closest('form').requestSubmit(btn). Coordinate clicks are flaky; requestSubmit is not.
5. Verify commit landed: navigate commits/main and check the message appears.
6. Push to *.py triggers the FULL daily workflow including the digest email (mention to Ashwani when multiple deploys happen in a day). Deploy takes ~2.5-4 min. GitHub outages happen — re-trigger by pushing a comment-line bump.
7. Verify LIVE with javascript_tool on the pages (location.reload(true) first — Pages caches hard; tell Ashwani Ctrl+Shift+R). Screenshot for visual changes.
8. Chrome tabs die if Chrome restarts: list_connected_browsers -> tabs_context_mcp createIfEmpty:true.

## Code pitfalls (each cost a debugging round once)
- f-string pages: CSS braces must be doubled {{ }}; backslashes FORBIDDEN in f-string expressions (reword instead); define variables (like _WINDOW) BEFORE first f-string use.
- Text inserted into build_site.py source becomes Python string content: \25b2 parses as OCTAL escape garbage — use literal unicode arrows/symbols instead of escapes.
- _ANCH_JS is a plain """string""" appended after the anchors f-string, with .replace("__FD__", json.dumps(_FDATA)) at concat time. New anchors-page JS/CSS goes THERE (single braces OK). No backslashes in new JS (it lives inside a Python string) — no regex literals with \, use literal unicode chars.
- Share-count regex must match comma-grouped numbers WITHOUT "shares" suffix (raw HTML has <!-- --> between).
- Fund names normalize via .title() — causes "Hdfc Bank", "Ccv" cosmetics (known, accepted). Registry house keys title-case-match _fund_obs keys; _reg_tc re-normalizes defensively.
- outcomes keys "slug|TYPE"; ret5 fallback field ret5_pct (_r5 helper handles both).
- Every IPO = TWO anchor unlocks (30D+90D): "unlocks watched" can exceed "IPOs anchored" — explained on page, don't "fix".
- jpast rows: recent (<5 sessions) correctly show "syncing" — not a bug.
- anchors sort val(): any non-numeric cell text must be added to the null list ('', em-dash, 'new') or string/number mixed sorting floats it to the top on descending.
- colspan=11 fallback row only renders when the fund table is EMPTY — don't probe live HTML for it.
- Chrome extension CANNOT open file:// URLs (navigate tool force-prepends https://, location.href assignment also blocked) — use jsdom in the sandbox for local page JS testing instead.

## Backlog (discussed, not built)
Watchlist + T-7/T-1 email alerts; free-float map; catalyst collisions; fixed-price (no-anchor) IPO coverage; mainboard promoter events; AI morning brief (needs paid API — declined for now); fund-name Title-case polish; pressure-board "% of co" wrap on narrow widths; deep-link index.html#slug so history-tab IPO names could link to the company modal.

_Last updated: 2026-07-15 (session: anchors overlay tabs — score breakdown + per-unlock IPO history with score replay, sparkline, pending deals; trend 90d column; movers strip)_
