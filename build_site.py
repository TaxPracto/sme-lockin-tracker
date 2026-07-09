#!/usr/bin/env python3
"""Builds docs/index.html + docs/lockins.ics + docs/data.json from data/lockins.json."""
import datetime as dt
import json
import os

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

with open("data/lockins.json", encoding="utf-8") as f:
    payload = json.load(f)

records = payload["records"]
now_ist = dt.datetime.now(IST)
gen_label = now_ist.strftime("%d %b %Y, %H:%M IST")

# ---------------- ICS calendar feed (future events, SME + Mainboard tagged) ----
def ics_escape(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//UnlockRadar//AnchorLockins//EN",
         "CALSCALE:GREGORIAN", "X-WR-CALNAME:Anchor Lock-in Expiries",
         "X-WR-TIMEZONE:Asia/Kolkata"]
today_iso = now_ist.date().isoformat()
for r in records:
    for tranche, d in (("30D", r["d30"]), ("90D", r["d90"])):
        if not d or d < today_iso:
            continue
        val = r["anchor_investment_cr"]
        val_txt = f" ~Rs.{val/2:.1f} cr" if val else ""
        dstart = d.replace("-", "")
        dend = (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat().replace("-", "")
        lines += ["BEGIN:VEVENT",
                  f"UID:{r['slug']}-{tranche}@unlockradar",
                  f"DTSTART;VALUE=DATE:{dstart}",
                  f"DTEND;VALUE=DATE:{dend}",
                  f"SUMMARY:{ics_escape('🔓 ' + r['company'] + ' — ' + tranche + ' anchor unlock' + val_txt)}",
                  f"DESCRIPTION:{ics_escape(r['category'] + ' IPO. 50% of anchor shares release. ' + (r['url'] or ''))}",
                  "END:VEVENT"]
lines.append("END:VCALENDAR")
os.makedirs("docs", exist_ok=True)
with open("docs/lockins.ics", "w", encoding="utf-8") as f:
    f.write("\r\n".join(lines) + "\r\n")

with open("docs/data.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=1)
open("docs/.nojekyll", "w").close()

# ---------------- HTML ----------------
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unlock Radar — SME IPO anchor lock-in expiries</title>
<meta name="description" content="Daily-refreshed calendar of 30-day and 90-day anchor investor lock-in expiries for Indian SME IPOs.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#06090f; --panel:#0b111b; --panel2:#0e1522; --line:rgba(147,177,255,.09);
  --line2:rgba(147,177,255,.16); --txt:#e9eef8; --mut:#67758f; --mut2:#8b99b4;
  --amber:#ffb020; --cyan:#3bd6e0; --red:#ff4d5e; --green:#3ddc84;
  --amber-dim:rgba(255,176,32,.13); --cyan-dim:rgba(59,214,224,.12); --red-dim:rgba(255,77,94,.12);
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:"IBM Plex Mono",monospace;font-size:14px;
  background-image:radial-gradient(1100px 480px at 18% -8%, rgba(59,120,224,.13), transparent 60%),
                   radial-gradient(900px 420px at 95% 0%, rgba(255,176,32,.05), transparent 55%);
  min-height:100vh; padding-bottom:60px}
.grain{position:fixed;inset:0;pointer-events:none;opacity:.05;z-index:99;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
a{color:inherit;text-decoration:none}
h2{font-family:Fraunces,serif;font-weight:400;font-style:italic;font-size:21px;color:var(--mut2);letter-spacing:.5px;margin-bottom:14px}
::selection{background:rgba(255,176,32,.35)}

/* masthead */
.mast{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:44px 0 26px;border-bottom:1px solid var(--line2);flex-wrap:wrap}
.kicker{font-size:11px;letter-spacing:.32em;color:var(--mut);display:flex;align-items:center;gap:14px;animation:rise .6s .05s both}
.live{display:inline-flex;align-items:center;gap:6px;color:var(--green);letter-spacing:.18em;font-size:10px}
.live i{width:6px;height:6px;border-radius:50%;background:var(--green);animation:blink 2.2s infinite}
h1{font-family:Fraunces,serif;font-weight:340;font-size:clamp(44px,7vw,76px);line-height:.98;letter-spacing:-.01em;margin:12px 0 10px;animation:rise .6s .12s both}
h1 em{font-style:italic;color:var(--amber)}
.sub{color:var(--mut);max-width:520px;font-size:12.5px;line-height:1.75;animation:rise .6s .2s both}
.mast-right{text-align:right;animation:rise .6s .26s both}
.today-date{font-family:Fraunces,serif;font-style:italic;font-size:22px;color:var(--mut2)}
.updated{font-size:11px;color:var(--mut);margin-top:8px;line-height:1.9}
.updated a{color:var(--cyan);border-bottom:1px dotted rgba(59,214,224,.5)}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}

/* stats */
.stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line2);border-radius:14px;margin:30px 0 8px;overflow:hidden;background:linear-gradient(180deg,var(--panel),transparent);animation:rise .6s .32s both}
.stat{padding:20px 22px;border-right:1px solid var(--line)}
.stat:last-child{border-right:0}
.stat .k{font-size:10px;letter-spacing:.26em;color:var(--mut)}
.stat .v{font-size:32px;margin-top:8px;font-weight:500}
.stat .s{font-size:11px;color:var(--mut);margin-top:4px}
.stat.hot .v{color:var(--red)} .stat.warm .v{color:var(--amber)} .stat.cool .v{color:var(--cyan)}

