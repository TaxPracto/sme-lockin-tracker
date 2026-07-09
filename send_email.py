#!/usr/bin/env python3
"""
Sends the morning lock-in digest email via Gmail SMTP.
Env vars (set as GitHub Secrets):
  GMAIL_ADDRESS       - your gmail (sender + default recipient)
  GMAIL_APP_PASSWORD  - app password (myaccount.google.com/apppasswords)
  DIGEST_TO           - optional, comma-separated recipients (default: GMAIL_ADDRESS)
  PAGE_URL            - optional, dashboard link (auto-derived on GitHub Actions)
Usage:  python send_email.py            -> send
        python send_email.py --preview  -> write email_preview.html only (no send)
"""
import datetime as dt
import json
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

AMBER, CYAN, RED, INK, MUT = "#b97900", "#0e7c86", "#d92638", "#101623", "#5c6b85"

def page_url():
    if os.environ.get("PAGE_URL"):
        return os.environ["PAGE_URL"]
    repo = os.environ.get("GITHUB_REPOSITORY", "")  # owner/repo
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return "#"

def load_events():
    with open("data/lockins.json", encoding="utf-8") as f:
        payload = json.load(f)
    today = dt.datetime.now(IST).date()
    tname = {"A30": "30D", "A90": "90D", "PRE6M": "6M PRE-IPO", "PX1Y": "1Y PROM", "PX2Y": "2Y PROM"}
    tcol = {"A30": ("#fff3d9", AMBER), "A90": ("#dff7f9", CYAN),
            "PRE6M": ("#efe9ff", "#6d4fd1"), "PX1Y": ("#ffe9df", "#c2410c"), "PX2Y": ("#ffe9df", "#c2410c")}
    evs = []
    for r in payload["records"]:
        if r["category"] != "SME":          # digest = SME only (page has a mainboard toggle)
            continue
        for e in r.get("events", []):
            if not e.get("d"):
                continue
            dd = (dt.date.fromisoformat(e["d"]) - today).days
            if dd < 0 or dd > 30:
                continue
            evs.append({
                "dd": dd, "date": e["d"], "tlbl": tname.get(e["t"], e["t"]),
                "tbg": tcol.get(e["t"], ("#eee", "#555"))[0], "tfg": tcol.get(e["t"], ("#eee", "#555"))[1],
                "company": r["company"], "url": r["url"], "est": e.get("est", False),
                "shares": e.get("sh"), "val": e.get("val"), "cappct": e.get("pct"),
            })
    evs.sort(key=lambda e: (e["date"], -(e["cappct"] or 0), -(e["val"] or 0)))
    return today, evs

def sh_fmt(n):
    if not n:
        return "—"
    if n >= 1e7: return f"{n/1e7:.2f} Cr"
    if n >= 1e5: return f"{n/1e5:.2f} L"
    return f"{n:,}"

def cr(v):
    return f"₹{v:,.1f} cr" if v is not None else "—"

def rows_html(evs, accent):
    if not evs:
        return f'<tr><td style="padding:10px 14px;color:{MUT};font-size:13px">nothing scheduled</td></tr>'
    out = []
    for e in evs:
        d = dt.date.fromisoformat(e["date"])
        size = cr(e["val"]) if e["val"] is not None else (f"{e['cappct']}% cap" if e["cappct"] is not None else "—")
        size_lbl = "at issue px" if e["val"] is not None else ("of capital" + (" · est" if e["est"] else ""))
        out.append(f"""<tr>
  <td style="padding:9px 6px 9px 14px;white-space:nowrap;color:{MUT};font-size:12px">{d.strftime('%a, %d %b')}</td>
  <td style="padding:9px 6px"><a href="{e['url'] or '#'}" style="color:{INK};font-weight:600;font-size:13.5px;text-decoration:none">{e['company']}</a></td>
  <td style="padding:9px 6px;white-space:nowrap"><span style="background:{e['tbg']};color:{e['tfg']};font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:99px">{e['tlbl']}</span></td>
  <td style="padding:9px 6px;text-align:right;font-size:12.5px">{sh_fmt(e['shares'])}<br><span style="color:{MUT};font-size:10px">shares{' · est' if e['est'] else ''}</span></td>
  <td style="padding:9px 14px 9px 6px;text-align:right;font-size:12.5px;font-weight:600">{size}<br><span style="color:{MUT};font-size:10px;font-weight:400">{size_lbl}</span></td>
</tr>""")
    return "\n".join(out)

