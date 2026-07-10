"""Export a self-contained HTML match replay with SKM moment overlays.

The replay animates the real event stream (StatsBomb open data) on a 2D
pitch: the ball moves action by action, moments are flagged as they occur,
and per-team / per-player SKM tickers update live.

No broadcast footage is bundled (open data has none, and clips are
copyrighted). A "Load video" control lets a viewer overlay the same flags
on their own local clip of the match, synced by an offset to the match
clock. The file input never uploads anything — the video plays locally.

Usage:
    skm-export-replay --game-id 3895067 --output replay.html
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from skm.config import ACTIONS_SCORED_PARQUET, EVENTS_PARQUET

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATA_TOKEN = "__SKM_REPLAY_DATA__"


def _clock(period_id: pd.Series, time_seconds: pd.Series) -> pd.Series:
    """Continuous match clock: period 2 starts at 45:00 (stoppage overlaps ignored)."""
    return (period_id.clip(lower=1) - 1) * 45 * 60 + time_seconds


def build_replay_data(
    game_id: int,
    actions: pd.DataFrame,
    events: Optional[pd.DataFrame] = None,
) -> dict:
    """Assemble the JSON payload for one match.

    Moments are re-derived on the single game's actions so that moment ids
    in the action stream and the moment table are consistent (segmentation
    never crosses game boundaries, so values match the global build).
    """
    from skm.models.moments import SHOT_TYPES, build_moments, infer_home_teams

    ga = actions[actions["game_id"] == game_id]
    if ga.empty:
        raise ValueError(f"No actions for game {game_id}")

    home_id = infer_home_teams(ga)[int(game_id)]
    gm, _, seg = build_moments(ga, home_teams={int(game_id): home_id})
    named = seg  # segmented actions, SPADL-named, in match order
    team_ids = sorted(named["team_id"].unique(), key=lambda t: t != home_id)  # home first

    home_name, away_name = f"Team {team_ids[0]}", f"Team {len(team_ids) > 1 and team_ids[1]}"
    if events is not None:
        ev = events[events["match_id"] == game_id]
        if len(ev):
            home_name = str(ev["home_team"].iloc[0])
            away_name = str(ev["away_team"].iloc[0])

    names = {}
    if events is not None:
        ev = events[events["match_id"] == game_id].dropna(subset=["player_id"])
        names = ev.groupby("player_id")["player"].first().to_dict()

    named = named.sort_values(["period_id", "time_seconds"], kind="stable")
    named["t"] = _clock(named["period_id"], named["time_seconds"])
    named["is_goal"] = named["type_name"].isin(SHOT_TYPES) & (
        named["result_name"] == "success"
    )

    acts = []
    for _, r in named.iterrows():
        pid = r["player_id"]
        acts.append(
            {
                "t": round(float(r["t"]), 1),
                "x": None if pd.isna(r["start_x"]) else round(float(r["start_x"]), 1),
                "y": None if pd.isna(r["start_y"]) else round(float(r["start_y"]), 1),
                "ex": None if pd.isna(r["end_x"]) else round(float(r["end_x"]), 1),
                "ey": None if pd.isna(r["end_y"]) else round(float(r["end_y"]), 1),
                "team": 0 if int(r["team_id"]) == team_ids[0] else 1,
                "player": names.get(pid, f"#{int(pid)}" if pd.notna(pid) else ""),
                "type": str(r["type_name"]),
                "skm": round(float(r["skm"]) if pd.notna(r["skm"]) else 0.0, 5),
                "mid": int(r["moment_id"]),
                "goal": bool(r["is_goal"]),
            }
        )

    moms = [
        {
            "mid": int(r["moment_id"]),
            "type": str(r["moment_type"]),
            "t0": round(float(_clock(pd.Series([r["period_id"]]), pd.Series([r["start_time_s"]])).iloc[0]), 1),
            "t1": round(float(_clock(pd.Series([r["period_id"]]), pd.Series([r["end_time_s"]])).iloc[0]), 1),
            "team": 0 if int(r["team_id"]) == team_ids[0] else 1,
            "value": round(float(r["skm_sum"]), 5),
            "shot": bool(r["contains_shot"]),
            "goal": bool(r["contains_goal"]),
        }
        for _, r in gm.iterrows()
    ]

    return {
        "meta": {
            "game_id": int(game_id),
            "home": home_name,
            "away": away_name,
            "title": f"{home_name} vs {away_name}",
        },
        "actions": acts,
        "moments": moms,
    }


def render_html(data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    return _TEMPLATE.replace(DATA_TOKEN, payload)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Export SKM match replay HTML")
    parser.add_argument("--game-id", type=int, required=True)
    parser.add_argument("--output", default="replay.html")
    args = parser.parse_args(argv)

    actions = pd.read_parquet(ACTIONS_SCORED_PARQUET)
    events = pd.read_parquet(EVENTS_PARQUET) if EVENTS_PARQUET.exists() else None

    data = build_replay_data(args.game_id, actions, events)
    html = render_html(data)
    out = Path(args.output)
    out.write_text(html, encoding="utf-8")
    logger.info(
        "Wrote replay (%s actions, %s moments) → %s",
        len(data["actions"]),
        len(data["moments"]),
        out,
    )
    return 0


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SKM Match Replay</title>
<style>
:root{
  --bg:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --panel:#f0efec; --line:#d8d7d2;
  --pitch:#e8ece5; --pitch-line:#9aa294;
  --home:#2a78d6; --away:#1baf7a;
  --open:#2a78d6; --setp:#eda100; --trans:#1baf7a;
  --goal:#d03b3b;
}
@media (prefers-color-scheme: dark){:root{
  --bg:#1a1a19; --ink:#ffffff; --ink-2:#c3c2b7; --panel:#242423; --line:#3a3a37;
  --pitch:#20241f; --pitch-line:#5a6355;
  --home:#3987e5; --away:#199e70;
  --open:#3987e5; --setp:#c98500; --trans:#199e70;
}}
:root[data-theme="light"]{
  --bg:#fcfcfb; --ink:#0b0b0b; --ink-2:#52514e; --panel:#f0efec; --line:#d8d7d2;
  --pitch:#e8ece5; --pitch-line:#9aa294;
  --home:#2a78d6; --away:#1baf7a; --open:#2a78d6; --setp:#eda100; --trans:#1baf7a;
}
:root[data-theme="dark"]{
  --bg:#1a1a19; --ink:#ffffff; --ink-2:#c3c2b7; --panel:#242423; --line:#3a3a37;
  --pitch:#20241f; --pitch-line:#5a6355;
  --home:#3987e5; --away:#199e70; --open:#3987e5; --setp:#c98500; --trans:#199e70;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.wrap{max-width:1060px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:0 0 2px}
.sub{color:var(--ink-2);font-size:12px;margin-bottom:12px}
.grid{display:grid;grid-template-columns:minmax(0,2fr) minmax(240px,1fr);gap:14px}
@media(max-width:760px){.grid{grid-template-columns:1fr}}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px}
canvas{display:block;width:100%;border-radius:8px}
.scorebar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.score{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}
.clock{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums;color:var(--ink-2)}
.teams{font-size:13px;color:var(--ink-2)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:baseline}
.banner{display:flex;align-items:center;gap:8px;min-height:38px;padding:7px 10px;border-radius:8px;
  border:1px solid var(--line);margin-top:10px;font-weight:600}
.banner .chip{padding:2px 8px;border-radius:99px;font-size:11px;font-weight:700;color:#fff}
.banner.goalflash{outline:2px solid var(--goal)}
.ticker{margin-top:10px}
.ticker h3{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-2);margin:0 0 6px}
.bar{height:14px;border-radius:4px;margin:3px 0 8px;position:relative;background:transparent}
.bar i{position:absolute;left:0;top:0;bottom:0;border-radius:4px}
.bar span{position:absolute;right:6px;top:-1px;font-size:11px;font-variant-numeric:tabular-nums;color:var(--ink)}
.plist{list-style:none;margin:0;padding:0;font-variant-numeric:tabular-nums}
.plist li{display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px dashed var(--line);font-size:13px}
.plist li b{font-weight:600}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px}
button{background:var(--panel);border:1px solid var(--line);color:var(--ink);border-radius:8px;
  padding:6px 14px;font-size:14px;cursor:pointer}
button:hover{border-color:var(--ink-2)}
input[type=range]{flex:1;min-width:140px}
select,input[type=number]{background:var(--panel);color:var(--ink);border:1px solid var(--line);
  border-radius:6px;padding:4px 6px}
.videobox{margin-top:12px}
video{width:100%;border-radius:8px;background:#000;display:none}
.note{font-size:11px;color:var(--ink-2);margin-top:8px}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ink-2);margin-top:8px}
</style>
</head>
<body>
<div class="wrap">
  <h1 id="title">SKM Match Replay</h1>
  <div class="sub">Event-data replay (StatsBomb open data) — not broadcast footage.
    SKM moments are flagged live; numbers update as the match plays.</div>

  <div class="grid">
    <div class="panel">
      <div class="scorebar">
        <div class="teams"><span class="dot" style="background:var(--home)"></span><span id="homeName"></span></div>
        <div class="score" id="score">0 – 0</div>
        <div class="teams"><span id="awayName"></span><span class="dot" style="background:var(--away);margin:0 0 0 5px"></span></div>
      </div>
      <div class="clock" id="clock" style="text-align:center">00:00</div>
      <canvas id="pitch" width="840" height="560" aria-label="pitch replay"></canvas>
      <canvas id="timeline" width="840" height="56" style="margin-top:8px" aria-label="moment timeline"></canvas>
      <div class="legend">
        <span><span class="dot" style="background:var(--open)"></span>open play</span>
        <span><span class="dot" style="background:var(--trans)"></span>transition</span>
        <span><span class="dot" style="background:var(--setp)"></span>set piece</span>
        <span>◆ = moment with shot</span><span style="color:var(--goal)">▮ = goal</span>
      </div>
      <div class="controls">
        <button id="play">▶ Play</button>
        <label>Speed <select id="speed">
          <option value="5">5×</option><option value="15" selected>15×</option>
          <option value="40">40×</option><option value="90">90×</option>
        </select></label>
        <input type="range" id="scrub" min="0" max="5700" value="0" step="1" aria-label="scrub">
      </div>
      <div class="videobox panel" style="padding:10px">
        <b style="font-size:13px">Overlay on your own clip</b>
        <div class="note">Load a local video of this match (plays locally, nothing uploads).
          Set the offset = match clock at the clip's first frame; flags & tickers then sync to the video.</div>
        <div class="controls" style="margin-top:8px">
          <input type="file" id="vfile" accept="video/*">
          <label>Offset (s) <input type="number" id="voffset" value="0" step="1" style="width:80px"></label>
        </div>
        <video id="video" controls></video>
      </div>
    </div>

    <div class="panel">
      <div class="banner" id="banner"><span class="chip" style="background:var(--open)">—</span>
        <span id="bannerText">waiting…</span></div>
      <div class="ticker">
        <h3>Cumulative SKM</h3>
        <div class="teams" id="tHome"></div>
        <div class="bar"><i id="barHome" style="background:var(--home);width:0%"></i><span id="valHome">0</span></div>
        <div class="teams" id="tAway"></div>
        <div class="bar"><i id="barAway" style="background:var(--away);width:0%"></i><span id="valAway">0</span></div>
      </div>
      <div class="ticker">
        <h3>Top players by SKM (live)</h3>
        <ul class="plist" id="plist"></ul>
      </div>
      <div class="ticker">
        <h3>Current moment</h3>
        <ul class="plist" id="mstats">
          <li><span>Type</span><b id="msType">—</b></li>
          <li><span>Value so far</span><b id="msVal">0</b></li>
          <li><span>Actions</span><b id="msN">0</b></li>
        </ul>
      </div>
      <div class="note">SKM values are model outputs on open event data
        (VAEP ΔP × difficulty/context/role) — see repo docs for limits.</div>
    </div>
  </div>
</div>

<script>
const DATA = __SKM_REPLAY_DATA__;
const A = DATA.actions, M = DATA.moments;
const maxT = A.length ? A[A.length-1].t + 5 : 5700;
document.getElementById('title').textContent = 'SKM Match Replay — ' + DATA.meta.title;
document.getElementById('homeName').textContent = DATA.meta.home;
document.getElementById('awayName').textContent = DATA.meta.away;
document.getElementById('tHome').textContent = DATA.meta.home;
document.getElementById('tAway').textContent = DATA.meta.away;
document.getElementById('scrub').max = Math.ceil(maxT);

const momById = {}; M.forEach(m => momById[m.mid] = m);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const TYPEVAR = {open_play:'--open', set_piece:'--setp', transition:'--trans'};

let clock = 0, playing = false, idx = -1, last = null;
let cumHome = 0, cumAway = 0, playerTot = {}, score = [0,0];
let momVal = 0, momN = 0, curMid = -1;

function resetState(){ idx=-1; cumHome=0; cumAway=0; playerTot={}; score=[0,0]; momVal=0; momN=0; curMid=-1; }
function applyAction(a){
  if (a.team===0) cumHome+=a.skm; else cumAway+=a.skm;
  if (a.player){ playerTot[a.player]=(playerTot[a.player]||0)+a.skm; }
  if (a.mid!==curMid){ curMid=a.mid; momVal=0; momN=0; }
  momVal+=a.skm; momN++;
  if (a.goal) score[a.team]++;
}
function seek(t){
  if (idx>=0 && t < A[idx].t) resetState();
  while (idx+1 < A.length && A[idx+1].t <= t){ idx++; applyAction(A[idx]); }
  clock = t;
}

const P = document.getElementById('pitch'), pc = P.getContext('2d');
const TL = document.getElementById('timeline'), tc = TL.getContext('2d');
const SX = P.width/120, SY = P.height/80;

function drawPitch(){
  pc.fillStyle = css('--pitch'); pc.fillRect(0,0,P.width,P.height);
  pc.strokeStyle = css('--pitch-line'); pc.lineWidth = 2;
  pc.strokeRect(4,4,P.width-8,P.height-8);
  pc.beginPath(); pc.moveTo(P.width/2,4); pc.lineTo(P.width/2,P.height-4); pc.stroke();
  pc.beginPath(); pc.arc(P.width/2,P.height/2,60,0,7); pc.stroke();
  [[0,18,18,44],[102,18,18,44],[0,30,6,20],[114,30,6,20]].forEach(b=>{
    pc.strokeRect(b[0]*SX+ (b[0]===0?4:-4),b[1]*SY,b[2]*SX,b[3]*SY);
  });
}
function drawBall(){
  if (idx<0 || idx>=A.length) return;
  const a=A[idx], nt=(idx+1<A.length? A[idx+1].t : a.t+2);
  const f=Math.min(1,Math.max(0,(clock-a.t)/Math.max(0.4,nt-a.t)));
  const x=(a.x==null? 60 : a.x + ((a.ex==null?a.x:a.ex)-a.x)*f);
  const y=(a.y==null? 40 : a.y + ((a.ey==null?a.y:a.ey)-a.y)*f);
  const col = a.team===0? css('--home') : css('--away');
  pc.beginPath(); pc.arc(x*SX,y*SY,10,0,7); pc.fillStyle=col; pc.fill();
  pc.lineWidth=2; pc.strokeStyle=css('--bg'); pc.stroke();
  pc.font='600 13px sans-serif'; pc.fillStyle=css('--ink');
  const label=(a.player||'')+' · '+a.type;
  pc.fillText(label, Math.min(P.width-pc.measureText(label).width-8, Math.max(8,x*SX+14)), Math.max(16,y*SY-12));
}
function drawTimeline(){
  tc.fillStyle=css('--panel'); tc.fillRect(0,0,TL.width,TL.height);
  const w=TL.width/maxT;
  M.forEach(m=>{
    tc.fillStyle=css(TYPEVAR[m.type]||'--open');
    tc.globalAlpha=0.85;
    tc.fillRect(m.t0*w, m.team===0?8:32, Math.max(1.5,(m.t1-m.t0)*w), 16);
    tc.globalAlpha=1;
    if (m.goal){ tc.fillStyle=css('--goal'); tc.fillRect(m.t0*w-1, 4, 3, TL.height-8); }
    else if (m.shot){ tc.fillStyle=css('--ink'); tc.beginPath();
      const cx=m.t0*w+2, cy=m.team===0?6:52; tc.moveTo(cx,cy-3); tc.lineTo(cx+3,cy);
      tc.lineTo(cx,cy+3); tc.lineTo(cx-3,cy); tc.fill(); }
  });
  tc.fillStyle=css('--ink'); tc.fillRect(clock*w-1,0,2,TL.height);
}
function fmt(t){const m=Math.floor(t/60),s=Math.floor(t%60);return String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');}
function renderPanels(){
  document.getElementById('clock').textContent=fmt(clock);
  document.getElementById('score').textContent=score[0]+' – '+score[1];
  const span=Math.max(Math.abs(cumHome),Math.abs(cumAway),0.5);
  document.getElementById('barHome').style.width=(Math.max(0,cumHome)/span*100)+'%';
  document.getElementById('barAway').style.width=(Math.max(0,cumAway)/span*100)+'%';
  document.getElementById('valHome').textContent=cumHome.toFixed(2);
  document.getElementById('valAway').textContent=cumAway.toFixed(2);
  const top=Object.entries(playerTot).sort((a,b)=>b[1]-a[1]).slice(0,5);
  document.getElementById('plist').innerHTML=top.map(p=>'<li><span>'+p[0]+'</span><b>'+p[1].toFixed(3)+'</b></li>').join('');
  const m=momById[curMid], banner=document.getElementById('banner');
  if(m){
    const label=m.type.replace('_',' ');
    banner.querySelector('.chip').style.background=css(TYPEVAR[m.type]||'--open');
    banner.querySelector('.chip').textContent=label.toUpperCase();
    document.getElementById('bannerText').textContent=(m.team===0?DATA.meta.home:DATA.meta.away)
      +(m.goal?' — GOAL in this moment':(m.shot?' — shot in this moment':' moment'));
    banner.classList.toggle('goalflash', !!m.goal);
    document.getElementById('msType').textContent=label;
    document.getElementById('msVal').textContent=momVal.toFixed(3);
    document.getElementById('msN').textContent=momN;
  }
}
function render(){ drawPitch(); drawBall(); drawTimeline(); renderPanels(); }

let raf=null;
function loop(ts){
  if(last==null) last=ts;
  const dt=(ts-last)/1000; last=ts;
  if(playing && !videoDriven){ seek(Math.min(maxT, clock+dt*Number(speedEl.value)));
    scrub.value=clock; if(clock>=maxT) togglePlay(false); }
  render();
  raf=requestAnimationFrame(loop);
}
const speedEl=document.getElementById('speed'), scrub=document.getElementById('scrub');
const playBtn=document.getElementById('play');
function togglePlay(v){ playing=(v===undefined? !playing : v); playBtn.textContent=playing?'❚❚ Pause':'▶ Play'; }
playBtn.onclick=()=>togglePlay();
scrub.oninput=e=>{ seek(Number(e.target.value)); };

// Video sync mode
const video=document.getElementById('video'), vfile=document.getElementById('vfile'),
      voff=document.getElementById('voffset');
let videoDriven=false;
vfile.onchange=()=>{
  const f=vfile.files[0]; if(!f) return;
  video.src=URL.createObjectURL(f); video.style.display='block'; videoDriven=true; togglePlay(false);
};
video.addEventListener('timeupdate',()=>{ if(videoDriven) seek(Math.min(maxT, video.currentTime+Number(voff.value||0))); });

seek(0); raf=requestAnimationFrame(loop);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
