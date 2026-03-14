"""
astar.py
A* pathfinding for the Singapore MRT/LRT network.

State space: (station_name, current_line)
  - Tracks which line the traveller is currently on so transfer penalties
    are applied correctly when the line changes.

Four optimisation modes:
  fastest           – minimise total travel time (including transfer waits)
  least_transfers   – minimise number of line changes
  shortest_distance – minimise total track distance
  fewest_stations   – minimise number of intermediate stops

Key implementation notes:
  - Parent-pointer path reconstruction: paths are NOT stored in heap entries,
    eliminating O(path_len) memory overhead per heap node.
  - O(1) cycle avoidance via best_g dict (no list membership scan).
  - Informed heuristics for all four modes so A* never degrades to Dijkstra.
  - find_line() extracted as a single shared module-level utility.
"""

import heapq
import re
from mrt_graph import haversine, TRANSFER_PENALTY, LINE_SPEED

# Assumed max MRT speed for admissible time heuristic (km/h).
# Must be >= the fastest real line speed to remain admissible.
MRT_SPEED_HEURISTIC = 45.0

# Upper-bound on inter-station distance (km), derived from the actual graph.
# The longest non-transfer segment in the network is Dhoby Ghaut ↔ HarbourFront
# on the Circle Line at 4.6016 km. We use 4.62 km (a small epsilon above the
# true max) to guarantee strict admissibility: h(n) = haversine / 4.62 always
# yields a lower-bound hop count, never an overestimate.
#
# Admissibility proof:
#   True hops ≥ haversine(n, goal) / max_real_segment
#             ≥ haversine(n, goal) / 4.62  = h(n)   ✓
#
# Using MIN segment (0.37 km) instead would give h(n) >> true hops — inadmissible.
_MAX_SEGMENT_KM = 4.62  # CC line: Dhoby Ghaut ↔ HarbourFront = 4.6016 km


# ── Shared utility ────────────────────────────────────────────────────────────

def find_line(station_a: str, station_b: str, graph: dict) -> str:
    """Return the line code of the edge from station_a to station_b.

    Extracted as a module-level function to avoid identical inner-function
    duplication in get_path_segments() and get_transfer_stations().
    Returns 'Unknown' if no such edge exists.
    """
    for nb, _, _, line in graph.get(station_a, []):
        if nb == station_b:
            return line
    return "Unknown"


def _get_dest_lines(end_name: str, stations: dict) -> set:
    """Return the set of line prefixes that serve end_name (e.g. {'EW','NS'})."""
    dest_lines = set()
    for c in stations[end_name].get("codes", []):
        m = re.match(r"([A-Z]+)\d", c)
        if m:
            dest_lines.add(m.group(1))
    return dest_lines


# ── A* core ───────────────────────────────────────────────────────────────────

