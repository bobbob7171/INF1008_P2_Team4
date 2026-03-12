# Smart MRT Navigator

A* pathfinding for the Singapore MRT & LRT network, with a side-by-side Dijkstra comparison — built with Streamlit.

## Live Demo

**[https://smartmrtnavigator.streamlit.app/](https://smartmrtnavigator.streamlit.app/)**

No installation required — open the link and start planning routes immediately.

---

## Local Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI — map, route planner, stats, directions, A* vs Dijkstra comparison |
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
| `g(n)` | Exact cost | Actual travel time + transfer penalties accumulated from start |
| `h(n)` | Heuristic | Haversine distance ÷ max line speed — never overestimates, so optimality is guaranteed |

**Dijkstra** is identical except `h(n) = 0`, causing it to expand nodes uniformly in all directions. Both share the same `O((V + E) log V)` worst-case complexity; A*'s advantage is a smaller practical constant from heuristic pruning.

### Route Optimisation Modes

| Mode | g(n) edge cost | Transfer penalty |
|------|----------------|-----------------|
| Fastest Route | travel time (min) | +5 min per line change |
| Least Transfers | travel time / 1000 as tiebreaker | +1.0 per transfer |
| Shortest Distance | distance (km) | none |
| Fewest Stations | 1 per station hop | none |

### Heuristics

| Mode | h(n) | Admissible? |
|------|------|-------------|
| Fastest | haversine(n, goal) ÷ 45 km/h → lower-bound minutes | ✓ |
| Shortest Distance | haversine(n, goal) → lower-bound km | ✓ |
| Least Transfers | 0 if current line serves goal, else 1 | ✓ |
| Fewest Stations | haversine(n, goal) ÷ 0.37 km → lower-bound hops | ⚠ May overestimate on routes with multiple interchanges due to near-zero-distance transfer edges |

---

## Network Coverage

| Line | Name | Stations |
|------|------|----------|
| EW | East West Line | 33 |
| NS | North South Line | 27 |
| NE | North East Line | 16 |
| CC | Circle Line (loop) | 29 |
| DT | Downtown Line | 35 |
| TE | Thomson-East Coast Line (partial) | 12 |
| CG | Changi Airport Branch | 2 |
| CE | Circle Line Extension | 2 |
| BP | Bukit Panjang LRT | 13 |
| SE | Sengkang East LRT | 6 |
| SW | Sengkang West LRT | 9 |
| PE | Punggol East LRT | 8 |
| PW | Punggol West LRT | 8 |

**Total: 171 stations, 199 edges**

---

## Implementation Notes

- **State space:** `(station_name, current_line)` — tracks active line so transfer penalties apply correctly across line changes
- **Path reconstruction:** parent-pointer backtracking instead of storing full paths in heap entries, reducing heap memory from O(V × path_len) to O(V)
- **Cycle avoidance:** O(1) via `best_g` dict — no list membership scans
- **Parent pointer guard:** `open_g` dict ensures only strictly better paths overwrite parent pointers, preventing corruption from stale lazy-deletion heap entries
- **Transfer edges:** fixed 5-minute cross-platform penalty for LRT ↔ MRT interchanges (Choa Chu Kang, Bukit Panjang, Sengkang, Punggol)