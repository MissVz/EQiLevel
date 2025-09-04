# app/api/v1/metrics_router.py
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from app.services.metrics import compute_metrics, compute_series

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get(
    "",
    responses={
        200: {
            "description": "Metrics snapshot",
            "content": {
                "application/json": {
                    "example": {
                        "turns_total": 12,
                        "avg_reward": 0.21,
                        "frustration_adaptation_rate": 0.78,
                        "tone_alignment_rate": 0.81,
                        "last_10_reward_avg": 0.25,
                        "by_emotion": {"frustrated": 5, "engaged": 4, "calm": 3, "bored": 0},
                        "action_distribution": {
                            "tone": {"warm": 5, "encouraging": 4, "neutral": 3, "concise": 0},
                            "pacing": {"slow": 5, "medium": 3, "fast": 4},
                            "difficulty": {"down": 5, "hold": 5, "up": 2},
                            "next_step": {"example": 5, "explain": 3, "quiz": 4, "prompt": 0, "review": 0}
                        },
                        "filters": {"session_id": "s3", "since_minutes": 60, "window_start_utc": "2025-09-02T20:51:30Z"}
                    }
                }
            },
        }
    },
)
def get_metrics(
    session_id: Optional[str] = Query(
        None,
        example="s3",
        description="Filter metrics by session ID"
    ),
    since_minutes: Optional[int] = Query(
        None,
        ge=1,
        example=60,
        description="Only include turns from the last N minutes"
    ),
    since_hours: Optional[int] = Query(
        None,
        ge=1,
        example=24,
        description="Only include turns from the last N hours (converted to minutes if since_minutes not provided)"
    ),
):
    # prefer since_minutes; otherwise convert hours → minutes
    if since_minutes is None and since_hours is not None:
        since_minutes = since_hours * 60

    return compute_metrics(session_id=session_id, since_minutes=since_minutes)

@router.get(
    "/series",
    responses={
        200: {
            "description": "Time series for dashboard charts",
            "content": {"application/json": {"example": {
                "bucket": "minute",
                "since_minutes": 240,
                "window_start_utc": "2025-09-02T20:51:30Z",
                "session_id": "s3",
                "points": [
                    {"ts":"2025-09-02T20:10:00Z","turns":4,"avg_reward":0.23,"frustrated":1},
                    {"ts":"2025-09-02T20:11:00Z","turns":2,"avg_reward":0.17,"frustrated":0},
                ]
            }}}
        }
    }
)
def get_series(
    session_id: Optional[str] = Query(
        None, example="s3", description="Filter series by session ID"
    ),
    bucket: str = Query(
        "minute", pattern="^(minute|hour)$", description="Time bucket for aggregation"
    ),
    since_minutes: int = Query(
        240, ge=1, example=240, description="Window size in minutes (default 4 hours)"
    ),
):
    return compute_series(session_id=session_id, since_minutes=since_minutes, bucket=bucket)