/* rail */
.rail-wrap{margin-top:42px;animation:rise .6s .4s both}
.rail{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 16px;scroll-snap-type:x mandatory;scrollbar-width:thin;scrollbar-color:var(--line2) transparent}
.card{min-width:212px;scroll-snap-align:start;background:var(--panel);border:1px solid var(--line2);border-radius:14px;padding:16px 16px 14px;position:relative;transition:transform .22s,border-color .22s;display:flex;flex-direction:column;gap:9px}
.card:hover{transform:translateY(-4px);border-color:rgba(147,177,255,.34)}
.card.today{border-color:rgba(255,77,94,.55);box-shadow:0 0 26px rgba(255,77,94,.12);animation:glow 2.4s infinite}
@keyframes glow{0%,100%{box-shadow:0 0 14px rgba(255,77,94,.10)}50%{box-shadow:0 0 30px rgba(255,77,94,.22)}}
.dbadge{font-size:11px;letter-spacing:.14em;color:var(--mut2);display:flex;justify-content:space-between;align-items:center}
.dbadge b{font-size:17px;font-weight:600;color:var(--txt)}
.card.today .dbadge b{color:var(--red)}
.card.soon .dbadge b{color:var(--amber)}
.cname{font-size:13.5px;line-height:1.45;min-height:39px;font-weight:500}
.pill{display:inline-block;font-size:10px;letter-spacing:.12em;padding:3px 9px;border-radius:99px;font-weight:600}
.p30{background:var(--amber-dim);color:var(--amber);border:1px solid rgba(255,176,32,.35)}
.p90{background:var(--cyan-dim);color:var(--cyan);border:1px solid rgba(59,214,224,.35)}
.pmb{background:rgba(147,177,255,.1);color:#9fb4e8;border:1px solid rgba(147,177,255,.3)}
.cnums{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:10px;font-size:12.5px}
.cnums span{display:block;font-size:9.5px;color:var(--mut);letter-spacing:.14em;margin-top:3px}

/* calendar strips */
.cal-wrap{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:34px;animation:rise .6s .46s both}
.cal{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.cal h3{font-family:Fraunces,serif;font-style:italic;font-weight:400;font-size:15px;color:var(--mut2);margin-bottom:12px}
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(30px,1fr));gap:5px}
.day{aspect-ratio:1;border-radius:7px;border:1px solid transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:10.5px;color:var(--mut);cursor:default}
.day.has{border-color:var(--line2);background:var(--panel2);cursor:pointer;color:var(--mut2)}
.day.has:hover{border-color:rgba(147,177,255,.4)}
.day.today{border-color:var(--red);color:var(--txt)}
.dots{display:flex;gap:2px}
.dot{width:4px;height:4px;border-radius:50%}
.dot.a{background:var(--amber)}.dot.c{background:var(--cyan)}

