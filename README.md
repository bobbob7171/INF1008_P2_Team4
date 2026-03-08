# Smart MRT Navigator

A* pathfinding for the Singapore MRT & LRT network.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit GUI – map, inputs, route display |
| `astar.py` | A* algorithm with 4 optimisation modes |
| `mrt_graph.py` | Graph construction from CSV dataset |
| `MRT_Stations.csv` | Station data (name, code, lat/lon) |
| `requirements.txt` | Python dependencies |

## Algorithm

**A\*** evaluates each node with:

```
f(n) = g(n) + h(n)
```

- `g(n)` — actual cost from start (travel time / distance / station count)
- `h(n)` — admissible heuristic (haversine distance ÷ average MRT speed)
- `transfer_penalty` — added to `g(n)` when the line changes

### Route Preferences

| Mode | g(n) weight | Transfer penalty |
|------|-------------|-----------------|
| Fastest Route | travel time (min) | +5 min |
| Least Transfers | travel time + **999** if transfer | +999 (deters changes) |
| Shortest Distance | distance (km) | none |
| Fewest Stations | 1 per station | none |

## Network Coverage

- **EW** East West Line (33 stations)  
- **NS** North South Line (28 stations)  
- **NE** North East Line (15 stations)  
- **CC** Circle Line (29 stations, loop)  
- **DT** Downtown Line (35 stations)  
- **TE** Thomson-East Coast Line (partial, 12 stations)  
- **CG** Changi Airport Branch  
- **CE** Circle Line Extension  
- **BP** Bukit Panjang LRT  
- **PE/PW** Punggol LRT loops  
- **SE/SW** Sengkang LRT loops  

**Total: 171 stations, ~350+ edges**
