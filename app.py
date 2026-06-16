#!/usr/bin/env python3
"""
Gaula Control Center — Streamlit App
Scraper elveguiden.no + NVE vandføring live
"""

import streamlit as st
import requests
import json
from datetime import date, datetime, timedelta
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ─── CONFIG ───────────────────────────────────────────────────────────────────
RIVER_ID   = 25
PAGE_SIZE  = 50
API_CATCHES = "https://api.elveguiden.no/api/v2/catches/latest-catches"
API_STATS   = "https://api.elveguiden.no/api/v1/catches/stats"
NVE_URL     = "https://hydapi.nve.no/api/v1/Observations"
NVE_STATION = "122.9.0"
NVE_API_KEY = "rl7qiEo77ECT+9Bm4smjSQ=="

HEADERS = {
    "x-setlanguage": "nb",
    "accept":        "application/json",
    "content-type":  "application/json",
    "referer":       "https://elveguiden.no/",
    "user-agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

import pytz
TZ = pytz.timezone("Europe/Oslo")
NOW_LOCAL = datetime.now(TZ)
TODAY = NOW_LOCAL.date()
CUR_YEAR = TODAY.year

# Auto-refresh hvert minutut (180.000 ms)
count = count = st_autorefresh(interval=60_000, key="auto_refresh")

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Gaula Control Center",
    page_icon="🐟",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Page Visibility API: reload når bruger kommer tilbage til appen
st.markdown("""
<script>
(function() {
    // Reload når siden bliver synlig igen efter at have været i baggrunden
    var hiddenAt = null;

    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            hiddenAt = Date.now();
        } else {
            // Hvis siden har været skjult i mere end 60 sekunder → reload
            if (hiddenAt && (Date.now() - hiddenAt) > 60000) {
                window.location.reload();
            }
            hiddenAt = null;
        }
    });

    // Samme trick via pageshow (iOS Safari PWA)
    window.addEventListener('pageshow', function(e) {
        if (e.persisted) {
            // Side kom fra bfcache — tving reload
            window.location.reload();
        }
    });

    // Focus-event som backup
    window.addEventListener('focus', function() {
        if (hiddenAt && (Date.now() - hiddenAt) > 60000) {
            window.location.reload();
        }
    });
})();
</script>
""", unsafe_allow_html=True)

# No-cache meta tags — tvinger Safari PWA til ikke at cache siden
st.markdown("""
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
""", unsafe_allow_html=True)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main { background: #f8fafb; padding: 0; }
    
    /* Mobile-first padding */
    .block-container { 
        padding: 0.5rem 0.75rem 2rem 0.75rem !important; 
        max-width: 100% !important; 
    }
    
    /* Hide Streamlit top decorations on mobile */
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }

    /* Header */
    .gc-header {
        display: flex; align-items: center; justify-content: space-between;
        border-bottom: 2px solid #1a6b4a;
        padding: 10px 0 8px 0; margin-bottom: 12px;
    }
    .gc-title { font-size: 18px; font-weight: 700; color: #1a6b4a; margin: 0; }
    .gc-subtitle { font-size: 12px; color: #888; margin: 0; }
    .gc-meta { font-size: 10px; color: #aaa; line-height: 1.6; margin-bottom: 8px; }
    
    /* KPI grid — 2 columns on mobile */
    .kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 8px;
    }
    .kpi-grid-4 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-bottom: 8px;
    }
    .kpi-grid-3 {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 8px;
        margin-bottom: 8px;
    }

    /* KPI cards */
    .kpi-card {
        background: white;
        border: 1px solid #e8f0eb;
        border-radius: 10px;
        padding: 10px 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    .kpi-card-hero {
        background: white;
        border: 1px solid #e8f0eb;
        border-left: 4px solid #1a6b4a;
        border-radius: 10px;
        padding: 10px 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        grid-column: span 2;
    }
    .kpi-label { 
        font-size: 10px; font-weight: 600; color: #888; 
        text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2px; 
    }
    .kpi-value { font-size: 28px; font-weight: 700; color: #1a1a2e; line-height: 1.1; }
    .kpi-value-lg { font-size: 42px; font-weight: 800; color: #1a6b4a; }
    .kpi-value-sm { font-size: 22px; font-weight: 700; color: #1a1a2e; line-height: 1.1; }
    .kpi-sub { font-size: 11px; color: #aaa; margin-top: 2px; }
    
    /* Delta */
    .delta-pos { color: #1a6b4a; font-size: 22px; font-weight: 700; }
    .delta-neg { color: #c0392b; font-size: 22px; font-weight: 700; }
    .delta-pct-pos { color: #1a6b4a; font-size: 12px; font-weight: 500; }
    .delta-pct-neg { color: #c0392b; font-size: 12px; font-weight: 500; }
    
    /* YTD bar */
    .ytd-bar-bg { background: #e8f0eb; border-radius: 4px; height: 5px; margin-top: 6px; }
    .ytd-bar-fill { background: #1a6b4a; border-radius: 4px; height: 5px; }
    .ytd-bar-fill-25 { background: #4a9b6f; border-radius: 4px; height: 5px; }
    .ytd-bar-fill-24 { background: #8bc4a0; border-radius: 4px; height: 5px; }
    
    /* Section headers */
    .section-header {
        display: flex; align-items: center; gap: 8px;
        font-size: 13px; font-weight: 600; color: #1a1a2e;
        margin: 16px 0 8px 0;
        border-left: 3px solid #1a6b4a;
        padding-left: 8px;
    }
    .count-badge {
        background: #1a6b4a; color: white;
        font-size: 10px; font-weight: 600;
        padding: 2px 6px; border-radius: 10px;
    }
    
    /* Table — smaller font on mobile */
    .stDataFrame { border: 1px solid #e8f0eb; border-radius: 8px; overflow: hidden; }
    .stDataFrame td, .stDataFrame th { font-size: 12px !important; }
    
    /* NVE card */
    .nve-value { font-size: 26px; font-weight: 700; color: #1a6b4a; }
    
    /* Footer */
    .gc-footer {
        text-align: center; font-size: 10px; color: #bbb;
        margin-top: 24px; padding-top: 10px;
        border-top: 1px solid #eee;
    }
    
    div[data-testid="stMetric"] { display: none; }
    .horg-row { background: #fff8f0 !important; }

    /* Streamlit column gaps tighter on mobile */
    [data-testid="column"] { padding: 0 3px !important; }
    
    /* Selectbox smaller */
    .stSelectbox label { font-size: 12px !important; }

    /* Desktop overrides */
    @media (min-width: 768px) {
        .block-container { padding: 1rem 1.5rem 2rem 1.5rem !important; }
        .kpi-grid-4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
        .kpi-grid-3 { grid-template-columns: 1fr 1fr 1fr; }
        .kpi-card-hero { grid-column: span 1; }
        .kpi-value-lg { font-size: 48px; }
        .kpi-value { font-size: 36px; }
        .kpi-value-sm { font-size: 28px; }
        .kpi-label { font-size: 11px; }
        .gc-title { font-size: 22px; }
    }
</style>
""", unsafe_allow_html=True)

# ─── API FUNCTIONS ─────────────────────────────────────────────────────────────
def to_danish(d):
    if not d or "-" not in d: return d
    p = d[:10].split("-")
    return f"{p[2]}.{p[1]}.{p[0]}"

def parse_datetime(raw):
    """
    Returnerer (dato_iso, tid_str) fra API-datofelter.
    Håndterer: '2026-06-16T04:22:00.000000Z', '2026-06-16T06:22:00+02:00', '2026-06-16', None
    Konverterer UTC → norsk sommertid (CEST = UTC+2).
    """
    if not raw:
        return "", ""
    try:
        from datetime import timezone, timedelta
        s = str(raw).strip()
        # Kun dato
        if len(s) == 10:
            return s, ""
        # Har tidsdel
        if "T" in s:
            # Normaliser: fjern mikrosekunder, håndter Z og +offset
            s_clean = s.replace("Z", "+00:00")
            # Python 3.7+ kan parse ISO 8601 med offset
            try:
                from datetime import datetime as dt
                parsed = dt.fromisoformat(s_clean)
                # Konverter til CEST (UTC+2)
                cest = timezone(timedelta(hours=2))
                parsed_local = parsed.astimezone(cest)
                dato_iso = parsed_local.strftime("%Y-%m-%d")
                tid_str  = parsed_local.strftime("%H:%M")
                return dato_iso, tid_str
            except:
                # Fallback: tag første 10 og 11:16 som UTC
                return s[:10], s[11:16]
        return s[:10], ""
    except:
        return "", ""

def fetch_page(year, page):
    body = {
        "page": page, "river_id": RIVER_ID, "year": year,
        "orderBy": "date", "order": "desc",
        "equipment_filter": [], "fish_type_filter": [],
        "catch_release_filter": [], "boat_filter": [],
        "limit": PAGE_SIZE
    }
    try:
        r = requests.post(API_CATCHES, json=body, headers=HEADERS, timeout=20)
        if not r.ok: return None, 0
        data = r.json()
        catches_obj = data.get("data", {}).get("catches", {})
        return catches_obj.get("data", []), catches_obj.get("last_page", 1)
    except:
        return None, 0

def parse_catch(item):
    try:
        cid = int(item.get("id", 0))
        if not cid: return None
        # Prøv alle mulige datofelter i API'et
        raw_date = (item.get("date") or item.get("caught_at") or
                    item.get("created_at") or item.get("updated_at") or "")
        dato_iso, tid = parse_datetime(raw_date)
        # Tid ligger i time_of_day feltet
        if not tid:
            raw_time = (item.get("time_of_day") or item.get("time") or 
                        item.get("catch_time") or item.get("hour") or "")
            if raw_time:
                tid = str(raw_time)[:5]
        if not dato_iso: return None
        dato = to_danish(dato_iso)
        if not dato: return None
        parts = dato.split(".")
        yr = int(parts[2]) if len(parts) == 3 else CUR_YEAR

        fisker = item.get("fisher_name", "") or ""
        if not fisker.strip():
            u = item.get("user") or {}
            fisker = f"{u.get('first_name','')} {u.get('last_name','')}".strip()

        beat = item.get("beat") or {}
        vald = beat.get("name", "") if isinstance(beat, dict) else str(beat)

        vaegt = item.get("weight")
        lgd = item.get("length")
        try: vaegt = float(vaegt) if vaegt is not None else None
        except: vaegt = None
        try: lgd = int(lgd) if lgd is not None else None
        except: lgd = None

        ft = item.get("fish_type") or {}
        art = ft.get("name_no", "Laks") if isinstance(ft, dict) else "Laks"

        eq = item.get("equipment") or {}
        redskab = eq.get("name_no", "") if isinstance(eq, dict) else ""

        genudsat = "Ja" if item.get("released_catch") else "Nej"
        lus_raw = item.get("lice")
        if lus_raw is None:
            lus = "Nej"
        else:
            lus = f"Ja ({lus_raw})" if lus_raw else "Nej"

        sex = item.get("sex", "")
        koen = {"male": "Han", "female": "Hun"}.get(str(sex).lower(), sex or "")

        is_horg = "orgøien" in vald.lower()

        return {
            "id": cid, "dato": dato, "dato_iso": dato_iso[:10] if dato_iso else "",
            "aar": yr, "tid": tid, "vald": vald, "fisker": fisker,
            "vaegt": vaegt, "laengde": lgd, "art": art,
            "redskab": redskab, "genudsat": genudsat,
            "koen": koen, "lus": lus, "is_horg": is_horg
        }
    except:
        return None

# Hurtig load: kun side 1 (50 nyeste) — til dagens/gårsdagens visning
@st.cache_data(ttl=60, show_spinner=False)
def load_catches_fast(year, pages=1):
    catches = []
    for page in range(1, pages + 1):
        items, last_page = fetch_page(year, page)
        if items is None:
            break
        for item in items:
            c = parse_catch(item)
            if c:
                catches.append(c)
        if page >= last_page:
            break
    return catches

# Fuld sæson: alle sider — til YTD/charts/tabeller, cache 6 timer
@st.cache_data(ttl=21600, show_spinner=False)
def load_catches_full(year):
    catches = []
    page = 1
    last_page = 999
    while page <= last_page:
        items, last_page = fetch_page(year, page)
        if items is None:
            break
        for item in items:
            c = parse_catch(item)
            if c:
                catches.append(c)
        page += 1
    return catches

# NVE: cache 3 minutter
@st.cache_data(ttl=60, show_spinner=False)
def load_nve(date_from, date_to):
    headers = {"X-API-Key": NVE_API_KEY, "Accept": "application/json"}
    results = {}
    try:
        r = requests.get(NVE_URL, headers=headers, params={
            "StationId": NVE_STATION, "Parameter": "1001",
            "ResolutionTime": "1440",
            "ReferenceTime": f"{date_from}/{date_to}",
        }, timeout=20)
        if r.ok:
            for obs in r.json().get("data", []):
                for val in obs.get("observations", []):
                    d = val.get("time", "")[:10]
                    v = val.get("value")
                    if d and v is not None:
                        results[d] = round(float(v), 1)
    except:
        pass
    return results

# ─── LOAD DATA ────────────────────────────────────────────────────────────────
season_start = f"{CUR_YEAR}-06-01"
today_iso    = TODAY.isoformat()
now_str      = NOW_LOCAL.strftime("%d.%m.%Y kl. %H:%M")

# Historiske år: én gang pr. session i state (ændrer sig ikke i løbet af dagen)
if "catches_prev" not in st.session_state:
    with st.spinner("Første load — henter sæsondata..."):
        st.session_state.catches_prev = load_catches_full(CUR_YEAR - 1)
        st.session_state.catches_2y   = load_catches_full(CUR_YEAR - 2)

if "catches_cur" not in st.session_state:
    with st.spinner("Henter sæson {CUR_YEAR}..."):
        st.session_state.catches_cur = load_catches_fast(CUR_YEAR, pages=10)

# Ved auto-refresh eller visibility-reload: kun hent side 1 og merge
fresh = load_catches_fast(CUR_YEAR, pages=1)
known_ids = {c["id"] for c in st.session_state.catches_cur}
new_catches = [c for c in fresh if c["id"] not in known_ids]
if new_catches:
    st.session_state.catches_cur = new_catches + st.session_state.catches_cur

catches_cur  = st.session_state.catches_cur
catches_prev = st.session_state.catches_prev
catches_2y   = st.session_state.catches_2y

nve_data = load_nve(season_start, today_iso)
total_sources = len(catches_cur) + len(catches_prev) + len(catches_2y)

# ─── FILTER: YTD ──────────────────────────────────────────────────────────────
def ytd_filter(catches, year):
    cutoff = TODAY.replace(year=year) if year != TODAY.year else TODAY
    return [c for c in catches if c["dato_iso"] and c["dato_iso"] <= cutoff.isoformat()]

ytd_cur  = ytd_filter(catches_cur,  CUR_YEAR)
ytd_prev = ytd_filter(catches_prev, CUR_YEAR - 1)
ytd_2y   = ytd_filter(catches_2y,   CUR_YEAR - 2)

today_c = [c for c in catches_cur if c["dato_iso"] == TODAY.isoformat()]
yest_c  = [c for c in catches_cur if c["dato_iso"] == (TODAY - timedelta(days=1)).isoformat()]

# NVE: seneste vandføring
nve_latest = None
nve_latest_date = None
if nve_data:
    nve_latest_date = max(nve_data.keys())
    nve_latest = nve_data[nve_latest_date]

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="gc-header">
    <div>
        <div class="gc-title">🐟 Gaula Control Center</div>
        <div class="gc-subtitle">vs {CUR_YEAR-1} / {CUR_YEAR-2}</div>
    </div>
</div>
<div class="gc-meta">
    Opdateret: {now_str} &nbsp;·&nbsp; {total_sources} fangster i datasæt
</div>
""", unsafe_allow_html=True)

# Vis sidst opdateret + næste auto-refresh — ingen manuel knap
col_cap, col_btn = st.columns([4, 1])
with col_cap:
    st.caption(f"🔄 Opdateres automatisk hvert minut · Sidst: {now_str}")
with col_btn:
    if st.button("🔄 Opdater", use_container_width=True):
        # Ryd kun side 1 cache — behold session state datasæt
        load_catches_fast.clear()
        load_nve.clear()
        # Fjern current year fra session state så den genindlæses
        if "catches_cur" in st.session_state:
            del st.session_state["catches_cur"]
        st.rerun()

# ─── ROW 1: TOP KPI CARDS ─────────────────────────────────────────────────────
today_count = len(today_c)
today_kg    = sum(c["vaegt"] or 0 for c in today_c)
today_horg  = sum(1 for c in today_c if c["is_horg"])

nve_str = f"{nve_latest} m³/s" if nve_latest else "—"
nve_date_str = f"Senest {to_danish(nve_latest_date)}" if nve_latest_date else ""

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card-hero">
        <div class="kpi-label">Dagens fangster</div>
        <div class="kpi-value-lg">{today_count}</div>
        <div class="kpi-sub">🐟 i dag på hele Gaula · {today_kg:.1f} kg</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Horgøien i dag</div>
        <div class="kpi-value">{today_horg}</div>
        <div class="kpi-sub">📍 fangster</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Vandføring Gaulfoss</div>
        <div class="nve-value">{nve_str}</div>
        <div class="kpi-sub">〰 {nve_date_str}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── ROW 2: YTD SAMMENLIGNING ─────────────────────────────────────────────────
ytd_count_cur  = len(ytd_cur)
ytd_count_prev = len(ytd_prev)
ytd_count_2y   = len(ytd_2y)
ytd_kg_cur     = sum(c["vaegt"] or 0 for c in ytd_cur)
ytd_kg_prev    = sum(c["vaegt"] or 0 for c in ytd_prev)
ytd_kg_2y      = sum(c["vaegt"] or 0 for c in ytd_2y)
ytd_horg_cur   = sum(1 for c in ytd_cur if c["is_horg"])

max_ytd = max(ytd_count_cur, ytd_count_prev, ytd_count_2y, 1)

def bar(val, max_val, color_class):
    pct = min(100, int(val / max_val * 100))
    return f'<div class="ytd-bar-bg"><div class="{color_class}" style="width:{pct}%"></div></div>'

st.markdown(f"""
<div class="kpi-grid-4">
    <div class="kpi-card">
        <div class="kpi-label">Gaula YTD {CUR_YEAR}</div>
        <div class="kpi-value-sm" style="color:#1a6b4a;">{ytd_count_cur}</div>
        <div class="kpi-sub">{ytd_kg_cur:.0f} kg</div>
        {bar(ytd_count_cur, max_ytd, 'ytd-bar-fill')}
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Gaula YTD {CUR_YEAR-1}</div>
        <div class="kpi-value-sm">{ytd_count_prev}</div>
        <div class="kpi-sub">{ytd_kg_prev:.0f} kg</div>
        {bar(ytd_count_prev, max_ytd, 'ytd-bar-fill-25')}
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Gaula YTD {CUR_YEAR-2}</div>
        <div class="kpi-value-sm">{ytd_count_2y}</div>
        <div class="kpi-sub">{ytd_kg_2y:.0f} kg</div>
        {bar(ytd_count_2y, max_ytd, 'ytd-bar-fill-24')}
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Horgøien YTD {CUR_YEAR}</div>
        <div class="kpi-value-sm">{ytd_horg_cur}</div>
        <div class="kpi-sub">{sum(c["vaegt"] or 0 for c in ytd_cur if c["is_horg"]):.0f} kg</div>
        {bar(ytd_horg_cur, max(ytd_horg_cur,1), 'ytd-bar-fill')}
    </div>
</div>
""", unsafe_allow_html=True)

# ─── ROW 3: DELTA CARDS ───────────────────────────────────────────────────────
delta_prev = ytd_count_cur - ytd_count_prev
delta_2y   = ytd_count_cur - ytd_count_2y
delta_kg_prev = ytd_kg_cur - ytd_kg_prev
pct_prev = (delta_prev / ytd_count_prev * 100) if ytd_count_prev else 0
pct_2y   = (delta_2y   / ytd_count_2y   * 100) if ytd_count_2y   else 0

def delta_class(v): return "delta-pos" if v >= 0 else "delta-neg"
def pct_class(v): return "delta-pct-pos" if v >= 0 else "delta-pct-neg"
def sign(v): return "+" if v >= 0 else ""

ytd_label = f"06-{TODAY.strftime('%d')}" if TODAY.month == 6 else TODAY.strftime("%m-%d")
st.markdown(f"""
<div class="kpi-grid-3">
    <div class="kpi-card">
        <div class="kpi-label">Δ vs {CUR_YEAR-1}</div>
        <div class="{delta_class(delta_prev)}">{sign(delta_prev)}{delta_prev}</div>
        <div class="{pct_class(delta_prev)}">{sign(pct_prev)}{pct_prev:.1f}%</div>
        <div class="kpi-sub">{sign(delta_kg_prev)}{delta_kg_prev:.0f} kg</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">Δ vs {CUR_YEAR-2}</div>
        <div class="{delta_class(delta_2y)}">{sign(delta_2y)}{delta_2y}</div>
        <div class="{pct_class(pct_2y)}">{sign(pct_2y)}{pct_2y:.1f}%</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-label">YTD dato</div>
        <div class="kpi-value-sm">{ytd_label}</div>
        <div class="kpi-sub">1. juni → {TODAY.day}. juni</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── TABLE HELPERS ────────────────────────────────────────────────────────────
def make_df(catches):
    if not catches:
        return pd.DataFrame()
    rows = []
    for c in catches:
        rows.append({
            "Tid":       c["tid"],
            "Fisker":    c["fisker"],
            "Vald":      c["vald"],
            "Kg":        c["vaegt"],
            "Længde (cm)": c["laengde"],
            "Art":       c["art"],
            "Redskab":   c["redskab"],
            "Genudsat":  c["genudsat"],
            "Lus":       c["lus"],
            "Id":        c["id"],
            "_horg":     c["is_horg"],
        })
    df = pd.DataFrame(rows)
    df = df.sort_values("Tid", ascending=False).reset_index(drop=True)
    return df

def show_table(df, highlight_horg=True):
    if df.empty:
        st.info("Ingen fangster endnu.")
        return
    display_cols = [c for c in df.columns if not c.startswith("_")]
    
    def style_row(row):
        if highlight_horg and df.loc[row.name, "_horg"]:
            return ['background-color: #fff3e6'] * len(row)
        return [''] * len(row)
    
    styled = df[display_cols + ["_horg"]].copy()
    
    st.dataframe(
        df[display_cols].style.apply(
            lambda row: ['background-color: #fff3e6; font-weight:500' if df.loc[row.name, '_horg'] else '' for _ in row],
            axis=1
        ).format({"Kg": lambda x: f"{x:.1f}" if pd.notna(x) else "—",
                  "Længde (cm)": lambda x: str(int(x)) if pd.notna(x) else "—"}),
        use_container_width=True,
        height=min(400, max(150, len(df) * 36 + 40)),
        hide_index=True,
    )

# ─── DAGENS FANGSTER ──────────────────────────────────────────────────────────
st.markdown(f"""
<div class="section-header">
    Dagens fangster <span class="count-badge">{len(today_c)}</span>
</div>
""", unsafe_allow_html=True)

show_table(make_df(today_c))

# ─── GÅRSDAGENS FANGSTER ──────────────────────────────────────────────────────
st.markdown(f"""
<div class="section-header">
    Gårsdagens fangster <span class="count-badge">{len(yest_c)}</span>
</div>
""", unsafe_allow_html=True)

show_table(make_df(yest_c))

# ─── DAG-FOR-DAG CHART ────────────────────────────────────────────────────────
st.markdown(f"""
<div class="section-header">
    Daglig udvikling — {CUR_YEAR} vs {CUR_YEAR-1}
</div>
""", unsafe_allow_html=True)

def daily_series(catches, year):
    df = pd.DataFrame(catches)
    if df.empty: return pd.Series(dtype=int)
    df = df[df["dato_iso"] != ""]
    df["dato_iso"] = pd.to_datetime(df["dato_iso"])
    daily = df.groupby("dato_iso").size()
    return daily

series_cur  = daily_series(ytd_cur,  CUR_YEAR)
series_prev = daily_series(ytd_prev, CUR_YEAR - 1)

if not series_cur.empty or not series_prev.empty:
    # Align by day-of-season (days since June 1)
    def to_season_day(series, year):
        june1 = pd.Timestamp(f"{year}-06-01")
        s = series.copy()
        s.index = (s.index - june1).days
        return s

    sc = to_season_day(series_cur,  CUR_YEAR)
    sp = to_season_day(series_prev, CUR_YEAR - 1)
    
    chart_df = pd.DataFrame({
        str(CUR_YEAR):     sc,
        str(CUR_YEAR - 1): sp,
    }).fillna(0)
    
    # Cumulative
    chart_df_cum = chart_df.cumsum()
    
    tab1, tab2 = st.tabs(["Kumulativ YTD", "Dagligt"])
    with tab1:
        st.line_chart(chart_df_cum, color=["#1a6b4a", "#8bc4a0"])
    with tab2:
        st.bar_chart(chart_df, color=["#1a6b4a", "#8bc4a0"])

# ─── VANDFØRING CHART ─────────────────────────────────────────────────────────
if nve_data:
    st.markdown(f"""
    <div class="section-header">Vandføring Gaulfoss (m³/s)</div>
    """, unsafe_allow_html=True)
    nve_df = pd.DataFrame([
        {"Dato": pd.Timestamp(k), "m³/s": v} for k, v in sorted(nve_data.items())
    ]).set_index("Dato")
    st.line_chart(nve_df, color=["#2196f3"])

# ─── TOP VALDA + SÆSON OVERSIGT ──────────────────────────────────────────────
all_df = make_df(catches_cur)

col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown(f"""
    <div class="section-header">Top valda {CUR_YEAR} — antal fangster</div>
    """, unsafe_allow_html=True)

    if not all_df.empty:
        vald_stats = (
            all_df.groupby("Vald")
            .agg(
                Fangster=("Kg", "count"),
                Kg_total=("Kg", "sum"),
                Snit_kg=("Kg", "mean"),
            )
            .reset_index()
            .sort_values("Fangster", ascending=False)
            .reset_index(drop=True)
        )
        vald_stats.index += 1  # Rank fra 1
        vald_stats["Kg total"] = vald_stats["Kg_total"].map(lambda x: f"{x:.0f}")
        vald_stats["Snit kg"] = vald_stats["Snit_kg"].map(lambda x: f"{x:.1f}")
        vald_stats = vald_stats.drop(columns=["Kg_total", "Snit_kg"])

        def highlight_horg_vald(row):
            if "orgøien" in str(row["Vald"]).lower():
                return ["background-color: #fff3e6; font-weight:500"] * len(row)
            if row.name == 1:
                return ["background-color: #f0f8f0; font-weight:600"] * len(row)
            return [""] * len(row)

        st.dataframe(
            vald_stats.style.apply(highlight_horg_vald, axis=1),
            use_container_width=True,
            height=min(600, len(vald_stats) * 36 + 40),
        )

with col_right:
    st.markdown(f"""
    <div class="section-header">Hele sæsonen {CUR_YEAR} — alle fangster</div>
    """, unsafe_allow_html=True)

    if not all_df.empty:
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        with col_f1:
            vald_opts = ["Alle"] + sorted(all_df["Vald"].dropna().unique().tolist())
            vald_sel = st.selectbox("Vald", vald_opts, key="vald_filter")
        with col_f2:
            art_opts = ["Alle"] + sorted(all_df["Art"].dropna().unique().tolist())
            art_sel = st.selectbox("Art", art_opts, key="art_filter")
        with col_f3:
            gen_opts = ["Alle", "Ja", "Nej"]
            gen_sel = st.selectbox("Genudsat", gen_opts, key="gen_filter")
        with col_f4:
            red_opts = ["Alle"] + sorted(all_df["Redskab"].dropna().unique().tolist())
            red_sel = st.selectbox("Redskab", red_opts, key="red_filter")

        filtered = all_df.copy()
        if vald_sel != "Alle": filtered = filtered[filtered["Vald"] == vald_sel]
        if art_sel  != "Alle": filtered = filtered[filtered["Art"]  == art_sel]
        if gen_sel  != "Alle": filtered = filtered[filtered["Genudsat"] == gen_sel]
        if red_sel  != "Alle": filtered = filtered[filtered["Redskab"] == red_sel]

        st.caption(f"{len(filtered)} fangster vises · {filtered['Kg'].sum():.0f} kg total · snit {filtered['Kg'].mean():.1f} kg")
        show_table(filtered)

# ─── FOOTER ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="gc-footer">
    Gaula Control Center v2 &nbsp;·&nbsp; YTD {CUR_YEAR} vs {CUR_YEAR-1} og {CUR_YEAR-2} &nbsp;·&nbsp; 
    Data: elveguiden.no + NVE HydAPI &nbsp;·&nbsp; Opdateres automatisk
</div>
""", unsafe_allow_html=True)
