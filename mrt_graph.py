"""
mrt_graph.py
Builds the Singapore MRT/LRT network graph for A* pathfinding.
"""

import pandas as pd
import re
from math import radians, sin, cos, sqrt, atan2
from collections import defaultdict

# ─────────────────────────── Utilities ───────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    """Straight-line distance in km between two GPS coordinates."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def display_name(full_name):
    """Convert 'CITY HALL MRT STATION' → 'City Hall'."""
    return full_name.replace(" MRT STATION", "").replace(" LRT STATION", "").title()


def get_line_prefix(code):
    """Extract line prefix from station code, e.g. 'EW14' → 'EW'."""
    m = re.match(r"([A-Z]+)\d*", code)
    return m.group(1) if m else None


# ─────────────────────────── Constants ───────────────────────────

LINE_COLORS = {
    "EW": "#009645", "NS": "#D42E12", "NE": "#9900AA",
    "CC": "#FA9E0D", "DT": "#005EC4", "TE": "#9D5B25",
    "CG": "#009645", "CE": "#005EC4",
    "BP": "#748477", "PE": "#748477", "PW": "#748477",
    "SE": "#748477", "SW": "#748477",
}

LINE_NAMES = {
    "EW": "East West Line",         "NS": "North South Line",
    "NE": "North East Line",        "CC": "Circle Line",
    "DT": "Downtown Line",          "TE": "Thomson-East Coast Line",
    "CG": "Changi Airport Branch",  "CE": "Circle Line Extension",
    "BP": "Bukit Panjang LRT",      "PE": "Punggol East LRT",
    "PW": "Punggol West LRT",       "SE": "Sengkang East LRT",
    "SW": "Sengkang West LRT",
}

# Average operating speed in km/h per line type
LINE_SPEED = {
    "EW": 45, "NS": 45, "NE": 45, "CC": 40, "DT": 45, "TE": 45,
    "CG": 45, "CE": 40,
    "BP": 25, "PE": 25, "PW": 25, "SE": 25, "SW": 25,
}

TRANSFER_PENALTY = 5.0   # minutes added for every line change

# ─────────────────────────── Line Sequences ───────────────────────────
# Ordered station codes for each line (determines adjacency)

LINE_SEQUENCES = {
    "EW": [
        "EW1","EW2","EW3","EW4","EW5","EW6","EW7","EW8","EW9","EW10",
        "EW11","EW12","EW13","EW14","EW15","EW16","EW17","EW18","EW19",
        "EW20","EW21","EW22","EW23","EW24","EW25","EW26","EW27","EW28",
        "EW29","EW30","EW31","EW32","EW33",
    ],
    "NS": [
        "NS1","NS2","NS3","NS4","NS5","NS7","NS8","NS9","NS10","NS11",
        "NS12","NS13","NS14","NS15","NS16","NS17","NS18","NS19","NS20",
        "NS21","NS22","NS23","NS24","NS25","NS26","NS27","NS28",
    ],
    "NE": [
        "NE1","NE3","NE4","NE5","NE6","NE7","NE8","NE9","NE10",
        "NE11","NE12","NE13","NE14","NE15","NE16","NE17",
    ],
    "CC": [
        "CC1","CC2","CC3","CC4","CC5","CC6","CC7","CC8","CC9","CC10",
        "CC11","CC12","CC13","CC14","CC15","CC16","CC17","CC18","CC19",
        "CC20","CC21","CC22","CC23","CC24","CC25","CC26","CC27","CC28","CC29",
    ],
    "DT": [
        "DT1","DT2","DT3","DT4","DT5","DT6","DT7","DT8","DT9","DT10",
        "DT11","DT12","DT13","DT14","DT15","DT16","DT17","DT18","DT19",
        "DT20","DT21","DT22","DT23","DT24","DT25","DT26","DT27","DT28",
        "DT29","DT30","DT31","DT32","DT33","DT34","DT35",
    ],
    "TE": [
        "TE1","TE2","TE3","TE4","TE5","TE6","TE7","TE8",
        "TE9","TE11","TE14","TE20",
    ],
    "CG": ["CG1","CG2"],
    "CE": ["CE1","CE2"],
    "BP": [
        "BP1","BP2","BP3","BP4","BP5","BP6",
        "BP7","BP8","BP9","BP10","BP11","BP12","BP13",
    ],
    "SE": ["STC","SE1","SE2","SE3","SE4","SE5"],
    "SW": ["STC","SW1","SW2","SW3","SW4","SW5","SW6","SW7","SW8"],
    "PE": ["PTC","PE1","PE2","PE3","PE4","PE5","PE6","PE7"],
    "PW": ["PTC","PW1","PW2","PW3","PW4","PW5","PW6","PW7"],
}

