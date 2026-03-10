"""
dijkstra.py
Dijkstra's algorithm for the Singapore MRT/LRT network.

Used as a h(n) = 0 baseline against A* to demonstrate the heuristic advantage.
Identical edge cost to A* 'fastest' mode (travel time + transfer penalty) —
the only difference is no heuristic is added, so f(n) = g(n) only.

This means Dijkstra expands nodes in all directions uniformly, while A*
focuses the search toward the destination using geographic distance.

Time complexity:  O((V + E) log V)
Space complexity: O(V)
"""

import heapq
from mrt_graph import LINE_SPEED, TRANSFER_PENALTY


def dijkstra(graph: dict, stations: dict, start_name: str, end_name: str):
    """
    Dijkstra's algorithm for MRT shortest-time path.

    Identical edge cost to A* 'fastest' mode (travel time + transfer penalty),
    but with NO heuristic: h(n) = 0, so f(n) = g(n) only.

    This makes Dijkstra a direct apples-to-apples baseline for A* fastest:
    both find the same optimal path, but Dijkstra explores more nodes because
    it cannot use geographic distance to guide the search.

    Returns the same 7-tuple as astar() for easy side-by-side comparison:
        (path, g_cost, transfers, total_time_min, total_dist_km,
         nodes_explored, explored_set)

    path is [] if no route was found.
    """
    if start_name not in stations or end_name not in stations:
        return [], 0, 0, 0.0, 0.0, 0, set()
    if start_name == end_name:
        return [start_name], 0, 0, 0.0, 0.0, 1, {start_name}

    counter = 0
    start_state = (start_name, None)
    heap = [(0.0, counter, 0.0, start_name, None)]  # (g, tie, g, name, line)

    # best_g[(station, line)] = lowest g settled for this state (closed set).
    best_g: dict = {}

    # open_g[(station, line)] = best g seen so far (settled OR unsettled).
    # Guards parent/stats writes so they only happen on strictly better paths,
    # preventing parent pointer corruption from lazy-deletion heap entries.
    open_g: dict = {start_state: 0.0}

    # parent[(station, line)] = predecessor state for path reconstruction.
    parent: dict = {start_state: None}

    # Running totals per state — separate from the optimisation cost g.
    # stats[(station, line)] = (transfers, real_time_min, dist_km)
    stats: dict = {start_state: (0, 0.0, 0.0)}

    # Every unique station name that has been settled (popped from heap).
    explored_set: set = set()

    while heap:
        _, _, g, curr_name, curr_line = heapq.heappop(heap)
        state = (curr_name, curr_line)

        # Skip stale heap entries (lazy deletion).
        if state in best_g and best_g[state] <= g:
            continue
        best_g[state] = g
        explored_set.add(curr_name)

        # Goal test — reconstruct path via parent pointers.
        if curr_name == end_name:
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

            speed = LINE_SPEED.get(edge_line, 40)
            travel_time = (dist_km / speed) * 60 + 0.5
            is_transfer = (
                curr_line is not None
                and edge_line not in ("transfer", curr_line)
            )

            # Same cost function as A* fastest — no heuristic added.
            move_cost = travel_time
            if is_transfer or edge_line == "transfer":
                move_cost += TRANSFER_PENALTY

            new_g = g + move_cost

            # Skip if already settled with a cheaper cost.
            if new_state in best_g and best_g[new_state] <= new_g:
                continue

            counter += 1
            heapq.heappush(heap, (new_g, counter, new_g, neighbor, actual_line))

            # Only overwrite parent/stats if this is a strictly better path.
            if new_g < open_g.get(new_state, float("inf")):
                open_g[new_state] = new_g
                parent[new_state] = state
                stats[new_state] = (
                    cur_xfers + (1 if is_transfer else 0),
                    cur_time  + seg_time + (TRANSFER_PENALTY if is_transfer else 0),
                    cur_dist  + dist_km,
                )

    return [], 0, 0, 0.0, 0.0, len(explored_set), explored_set