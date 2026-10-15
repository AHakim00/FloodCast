"""
GeoJSON Flood Depth API Router.

Serves hourly ICM 2D contour GeoJSON files as clean REST API endpoints,
mirroring public forecast API conventions.

Endpoints:
    GET /api/v1/flood-depth               -- list all available timesteps
    GET /api/v1/flood-depth/latest        -- most recent GeoJSON data
    GET /api/v1/flood-depth/{timestep}    -- specific timestep (e.g. 0930)
    GET /api/v1/flood-depth/view          -- browser-friendly HTML viewer
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from app.config import GEOJSON_DIR

logger = logging.getLogger("flood.geojson")

router = APIRouter(prefix="/api/v1/flood-depth", tags=["Flood Depth GeoJSON"])

TIMEZONE = "Asia/Kuching"
TIMEZONE_ABBR = "MYT"
GEOJSON_PATH = Path(GEOJSON_DIR)

# Accepted file names (the date format is used to parse the date part):
#   DTM_YYYYMMDDTHHMM.geojson        e.g. DTM_20260911T0930.geojson
#   FloodContours_YYMMDD_HHMM.geojson e.g. FloodContours_260826_1000.geojson
_PATTERNS = [
    (re.compile(r"DTM_(\d{8})T(\d{4})\.geojson$", re.IGNORECASE), "%Y%m%d"),
    (re.compile(r"FloodContours_(\d{6})_(\d{4})\.geojson$", re.IGNORECASE), "%y%m%d"),
    (re.compile(r"FloodContours_(\d{8})_(\d{4})\.geojson$", re.IGNORECASE), "%Y%m%d"),
]


def _list_geojson_files() -> list:
    """Return all hourly GeoJSON files sorted by timestamp, excluding Maxima."""
    files = [
        f for f in GEOJSON_PATH.glob("*.geojson")
        if "Maxima" not in f.name and _parse_timestep(f.name) is not None
    ]
    return sorted(files, key=lambda f: _parse_timestep(f.name)["iso"])


def _parse_timestep(filename: str):
    """Parse filename into metadata dict (None if the name is not recognised)."""
    for pattern, date_fmt in _PATTERNS:
        m = pattern.match(filename)
        if m:
            break
    else:
        return None
    date_str, time_str = m.group(1), m.group(2)
    try:
        dt = datetime.strptime(date_str + time_str, date_fmt + "%H%M").replace(
            tzinfo=ZoneInfo(TIMEZONE)
        )
    except ValueError:
        return None
    return {
        "timestep": time_str,
        "localDate": dt.strftime("%d %b %Y"),
        "localTime": dt.strftime("%I:%M %p"),
        "iso": dt.isoformat(),
        "filename": filename,
    }


def _build_response(geojson_path: Path) -> dict:
    """Load a GeoJSON file and wrap it in the standard API envelope."""
    if not geojson_path.exists():
        raise HTTPException(status_code=404, detail=f"GeoJSON file not found: {geojson_path.name}")

    meta = _parse_timestep(geojson_path.name)
    if meta is None:
        raise HTTPException(status_code=500, detail="Could not parse timestep from filename.")

    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    feature_count = len(geojson_data.get("features", []))

    return {
        "label": "FLOOD DEPTH FORECAST",
        "source": "InfoWorks ICM 2D Surface Model",
        "timezone": TIMEZONE,
        "timezoneAbbreviation": TIMEZONE_ABBR,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "timestep": meta["timestep"],
        "localTime": meta["localTime"],
        "localDate": meta["localDate"],
        "featureCount": feature_count,
        "units": "metres",
        "data": geojson_data,
    }

# ---------------------------------------------------------------------------
# HTML Viewer
# ---------------------------------------------------------------------------

@router.get("/view", response_class=HTMLResponse, summary="Browser-friendly API viewer")
async def view_api():
    """Render an interactive HTML page for browsing the flood depth API."""
    files = _list_geojson_files()
    timestep_options = ""
    for f in files:
        meta = _parse_timestep(f.name)
        if meta:
            label = f"{meta['localDate']} {meta['localTime']} ({meta['timestep']})"
            timestep_options += f'<option value="{meta["timestep"]}">{label}</option>\n'

    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flood Depth API Viewer</title>
    <link rel="icon" type="image/png" href="/Bimage-mark.png">
    <link rel="apple-touch-icon" href="/Bimage-mark.png">
    <link rel="alternate icon" href="/favicon.ico">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        :root{--bg:#0d1117;--surface:#161b22;--border:#30363d;--accent:#1f6feb;--accent2:#388bfd;--success:#3fb950;--danger:#f85149;--text:#e6edf3;--muted:#8b949e;--radius:8px}
        body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;flex-direction:column}
        header{background:var(--surface);border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;gap:1rem}
        .badge{background:linear-gradient(135deg,#1f6feb,#388bfd);color:#fff;padding:.25rem .75rem;border-radius:999px;font-size:.72rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase}
        .title{font-size:1.05rem;font-weight:600}
        .sub{font-size:.8rem;color:var(--muted);margin-left:auto}
        main{flex:1;max-width:1100px;width:100%;margin:0 auto;padding:2rem 1.5rem}
        .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem;margin-bottom:2rem}
        .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1rem 1.25rem;transition:border-color .2s}
        .card:hover{border-color:var(--accent)}
        .method{display:inline-block;background:rgba(63,185,80,.15);color:var(--success);border:1px solid rgba(63,185,80,.3);font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600;padding:.1rem .4rem;border-radius:4px;margin-right:.4rem;vertical-align:middle}
        .ep{font-family:'JetBrains Mono',monospace;font-size:.82rem;color:var(--accent2);vertical-align:middle}
        .desc{font-size:.8rem;color:var(--muted);margin-top:.4rem}
        .try-link{display:inline-block;margin-top:.6rem;padding:.3rem .7rem;background:rgba(31,111,235,.15);border:1px solid rgba(31,111,235,.3);color:var(--accent2);border-radius:5px;font-size:.75rem;cursor:pointer;transition:background .2s;text-decoration:none}
        .try-link:hover{background:rgba(31,111,235,.3)}
        .panel{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1.25rem 1.5rem;margin-bottom:1.5rem}
        .panel h2{font-size:.85rem;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:1rem}
        .row{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap}
        select,input{background:#0d1117;border:1px solid var(--border);color:var(--text);border-radius:var(--radius);padding:.5rem .75rem;font-family:'JetBrains Mono',monospace;font-size:.82rem;outline:none;transition:border-color .2s}
        select:focus,input:focus{border-color:var(--accent)}
        select{min-width:280px}
        .btn{padding:.5rem 1.25rem;background:var(--accent);color:#fff;border:none;border-radius:var(--radius);font-family:'Inter',sans-serif;font-size:.85rem;font-weight:600;cursor:pointer;transition:background .2s,transform .1s}
        .btn:hover{background:var(--accent2)}
        .btn:active{transform:scale(.97)}
        .btn-outline{background:transparent;color:var(--success);border:1px solid var(--success);padding:.5rem 1rem;border-radius:var(--radius);font-size:.82rem;font-weight:600;cursor:pointer;transition:background .2s}
        .btn-outline:hover{background:rgba(63,185,80,.1)}
        .resp-wrap{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}
        .resp-head{display:flex;align-items:center;justify-content:space-between;padding:.75rem 1.25rem;border-bottom:1px solid var(--border);background:rgba(255,255,255,.02)}
        .resp-left{display:flex;align-items:center;gap:.75rem;font-size:.82rem}
        .pill{display:inline-block;padding:.15rem .5rem;border-radius:4px;font-size:.72rem;font-weight:600;font-family:'JetBrains Mono',monospace}
        .ok{background:rgba(63,185,80,.15);color:var(--success);border:1px solid rgba(63,185,80,.3)}
        .err{background:rgba(248,81,73,.15);color:var(--danger);border:1px solid rgba(248,81,73,.3)}
        .copy-btn{padding:.25rem .6rem;background:transparent;border:1px solid var(--border);color:var(--muted);border-radius:5px;font-size:.75rem;cursor:pointer;transition:color .2s,border-color .2s}
        .copy-btn:hover{color:var(--text);border-color:var(--muted)}
        #resp-url{font-family:'JetBrains Mono',monospace;font-size:.75rem;color:var(--muted)}
        #resp-body{margin:0;padding:1.25rem 1.5rem;font-family:'JetBrains Mono',monospace;font-size:.78rem;line-height:1.7;white-space:pre-wrap;word-break:break-all;max-height:580px;overflow-y:auto;color:var(--text)}
        .jk{color:#79c0ff}.js{color:#a5d6ff}.jn{color:#f0883e}.jb{color:#ff7b72}.jnu{color:var(--muted)}
        .meta{display:flex;gap:1.5rem;padding:.5rem 1.25rem;border-top:1px solid var(--border);background:rgba(255,255,255,.015);flex-wrap:wrap}
        .mi{font-size:.74rem;color:var(--muted)}
        .mi span{color:var(--text);font-weight:500}
        .spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.15);border-top-color:var(--accent2);border-radius:50%;animation:spin .6s linear infinite}
        @keyframes spin{to{transform:rotate(360deg)}}
        .ph{color:var(--muted);font-style:italic;padding:2rem 1.5rem;font-size:.85rem;text-align:center}
        footer{text-align:center;padding:1.5rem;font-size:.75rem;color:var(--muted);border-top:1px solid var(--border)}
    </style>
</head>
<body>
<header>
    <span class="badge">API</span>
    <span class="title">Flood Depth GeoJSON API</span>
    <span class="sub">InfoWorks ICM 2D Surface Model &mdash; Hourly Updates</span>
</header>
<main>
    <div class="grid">
        <div class="card">
            <span class="method">GET</span><span class="ep">/api/v1/flood-depth</span>
            <div class="desc">List all available hourly timesteps.</div>
            <a class="try-link" href="/api/v1/flood-depth" target="_blank">Open in new tab &#8599;</a>
        </div>
        <div class="card">
            <span class="method">GET</span><span class="ep">/api/v1/flood-depth/latest</span>
            <div class="desc">Returns the most recent hourly GeoJSON flood depth data.</div>
            <a class="try-link" href="/api/v1/flood-depth/latest" target="_blank">Open in new tab &#8599;</a>
        </div>
        <div class="card">
            <span class="method">GET</span><span class="ep">/api/v1/flood-depth/{timestep}</span>
            <div class="desc">Returns GeoJSON for a specific timestep, e.g. <code>0930</code>, <code>1030</code>.</div>
        </div>
    </div>
    <div class="panel">
        <h2>Try It</h2>
        <div class="row">
            <select id="ts-sel">
                <option value="">-- Select a timestep --</option>
                TIMESTEP_OPTIONS
            </select>
            <button class="btn" onclick="fetchTs()">Fetch</button>
            <button class="btn-outline" onclick="fetchLatest()">&#x26A1; Latest</button>
        </div>
    </div>
    <div class="resp-wrap">
        <div class="resp-head">
            <div class="resp-left">
                <div id="status-badge"></div>
                <div id="resp-url"></div>
            </div>
            <button class="copy-btn" onclick="copyResp()">Copy JSON</button>
        </div>
        <pre id="resp-body"><span class="ph">Select a timestep above and click Fetch to see the API response.</span></pre>
        <div class="meta" id="meta" style="display:none">
            <div class="mi">Features: <span id="m-feat">-</span></div>
            <div class="mi">Timestep: <span id="m-ts">-</span></div>
            <div class="mi">Local Time: <span id="m-time">-</span></div>
            <div class="mi">Generated: <span id="m-gen">-</span></div>
        </div>
    </div>
</main>
<footer>Flood Depth GeoJSON API &mdash; Powered by InfoWorks ICM &amp; FastAPI</footer>
<script>
let _last=null;
var chr34=String.fromCharCode(34),chr92=String.fromCharCode(92);
function hl(json){
    json=json.replace(/&/g,"\u0026amp;").replace(/</g,"\u0026lt;").replace(/>/g,"\u0026gt;");
    var r="",i=0,n=json.length;
    while(i<n){
        if(json[i]===chr34){var j=i+1;while(j<n&&json[j]!==chr34){if(json[j]===chr92)j++;j++;}j++;var tok=json.slice(i,j);var rest=json.slice(j);var af=rest.match(/^[ \t]*:/);if(af){r+="<span class=jk>"+tok+af[0]+"</span>";i=j+af[0].length;}else{r+="<span class=js>"+tok+"</span>";i=j;}}
        else{var m2=json.slice(i).match(/^(true|false|null|-?[0-9]+[.0-9]*)/);if(m2){var c2={"true":"jb","false":"jb","null":"jnu"}[m2[1]]||"jn";r+="<span class="+c2+">"+m2[1]+"</span>";i+=m2[1].length;}else{r+=json[i];i++;}}
    }
    return r;
}
function setSt(ok,txt){document.getElementById('status-badge').innerHTML='<span class="pill '+(ok?'ok':'err')+'">'+txt+'</span>';}
async function doFetch(url){
    document.getElementById('resp-url').textContent=url;
    document.getElementById('resp-body').innerHTML='<div style="padding:1.5rem;text-align:center"><div class="spinner"></div></div>';
    document.getElementById('meta').style.display='none';
    setSt(true,'...');
    try{
        const t0=Date.now();
        const res=await fetch(url);
        const ms=Date.now()-t0;
        const data=await res.json();
        _last=data;
        setSt(res.ok,res.status+' '+(res.ok?'OK':'ERR')+' \u00B7 '+ms+'ms');
        const prev=Object.assign({},data);
        if(prev.data&&prev.data.features){prev.data={...prev.data,features:'['+prev.data.features.length+' features - use raw endpoint for full GeoJSON]'};}
        document.getElementById('resp-body').innerHTML=hl(JSON.stringify(res.ok?prev:data,null,2));
        if(res.ok&&data.featureCount!==undefined){
            document.getElementById('m-feat').textContent=data.featureCount.toLocaleString();
            document.getElementById('m-ts').textContent=data.timestep||'-';
            document.getElementById('m-time').textContent=(data.localTime||'')+' '+(data.localDate||'');
            document.getElementById('m-gen').textContent=data.generatedAt?new Date(data.generatedAt).toLocaleString():'-';
            document.getElementById('meta').style.display='flex';
        }
    }catch(e){setSt(false,'ERR');document.getElementById('resp-body').innerHTML='<span style="color:var(--danger);padding:1rem 1.5rem;display:block">Error: '+e.message+'</span>';}
}
function fetchTs(){const ts=document.getElementById('ts-sel').value;if(!ts){alert('Please select a timestep.');return;}doFetch('/api/v1/flood-depth/'+ts);}
function fetchLatest(){doFetch('/api/v1/flood-depth/latest');}
function copyResp(){if(!_last)return;navigator.clipboard.writeText(JSON.stringify(_last,null,2)).then(()=>{const b=document.querySelector('.copy-btn');b.textContent='Copied!';setTimeout(()=>b.textContent='Copy JSON',1500)}).catch(()=>alert('Copy failed.'));}
</script>
</body>
</html>"""
    html = html.replace("TIMESTEP_OPTIONS", timestep_options)
    return HTMLResponse(content=html, status_code=200)


