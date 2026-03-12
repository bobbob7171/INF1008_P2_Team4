"""
app.py  –  Smart MRT Navigator 
Run:  streamlit run app.py
"""

import re
import streamlit as st
import folium
from folium import plugins
from streamlit_folium import st_folium
import time as _time

from mrt_graph import (
    build_graph, display_name,
    LINE_COLORS, LINE_NAMES, TRANSFER_PENALTY,
)
from astar import astar, get_path_segments, get_transfer_stations
from dijkstra import dijkstra

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Smart MRT Navigator",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

*, html, body { font-family: 'DM Sans', sans-serif !important; }

/* App shell */
.stApp                { background: #F5F7FA !important; color: #1E293B !important; }
[data-testid="stHeader"] { background: transparent !important; }
.block-container      { padding: 0 1.5rem 2rem !important; max-width: 100% !important; }

/* ── Selectbox ── */
div[data-baseweb="select"] > div               { background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; border-radius: 10px !important; color: #1E293B !important; }
div[data-baseweb="select"] * { color: #1E293B !important; }
div[data-baseweb="select"] input               { background: transparent !important; caret-color: #1E293B !important; }
div[data-baseweb="popover"]                    { background: #FFFFFF !important; border: 1.5px solid #CBD5E1 !important; border-radius: 10px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.10) !important; }
div[data-baseweb="popover"] * { background: #FFFFFF !important; color: #1E293B !important; }
ul[data-baseweb="menu"]                        { background: #FFFFFF !important; border: none !important; }
ul[data-baseweb="menu"] li                     { background: #FFFFFF !important; color: #1E293B !important; }
ul[data-baseweb="menu"] li:hover               { background: #F1F5F9 !important; }
ul[data-baseweb="menu"] li[aria-selected="true"] { background: #E2E8F0 !important; }
[role="combobox"] input                        { color: #1E293B !important; background: transparent !important; }
[role="option"]                                { background: #FFFFFF !important; color: #1E293B !important; }
[role="option"]:hover                          { background: #F1F5F9 !important; }
.stSelectbox > label                           { color: #475569 !important; font-size: 0.85rem !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.8px; }
.stSelectbox svg                               { fill: #64748B !important; }

/* ── Hero ── */
.hero                 { background: linear-gradient(135deg, #1A3A5C 0%, #0F5C3A 100%);
                        border-radius: 0 0 20px 20px; padding: 1.4rem 2rem;
                        display: flex; align-items: center; gap: 1.2rem;
                        margin: 0 -1.5rem 1.8rem; box-shadow: 0 4px 24px rgba(0,0,0,0.10); }
.hero-title           { font-size: 1.8rem; font-weight: 700; color: #FFF; letter-spacing: -0.5px; line-height: 1.1; }
.hero-sub             { font-size: 0.85rem; color: rgba(255,255,255,0.7); margin-top: 4px; }

/* ── Cards ── */
.card, .journey-card, .dir-wrap, .cmp-wrap { 
    background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 14px; 
    padding: 1rem 1.25rem; margin-bottom: 0.85rem; box-shadow: 0 2px 8px rgba(0,0,0,0.03); 
}
.journey-card { padding-bottom: 0.6rem; }
.card-title           { font-size: 0.75rem; font-weight: 700; letter-spacing: 1.6px;
                        text-transform: uppercase; color: #334155; margin-bottom: 0.7rem; }

/* ── Journey planner card ── */
.journey-field-label  { font-size: 0.75rem; font-weight: 700; letter-spacing: 1.4px;
                        text-transform: uppercase; color: #334155; margin-bottom: 2px; }
.journey-info         { display: flex; align-items: center; gap: 6px;
                        padding: 5px 10px 5px 8px; background: #F8FAFC;
                        border: 1px solid #CBD5E1; border-radius: 0 0 8px 8px;
                        margin-top: -6px; margin-bottom: 4px; }
.journey-info-lines   { font-size: 0.75rem; color: #475569; }
.journey-divider      { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
.journey-divider-line { flex: 1; height: 1px; background: #CBD5E1; }
.journey-divider-icon { font-size: 0.8rem; color: #64748B; }

/* ── Badge ── */
.lbadge               { display: inline-block; border-radius: 4px; padding: 1px 6px;
                        font-size: 0.65rem; font-weight: 700; color: #FFF; margin-left: 3px; }

/* ── Stat grid ── */
.stat-grid            { display: flex; gap: 0.65rem; flex-wrap: wrap; margin-bottom: 0.85rem; }
.stat-box             { flex: 1; min-width: 84px; background: #FFFFFF;
                        border: 1px solid #CBD5E1; border-radius: 10px;
                        padding: 14px 8px; text-align: center;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.03); }
.stat-val             { font-size: 26px !important; font-weight: 700; color: #0F172A; line-height: 1; }
.stat-lbl             { font-size: 12px !important; font-weight: 600; color: #475569; 
                        text-transform: uppercase; letter-spacing: 1px; margin-top: 5px; }

/* ── Directions ── */
.dir-seg              { display: flex; align-items: flex-start; gap: 0.65rem;
                        padding: 0.65rem 0; border-bottom: 1px solid #E2E8F0; }
.dir-seg:last-child   { border-bottom: none; }
.seg-dot              { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.seg-body             { font-size: 0.88rem; color: #1E293B; line-height: 1.55; }
.seg-body .dim        { color: #475569; font-size: 0.8rem; }
.seg-body .xfer-pill  { display: inline-block; font-size: 0.72rem; color: #B45309; font-weight: 600;
                        background: #FEF3C7; border: 1px solid #FDE68A;
                        border-radius: 4px; padding: 1px 7px; margin-top: 4px; }
.dir-stop             { display: flex; align-items: center; gap: 0.55rem;
                        padding: 0.3rem 0 0.3rem 1.5rem; border-bottom: 1px solid #F1F5F9; }
.dir-stop:last-child  { border-bottom: none; }
.stop-dot             { width: 6px; height: 6px; border-radius: 50%; opacity: 0.4; flex-shrink: 0; }
.stop-name            { font-size: 0.8rem; color: #475569; }

/* ── Comparison table ── */
table.cmp             { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
table.cmp th          { color: #334155; font-size: 0.75rem; font-weight: 700; letter-spacing: 1px;
                        text-transform: uppercase; padding: 10px 8px; text-align: left;
                        border-bottom: 2px solid #E2E8F0; background: #F8FAFC; }
table.cmp td          { padding: 10px 8px; border-bottom: 1px solid #E2E8F0; color: #1E293B; }
table.cmp tr:last-child td { border-bottom: none; }
table.cmp tr.hi td    { background: rgba(0,150,69,0.06); color: #0F172A; font-weight: 600; }
table.cmp tr.hi td:first-child::before { content: "▶  "; color: #009645; }

/* ── Explored nodes radio ── */
div[data-testid="stRadio"] > label       { font-size: 0.75rem !important; font-weight: 700 !important;
                                           letter-spacing: 1px; text-transform: uppercase; color: #334155 !important; }
div[data-testid="stRadio"] label span    { font-size: 0.85rem !important; color: #1E293B !important; font-weight: 500 !important; }

/* scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #F8FAFC; }
::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }

/* ── Route option cards ── */
.route-opt-card  { border-radius: 12px 12px 0 0; padding: 10px 8px 8px; /* Tighter padding */
                   text-align: center; border-bottom: none !important; }
.route-opt-icon  { font-size: 20px !important; line-height: 1; }
.route-opt-label { font-size: 12px !important; font-weight: 800; letter-spacing: 1.1px;
                   text-transform: uppercase; color: #0F172A; margin: 4px 0 2px; }
.route-opt-algo  { font-size: 11px !important; color: #64748B; margin-bottom: 5px; }
.route-opt-val   { font-size: 18px !important; font-weight: 700; color: #0F172A; line-height: 1; }
.route-opt-sub   { font-size: 12px !important; color: #475569; margin: 3px 0 6px; }

/* ── Educational Expander ── */
[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 14px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
    overflow: hidden;
}
[data-testid="stExpander"] details { background: transparent !important; }
[data-testid="stExpander"] details summary {
    font-size: 0.75rem !important; font-weight: 700 !important;
    letter-spacing: 1.6px !important; text-transform: uppercase !important;
    color: #334155 !important; padding: 1rem 1.25rem !important;
    background: #FFFFFF !important;
}
[data-testid="stExpander"] details[open] summary {
    border-bottom: 1px solid #E2E8F0 !important;
}
[data-testid="stExpander"] details > div[data-testid="stExpanderDetails"] {
    padding: 1rem 1.25rem 0.75rem !important; background: #FFFFFF !important;
}

/* ── Toggle (explored nodes) ── */
div[data-testid="stToggle"] p,
div[data-testid="stCheckbox"] p {
    font-size: 0.82rem !important; font-weight: 600 !important;
    color: #334155 !important; letter-spacing: 0.2px;
}
/* Toggle track — BaseUI renders it as the first div child of the label */
div[data-testid="stCheckbox"] label > div:first-child {
    background-color: #94A3B8 !important;
}
div[data-testid="stCheckbox"] label:has(input:checked) > div:first-child {
    background-color: #009645 !important;
}

/* Fix secondary buttons */
div.stButton > button, div[data-testid="stButton"] > button {
    background-color: #FFFFFF !important; color: #1E293B !important;
    border: 1px solid #CBD5E1 !important; font-weight: 600 !important;
}
div.stButton > button:hover, div[data-testid="stButton"] > button:hover {
    background-color: #F8FAFC !important; border-color: #94A3B8 !important;
}
div.stButton > button[kind="primary"], div[data-testid="stButton"] > button[kind="primary"] {
    background-color: #009645 !important; color: #FFFFFF !important; border: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── data ───────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_data():
    return build_graph("MRT_Stations.csv")

graph, stations, code_to_name = load_data()

all_names       = sorted(stations.keys())
all_display     = [display_name(n) for n in all_names]
display_to_full = {display_name(n): n for n in all_names}

# ── constants ──────────────────────────────────────────────────────────────────
PREF_OPTIONS = {
    "  Fastest Route":     "fastest",
    "  Least Transfers":   "least_transfers",
    "  Shortest Distance": "shortest_distance",
    "  Fewest Stations":   "fewest_stations",
}
MODE_LABELS = {v: k for k, v in PREF_OPTIONS.items()}

# ── helper functions ───────────────────────────────────────────────────────────

def fmt_time(mins: float) -> str:
    t = int(round(mins))
    if t < 60:
        return f"{t} min"
    h, m = divmod(t, 60)
    return f"{h}h" if m == 0 else f"{h}h {m:02d}min"


def get_line_codes(full_name: str) -> list:
    codes = stations.get(full_name, {}).get("codes", [])
    out = []
    for c in codes:
        m = re.match(r"([A-Z]+)\d", c)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out if out else ["EW"]


def lbadge(line: str) -> str:
    c = LINE_COLORS.get(line, "#748477")
    return f'<span class="lbadge" style="background:{c};">{line}</span>'


# ── HTML builders ─────────────────────────────────────────────────────────────

def build_stats_html(ttime, stops, xfers, dist, nodes_explored=0):
    return (
        '<div class="stat-grid">'
        f'<div class="stat-box"><div class="stat-val">{fmt_time(ttime)}</div><div class="stat-lbl">Travel Time</div></div>'
        f'<div class="stat-box"><div class="stat-val">{stops}</div><div class="stat-lbl">Stops</div></div>'
        f'<div class="stat-box"><div class="stat-val">{xfers}</div><div class="stat-lbl">Transfers</div></div>'
        f'<div class="stat-box"><div class="stat-val">{dist:.1f}</div><div class="stat-lbl">km</div></div>'
        f'<div class="stat-box"><div class="stat-val">{nodes_explored}</div><div class="stat-lbl">Nodes Explored</div></div>'
        '</div>'
    )


def build_lines_html(lines_used, elapsed_ms):
    badges = "".join(lbadge(l) for l in lines_used)
    return (
        '<div class="card">'
        '<div class="card-title">Lines Used</div>'
        f'{badges}'
        f'<span style="font-size:0.7rem;color:#5A6F8A;margin-left:8px;">computed in {elapsed_ms:.1f} ms</span>'
        '</div>'
    )


def build_route_html(path):
    route_str = " → ".join(display_name(s) for s in path)
    return (
        '<div class="card">'
        '<div class="card-title">Full Route</div>'
        f'<div style="font-size:0.77rem;color:#3D5270;line-height:1.85;">{route_str}</div>'
        '</div>'
    )


def build_comparison_html(results, active_mode, timings=None):
    rows = ""
    for mode, (path, g, xfers, ttime, dist, nodes_exp, _) in results.items():
        cls = "hi" if mode == active_mode else ""
        lbl = MODE_LABELS.get(mode, mode)
        ms  = f"{timings[mode]:.1f} ms" if timings and mode in timings else "—"
        if path:
            rows += (
                f'<tr class="{cls}">'
                f'<td>{lbl}</td>'
                f'<td><b>{fmt_time(ttime)}</b></td>'
                f'<td>{len(path)-1}</td>'
                f'<td>{xfers}</td>'
                f'<td>{dist:.1f} km</td>'
                f'<td>{nodes_exp}</td>'
                f'<td style="color:#748477;">{ms}</td>'
                f'</tr>'
            )
        else:
            rows += f'<tr class="{cls}"><td>{lbl}</td><td colspan="6" style="color:#5A6F8A;">No path</td></tr>'
    return (
        '<div class="cmp-wrap">'
        '<div class="card-title">Route Comparison</div>'
        '<table class="cmp"><thead><tr>'
        '<th>Mode</th><th>Time</th><th>Stops</th><th>Transfers</th><th>Dist</th>'
        '<th>Nodes Explored</th><th>Compute</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        '</div>'
    )


def build_algo_comparison_html(astar_result, dijkstra_result, astar_ms, dijkstra_ms, mode="fastest"):
    """Side-by-side A* vs Dijkstra comparison table for the active mode."""
    mode_label = MODE_LABELS.get(mode, mode).strip()
    a_path, _, a_xfers, a_ttime, a_dist, a_nodes, _ = astar_result
    d_path, _, d_xfers, d_ttime, d_dist, d_nodes, _ = dijkstra_result

    # Efficiency note
    if d_nodes > 0 and a_nodes > 0:
        saved_pct = int((1 - a_nodes / d_nodes) * 100)
        note = (
            f'A* explored <strong style="color:#009645;">{saved_pct}% fewer nodes</strong> '
            f'({a_nodes} vs {d_nodes}) by using a geographic heuristic '
            f'h(n) = straight-line distance ÷ max speed to guide the search '
            f'toward the destination. Dijkstra (h = 0) expands nodes uniformly.'
        )
    else:
        note = ""

    same_path = a_path == d_path if a_path and d_path else False
    same_tag = (
        '<span style="font-size:0.75rem;background:#E8F5EE;color:#009645;font-weight:600;'
        'border:1px solid #B2DFCB;border-radius:4px;padding:2px 6px;margin-left:6px;">'
        '✓ Same optimal path</span>'
    ) if same_path else ""

    _complexity = '<code style="font-size:0.8rem;background:#F1F5F9;color:#334155;padding:2px 6px;border-radius:4px;font-weight:600;">O((V+E) log V)</code>'

    rows = ""
    if a_path:
        rows += (
            f'<tr class="hi">'
            f'<td><strong>A*</strong> <span style="font-size:0.75rem;color:#009645;font-weight:600;">{mode_label}</span>{same_tag}</td>'
            f'<td><b>{fmt_time(a_ttime)}</b></td>'
            f'<td>{len(a_path)-1}</td>'
            f'<td>{a_xfers}</td>'
            f'<td style="color:#009645;font-weight:700;">{a_nodes}</td>'
            f'<td style="color:#009645;font-weight:700;">{astar_ms:.1f} ms</td>'
            f'<td>{_complexity} <span style="font-size:0.75rem;color:#009645;font-weight:600;margin-left:4px;">small const</span></td>'
            f'</tr>'
        )
    if d_path:
        rows += (
            f'<tr>'
            f'<td><strong>Dijkstra</strong> <span style="font-size:0.75rem;color:#64748B;">h(n) = 0</span></td>'
            f'<td><b>{fmt_time(d_ttime)}</b></td>'
            f'<td>{len(d_path)-1}</td>'
            f'<td>{d_xfers}</td>'
            f'<td style="color:#B45309;font-weight:700;">{d_nodes}</td>'
            f'<td style="color:#B45309;font-weight:700;">{dijkstra_ms:.1f} ms</td>'
            f'<td>{_complexity} <span style="font-size:0.75rem;color:#B45309;font-weight:600;margin-left:4px;">large const</span></td>'
            f'</tr>'
        )

    note_block = (
        f'<div style="margin-top:0.85rem;font-size:0.85rem;color:#1E293B;'
        f'padding:10px 12px;background:#F0FDF4;border-radius:8px;'
        f'border:1px solid #BBF7D0;line-height:1.6;">{note}'
        f' Both share the same worst-case complexity class — A*\'s advantage is a '
        f'<strong>smaller practical constant</strong> from heuristic pruning.</div>'
    ) if note else ""

    astar_explainer = (
        '<div class="cmp-wrap" style="padding:0;overflow:hidden;">'
        '<details>'
        # Summary = clickable header
        '<summary style="list-style:none;cursor:pointer;padding:1rem 1.25rem;'
        'display:flex;align-items:center;justify-content:space-between;'
        'user-select:none;">'
        '<span class="card-title" style="margin:0;">How does A* Pathfinding actually work?</span>'
        '<span class="details-chevron" style="font-size:0.75rem;color:#64748B;transition:transform 0.2s;">▼</span>'
        '</summary>'
        # Collapsible body
        '<div style="padding:0 1.25rem 1.25rem;border-top:1px solid #E2E8F0;">'
        # Intro blurb
        '<div style="font-size:0.85rem;color:#475569;margin:0.85rem 0;line-height:1.6;">'
        'A* (A-Star) is an <strong>informed search algorithm</strong> that finds the shortest path '
        'faster than Dijkstra by using a <strong>heuristic</strong> — a smart geographic estimate — '
        'to guide its search toward the destination.'
        '</div>'
        # Formula pill
        '<div style="text-align:center;margin-bottom:0.85rem;">'
        '<code style="font-size:1rem;font-weight:700;background:#F1F5F9;color:#1A3A5C;'
        'padding:7px 18px;border-radius:8px;border:1px solid #CBD5E1;letter-spacing:1px;">'
        'f(n) = g(n) + h(n)'
        '</code>'
        '</div>'
        # Explainer table
        '<table class="cmp"><thead><tr>'
        '<th style="width:60px;">Term</th>'
        '<th style="width:120px;">Role</th>'
        '<th>Definition</th>'
        '</tr></thead><tbody>'
        '<tr>'
        '<td><code style="font-size:0.85rem;background:#F1F5F9;color:#1A3A5C;padding:2px 7px;border-radius:4px;font-weight:700;">g(n)</code></td>'
        '<td><span style="background:#E8F5EE;color:#0F5C3A;font-size:0.75rem;font-weight:700;'
        'padding:2px 8px;border-radius:4px;border:1px solid #B2DFCB;">Exact Cost</span></td>'
        '<td style="color:#1E293B;">Actual travel time + transfer penalties accumulated from the <strong>start</strong> to the current station.</td>'
        '</tr>'
        '<tr>'
        '<td><code style="font-size:0.85rem;background:#F1F5F9;color:#1A3A5C;padding:2px 7px;border-radius:4px;font-weight:700;">h(n)</code></td>'
        '<td><span style="background:#FEF3C7;color:#B45309;font-size:0.75rem;font-weight:700;'
        'padding:2px 8px;border-radius:4px;border:1px solid #FDE68A;">Heuristic</span></td>'
        '<td style="color:#1E293B;">Estimated time to destination using '
        '<strong>straight-line distance ÷ max train speed</strong> — never overestimates, so the optimal path is guaranteed.</td>'
        '</tr>'
        '</tbody></table>'
        # Why it matters callout
        '<div style="margin-top:0.85rem;font-size:0.85rem;color:#1E293B;'
        'padding:10px 12px;background:#EFF6FF;border-radius:8px;'
        'border:1px solid #BFDBFE;line-height:1.65;">'
        '<strong>Why does this matter?</strong><br>'
        'Dijkstra uses <code style="background:#F1F5F9;color:#334155;padding:1px 5px;border-radius:3px;">h(n) = 0</code>, '
        'expanding nodes in <em>all directions equally</em>. '
        'A* uses station coordinates to <strong>steer the search directly toward the destination</strong> — '
        'exploring significantly fewer nodes while <strong>guaranteeing the same optimal route</strong>.'
        '</div>'
        '</div>'  # end body
        '</details>'
        '<style>'
        'details[open] .details-chevron { transform: rotate(180deg); }'
        'details summary::-webkit-details-marker { display:none; }'
        '</style>'
        '</div>'
    )

    return (
        '<div class="cmp-wrap">'
        '<div class="card-title">Algorithm Comparison: A* vs Dijkstra</div>'
        '<div style="font-size:0.85rem;color:#475569;margin-bottom:0.85rem;line-height:1.55;">'
        'Both algorithms use the same edge cost (travel time + transfer penalty). '
        'The only difference is <strong>A* adds a heuristic</strong> — Dijkstra does not.</div>'
        '<table class="cmp"><thead><tr>'
        '<th>Algorithm</th><th>Time</th><th>Stops</th>'
        '<th>Transfers</th><th>Nodes Explored</th><th>Compute</th><th>Complexity</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        f'{note_block}'
        f'</div>'
        f'{astar_explainer}'
    )


def build_directions_html(path):
    if len(path) < 2:
        return ""
    segments     = get_path_segments(path, graph)
    transfer_set = {t[1] for t in get_transfer_stations(path, graph)}

    parts = ['<div class="dir-wrap"><div class="card-title">Step-by-Step Directions</div>']

    for seg_idx, (line, seg) in enumerate(segments):
        color = LINE_COLORS.get(line, "#748477")
        lname = LINE_NAMES.get(line, line)
        badge = lbadge(line)

        action = "Transfer &amp; Board" if seg_idx > 0 else "Board"
        xpill  = '<br><span class="xfer-pill">↔ Line Change · +5 min</span>' if seg_idx > 0 else ""
        parts.append(
            f'<div class="dir-seg">'
            f'<div class="seg-dot" style="background:{color};"></div>'
            f'<div class="seg-body">'
            f'<strong>{action}</strong> {badge} <span class="dim">{lname}</span> '
            f'at <strong>{display_name(seg[0])}</strong>'
            f'{xpill}'
            f'</div></div>'
        )

        mid = seg[1:-1]
        MAX = 3
        if len(mid) > MAX * 2:
            shown_top, hidden, shown_bot = mid[:MAX], mid[MAX:-MAX], mid[-MAX:]
            for s in shown_top:
                parts.append(
                    f'<div class="dir-stop">'
                    f'<div class="stop-dot" style="background:{color};"></div>'
                    f'<span class="stop-name">{display_name(s)}</span></div>'
                )
            parts.append(
                f'<div class="dir-stop">'
                f'<span class="stop-name" style="font-style:italic;padding-left:0.2rem;">'
                f'··· {len(hidden)} more station{"s" if len(hidden)>1 else ""} ···'
                f'</span></div>'
            )
            for s in shown_bot:
                parts.append(
                    f'<div class="dir-stop">'
                    f'<div class="stop-dot" style="background:{color};"></div>'
                    f'<span class="stop-name">{display_name(s)}</span></div>'
                )
        else:
            for s in mid:
                parts.append(
                    f'<div class="dir-stop">'
                    f'<div class="stop-dot" style="background:{color};"></div>'
                    f'<span class="stop-name">{display_name(s)}</span></div>'
                )

        if seg_idx < len(segments) - 1:
            parts.append(
                f'<div class="dir-seg">'
                f'<div class="seg-dot" style="background:{color};border:2px solid #F5A623;box-sizing:border-box;"></div>'
                f'<div class="seg-body">Alight at <strong>{display_name(seg[-1])}</strong></div>'
                f'</div>'
            )
        else:
            parts.append(
                f'<div class="dir-seg">'
                f'<div class="seg-dot" style="background:#D42E12;border:2px solid #FFF;box-sizing:border-box;"></div>'
                f'<div class="seg-body"><strong>Arrive</strong> at <strong>{display_name(seg[-1])}</strong></div>'
                f'</div>'
            )

    parts.append('</div>')
    return "".join(parts)


# ── Map helpers ───────────────────────────────────────────────────────────────

def _get_station_line_color(stn: str, path: list, segments: list) -> str:
    """Return the line color for a station based on which segment it belongs to."""
    for line, seg in segments:
        if stn in seg:
            return LINE_COLORS.get(line, "#4A6080")
    return "#4A6080"


# ── Map builder ───────────────────────────────────────────────────────────────

def _station_line_color(name: str) -> str:
    """Pick a representative line color for a station from its codes."""
    import re as _re
    for code in stations.get(name, {}).get("codes", []):
        m = _re.match(r"([A-Z]+)\d", code)
        if m:
            line = m.group(1)
            if line in LINE_COLORS:
                return LINE_COLORS[line]
    return "#748477"


def build_map(path, explored_set=None, show_explored=True):
    base   = dict(tiles="CartoDB positron")
    centre = [1.352, 103.82]

    if not path:
        m = folium.Map(location=centre, zoom_start=12, **base)
    else:
        lats = [stations[s]["lat"] for s in path]
        lons = [stations[s]["lon"] for s in path]
        m = folium.Map(location=[sum(lats)/len(lats), sum(lons)/len(lons)],
                       zoom_start=12, **base)

    # Draw explored-but-not-on-path nodes first so path sits on top
    path_set = set(path) if path else set()
    if show_explored and explored_set:
        for name in explored_set:
            if name in path_set:
                continue
            data = stations.get(name)
            if not data:
                continue
            color = _station_line_color(name)
            folium.CircleMarker(
                [data["lat"], data["lon"]], radius=4,
                color=color, fill=True, fill_color=color,
                fill_opacity=0.35, weight=1,
                tooltip=f"Explored: {display_name(name)}",
            ).add_to(m)

    for name, data in stations.items():
        if name in path_set:
            continue
        if show_explored and explored_set and name in explored_set:
            continue  # already drawn as colored explored marker
        folium.CircleMarker(
            [data["lat"], data["lon"]], radius=2,
            color="#8A9AB8", fill=True, fill_color="#8A9AB8",
            fill_opacity=0.7, weight=0, tooltip=display_name(name),
        ).add_to(m)

    if not path:
        return m

    segments     = get_path_segments(path, graph)
    transfer_set = {t[1] for t in get_transfer_stations(path, graph)}

    for line, seg in segments:
        color  = LINE_COLORS.get(line, "#748477")
        coords = [[stations[s]["lat"], stations[s]["lon"]] for s in seg]
        folium.PolyLine(coords, color=color, weight=6, opacity=0.95,
                        tooltip=LINE_NAMES.get(line, line)).add_to(m)

    for stn in path[1:-1]:
        lat, lon = stations[stn]["lat"], stations[stn]["lon"]
        if stn in transfer_set:
            folium.CircleMarker(
                [lat, lon], radius=9, color="#FFFFFF",
                fill=True, fill_color="#F5A623", fill_opacity=1, weight=2.5,
                popup=folium.Popup(f"Transfer: {display_name(stn)}", max_width=160),
                tooltip=f"⇄ Transfer: {display_name(stn)}",
            ).add_to(m)
        else:
            # Fill with the line's own color so stations are visible on the light map
            seg_color = _get_station_line_color(stn, path, segments)
            folium.CircleMarker(
                [lat, lon], radius=5, color="#FFFFFF",
                fill=True, fill_color=seg_color, fill_opacity=1.0, weight=2,
                tooltip=display_name(stn),
            ).add_to(m)

    folium.Marker(
        [stations[path[0]]["lat"], stations[path[0]]["lon"]],
        tooltip=f"🟢 START: {display_name(path[0])}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
    ).add_to(m)
    folium.Marker(
        [stations[path[-1]]["lat"], stations[path[-1]]["lon"]],
        tooltip=f"🔴 END: {display_name(path[-1])}",
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
    ).add_to(m)

    # ── Fixed legend overlay (bottom-right) ──────────────────────────────────
    _leg_rows = ""
    for _ln in ["EW","NS","NE","CC","DT","TE"]:
        _lc = LINE_COLORS.get(_ln, "#748477")
        _ln_name = LINE_NAMES.get(_ln, _ln)
        _leg_rows += (
            f'<div style="display:flex;align-items:center;gap:6px;margin:1.5px 0;">'
            f'<span style="display:inline-block;width:14px;height:3.5px;border-radius:2px;'
            f'background:{_lc};flex-shrink:0;"></span>'
            f'<span style="font-size:11px;color:#1E293B;font-weight:500;">{_ln_name}</span></div>'
        )
    # Group all LRT lines under one entry
    _leg_rows += (
        '<div style="display:flex;align-items:center;gap:6px;margin:1.5px 0;">'
        '<span style="display:inline-block;width:14px;height:3.5px;border-radius:2px;'
        'background:#748477;flex-shrink:0;"></span>'
        '<span style="font-size:11px;color:#1E293B;font-weight:500;">LRT Lines</span></div>'
    )
    _leg_rows += (
        '<div style="display:flex;align-items:center;gap:6px;margin:1.5px 0;">'
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        'background:#F5A623;flex-shrink:0;margin-left:3px;"></span>'
        '<span style="font-size:11px;color:#1E293B;font-weight:500;">Transfer</span></div>'
    )
    m.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;bottom:10px;right:10px;z-index:9999;'
        'background:rgba(255,255,255,0.95);padding:8px 12px;border-radius:8px;'
        'border:1px solid #CBD5E1;box-shadow:0 2px 8px rgba(0,0,0,0.12);font-family:sans-serif;">'
        '<div style="font-size:10px;font-weight:800;color:#64748B;text-transform:uppercase;'
        'letter-spacing:1px;margin-bottom:4px;">MRT Lines</div>'
        + _leg_rows + '</div>'
    ))
    
    # Hide the default map attribution inside the iframe
    m.get_root().html.add_child(folium.Element(
        '<style>.leaflet-control-attribution { display: none !important; }</style>'
    ))

    # Add a fullscreen button to the map
    plugins.Fullscreen(position='topright').add_to(m)
    
    return m


# ── hero ───────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero">'
    '<span style="font-size:2.3rem;">🚇</span>'
    '<div>'
    '<div class="hero-title">Smart MRT Navigator</div>'
    '<div class="hero-sub">A* Pathfinding &nbsp;·&nbsp; Singapore MRT &amp; LRT &nbsp;·&nbsp; 171 Stations</div>'
    '</div></div>',
    unsafe_allow_html=True,
)

# ── layout ─────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="medium")

# ═══════════════════ LEFT ═══════════════════

# ── Initialize session state for swapping ──
def_s = all_display.index("Jurong East")    if "Jurong East"    in all_display else 0
def_e = all_display.index("Changi Airport") if "Changi Airport" in all_display else 1

if "sel_start" not in st.session_state:
    st.session_state.sel_start = all_display[def_s]
if "sel_end" not in st.session_state:
    st.session_state.sel_end = all_display[def_e]

def swap_stations():
    # Swap the actual selected string values in session state
    st.session_state.sel_start, st.session_state.sel_end = st.session_state.sel_end, st.session_state.sel_start

with left:

    st.markdown('<div class="journey-card"><div class="card-title">Plan Your Journey</div>', unsafe_allow_html=True)

    # ── Google Maps Style Layout (Inputs on Left, Swap on Right) ──
    col_inputs, col_swap = st.columns([0.88, 0.12], gap="small")

    with col_inputs:
        # FROM
        st.markdown('<div class="journey-field-label">FROM</div>', unsafe_allow_html=True)
        start_disp = st.selectbox("Origin Station", all_display, key="sel_start", label_visibility="collapsed")
        start_full = display_to_full[start_disp]
        s_lines  = get_line_codes(start_full)
        s_badges = "".join(lbadge(l) for l in s_lines)
        s_lnames = " · ".join(LINE_NAMES.get(l, l) for l in s_lines)
        st.markdown(
            f'<div class="journey-info">{s_badges}'
            f'<span class="journey-info-lines">{s_lnames}</span></div>',
            unsafe_allow_html=True,
        )

        # Tiny gap between From and To
        st.markdown('<div style="height: 6px;"></div>', unsafe_allow_html=True) 

        # TO
        st.markdown('<div class="journey-field-label">TO</div>', unsafe_allow_html=True)
        end_disp = st.selectbox("Destination Station", all_display, key="sel_end", label_visibility="collapsed")
        end_full = display_to_full[end_disp]
        e_lines  = get_line_codes(end_full)
        e_badges = "".join(lbadge(l) for l in e_lines)
        e_lnames = " · ".join(LINE_NAMES.get(l, l) for l in e_lines)
        st.markdown(
            f'<div class="journey-info" style="margin-bottom:0;">{e_badges}'
            f'<span class="journey-info-lines">{e_lnames}</span></div>',
            unsafe_allow_html=True,
        )

    with col_swap:
        # Pushes the button down so it centers perfectly between the two input fields
        st.markdown('<div style="height: 105px;"></div>', unsafe_allow_html=True)
        st.button("⇅", on_click=swap_stations, key="btn_swap", help="Swap Origin and Destination", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)  # close journey-card

    # ── Restore missing session state variables ──
    if "active_mode" not in st.session_state:
        st.session_state.active_mode = "fastest"
    active_mode = st.session_state.active_mode

    if "active_algo" not in st.session_state:
        st.session_state.active_algo = "astar"
    active_algo = st.session_state.active_algo

    # ── Auto-compute on every render ──────────────────────
    dijkstra_results = {}
    dijkstra_timings = {}

    if start_full == end_full:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#5A6F8A;">'
            '⚠️ Origin and destination are the same station.'
            '</div>',
            unsafe_allow_html=True,
        )
        results    = None
        timings    = {}
        elapsed_ms = 0.0
    else:
        results  = {}
        timings  = {}
        for _m in ["fastest", "least_transfers", "shortest_distance", "fewest_stations"]:
            _t0 = _time.perf_counter()
            results[_m] = astar(graph, stations, start_full, end_full, _m)
            timings[_m] = (_time.perf_counter() - _t0) * 1000
            _t0 = _time.perf_counter()
            dijkstra_results[_m] = dijkstra(graph, stations, start_full, end_full, _m)
            dijkstra_timings[_m] = (_time.perf_counter() - _t0) * 1000
        elapsed_ms = sum(timings.values())

    # ── Algorithm toggle ──────────────────────────────────────────────────────
    if results:
        st.markdown(
            '<div class="card-title" style="margin:0.7rem 0 0.4rem;">ALGORITHM</div>',
            unsafe_allow_html=True,
        )
        _ac1, _ac2 = st.columns(2, gap="small")
        _algo_meta = [
            ("astar",    "A* Search",   "Uses h(n) = geographic distance heuristic"),
            ("dijkstra", "Dijkstra",    "h(n) = 0 · Explores all directions uniformly"),
        ]
        for _algo_key, _lbl, _desc in _algo_meta: # Removed _icon from the loop unpack
            _active = (_algo_key == active_algo)
            _bc = "#009645" if _active else "#DDE3EE"
            _bw = "2px" if _active else "1.5px"
            _bg = "rgba(0,150,69,0.04)" if _active else "#FFFFFF"
            _vc = "#0F172A" if _active else "#475569"

            # Pick result to display on the card
            if _algo_key == "astar":
                _r      = results[active_mode]
                _ms_val = timings[active_mode]
            else:
                _r      = dijkstra_results.get(active_mode)
                _ms_val = dijkstra_timings.get(active_mode, 0.0)

            _nodes = _r[5] if _r and _r[0] else "—"

            _col = _ac1 if _algo_key == "astar" else _ac2
            with _col:
                st.markdown(
                    f'<div style="border:{_bw} solid {_bc};background:{_bg};'
                    f'border-radius:12px 12px 0 0;padding:10px 8px 8px;text-align:center;">'
                    f'<div style="font-size:13px;font-weight:700;letter-spacing:1px;'
                    f'text-transform:uppercase;color:{_vc};margin:3px 0 1px;">{_lbl}</div>'
                    f'<div style="font-size:11px;color:#64748B;margin-bottom:6px;">{_desc}</div>'
                    f'<div style="font-size:18px;font-weight:700;color:#0F172A;">{_nodes}</div>'
                    f'<div style="font-size:11px;font-weight:600;color:#475569;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:2px;">nodes explored</div>'
                    f'<div style="font-size:11px;color:#64748B;">{_ms_val:.1f} ms</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "✓ Active" if _active else "Select",
                    key=f"algo_btn_{_algo_key}",
                    use_container_width=True,
                    type="primary" if _active else "secondary",
                ):
                    st.session_state.active_algo = _algo_key
                    st.rerun()

    # ── Route option cards ────────────────────────────────────────────────────
    if results:
        st.markdown(
            '<div class="card-title" style="margin:0.9rem 0 0.4rem;">ROUTE OPTIONS</div>',
            unsafe_allow_html=True,
        )
        _rc1, _rc2 = st.columns(2, gap="small")
        _algo_prefix = "A*" if active_algo == "astar" else "Dijkstra"
        _active_results = results if active_algo == "astar" else dijkstra_results
        _mode_meta = [
            ("fastest",           "", "FASTEST ROUTE",      f"{_algo_prefix} · Time"),
            ("least_transfers",   "", "LEAST TRANSFERS",    f"{_algo_prefix} · Transfers"),
            ("shortest_distance", "", "SHORTEST DISTANCE",  f"{_algo_prefix} · Distance"),
            ("fewest_stations",   "", "FEWEST STATIONS",    f"{_algo_prefix} · Stops"),
        ]
        for _i, (_mode, _icon, _lbl, _algo) in enumerate(_mode_meta):
            _pm, _, _xm, _tm, _dm, _, _ = _active_results[_mode]
            _sv = ""
            if _mode == "fastest":
                _mv = fmt_time(_tm)
            elif _mode == "least_transfers":
                _mv = f"{_xm} transfer{'s' if _xm!=1 else ''}"
            elif _mode == "shortest_distance":
                _mv = f"{_dm:.1f} km"
            else:
                _mv = f"{len(_pm)-1} stops" if _pm else "-"
            _segs_m  = get_path_segments(_pm, graph) if _pm else []
            _lines_m = list(dict.fromkeys(s[0] for s in _segs_m if s[0] not in ("transfer","Unknown")))
            _badges  = "".join(lbadge(l) for l in _lines_m)
            _active  = (_mode == active_mode)
            _bc = "#009645" if _active else "#DDE3EE"
            _bw = "2px" if _active else "1.5px"
            _bg = "rgba(0,150,69,0.04)" if _active else "#FFFFFF"
            _col = _rc1 if _i % 2 == 0 else _rc2
            with _col:
                st.markdown(
                    f'<div class="route-opt-card" style="border:{_bw} solid {_bc};background:{_bg};">'
                    f'<div class="route-opt-icon">{_icon}</div>'
                    f'<div class="route-opt-label">{_lbl}</div>'
                    f'<div class="route-opt-algo">{_algo}</div>'
                    f'<div class="route-opt-val">{_mv}</div>'
                    f'<div class="route-opt-sub">{_sv}</div>'
                    f'<div style="margin-top:3px;">{_badges}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "✓ Selected" if _active else "Select",
                    key=f"mode_btn_{_mode}",
                    use_container_width=True,
                    type="primary" if _active else "secondary",
                ):
                    st.session_state.active_mode = _mode
                    st.rerun()

    # ── Results (left column: lines, route, directions) ───────────────────────
    if results:
        # Pick which result to display based on active algorithm
        if active_algo == "astar":
            _display_result = results[active_mode]
            _display_ms     = timings[active_mode]
        else:
            _display_result = dijkstra_results[active_mode]
            _display_ms     = dijkstra_timings[active_mode]

        path, g, xfers, ttime, dist, nodes_exp, explored_set = _display_result

        if not path:
            st.markdown(
                '<div style="text-align:center;padding:2rem;color:#5A6F8A;">⚠️ No route found.</div>',
                unsafe_allow_html=True,
            )
        else:
            segs       = get_path_segments(path, graph)
            lines_used = [s[0] for s in segs if s[0] != "transfer"]

            st.markdown(build_route_html(path),                    unsafe_allow_html=True)
            st.markdown(build_directions_html(path),               unsafe_allow_html=True)


# ═══════════════════ RIGHT – MAP ═══════════════════
with right:

    # ── Stats above the map ───────────────────────────────────────────────────
    _algo_display = {
        "fastest":           "Fastest Route · A* (Time Heuristic)",
        "least_transfers":   "Least Transfers · A* (Transfer Penalty)",
        "shortest_distance": "Shortest Distance · A* (Distance Heuristic)",
        "fewest_stations":   "Fewest Stations · A* (Hop Count)",
    }
    
    show_map_explored = False  # Default state
    
    if results:
        # Pick the result to show based on active algorithm
        if active_algo == "astar":
            _right_result = results[active_mode]
            _right_label  = _algo_display.get(active_mode, "A*")
        else:
            _right_result = dijkstra_results[active_mode]
            _right_label  = "Dijkstra · h(n) = 0 (No Heuristic)"

        path, g, xfers, ttime, dist, nodes_exp, _active_explored = _right_result
        if path:
            st.markdown(
                f'<div style="font-size:0.75rem;font-weight:700;color:#0F172A;'
                f'margin-bottom:0.2rem;letter-spacing:0.3px;">{_right_label}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(build_stats_html(ttime, len(path)-1, xfers, dist, nodes_exp),
                        unsafe_allow_html=True)
            
            # ── The Interactive Toggle ──
            with st.container(border=True):
                st.markdown(
                    '<div style="font-size:0.7rem;font-weight:700;letter-spacing:1.2px;'
                    'text-transform:uppercase;color:#334155;margin-bottom:2px;">Map Overlay</div>'
                    '<div style="font-size:0.75rem;color:#64748B;margin-bottom:4px;">'
                    'Show stations the algorithm visited, not just the final route</div>',
                    unsafe_allow_html=True,
                )
                show_map_explored = st.toggle(
                    "Show Explored Nodes on Map",
                    value=True,
                )

    # ── Map Title with Dynamic Suffix ──
    _exp_suffix = {
        "astar":    ' <span style="font-size:0.75rem;color:#009645;font-weight:700;">· A* explored</span>',
        "dijkstra": ' <span style="font-size:0.75rem;color:#B45309;font-weight:700;">· Dijkstra explored</span>',
    }
    
    _title_suffix = _exp_suffix.get(active_algo, "") if show_map_explored else ""

    st.markdown(
        f'<div class="card-title" style="margin-top:0.6rem; margin-bottom:0.4rem;">&nbsp;Interactive Route Map'
        f'{_title_suffix}</div>',
        unsafe_allow_html=True,
    )

    # ── Map Data Processing ──
    path = []
    _map_explored = set()
    if results:
        if active_algo == "astar":
            path = results[active_mode][0]
            # Only pass the explored set to the map if the toggle is ON
            if show_map_explored:
                _map_explored = results[active_mode][6]
        else:
            _dr = dijkstra_results.get(active_mode)
            path = _dr[0] if _dr else []
            # Only pass the explored set to the map if the toggle is ON
            if _dr and show_map_explored:
                _map_explored = _dr[6]

    st_folium(build_map(path, _map_explored, bool(_map_explored)), width=None, height=718, returned_objects=[])
    # ── Comparison table below the map ────────────────────────────────────────
    if results:
        _cmp_data    = results         if active_algo == "astar" else dijkstra_results
        _cmp_timings = timings         if active_algo == "astar" else dijkstra_timings
        st.markdown(build_comparison_html(_cmp_data, active_mode, _cmp_timings), unsafe_allow_html=True)

    # ── A* vs Dijkstra comparison ──────────────────────────────────────────────
    if results and dijkstra_results:
        st.markdown(
            build_algo_comparison_html(
                results[active_mode], dijkstra_results[active_mode],
                timings[active_mode], dijkstra_timings[active_mode],
                mode=active_mode,
            ),
            unsafe_allow_html=True,
        )

# ── footer ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="text-align:center;padding:1.2rem 0 0.4rem;color:#5A6F8A;font-size:0.7rem;'
    'border-top:1px solid #DDE3EE;margin-top:1rem;">'
    'Smart MRT Navigator &nbsp;·&nbsp; INF1008 Data Structures &amp; Algorithms &nbsp;·&nbsp; '
    'A* &nbsp;<code style="background:#F0F4FA;color:#3D5270;padding:1px 6px;border-radius:4px;">'
    'f(n) = g(n) + h(n) + transfer_penalty</code>'
    '</div>',
    unsafe_allow_html=True,
)