def astar(graph: dict, stations: dict, start_name: str, end_name: str,
          mode: str = "fastest"):
    """
    Run A* from start_name to end_name using the given optimisation mode.

    Returns:
        (path, g_cost, transfers, total_time_min, total_dist_km)
        path is [] if no route was found.

    Time complexity:  O((V + E) log V)
    Space complexity: O(V)  – parent pointers only, not full paths in heap
    """
    if start_name not in stations or end_name not in stations:
        return [], 0, 0, 0.0, 0.0, 0, set()
    if start_name == end_name:
        return [start_name], 0, 0, 0.0, 0.0, 1, {start_name}

    end_lat = stations[end_name]["lat"]
    end_lon = stations[end_name]["lon"]
    dest_lines = _get_dest_lines(end_name, stations)   # pre-computed once

    # ── Heuristics (admissible: h(n) ≤ true cost to goal) ────────────────────

    def heuristic(name: str, curr_line) -> float:
        """
        fastest:          straight-line dist ÷ max speed  →  lower-bound minutes.
        shortest_distance: straight-line dist              →  lower-bound km.
        least_transfers:  0 if current line reaches goal, else 1.
                          Admissible because if curr_line ∉ dest_lines at least
                          one more transfer must occur.
        fewest_stations:  straight-line dist ÷ MAX segment →  lower-bound stops.
                          Dividing by MAX (not MIN) segment length ensures h(n)
                          never overestimates — using MIN would inflate h(n) and
                          break admissibility, causing suboptimal paths.
        """
        lat = stations[name]["lat"]
        lon = stations[name]["lon"]
        dist = haversine(lat, lon, end_lat, end_lon)

        if mode == "fastest":
            return (dist / MRT_SPEED_HEURISTIC) * 60

        if mode == "shortest_distance":
            return dist

        if mode == "least_transfers":
            if curr_line is not None and curr_line in dest_lines:
                return 0.0
            return 1.0 if dest_lines else 0.0

        if mode == "fewest_stations":
            return dist / _MAX_SEGMENT_KM

        return 0.0

    # ── Edge cost g(n) ────────────────────────────────────────────────────────

    def edge_cost(edge_line: str, curr_line, dist_km: float) -> float:
        speed = LINE_SPEED.get(edge_line, 40)
        travel_time = (dist_km / speed) * 60 + 0.5
        is_transfer = (
            curr_line is not None
            and edge_line not in ("transfer", curr_line)
        )

        if mode == "fastest":
            cost = travel_time
            if is_transfer or edge_line == "transfer":
                cost += TRANSFER_PENALTY

        elif mode == "least_transfers":
            # Small travel-time component as tiebreaker; integer transfer
            # count drives the optimisation.
            cost = travel_time / 1000.0
            if is_transfer or edge_line == "transfer":
                cost += 1.0

        elif mode == "shortest_distance":
            cost = dist_km

        elif mode == "fewest_stations":
            # Transfer edges are platform changes, not actual station stops.
            # Counting them as 1 would penalise transfers unfairly and inflate
            # the stop count vs Dijkstra. Only true station hops cost 1.
            cost = 0.0 if edge_line == "transfer" else 1.0

        else:
            cost = travel_time

        return cost

    # ── Search ────────────────────────────────────────────────────────────────

    # Heap entry: (f, tie_counter, g, station_name, current_line)
    # Full paths are NOT pushed into the heap. Instead, parent pointers
    # are stored separately and the path is reconstructed on goal discovery.
    # This reduces heap memory from O(V * path_len) to O(V).
    counter = 0
    start_state = (start_name, None)
    heap = [(heuristic(start_name, None), counter, 0.0, start_name, None)]

    # best_g[(station, line)] = lowest g-cost reached for this state.
    # Doubles as the "closed set" — no separate visited structure needed.
    best_g: dict = {}

    # open_g[(station, line)] = best g seen so far (settled OR unsettled).
    # Used to guard parent/stats writes so they only happen when a strictly
    # better path is found — prevents parent pointer corruption when multiple
    # heap entries point to the same state.
    open_g: dict = {start_state: 0.0}

    # parent[(station, line)] = predecessor state for path reconstruction.
    parent: dict = {start_state: None}

    # Running totals stored per state (separate from optimisation cost g).
    # stats[(station, line)] = (transfers, real_time_min, dist_km)
    stats: dict = {start_state: (0, 0.0, 0.0)}

    # Tracks every unique station name that has been settled (popped from heap).
    explored_set: set = set()

    while heap:
        f, _, g, curr_name, curr_line = heapq.heappop(heap)
        state = (curr_name, curr_line)

        # O(1) dominance check — skip if a cheaper path already settled here.
        if state in best_g and best_g[state] <= g:
            continue
        best_g[state] = g
        explored_set.add(curr_name)

        # Goal test.
        if curr_name == end_name:
            # Reconstruct path via parent pointers — O(path_len).
            path = []
            cur = state
            while cur is not None:
                path.append(cur[0])
                cur = parent[cur]
            path.reverse()
            xfers, tot_time, tot_dist = stats[state]
            return path, g, xfers, tot_time, tot_dist, len(explored_set), explored_set

        cur_xfers, cur_time, cur_dist = stats[state]

        for neighbor, seg_time, dist_km, edge_line in graph.get(curr_name, []):
            actual_line = curr_line if edge_line == "transfer" else edge_line
            new_state   = (neighbor, actual_line)

            is_transfer = (
                curr_line is not None
                and edge_line not in ("transfer", curr_line)
            )

            move_cost = edge_cost(edge_line, curr_line, dist_km)
            new_g = g + move_cost

            # O(1) pruning — skip if this state has already been settled cheaper.
            if new_state in best_g and best_g[new_state] <= new_g:
                continue

            counter += 1
            new_f = new_g + heuristic(neighbor, actual_line)
            heapq.heappush(heap, (new_f, counter, new_g, neighbor, actual_line))

            # Only update parent and stats if this is a strictly better path
            # to new_state than any previously seen (settled or unsettled).
            # Without this guard, a worse path pushed later can corrupt the
            # parent pointer that a better heap entry will rely on at goal time.
            if new_g < open_g.get(new_state, float("inf")):
                open_g[new_state] = new_g
                parent[new_state] = state
                stats[new_state] = (
                    cur_xfers + (1 if is_transfer else 0),
                    cur_time  + seg_time + (TRANSFER_PENALTY if is_transfer else 0),
                    cur_dist  + dist_km,
                )

    return [], 0, 0, 0.0, 0.0, len(explored_set), explored_set


# ── Path analysis helpers ─────────────────────────────────────────────────────

def get_path_segments(path: list, graph: dict) -> list:
    """Break a path into contiguous same-line segments.

    Returns [(line_code, [station_names]), ...]

    Uses the shared find_line() module utility — no duplication.
    """
    if len(path) < 2:
        return []

    segments   = []
    curr_line  = find_line(path[0], path[1], graph)
    curr_seg   = [path[0], path[1]]

    for i in range(2, len(path)):
        line = find_line(path[i - 1], path[i], graph)
        if line == curr_line or line == "transfer":
            curr_seg.append(path[i])
        else:
            segments.append((curr_line, curr_seg))
            curr_line = line
            curr_seg  = [path[i - 1], path[i]]

    segments.append((curr_line, curr_seg))
    return segments


def get_transfer_stations(path: list, graph: dict) -> list:
    """Return [(index, station_name)] for every line-change in path.

    Uses the shared find_line() module utility — no duplication.
    """
    transfers = []
    if len(path) < 3:
        return transfers

    prev_line = find_line(path[0], path[1], graph)
    for i in range(1, len(path) - 1):
        curr_line = find_line(path[i], path[i + 1], graph)
        if curr_line != prev_line and curr_line not in ("transfer", "Unknown"):
            transfers.append((i, path[i]))
        prev_line = curr_line

    return transfers