# ---------------------------------------------------------------------------
# JSON Endpoints
# ---------------------------------------------------------------------------

@router.get("", summary="List all available flood depth timesteps")
async def list_timesteps():
    """Return metadata for all available hourly GeoJSON flood depth files."""
    files = _list_geojson_files()
    timesteps = []
    for f in files:
        meta = _parse_timestep(f.name)
        if meta:
            timesteps.append({
                "timestep": meta["timestep"],
                "localTime": meta["localTime"],
                "localDate": meta["localDate"],
                "iso": meta["iso"],
                "endpoint": f"/api/v1/flood-depth/{meta['timestep']}",
                "filename": meta["filename"],
            })

    return {
        "label": "FLOOD DEPTH FORECAST",
        "source": "InfoWorks ICM 2D Surface Model",
        "timezone": TIMEZONE,
        "timezoneAbbreviation": TIMEZONE_ABBR,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "availableTimesteps": len(timesteps),
        "timesteps": timesteps,
        "viewer": "/api/v1/flood-depth/view",
    }


@router.get("/latest", summary="Get the latest flood depth GeoJSON")
async def get_latest():
    """Return the most recently generated flood depth GeoJSON file."""
    files = _list_geojson_files()
    if not files:
        raise HTTPException(status_code=404, detail="No flood depth GeoJSON files available.")
    return _build_response(files[-1])


@router.get("/{timestep}", summary="Get flood depth GeoJSON for a specific timestep")
async def get_by_timestep(timestep: str):
    """
    Return flood depth GeoJSON for a given HHMM timestep string (e.g. 0930, 1030).
    """
    files = _list_geojson_files()
    matches = [f for f in files if (meta := _parse_timestep(f.name)) and meta["timestep"] == timestep]
    if not matches:
        available = [m["timestep"] for f in files if (m := _parse_timestep(f.name))]
        raise HTTPException(
            status_code=404,
            detail=f"No GeoJSON found for timestep '{timestep}'. Available: {available}",
        )
    return _build_response(matches[-1])