def section(title, accent, evs):
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;border:1px solid #e5e9f2;border-left:4px solid {accent};border-radius:10px;border-collapse:separate;overflow:hidden">
<tr><td style="background:#f7f9fd;padding:10px 14px;font-size:11px;letter-spacing:.18em;color:{MUT};font-weight:700">{title}</td></tr>
<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows_html(evs, accent)}</table></td></tr>
</table>"""

def build_email():
    today, evs = load_events()
    t = [e for e in evs if e["dd"] == 0]
    tom = [e for e in evs if e["dd"] == 1]
    week = [e for e in evs if 2 <= e["dd"] <= 7]
    month = [e for e in evs if 8 <= e["dd"] <= 30]
    url = page_url()

    subject = f"🔓 SME unlocks — {len(t)} today · {len(t)+len(tom)+len(week)} in 7 days ({today.strftime('%d %b')})"
    big = max(t + tom + week, key=lambda e: e["cappct"] or 0, default=None)
    big_txt = f"{big['cappct']}%" if big and big["cappct"] else "—"

    body = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#eef1f7">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:26px 12px">
<table role="presentation" width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;font-family:'Segoe UI',Arial,sans-serif">

<tr><td style="background:{INK};border-radius:14px 14px 0 0;padding:22px 26px">
  <div style="color:#ffb020;font-size:20px;font-weight:700;font-style:italic;font-family:Georgia,serif">Unlock Radar</div>
  <div style="color:#8b99b4;font-size:11px;letter-spacing:.22em;margin-top:4px">SME IPO · ANCHOR LOCK-IN DIGEST — {today.strftime('%A, %d %B %Y').upper()}</div>
</td></tr>

<tr><td style="background:#ffffff;padding:20px 26px 26px;border:1px solid #e5e9f2;border-top:0;border-radius:0 0 14px 14px">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="text-align:center">
<tr>
  <td style="padding:10px"><div style="font-size:30px;font-weight:800;color:{RED}">{len(t)}</div><div style="font-size:10px;letter-spacing:.16em;color:{MUT}">TODAY</div></td>
  <td style="padding:10px;border-left:1px solid #e5e9f2"><div style="font-size:30px;font-weight:800;color:{AMBER}">{len(t)+len(tom)+len(week)}</div><div style="font-size:10px;letter-spacing:.16em;color:{MUT}">NEXT 7 DAYS</div></td>
  <td style="padding:10px;border-left:1px solid #e5e9f2"><div style="font-size:30px;font-weight:800;color:{CYAN}">{big_txt}</div><div style="font-size:10px;letter-spacing:.16em;color:{MUT}">BIGGEST · % OF CAP · 7D</div></td>
</tr></table>

{section("🔴 OPENING TODAY", RED, t)}
{section("🟠 TOMORROW", AMBER, tom)}
{section("🟡 THIS WEEK (D-2 TO D-7)", AMBER, week)}
{section("⚪ NEXT 30 DAYS", "#9fb4e8", month)}

<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 0 6px">
<a href="{url}" style="background:{INK};color:#ffb020;font-size:13px;font-weight:700;padding:12px 26px;border-radius:10px;text-decoration:none">Open the full dashboard →</a>
</td></tr></table>

<div style="color:{MUT};font-size:10.5px;line-height:1.8;margin-top:16px;border-top:1px solid #e5e9f2;padding-top:12px">
Anchor: 50% at 30/90 days (values at issue price). Pre-IPO &amp; promoter events marked "est" are computed from SEBI ICDR rules and prospectus data — verify before acting. Data: Chittorgarh.com.
For research &amp; information only — not investment advice. Anchor selling post-unlock is a possibility, not a certainty.</div>

</td></tr></table></td></tr></table></body></html>"""
    return subject, body

def main():
    subject, body = build_email()
    if "--preview" in sys.argv:
        with open("email_preview.html", "w", encoding="utf-8") as f:
            f.write(body)
        print(f"[email] preview written: email_preview.html | subject: {subject}")
        return
    sender = os.environ["GMAIL_ADDRESS"].strip()
    pwd = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "").strip()
    to = [a.strip() for a in os.environ.get("DIGEST_TO", sender).split(",") if a.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, f"Unlock Radar <{sender}>", ", ".join(to)
    msg.attach(MIMEText(body, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
        s.login(sender, pwd)
        s.sendmail(sender, to, msg.as_string())
    print(f"[email] sent to {to} | {subject}")

if __name__ == "__main__":
    main()
