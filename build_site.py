#!/usr/bin/env python3
"""Builds docs/index.html + docs/lockins.ics + docs/data.json from data/lockins.json (v2: multi-event)."""
import datetime as dt
import json
import os

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

with open("data/lockins.json", encoding="utf-8") as f:
    payload = json.load(f)

records = payload["records"]
now_ist = dt.datetime.now(IST)
gen_label = now_ist.strftime("%d %b %Y, %H:%M IST")
today_iso = now_ist.date().isoformat()

TYPE_NAME = {"A30": "30D anchor", "A90": "90D anchor", "PRE6M": "6M pre-IPO",
             "PX1Y": "1Y promoter", "PX2Y": "2Y promoter"}

# ---------------- ICS ----------------
def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//UnlockRadar//v2//EN",
         "CALSCALE:GREGORIAN", "X-WR-CALNAME:Unlock Radar - lock-in expiries",
         "X-WR-TIMEZONE:Asia/Kolkata"]
for r in records:
    for e in r.get("events", []):
        if not e["d"] or e["d"] < today_iso:
            continue
        bits = []
        if e.get("sh"):
            bits.append(f"{e['sh']:,} sh")
        if e.get("pct"):
            bits.append(f"{e['pct']}% of capital")
        if e.get("val"):
            bits.append(f"~Rs.{e['val']:.1f} cr")
        summ = f"🔓 {r['company']} — {TYPE_NAME[e['t']]} unlock" + (f" ({'; '.join(bits)})" if bits else "")
        dstart = e["d"].replace("-", "")
        dend = (dt.date.fromisoformat(e["d"]) + dt.timedelta(days=1)).isoformat().replace("-", "")
        lines += ["BEGIN:VEVENT", f"UID:{r['slug']}-{e['t']}@unlockradar",
                  f"DTSTART;VALUE=DATE:{dstart}", f"DTEND;VALUE=DATE:{dend}",
                  f"SUMMARY:{esc(summ)}",
                  f"DESCRIPTION:{esc(('Estimated from SEBI ICDR rules. ' if e.get('est') else '') + (r['url'] or ''))}",
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
<title>Unlock Radar — SME IPO lock-in expiries</title>
<meta name="description" content="Daily-refreshed calendar of anchor, pre-IPO and promoter lock-in expiries for Indian SME IPOs.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#06090f; --panel:#0b111b; --panel2:#0e1522; --line:rgba(147,177,255,.09);
  --line2:rgba(147,177,255,.16); --txt:#e9eef8; --mut:#67758f; --mut2:#8b99b4;
  --amber:#ffb020; --cyan:#3bd6e0; --violet:#a78bfa; --coral:#ff7849; --red:#ff4d5e; --green:#3ddc84;
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
.mast{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:44px 0 22px;border-bottom:1px solid var(--line2);flex-wrap:wrap}
.kicker{font-size:11px;letter-spacing:.32em;color:var(--mut);display:flex;align-items:center;gap:14px;animation:rise .6s .05s both}
.live{display:inline-flex;align-items:center;gap:6px;color:var(--green);letter-spacing:.18em;font-size:10px}
.live i{width:6px;height:6px;border-radius:50%;background:var(--green);animation:blink 2.2s infinite}
h1{font-family:Fraunces,serif;font-weight:340;font-size:clamp(44px,7vw,76px);line-height:.98;margin:12px 0 10px;animation:rise .6s .12s both}
h1 em{font-style:italic;color:var(--amber)}
.sub{color:var(--mut);max-width:560px;font-size:12.5px;line-height:1.75;animation:rise .6s .2s both}
.mast-right{text-align:right;animation:rise .6s .26s both}
.today-date{font-family:Fraunces,serif;font-style:italic;font-size:22px;color:var(--mut2)}
.updated{font-size:11px;color:var(--mut);margin-top:8px;line-height:1.9}
.updated a{color:var(--cyan);border-bottom:1px dotted rgba(59,214,224,.5)}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}
.typebar{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0 4px;animation:rise .6s .3s both}
.tchip{display:flex;align-items:center;gap:8px;font-size:11px;letter-spacing:.1em;padding:8px 14px;border:1px solid var(--line2);border-radius:99px;cursor:pointer;color:var(--mut2);user-select:none;transition:all .15s}
.tchip i{width:8px;height:8px;border-radius:50%}
.tchip.off{opacity:.35;filter:grayscale(.7)}
.tchip:hover{border-color:rgba(147,177,255,.4)}
.i-a30{background:var(--amber)}.i-a90{background:var(--cyan)}.i-pre{background:var(--violet)}.i-px{background:var(--coral)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line2);border-radius:14px;margin:18px 0 8px;overflow:hidden;background:linear-gradient(180deg,var(--panel),transparent);animation:rise .6s .32s both}
.stat{padding:20px 22px;border-right:1px solid var(--line)}
.stat:last-child{border-right:0}
.stat .k{font-size:10px;letter-spacing:.26em;color:var(--mut)}
.stat .v{font-size:32px;margin-top:8px;font-weight:500}
.stat .s{font-size:11px;color:var(--mut);margin-top:4px}
.stat.hot .v{color:var(--red)} .stat.warm .v{color:var(--amber)} .stat.cool .v{color:var(--cyan)}
.rail-wrap{margin-top:40px;animation:rise .6s .4s both}
.rail{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 16px;scroll-snap-type:x mandatory;scrollbar-width:thin;scrollbar-color:var(--line2) transparent}
.card{min-width:218px;scroll-snap-align:start;background:var(--panel);border:1px solid var(--line2);border-radius:14px;padding:16px 16px 14px;transition:transform .22s,border-color .22s;display:flex;flex-direction:column;gap:9px}
.card:hover{transform:translateY(-4px);border-color:rgba(147,177,255,.34)}
.card.today{border-color:rgba(255,77,94,.55);animation:glow 2.4s infinite}
@keyframes glow{0%,100%{box-shadow:0 0 14px rgba(255,77,94,.10)}50%{box-shadow:0 0 30px rgba(255,77,94,.22)}}
.dbadge{font-size:11px;letter-spacing:.14em;color:var(--mut2);display:flex;justify-content:space-between;align-items:center}
.dbadge b{font-size:17px;font-weight:600;color:var(--txt)}
.card.today .dbadge b{color:var(--red)}
.card.soon .dbadge b{color:var(--amber)}
.cname{font-size:13.5px;line-height:1.45;min-height:39px;font-weight:500}
.pill{display:inline-block;font-size:10px;letter-spacing:.1em;padding:3px 9px;border-radius:99px;font-weight:600}
.p30{background:rgba(255,176,32,.13);color:var(--amber);border:1px solid rgba(255,176,32,.35)}
.p90{background:rgba(59,214,224,.12);color:var(--cyan);border:1px solid rgba(59,214,224,.35)}
.p6m{background:rgba(167,139,250,.13);color:var(--violet);border:1px solid rgba(167,139,250,.4)}
.ppx{background:rgba(255,120,73,.13);color:var(--coral);border:1px solid rgba(255,120,73,.4)}
.pmb{background:rgba(147,177,255,.1);color:#9fb4e8;border:1px solid rgba(147,177,255,.3)}
.cnums{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:10px;font-size:12.5px}
.cnums span{display:block;font-size:9.5px;color:var(--mut);letter-spacing:.14em;margin-top:3px}
.cal-wrap{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:34px;animation:rise .6s .46s both}
.cal{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.cal h3{font-family:Fraunces,serif;font-style:italic;font-weight:400;font-size:15px;color:var(--mut2);margin-bottom:12px}
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(30px,1fr));gap:5px}
.day{aspect-ratio:1;border-radius:7px;border:1px solid transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:10.5px;color:var(--mut)}
.day.has{border-color:var(--line2);background:var(--panel2);cursor:pointer;color:var(--mut2)}
.day.has:hover{border-color:rgba(147,177,255,.4)}
.day.today{border-color:var(--red);color:var(--txt)}
.dots{display:flex;gap:2px}
.dot{width:4px;height:4px;border-radius:50%}
.ledger-wrap{margin-top:44px;animation:rise .6s .5s both}
.ledger-head{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:16px}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.tabs{display:flex;border:1px solid var(--line2);border-radius:10px;overflow:hidden}
.tab{padding:8px 16px;font-size:11px;letter-spacing:.14em;color:var(--mut);cursor:pointer;background:transparent;border:0;font-family:inherit}
.tab.on{background:var(--panel2);color:var(--txt)}
.mb-toggle{display:flex;gap:7px;align-items:center;font-size:11px;color:var(--mut);cursor:pointer;letter-spacing:.1em}
.mb-toggle input{accent-color:var(--amber)}
#search{background:var(--panel);border:1px solid var(--line2);border-radius:10px;color:var(--txt);font-family:inherit;font-size:12px;padding:9px 14px;width:190px;outline:none}
#search:focus{border-color:rgba(255,176,32,.5)}
.lgroup{margin-bottom:6px}
.ldate{font-size:11px;letter-spacing:.22em;color:var(--mut);padding:18px 4px 8px;display:flex;gap:10px;align-items:center}
.ldate.today-l{color:var(--red)}
.lrow{display:grid;grid-template-columns:52px 1fr 110px 110px 110px 28px;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 16px;margin-bottom:6px;transition:border-color .18s,transform .18s}
.lrow:hover{border-color:rgba(147,177,255,.35);transform:translateX(3px)}
.lrow.past{opacity:.45}
.lrow .dd{font-size:17px;font-weight:600;color:var(--mut2)}
.lrow .dd span{display:block;font-size:9px;letter-spacing:.2em;color:var(--mut);font-weight:400}
.lrow .co{font-size:13px;font-weight:500;line-height:1.4}
.lrow .co span{display:block;font-size:10px;color:var(--mut);margin-top:2px;letter-spacing:.04em}
.num{text-align:right;font-size:12.5px}
.num span{display:block;font-size:9px;color:var(--mut);letter-spacing:.16em;margin-top:2px}
.go{color:var(--mut);font-size:15px;text-align:center}
.lrow:hover .go{color:var(--cyan)}
.empty{color:var(--mut);padding:30px 4px;font-size:12.5px}
mark{background:rgba(255,176,32,.3);color:var(--txt);border-radius:3px}
.mback{position:fixed;inset:0;background:rgba(4,7,12,.74);backdrop-filter:blur(7px);display:none;z-index:200;align-items:center;justify-content:center;padding:20px}
.mback.on{display:flex}
.mcard{background:linear-gradient(180deg,#0d1421,#0a1019);border:1px solid var(--line2);border-radius:18px;max-width:760px;width:100%;max-height:88vh;overflow-y:auto;padding:28px 30px 24px;animation:mup .28s cubic-bezier(.2,.9,.3,1);scrollbar-width:thin}
@keyframes mup{from{opacity:0;transform:translateY(26px) scale(.98)}to{opacity:1;transform:none}}
.mhead{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;border-bottom:1px solid var(--line);padding-bottom:14px}
.mhead h3{font-family:Fraunces,serif;font-style:italic;font-weight:400;font-size:24px;line-height:1.2}
.mhead .msub{font-size:11px;color:var(--mut);margin-top:6px;letter-spacing:.08em;line-height:1.9}
.mx{background:none;border:1px solid var(--line2);color:var(--mut2);border-radius:9px;font-family:inherit;font-size:13px;padding:6px 11px;cursor:pointer}
.mx:hover{border-color:rgba(255,77,94,.5);color:var(--red)}
.mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0 4px}
.mstat{background:var(--panel2);border:1px solid var(--line);border-radius:11px;padding:11px 13px}
.mstat .k{font-size:9px;letter-spacing:.2em;color:var(--mut)}
.mstat .v{font-size:14.5px;font-weight:600;margin-top:5px}
.mstat .v small{font-size:10px;color:var(--mut);font-weight:400}
.msec{font-size:10px;letter-spacing:.26em;color:var(--mut);margin:20px 0 10px}
.mev{border:1px solid var(--line);border-left-width:3px;border-radius:11px;padding:12px 15px;margin-bottom:9px;background:rgba(10,16,25,.5)}
.mev.b30{border-left-color:var(--amber)} .mev.b90{border-left-color:var(--cyan)}
.mev.bpre{border-left-color:var(--violet)} .mev.bpx{border-left-color:var(--coral)}
.mev .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.mev .top b{font-size:13.5px}
.mev .num2{font-size:12.5px;color:var(--mut2)}
.mev .how{font-size:11px;color:var(--mut);line-height:1.85;margin-top:8px;border-top:1px dashed var(--line);padding-top:8px}
.mev .how b{color:var(--mut2);font-weight:500}
.mnote{font-size:10.5px;color:var(--mut);line-height:1.9;margin-top:16px;border-top:1px solid var(--line);padding-top:12px}
.mbtns{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
.mbtn{border-radius:10px;padding:11px 18px;font-family:inherit;font-size:12px;font-weight:600;letter-spacing:.06em;cursor:pointer;text-align:center}
.mbtn.primary{background:var(--amber);color:#1a1205;border:0}
.mbtn.primary:hover{filter:brightness(1.1)}
.mbtn.ghost{background:transparent;border:1px solid var(--line2);color:var(--mut2)}
.mbtn.ghost:hover{border-color:rgba(147,177,255,.4);color:var(--txt)}
@media(max-width:700px){.mgrid{grid-template-columns:1fr 1fr}.mcard{padding:20px 18px}}
footer{border-top:1px solid var(--line);margin-top:52px;padding-top:22px;font-size:11px;color:var(--mut);line-height:2;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer b{color:var(--mut2);font-weight:500}
@media(max-width:860px){
  .stats{grid-template-columns:1fr 1fr}
  .stat:nth-child(2){border-right:0}
  .stat{border-bottom:1px solid var(--line)}
  .cal-wrap{grid-template-columns:1fr}
  .lrow{grid-template-columns:44px 1fr 100px 28px}
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
    <div class="kicker">SME IPO · LOCK-IN EXPIRIES <span class="live"><i></i>DAILY 07:00 IST</span></div>
    <h1>Unlock <em>Radar</em></h1>
    <div class="sub">Anchor tranches, pre-IPO holder windows and promoter releases on BSE SME &amp; NSE Emerge — who can sell, when, and how much of the company is unlocking.</div>
  </div>
  <div class="mast-right">
    <div class="today-date" id="mastDate"></div>
    <div class="updated">data as of <b>__GENERATED__</b><br>
    <a href="lockins.ics">calendar feed (.ics)</a> · <a href="data.json">raw json</a></div>
  </div>
</header>

<div class="typebar" id="typebar">
  <div class="tchip" data-f="a30"><i class="i-a30"></i>30D ANCHOR</div>
  <div class="tchip" data-f="a90"><i class="i-a90"></i>90D ANCHOR</div>
  <div class="tchip" data-f="pre"><i class="i-pre"></i>6M PRE-IPO <small style="opacity:.6">est.</small></div>
  <div class="tchip" data-f="px"><i class="i-px"></i>PROMOTER 1Y/2Y <small style="opacity:.6">est.</small></div>
</div>

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
      <label class="mb-toggle"><input type="checkbox" id="mbToggle"> + MAINBOARD (anchor only)</label>
      <input id="search" placeholder="search company…" autocomplete="off">
    </div>
  </div>
  <div id="ledger"></div>
</section>

<footer>
  <div><b>Unlock Radar v2</b> · data: Chittorgarh.com + SEBI ICDR rules · refreshed daily by GitHub Actions.<br>
  Anchor tranches = 50% each at 30/90 days. Pre-IPO = non-promoter pre-issue holders at 6 months (est.).<br>
  Promoter = holding above 20% MPC, 50% at 1yr + 50% at 2yrs for post-Mar-2025 listings, else 100% at 1yr (est.).</div>
  <div>Dates &amp; sizes marked <b>est.</b> are computed, not exchange-confirmed — verify before acting.<br>
  Exemptions (AIF/VC holdings, ESOPs) can reduce actual unlocking quantity.<br>
  For research &amp; information only — <b>not investment advice</b>.</div>
</footer>

</div>
<div class="mback" id="mback"><div class="mcard" id="mcard"></div></div>
<script>
const DATA = __DATA__;
const IST_OFF = 330;
function istToday(){
  const n = new Date();
  const ist = new Date(n.getTime() + (n.getTimezoneOffset() + IST_OFF) * 60000);
  return new Date(ist.getFullYear(), ist.getMonth(), ist.getDate());
}
const T0 = istToday();
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const pd = s => { const [y,m,dd] = s.split('-').map(Number); return new Date(y, m-1, dd); };
const dayDiff = s => Math.round((pd(s) - T0) / 86400000);
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
const crFmt = v => v == null ? null : '₹' + (v >= 100 ? Math.round(v).toLocaleString('en-IN') : v.toFixed(1)) + ' cr';
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TYPE = {
  A30:{lbl:'30D', cls:'p30', fam:'a30'}, A90:{lbl:'90D', cls:'p90', fam:'a90'},
  PRE6M:{lbl:'6M PRE-IPO', cls:'p6m', fam:'pre'},
  PX1Y:{lbl:'1Y PROM', cls:'ppx', fam:'px'}, PX2Y:{lbl:'2Y PROM', cls:'ppx', fam:'px'}
};
const FAM_ON = {a30:true, a90:true, pre:true, px:true};
let TAB='up', MB=false, Q='';

function events(){
  const out = [];
  for(const r of DATA.records){
    for(const e of (r.events || [])){
      const t = TYPE[e.t]; if(!t || !FAM_ON[t.fam]) continue;
      if(!MB && r.category !== 'SME') continue;
      if(r.category !== 'SME' && t.fam !== 'a30' && t.fam !== 'a90') continue;
      out.push({...e, r, meta:t});
    }
  }
  return out;
}
function sizeMain(e){ return crFmt(e.val) || (e.pct != null ? e.pct + '% cap' : shFmt(e.sh)); }
function sizeLbl(e){ return e.val != null ? 'AT ISSUE PX' : (e.pct != null ? 'OF CAPITAL' + (e.est?' · EST':'') : 'SHARES' + (e.est?' · EST':'')); }
function pills(e){
  let h = `<span class="pill ${e.meta.cls}">${e.meta.lbl}</span>`;
  if(e.r.category !== 'SME') h += ` <span class="pill pmb">MB</span>`;
  return h;
}
function subLine(r){
  const bits = [`anchor allotted ${r.anchor_allotment_date || '—'}`];
  if(r.nonprom_pre_shares) bits.push(`pre-IPO non-prom: ${shFmt(r.nonprom_pre_shares)} sh${r.nonprom_pre_pct_of_post ? ' · ' + r.nonprom_pre_pct_of_post + '% cap' : ''}`);
  else if(r.pct_of_issue) bits.push(r.pct_of_issue + '% of issue');
  return bits.join(' · ');
}
const $ = id => document.getElementById(id);
const TLONG = {A30:'30-day anchor unlock', A90:'90-day anchor unlock', PRE6M:'Pre-IPO holders unlock (6M)', PX1Y:'Promoter release (1 year)', PX2Y:'Promoter release (2 years)'};
const BCLS = {A30:'b30', A90:'b90', PRE6M:'bpre', PX1Y:'bpx', PX2Y:'bpx'};
const nfmt = n => n == null ? '—' : n.toLocaleString('en-IN');
function explain(e, r){
  const phased = (r.events||[]).some(x => x.t === 'PX2Y');
  if(e.t === 'A30' || e.t === 'A90')
    return `<b>50% of the anchor allotment</b> (${nfmt(r.anchor_shares)} sh total, ₹${r.anchor_investment_cr ?? '—'} cr at issue price) stays locked for ${e.t==='A30'?30:90} days from allotment. Date as published — exchange-confirmed schedule, not an estimate.`;
  if(e.t === 'PRE6M'){
    if(r.pre_shares && r.prom_pre_pct != null)
      return `<b>Pre-issue capital ${nfmt(r.pre_shares)} sh × (100% − ${r.prom_pre_pct}% promoter holding) = ${nfmt(r.nonprom_pre_shares)} sh</b> held by non-promoter pre-IPO investors${r.nonprom_pre_pct_of_post ? ` (${r.nonprom_pre_pct_of_post}% of post-issue capital)` : ''}. Date = allotment + 6 months per SEBI ICDR. <b>Estimated</b> — AIF/VC holdings may be exempt, which can reduce the actual quantity.`;
    return `Date = allotment + 6 months per SEBI ICDR. Size pending — shareholding data for this IPO syncs on an upcoming daily run.`;
  }
  const exc = (r.prom_post_pct != null && r.post_shares) ? Math.round(r.post_shares * (r.prom_post_pct - 20) / 100) : null;
  if(e.t === 'PX1Y'){
    const base = `<b>Promoter post-issue ${r.prom_post_pct}% − 20% minimum promoter contribution = ${(r.prom_post_pct - 20).toFixed(2)}% excess${exc ? ` = ${nfmt(exc)} sh` : ''}.</b> `;
    return base + (phased
      ? `Listing on/after 08-Mar-2025 ⇒ phased regime: <b>50% of the excess releases at 1 year</b> from allotment. <b>Estimated.</b>`
      : `Pre-Mar-2025 regime: <b>100% of the excess releases at 1 year</b> from allotment. <b>Estimated.</b>`);
  }
  if(e.t === 'PX2Y')
    return `The <b>remaining 50% of the promoter excess</b>${exc ? ` (${nfmt(Math.round(exc/2))} sh)` : ''} releases at 2 years from allotment. The 20% MPC core stays locked 3 years. <b>Estimated.</b>`;
  return '';
}
function openModal(slug){
  const r = DATA.records.find(x => x.slug === slug);
  if(!r) return;
  const evs = (r.events || []).slice().sort((a,b) => a.d.localeCompare(b.d));
  const evHtml = evs.map(e => {
    const dd = dayDiff(e.d);
    const when = dd === 0 ? 'TODAY' : dd > 0 ? `D-${dd}` : `${-dd}d ago`;
    const size = [e.sh ? shFmt(e.sh) + ' sh' : null, e.pct != null ? e.pct + '% of capital' : null, e.val != null ? crFmt(e.val) + ' at issue px' : null].filter(Boolean).join(' · ') || 'size n/a';
    return `<div class="mev ${BCLS[e.t]}">
      <div class="top"><b>${TLONG[e.t]}</b><span class="num2">${fmtL(e.d)} · ${when}</span></div>
      <div class="num2" style="margin-top:5px">${size}</div>
      <div class="how">${explain(e, r)}</div></div>`;
  }).join('') || '<div class="empty">no events computed</div>';
  const mpc = r.post_shares ? Math.round(r.post_shares * 0.2) : null;
  $('mcard').innerHTML = `
    <div class="mhead"><div>
      <h3>${esc(r.company)}</h3>
      <div class="msub">${r.category}${r.nse_symbol ? ' · NSE ' + esc(String(r.nse_symbol)) : ''}${r.bse_code ? ' · BSE ' + r.bse_code : ''}${r.isin ? ' · ' + esc(String(r.isin)) : ''}<br>
      anchor allotted ${r.anchor_allotment_date || '—'} · allotment (BOA) ${r.boa_date || '—'} · listed ${r.listing_date || '—'}</div>
    </div><button class="mx" onclick="closeModal()">✕ esc</button></div>
    <div class="mgrid">
      <div class="mstat"><div class="k">PRE-ISSUE CAPITAL</div><div class="v">${shFmt(r.pre_shares)} <small>sh</small></div></div>
      <div class="mstat"><div class="k">POST-ISSUE CAPITAL</div><div class="v">${shFmt(r.post_shares)} <small>sh</small></div></div>
      <div class="mstat"><div class="k">PROMOTER PRE → POST</div><div class="v">${r.prom_pre_pct != null ? r.prom_pre_pct + '%' : '—'} → ${r.prom_post_pct != null ? r.prom_post_pct + '%' : '—'}</div></div>
      <div class="mstat"><div class="k">NON-PROM PRE-IPO</div><div class="v">${shFmt(r.nonprom_pre_shares)} <small>${r.nonprom_pre_pct_of_post ? '· ' + r.nonprom_pre_pct_of_post + '% cap' : ''}</small></div></div>
      <div class="mstat"><div class="k">ANCHOR ALLOTMENT</div><div class="v">${shFmt(r.anchor_shares)} <small>${r.anchor_investment_cr ? '· ₹' + r.anchor_investment_cr + ' cr' : ''}</small></div></div>
      <div class="mstat"><div class="k">20% MPC (3YR LOCK)</div><div class="v">${shFmt(mpc)} <small>sh</small></div></div>
    </div>
    <div class="msec">UNLOCK TIMELINE — AND HOW EACH NUMBER IS BUILT</div>
    ${evHtml}
    <div class="mnote">Anchor dates are exchange-published. Pre-IPO and promoter events are computed from the prospectus shareholding + SEBI ICDR lock-in rules — treat as strong estimates and verify against the exchange listing circular before acting. AIF/VC exemptions and ESOP pools can change actual free-float.</div>
    <div class="mbtns">
      ${r.url ? `<a class="mbtn primary" href="${r.url}" target="_blank" rel="noopener">Chittorgarh page ↗</a>` : ''}
      <button class="mbtn ghost" onclick="closeModal()">Close</button>
    </div>`;
  $('mback').classList.add('on');
  document.body.style.overflow = 'hidden';
}
function closeModal(){
  $('mback').classList.remove('on');
  document.body.style.overflow = '';
}
document.addEventListener('click', ev => {
  const t = ev.target.closest('[data-slug]');
  if(t){ ev.preventDefault(); openModal(t.dataset.slug); return; }
  if(ev.target.id === 'mback') closeModal();
});
document.addEventListener('keydown', ev => { if(ev.key === 'Escape') closeModal(); });

function render(){
  const evs = events();
  const up = evs.filter(e => dayDiff(e.d) >= 0).sort((a,b) => a.d.localeCompare(b.d) || (b.pct||0)-(a.pct||0) || (b.val||0)-(a.val||0));
  const past = evs.filter(e => dayDiff(e.d) < 0).sort((a,b) => b.d.localeCompare(a.d));
  $('mastDate').textContent = fmtL(iso(T0));

  const tC = up.filter(e => dayDiff(e.d) === 0);
  const w7 = up.filter(e => dayDiff(e.d) <= 7);
  const m30 = up.filter(e => dayDiff(e.d) <= 30);
  const big30 = m30.reduce((mx,e) => (e.pct||0) > (mx.pct||0) ? e : mx, {});
  $('stats').innerHTML = `
    <div class="stat hot"><div class="k">OPENING TODAY</div><div class="v">${tC.length}</div>
      <div class="s">${tC.length ? tC.map(e=>e.meta.lbl).join(' · ') : 'quiet session'}</div></div>
    <div class="stat warm"><div class="k">NEXT 7 DAYS</div><div class="v">${w7.length}</div><div class="s">unlock events</div></div>
    <div class="stat cool"><div class="k">NEXT 30 DAYS</div><div class="v">${m30.length}</div><div class="s">unlock events</div></div>
    <div class="stat"><div class="k">BIGGEST · 30D</div><div class="v">${big30.pct ? big30.pct + '%' : '—'}</div>
      <div class="s">${big30.r ? esc(big30.r.company).slice(0,26) + ' · ' + big30.meta.lbl : 'of capital unlocking'}</div></div>`;

  $('rail').innerHTML = up.slice(0, 14).map(e => {
    const dd = dayDiff(e.d);
    const cls = dd === 0 ? 'today' : (dd <= 7 ? 'soon' : '');
    return `<a class="card ${cls}" href="#" data-slug="${e.r.slug}">
      <div class="dbadge"><b>${dd === 0 ? 'TODAY' : 'D-' + dd}</b><span>${fmtS(e.d)}</span></div>
      <div class="cname">${esc(e.r.company)}</div>
      <div>${pills(e)}</div>
      <div class="cnums">
        <div>${sizeMain(e) || '—'}<span>${sizeLbl(e)}</span></div>
        <div>${shFmt(e.sh)}<span>SHARES</span></div>
      </div></a>`;
  }).join('') || '<div class="empty">nothing on the radar for these filters</div>';

  const byDay = {};
  evs.forEach(e => { (byDay[e.d] = byDay[e.d] || []).push(e); });
  $('cals').innerHTML = [0, 1].map(off => {
    const first = new Date(T0.getFullYear(), T0.getMonth() + off, 1);
    const dim = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
    let cells = '';
    for(let d = 1; d <= dim; d++){
      const ds = iso(new Date(first.getFullYear(), first.getMonth(), d));
      const es = byDay[ds] || [];
      const dots = es.slice(0,3).map(e => `<i class="dot i-${e.meta.fam === 'px' ? 'px' : e.meta.fam === 'pre' ? 'pre' : e.t === 'A30' ? 'a30' : 'a90'}"></i>`).join('');
      cells += `<div class="day ${es.length?'has':''} ${ds===iso(T0)?'today':''}" ${es.length?`onclick="jump('${ds}')"`:''} title="${es.length ? es.length + ' unlock(s)' : ''}">
        <span>${d}</span><span class="dots">${dots}</span></div>`;
    }
    return `<div class="cal"><h3>${MON[first.getMonth()]} ${first.getFullYear()}</h3><div class="cal-grid">${cells}</div></div>`;
  }).join('');

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
      return `<a class="lrow ${dd<0?'past':''}" id="d${d}" href="#" data-slug="${e.r.slug}">
        <div class="dd">${String(day.getDate()).padStart(2,'0')}<span>${MON[day.getMonth()].toUpperCase()}</span></div>
        <div class="co">${nm}<span>${subLine(e.r)}</span></div>
        <div>${pills(e)}</div>
        <div class="num hm">${shFmt(e.sh)}<span>SHARES FREE${e.est ? ' · EST' : ''}</span></div>
        <div class="num">${e.pct != null ? e.pct + '%' : (crFmt(e.val) || '—')}<span>${e.pct != null ? 'OF CAPITAL' : 'AT ISSUE PX'}</span></div>
        <div class="go">ⓘ</div></a>`;
    }).join('');
    return `<div class="lgroup"><div class="ldate ${dd===0?'today-l':''}">${label}<span>· ${groups[d].length}</span></div>${rows}</div>`;
  }).join('') || '<div class="empty">no matches — clear search or switch tabs/filters</div>';
}
function jump(ds){
  TAB = dayDiff(ds) >= 0 ? 'up' : 'past';
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('on', b.dataset.t === TAB));
  render();
  const el = document.getElementById('d' + ds);
  if(el) el.scrollIntoView({behavior:'smooth', block:'center'});
}
document.querySelectorAll('.tchip').forEach(c => c.onclick = () => {
  FAM_ON[c.dataset.f] = !FAM_ON[c.dataset.f];
  c.classList.toggle('off', !FAM_ON[c.dataset.f]);
  render();
});
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
n_ev = sum(1 for r in records for e in r.get("events", []) if e["d"] and e["d"] >= today_iso)
print(f"[build] v2 site written ({len(html)//1024} KB), {n_ev} future events")