/* ledger */
.ledger-wrap{margin-top:44px;animation:rise .6s .5s both}
.ledger-head{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:16px}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.tabs{display:flex;border:1px solid var(--line2);border-radius:10px;overflow:hidden}
.tab{padding:8px 16px;font-size:11px;letter-spacing:.14em;color:var(--mut);cursor:pointer;background:transparent;border:0;font-family:inherit}
.tab.on{background:var(--panel2);color:var(--txt)}
.mb-toggle{display:flex;gap:7px;align-items:center;font-size:11px;color:var(--mut);cursor:pointer;letter-spacing:.1em}
.mb-toggle input{accent-color:var(--amber)}
#search{background:var(--panel);border:1px solid var(--line2);border-radius:10px;color:var(--txt);font-family:inherit;font-size:12px;padding:9px 14px;width:200px;outline:none}
#search:focus{border-color:rgba(255,176,32,.5)}
.lgroup{margin-bottom:6px}
.ldate{font-size:11px;letter-spacing:.22em;color:var(--mut);padding:18px 4px 8px;display:flex;gap:10px;align-items:center}
.ldate.today-l{color:var(--red)}
.ldate .cnt{color:var(--mut);opacity:.7;letter-spacing:0}
.lrow{display:grid;grid-template-columns:52px 1fr 96px 110px 110px 64px 28px;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 16px;margin-bottom:6px;transition:border-color .18s,transform .18s}
.lrow:hover{border-color:rgba(147,177,255,.35);transform:translateX(3px)}
.lrow.past{opacity:.45}
.lrow .dd{font-size:17px;font-weight:600;color:var(--mut2)}
.lrow .dd span{display:block;font-size:9px;letter-spacing:.2em;color:var(--mut);font-weight:400}
.lrow .co{font-size:13px;font-weight:500;line-height:1.4}
.lrow .co span{display:block;font-size:10px;color:var(--mut);margin-top:2px;letter-spacing:.06em}
.num{text-align:right;font-size:12.5px}
.num span{display:block;font-size:9px;color:var(--mut);letter-spacing:.16em;margin-top:2px}
.go{color:var(--mut);font-size:15px;text-align:center}
.lrow:hover .go{color:var(--cyan)}
.empty{color:var(--mut);padding:30px 4px;font-size:12.5px}
mark{background:rgba(255,176,32,.3);color:var(--txt);border-radius:3px}