@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def metrics_dashboard():
    """
    Minimal HTML dashboard (no templates required).
    """
    return HTML_TEMPLATE

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>EQīLevel Metrics</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    :root { --fg:#0b132b; --muted:#6c7a89; --good:#2a9d8f; --warn:#e9c46a; --bad:#e76f51; --blue:#3a86ff;}
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji"; margin: 24px; color: var(--fg);}
    h1 { margin: 0 0 6px 0; font-size: 20px;}
    .sub { color: var(--muted); margin-bottom: 16px; }
    .row { display: flex; gap: 16px; flex-wrap: wrap; }
    .card { border: 1px solid #eee; border-radius: 10px; padding: 12px 14px; min-width: 220px; }
    .kpi { font-size: 26px; font-weight: 700; margin-top: 6px;}
    .kpi small { font-size: 12px; color: var(--muted); font-weight: 400; }
    .form { display:flex; gap:10px; align-items:flex-end; margin: 10px 0 18px;}
    label { font-size:12px; color: var(--muted); display:block; margin-bottom:4px;}
    input, select, button { padding: 8px 10px; border:1px solid #ddd; border-radius:6px; }
    button { background: var(--blue); color:white; border:none; cursor:pointer; }
    canvas { background: #fff; border: 1px solid #eee; border-radius: 10px; padding: 12px; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    table { border-collapse: collapse; font-size: 13px;}
    td { padding:2px 6px;}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
</head>
<body>
  <h1>EQīLevel Metrics</h1>
  <div class="sub">Snapshot + live charts from <code>/api/v1/metrics</code> and <code>/api/v1/metrics/series</code></div>
  <div class="form">
    <div>
      <label>Session ID (optional)</label>
      <input id="sessionId" placeholder="e.g., s3" />
    </div>
    <div>
      <label>Since (minutes)</label>
      <input id="since" type="number" min="1" value="240" />
    </div>
    <div>
      <label>Bucket</label>
      <select id="bucket">
        <option value="minute" selected>minute</option>
        <option value="hour">hour</option>
      </select>
    </div>
    <button onclick="loadAll()">Refresh</button>
  </div>

  <div class="row">
    <div class="card">
      <div>Turns</div>
      <div class="kpi" id="kpiTurns">–</div>
    </div>
    <div class="card">
      <div>Avg Reward</div>
      <div class="kpi" id="kpiAvg">–</div>
    </div>
    <div class="card">
      <div>Frustration Adaptation</div>
      <div class="kpi" id="kpiAdapt">– <small>rate</small></div>
    </div>
    <div class="card">
      <div>Tone Alignment</div>
      <div class="kpi" id="kpiTone">– <small>rate</small></div>
    </div>
  </div>

  <div class="grid" style="margin-top:16px;">
    <canvas id="chartAvg"></canvas>
    <canvas id="chartTurns"></canvas>
  </div>

  <div style="margin-top:16px;">
    <div class="card">
      <div style="font-weight:600;margin-bottom:6px;">Emotion / Action breakdowns</div>
      <div class="row">
        <div>
          <table id="tblEmotion"></table>
        </div>
        <div>
          <table id="tblActions"></table>
        </div>
      </div>
    </div>
  </div>

<script>
let chartAvg, chartTurns;
function q(id){ return document.getElementById(id); }
function fmtPct(v){ return (v*100).toFixed(1)+'%'; }

async function fetchJSON(url){
  const r = await fetch(url);
  if(!r.ok) throw new Error(await r.text());
  return r.json();
}
function params(){
  const s = new URLSearchParams();
  const sess = q('sessionId').value.trim();
  const mins = parseInt(q('since').value,10);
  const bucket = q('bucket').value;
  if(sess) s.set('session_id', sess);
  if(mins) s.set('since_minutes', mins);
  return { search: s.toString(), bucket };
}
async function loadSnapshot(){
  const { search } = params();
  const data = await fetchJSON(`/api/v1/metrics?${search}`);
  q('kpiTurns').innerText = data.turns_total;
  q('kpiAvg').innerText = Number(data.avg_reward || 0).toFixed(3);
  q('kpiAdapt').innerHTML = fmtPct(data.frustration_adaptation_rate || 0) + ' <small>rate</small>';
  q('kpiTone').innerHTML = fmtPct(data.tone_alignment_rate || 0) + ' <small>rate</small>';

  // breakdowns
  const emo = data.by_emotion || {};
  const ad = data.action_distribution || {};
  q('tblEmotion').innerHTML = Object.entries(emo).map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('');
  const flat = [
    ...Object.entries(ad.tone || {}).map(([k,v])=>['tone.'+k,v]),
    ...Object.entries(ad.pacing || {}).map(([k,v])=>['pacing.'+k,v]),
    ...Object.entries(ad.difficulty || {}).map(([k,v])=>['difficulty.'+k,v]),
    ...Object.entries(ad.next_step || {}).map(([k,v])=>['next_step.'+k,v]),
  ];
  q('tblActions').innerHTML = flat.map(([k,v])=>`<tr><td>${k}</td><td>${v}</td></tr>`).join('');
}
async function loadSeries(){
  const { search, bucket } = params();
  const data = await fetchJSON(`/api/v1/metrics/series?bucket=${bucket}&${search}`);
  const xs = (data.points || []).map(p => p.ts);
  const avg = (data.points || []).map(p => p.avg_reward);
  const turns = (data.points || []).map(p => p.turns);

  if(chartAvg) chartAvg.destroy();
  if(chartTurns) chartTurns.destroy();

  const common = { type:'line', options:{ responsive:true, scales:{ x:{ ticks:{ maxRotation:0, autoSkip:true } }}}};

  chartAvg = new Chart(document.getElementById('chartAvg').getContext('2d'), {
    ...common,
    data:{ labels: xs, datasets:[{ label:'Avg Reward', data: avg, borderColor:'#2a9d8f', fill:false, tension:0.25 }] }
  });
  chartTurns = new Chart(document.getElementById('chartTurns').getContext('2d'), {
    ...common,
    data:{ labels: xs, datasets:[{ label:'Turns', data: turns, borderColor:'#3a86ff', fill:false, tension:0.25 }] }
  });
}
async function loadAll(){
  try {
    await Promise.all([loadSnapshot(), loadSeries()]);
  } catch (e) {
    alert('Failed to load metrics. Is the API running and seeded?\n\n'+e);
  }
}
loadAll();
</script>
</body>
</html>
"""
