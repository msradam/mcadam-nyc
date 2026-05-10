"""Load the OSW v0.3 GeoJSON into NetworkX, with a pickle cache so we don't
re-parse the 460 MB file on every CLI invocation.

The graph is undirected (pedestrian edges are bidirectional). Each edge carries
all its OSW properties verbatim plus a derived dict (`length_m`, `curbramps`,
`tactile_paving`) so the cost evaluator doesn't recompute on every Dijkstra
pop.
"""

from __future__ import annotations

import json
import math
import pickle
import sys
import time
from pathlib import Path
from typing import Optional

import networkx as nx

CACHE_VERSION = "v1"


def _haversine_m(p1, p2):
    R = 6371000.0
    lat1, lat2 = math.radians(p1[1]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = math.radians(p2[0] - p1[0])
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _polyline_length_m(coords) -> float:
    return sum(_haversine_m(coords[i], coords[i + 1])
               for i in range(len(coords) - 1))


def _cache_path(geojson: Path) -> Path:
    stat = geojson.stat()
    sig = f"{geojson.name}-{stat.st_size}-{int(stat.st_mtime)}-{CACHE_VERSION}"
    return geojson.parent / f".{sig}.cache.pkl"


def load_graph(geojson_path: Path, *, force: bool = False, log=print):
    """Return (G, node_coords). G is undirected.

    Edges carry: all OSW properties + a 'derived' dict (length_m, curbramps,
    tactile_paving). Nodes carry: lon, lat from the corresponding Point Feature.
    """
    cache = _cache_path(geojson_path)
    if cache.exists() and not force:
        log(f"[loader] cache hit: {cache.name}")
        with cache.open("rb") as f:
            return pickle.load(f)

    log(f"[loader] reading {geojson_path.name}...")
    t0 = time.time()
    fc = json.loads(geojson_path.read_text())
    log(f"[loader]   features: {len(fc['features']):,} ({time.time()-t0:.1f}s)")

    # Pass 1: nodes
    node_coords: dict[str, tuple[float, float]] = {}
    curb_node_ids: set[str] = set()
    tactile_node_ids: set[str] = set()
    for feat in fc["features"]:
        g = feat.get("geometry") or {}
        p = feat.get("properties") or {}
        if g.get("type") != "Point":
            continue
        nid = p.get("_id")
        coords = g.get("coordinates")
        if not nid or not coords:
            continue
        node_coords[nid] = (float(coords[0]), float(coords[1]))
        if p.get("barrier") == "kerb" or p.get("kerb") in {"lowered", "raised", "flush", "rolled"}:
            curb_node_ids.add(nid)
        if p.get("tactile_paving") in {"yes", "contrasted", "primitive"}:
            tactile_node_ids.add(nid)

    log(f"[loader]   points: {len(node_coords):,} (curb-annotated: {len(curb_node_ids):,})")

    # Pass 2: edges
    G = nx.Graph()
    skipped = 0
    for feat in fc["features"]:
        g = feat.get("geometry") or {}
        p = feat.get("properties") or {}
        if g.get("type") != "LineString":
            continue
        u = p.get("_u_id"); v = p.get("_v_id")
        if not u or not v or u == v:
            skipped += 1; continue
        coords = g.get("coordinates") or []
        if len(coords) < 2:
            skipped += 1; continue

        coords = [(float(c[0]), float(c[1])) for c in coords]
        derived = {
            "length_m":       round(_polyline_length_m(coords), 3),
            "curbramps":      (u in curb_node_ids) or (v in curb_node_ids),
            "tactile_paving": (u in tactile_node_ids) or (v in tactile_node_ids),
        }
        # Normalise some fields for cost-evaluator convenience
        edge_data = dict(p)  # copy
        edge_data["coordinates"] = coords
        edge_data["derived"] = derived

        # NetworkX undirected: parallel edges between (u,v) get merged. Keep
        # the longer-described one.
        if G.has_edge(u, v):
            existing = G[u][v]
            if (existing.get("derived", {}).get("length_m", 0)
                    >= derived["length_m"]):
                continue
        G.add_edge(u, v, **edge_data)

    log(f"[loader]   edges in graph: {G.number_of_edges():,} (skipped: {skipped:,})")
    log(f"[loader]   nodes in graph: {G.number_of_nodes():,}")
    log(f"[loader]   total time: {time.time()-t0:.1f}s")

    # Cache
    with cache.open("wb") as f:
        pickle.dump((G, node_coords), f, protocol=pickle.HIGHEST_PROTOCOL)
    log(f"[loader] cached: {cache.name} ({cache.stat().st_size/1024/1024:.1f} MB)")

    return G, node_coords


def snap_to_giant(node_coords: dict, G: nx.Graph, lon: float, lat: float
                  ) -> tuple[Optional[str], float]:
    """Brute-force nearest-node search restricted to the giant connected
    component. Fast enough up to ~1M nodes, but switch to scipy.spatial.cKDTree
    if benchmarks demand it.
    """
    giant = max(nx.connected_components(G), key=len)
    target = (lon, lat)
    best_id = None
    best_d = float("inf")
    for nid in giant:
        if nid not in node_coords:
            continue
        d = _haversine_m(target, node_coords[nid])
        if d < best_d:
            best_d = d
            best_id = nid
    return best_id, best_d