/* footer */
footer{border-top:1px solid var(--line);margin-top:52px;padding-top:22px;font-size:11px;color:var(--mut);line-height:2;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer b{color:var(--mut2);font-weight:500}

@media(max-width:860px){
  .stats{grid-template-columns:1fr 1fr}
  .stat:nth-child(2){border-right:0}
  .stat{border-bottom:1px solid var(--line)}
  .cal-wrap{grid-template-columns:1fr}
  .lrow{grid-template-columns:44px 1fr 90px 28px}
  .lrow .num.hm{display:none}
  .mast{padding-top:30px}
  .mast-right{text-align:left}
}
</style>
</head>
<body>
<div class="grain"></div>
<div class="wrap">

<header class="mast">
  <div>
    <div class="kicker">SME IPO · ANCHOR LOCK-IN EXPIRIES <span class="live"><i></i>DAILY 07:00 IST</span></div>
    <h1>Unlock <em>Radar</em></h1>
    <div class="sub">Every 30-day and 90-day anchor lock-in window on BSE SME &amp; NSE Emerge — who can sell, when, and how much is unlocking.</div>
  </div>
  <div class="mast-right">
    <div class="today-date" id="mastDate"></div>
    <div class="updated">data as of <b>__GENERATED__</b><br>
    <a href="lockins.ics">calendar feed (.ics)</a> · <a href="data.json">raw json</a></div>
  </div>
</header>

<section class="stats" id="stats"></section>
<section class="rail-wrap"><h2>Up next</h2><div class="rail" id="rail"></div></section>
<section class="cal-wrap" id="cals"></section>

<section class="ledger-wrap">
  <div class="ledger-head">
    <h2>The ledger</h2>
    <div class="controls">
      <div class="tabs" id="tabs">
        <button class="tab on" data-t="up">UPCOMING</button>
        <button class="tab" data-t="past">PAST</button>
        <button class="tab" data-t="all">ALL</button>
      </div>
      <label class="mb-toggle"><input type="checkbox" id="mbToggle"> + MAINBOARD</label>
      <input id="search" placeholder="search company…" autocomplete="off">
    </div>
  </div>
  <div id="ledger"></div>
</section>

<footer>
  <div><b>Unlock Radar</b> · data sourced from Chittorgarh.com (report #156), refreshed daily by GitHub Actions.<br>
  50% of anchor shares release at each date · values estimated at issue price.</div>
  <div>For research &amp; information only — <b>not investment advice</b>.<br>Anchor selling post-unlock is a possibility, not a certainty.</div>
</footer>

</div>
<script>
const DATA = __DATA__;
const IST_OFF = 330; // minutes
function istToday(){
  const n = new Date();
  const ist = new Date(n.getTime() + (n.getTimezoneOffset() + IST_OFF) * 60000);
  return new Date(ist.getFullYear(), ist.getMonth(), ist.getDate());
}
const T0 = istToday();
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const pd = s => { const [y,m,dd] = s.split('-').map(Number); return new Date(y, m-1, dd); };
const DAYMS = 86400000;
const dayDiff = s => Math.round((pd(s) - T0) / DAYMS);
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DOW = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const fmtL = s => { const d = pd(s); return `${DOW[d.getDay()]}, ${String(d.getDate()).padStart(2,'0')} ${MON[d.getMonth()]} ${d.getFullYear()}`; };
const fmtS = s => { const d = pd(s); return `${DOW[d.getDay()]} · ${String(d.getDate()).padStart(2,'0')} ${MON[d.getMonth()]}`; };
function shFmt(n){
  if(n == null || n === 0) return '—';
  if(n >= 1e7) return (n/1e7).toFixed(2).replace(/\.?0+$/,'') + ' Cr';
  if(n >= 1e5) return (n/1e5).toFixed(2).replace(/\.?0+$/,'') + ' L';
  return n.toLocaleString('en-IN');
}
const crFmt = v => v == null ? '—' : '₹' + (v >= 100 ? Math.round(v).toLocaleString('en-IN') : v.toFixed(1)) + ' cr';
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function events(includeMB){
  const out = [];
  for(const r of DATA.records){
    if(!includeMB && r.category !== 'SME') continue;
    for(const [tr, d] of [[30, r.d30], [90, r.d90]]){
      if(!d) continue;
      out.push({ d, tr, r,
        sh: r.anchor_shares ? Math.floor(r.anchor_shares/2) : null,
        val: r.anchor_investment_cr ? r.anchor_investment_cr/2 : null });
    }
  }
  return out;
}

const $ = id => document.getElementById(id);
let TAB = 'up', MB = false, Q = '';

function pills(e){
  let h = `<span class="pill ${e.tr===30?'p30':'p90'}">${e.tr}D</span>`;
  if(e.r.category !== 'SME') h += ` <span class="pill pmb">MB</span>`;
  return h;
}

function render(){
  const evs = events(MB);
  const up = evs.filter(e => dayDiff(e.d) >= 0).sort((a,b) => a.d.localeCompare(b.d) || (b.val||0)-(a.val||0));
  const past = evs.filter(e => dayDiff(e.d) < 0).sort((a,b) => b.d.localeCompare(a.d));

  // masthead date
  $('mastDate').textContent = fmtL(iso(T0));

  // stats
  const tCount = up.filter(e => dayDiff(e.d) === 0);
  const w7 = up.filter(e => dayDiff(e.d) <= 7);
  const m30 = up.filter(e => dayDiff(e.d) <= 30);
  const w7val = w7.reduce((s,e) => s + (e.val||0), 0);
  const m30val = m30.reduce((s,e) => s + (e.val||0), 0);
  $('stats').innerHTML = `
    <div class="stat hot"><div class="k">OPENING TODAY</div><div class="v">${tCount.length}</div>
      <div class="s">${tCount.length ? crFmt(tCount.reduce((s,e)=>s+(e.val||0),0)) + ' unlocking' : 'quiet session'}</div></div>
    <div class="stat warm"><div class="k">NEXT 7 DAYS</div><div class="v">${w7.length}</div><div class="s">${crFmt(w7val)} at issue px</div></div>
    <div class="stat cool"><div class="k">NEXT 30 DAYS</div><div class="v">${m30.length}</div><div class="s">${crFmt(m30val)} at issue px</div></div>
    <div class="stat"><div class="k">ON RADAR</div><div class="v">${up.length}</div><div class="s">future unlock events</div></div>`;

  // rail
  $('rail').innerHTML = up.slice(0, 12).map(e => {
    const dd = dayDiff(e.d);
    const cls = dd === 0 ? 'today' : (dd <= 7 ? 'soon' : '');
    const badge = dd === 0 ? 'TODAY' : 'D-' + dd;
    return `<a class="card ${cls}" href="${e.r.url||'#'}" target="_blank" rel="noopener">
      <div class="dbadge"><b>${badge}</b><span>${fmtS(e.d)}</span></div>
      <div class="cname">${esc(e.r.company)}</div>
      <div>${pills(e)}</div>
      <div class="cnums">
        <div>${crFmt(e.val)}<span>AT ISSUE PX</span></div>
        <div>${shFmt(e.sh)}<span>SHARES</span></div>
      </div></a>`;
  }).join('') || '<div class="empty">nothing on the radar</div>';

  // calendars: this month + next
  const byDay = {};
  evs.forEach(e => { (byDay[e.d] = byDay[e.d] || []).push(e); });
  const calHtml = [0, 1].map(off => {
    const first = new Date(T0.getFullYear(), T0.getMonth() + off, 1);
    const dim = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
    let cells = '';
    for(let d = 1; d <= dim; d++){
      const ds = iso(new Date(first.getFullYear(), first.getMonth(), d));
      const es = byDay[ds] || [];
      const isT = ds === iso(T0);
      const dots = es.slice(0,3).map(e => `<i class="dot ${e.tr===30?'a':'c'}"></i>`).join('');
      cells += `<div class="day ${es.length?'has':''} ${isT?'today':''}" ${es.length?`onclick="jump('${ds}')"`:''} title="${es.length? es.length+' unlock(s)':''}">
        <span>${d}</span><span class="dots">${dots}</span></div>`;
    }
    return `<div class="cal"><h3>${MON[first.getMonth()]} ${first.getFullYear()}</h3><div class="cal-grid">${cells}</div></div>`;
  }).join('');
  $('cals').innerHTML = calHtml;

  // ledger
  let list = TAB === 'up' ? up : TAB === 'past' ? past : up.concat(past);
  if(Q) list = list.filter(e => e.r.company.toLowerCase().includes(Q));
  const groups = {};
  list.forEach(e => { (groups[e.d] = groups[e.d] || []).push(e); });
  const keys = Object.keys(groups);
  if(TAB === 'up') keys.sort(); else if(TAB === 'past') keys.sort().reverse();
  $('ledger').innerHTML = keys.map(d => {
    const dd = dayDiff(d);
    const label = dd === 0 ? 'TODAY — ' + fmtL(d) : dd === 1 ? 'TOMORROW — ' + fmtL(d) : fmtL(d);
    const rows = groups[d].map(e => {
      const day = pd(d);
      const nm = Q ? esc(e.r.company).replace(new RegExp('(' + Q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')','ig'),'<mark>$1</mark>') : esc(e.r.company);
      return `<a class="lrow ${dd<0?'past':''}" id="d${d}" href="${e.r.url||'#'}" target="_blank" rel="noopener">
        <div class="dd">${String(day.getDate()).padStart(2,'0')}<span>${MON[day.getMonth()].toUpperCase()}</span></div>
        <div class="co">${nm}<span>anchor allotted ${e.r.anchor_allotment_date || '—'} · ${e.r.pct_of_issue ? e.r.pct_of_issue + '% of issue' : ''}</span></div>
        <div>${pills(e)}</div>
        <div class="num hm">${shFmt(e.sh)}<span>SHARES FREE</span></div>
        <div class="num">${crFmt(e.val)}<span>AT ISSUE PX</span></div>
        <div class="num hm">${e.r.anchor_investment_cr ? crFmt(e.r.anchor_investment_cr) : '—'}<span>TOTAL ANCHOR</span></div>
        <div class="go">↗</div></a>`;
    }).join('');
    return `<div class="lgroup"><div class="ldate ${dd===0?'today-l':''}">${label}<span class="cnt">· ${groups[d].length}</span></div>${rows}</div>`;
  }).join('') || '<div class="empty">no matches — try clearing the search or switching tabs</div>';
}

function jump(ds){
  TAB = dayDiff(ds) >= 0 ? 'up' : 'past';
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('on', b.dataset.t === TAB));
  render();
  const el = document.getElementById('d' + ds);
  if(el){ el.scrollIntoView({behavior:'smooth', block:'center'}); }
}
document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
  TAB = b.dataset.t;
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === b));
  render();
});
$('mbToggle').onchange = e => { MB = e.target.checked; render(); };
$('search').oninput = e => { Q = e.target.value.trim().toLowerCase(); render(); };
render();
</script>
</body>
</html>"""

html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False)) \
           .replace("__GENERATED__", gen_label)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

n_future = sum(1 for r in records for d in (r["d30"], r["d90"]) if d and d >= today_iso)
print(f"[build] docs/index.html written ({len(html)//1024} KB), "
      f"{n_future} future unlock events, ics + data.json + .nojekyll done")