# Connections that close loops or link branches not captured by sequences
LOOP_CONNECTIONS = [
    ("CC29", "CC1",  "CC"),  # Circle Line is a loop
    ("BP13", "BP6",  "BP"),  # Bukit Panjang LRT: Senja → Bukit Panjang
    ("SE5",  "STC",  "SE"),  # Sengkang East LRT loop
    ("SW8",  "STC",  "SW"),  # Sengkang West LRT loop
    ("PE7",  "PTC",  "PE"),  # Punggol East LRT loop
    ("PW7",  "PTC",  "PW"),  # Punggol West LRT loop
]

# Branch junctions not derivable from sequences alone
BRANCH_CONNECTIONS = [
    ("EW4", "CG1", "CG"),  # Tanah Merah → Expo (Changi Airport branch)
    ("CC4", "CE1", "CE"),  # Promenade → Bayfront (Circle Line Extension)
]

# LRT ↔ MRT interchange transfers (cross-platform at same complex)
LRT_MRT_CONNECTIONS = [
    ("BP1", "NS4",  "transfer"),  # Choa Chu Kang LRT ↔ NS MRT
    ("BP6", "DT1",  "transfer"),  # Bukit Panjang LRT ↔ DT MRT
    ("STC", "NE16", "transfer"),  # Sengkang LRT hub ↔ NE MRT
    ("PTC", "NE17", "transfer"),  # Punggol LRT hub ↔ NE MRT
]


# ─────────────────────────── Graph Builder ───────────────────────────

def load_stations(csv_path):
    """
    Parse MRT_Stations.csv.
    Returns:
        stations   : {station_name → {lat, lon, codes}}
        code_to_name : {station_code → station_name}
    """
    df = pd.read_csv(csv_path)
    stations = {}
    code_to_name = {}

    for _, row in df.iterrows():
        name = row["STN_NAME"]
        codes = [c.strip() for c in str(row["STN_NO"]).split("/")]
        lat, lon = float(row["Latitude"]), float(row["Longitude"])
        stations[name] = {"lat": lat, "lon": lon, "codes": codes}
        for c in codes:
            code_to_name[c] = name

    # Outram Park is EW16 in the dataset but also serves the NE line as NE3
    if "OUTRAM PARK MRT STATION" in stations:
        stations["OUTRAM PARK MRT STATION"]["codes"].append("NE3")
        code_to_name["NE3"] = "OUTRAM PARK MRT STATION"

    return stations, code_to_name


def build_graph(csv_path):
    """
    Build the undirected weighted MRT/LRT graph.

    Graph format:
        {station_name: [(neighbor_name, travel_time_min, distance_km, line_code), ...]}

    Returns: (graph, stations, code_to_name)
    """
    stations, code_to_name = load_stations(csv_path)
    graph = defaultdict(list)

    def add_edge(code_a, code_b, line, override_time=None):
        name_a = code_to_name.get(code_a)
        name_b = code_to_name.get(code_b)
        if not name_a or not name_b or name_a == name_b:
            return
        sta = stations[name_a]
        stb = stations[name_b]
        dist = haversine(sta["lat"], sta["lon"], stb["lat"], stb["lon"])
        speed = LINE_SPEED.get(line, 40)
        travel_time = override_time if override_time else (dist / speed) * 60 + 0.5
        # Undirected
        graph[name_a].append((name_b, travel_time, dist, line))
        graph[name_b].append((name_a, travel_time, dist, line))

    # 1. Sequential connections within each line
    for line, seq in LINE_SEQUENCES.items():
        for i in range(len(seq) - 1):
            add_edge(seq[i], seq[i + 1], line)

    # 2. Loop and branch closures
    for code_a, code_b, line in LOOP_CONNECTIONS:
        add_edge(code_a, code_b, line)

    for code_a, code_b, line in BRANCH_CONNECTIONS:
        add_edge(code_a, code_b, line)

    # 3. LRT ↔ MRT cross-platform transfers (fixed 4-min walk/platform change)
    for code_a, code_b, _ in LRT_MRT_CONNECTIONS:
        name_a = code_to_name.get(code_a)
        name_b = code_to_name.get(code_b)
        if name_a and name_b and name_a != name_b:
            sta = stations[name_a]
            stb = stations[name_b]
            dist = haversine(sta["lat"], sta["lon"], stb["lat"], stb["lon"])
            graph[name_a].append((name_b, TRANSFER_PENALTY, dist, "transfer"))
            graph[name_b].append((name_a, TRANSFER_PENALTY, dist, "transfer"))

    # Ensure every station has an entry
    for name in stations:
        if name not in graph:
            graph[name] = []

    return dict(graph), stations, code_to_name


def get_lines_at_station(station_name, stations):
    """Return set of line codes serving a station, e.g. {'EW','NS'}."""
    codes = stations.get(station_name, {}).get("codes", [])
    return {get_line_prefix(c) for c in codes if get_line_prefix(c)}
