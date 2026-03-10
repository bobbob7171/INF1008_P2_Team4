# Smart MRT Navigator

A* pathfinding for the Singapore MRT & LRT network, with a side-by-side Dijkstra comparison — built with Streamlit.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit GUI — map, route planner, stats, directions, A* vs Dijkstra comparison |
| `astar.py` | A* algorithm with 4 optimisation modes and admissible heuristics |
| `dijkstra.py` | Dijkstra baseline (h = 0) with matching 4 modes for direct comparison |
| `mrt_graph.py` | Graph construction from CSV — haversine distances, line speeds, transfer edges |
| `MRT_Stations.csv` | Station data (name, code, latitude, longitude) |
| `requirements.txt` | Python dependencies |

---

## Features

- **Journey Planner** — select origin and destination from all 171 stations, with a one-click swap button
- **4 Route Optimisation Modes** — Fastest, Least Transfers, Shortest Distance, Fewest Stations
- **Algorithm Toggle** — switch between A* and Dijkstra to compare results in real time
- **Interactive Folium Map** — colour-coded line polylines, transfer markers, fullscreen support
- **Explored Nodes Overlay** — toggle to visualise which nodes each algorithm visited during search
- **Route Comparison Table** — all 4 modes side-by-side (time, stops, transfers, distance, nodes explored, compute time)
- **A* vs Dijkstra Panel** — nodes explored, compute time, and an inline explainer of `f(n) = g(n) + h(n)`
- **Step-by-Step Directions** — board/alight/transfer instructions per line segment

---

## Algorithm

**A\*** evaluates each node with:

```
f(n) = g(n) + h(n)
```

| Term | Role | Detail |
|------|------|--------|
| `g(n)` | Exact cost | Actual travel time + transfer penalties from start |
| `h(n)` | Heuristic | Haversine distance ÷ max line speed — never overestimates, so optimality is guaranteed |

**Dijkstra** is identical except `h(n) = 0`, causing it to expand nodes uniformly in all directions. Both share the same `O((V + E) log V)` worst-case complexity; A*'s advantage is a smaller practical constant from heuristic pruning.

### Route Optimisation Modes

| Mode | g(n) weight | Transfer penalty |
|------|-------------|-----------------|
| Fastest Route | travel time (min) | +5 min |
| Least Transfers | travel time / 1000 as tiebreaker | +1.0 per transfer |
| Shortest Distance | distance (km) | none |
| Fewest Stations | 1 per station hop | none |

### Heuristics (all admissible)

| Mode | h(n) |
|------|------|
| Fastest | straight-line dist ÷ 45 km/h → lower-bound minutes |
| Shortest Distance | straight-line dist → lower-bound km |
| Least Transfers | 0 if current line reaches goal, else 1 |
| Fewest Stations | straight-line dist ÷ 0.37 km → lower-bound stops |

---

## Network Coverage

| Line | Name | Stations |
|------|------|----------|
| EW | East West Line | 33 |
| NS | North South Line | 28 |
| NE | North East Line | 15 |
| CC | Circle Line (loop) | 29 |
| DT | Downtown Line | 35 |
| TE | Thomson-East Coast Line (partial) | 12 |
| CG | Changi Airport Branch | 2 |
| CE | Circle Line Extension | 2 |
| BP | Bukit Panjang LRT | 13 |
| SE / SW | Sengkang LRT loops | 6 / 9 |
| PE / PW | Punggol LRT loops | 8 / 8 |

**Total: 171 stations, ~350+ edges**

---

## Implementation Notes

- **State space:** `(station_name, current_line)` — tracks active line so transfer penalties apply correctly
- **Path reconstruction:** parent-pointer backtracking (not stored in heap), reducing heap memory from O(V × path_len) to O(V)
- **Cycle avoidance:** O(1) via `best_g` dict — no list membership scans
- **Transfer edges:** fixed 5-minute cross-platform penalty for LRT ↔ MRT interchanges