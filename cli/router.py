"""Mcadam routing primitives — Python prototype.

Six tools that mirror the LLM tool catalog. Each consumes a NetworkX graph
plus a profile dict and returns a structured result dict the CLI renders as
a survey card.

The cost function is a closure over (profile) that takes (u, v, edge_data)
and returns a float or None. None means "blocked under this profile."
This matches NetworkX dijkstra's `weight` callable contract.
"""

from __future__ import annotations

import math
from typing import Any, Optional

import networkx as nx

from .cost import edge_cost


def _make_weight(profile: dict):
    def weight(u, v, d):
        c = edge_cost(profile, d, d.get("derived") or {})
        return c if c is not None else None
    return weight


def _haversine_m(p1, p2):
    R = 6371000.0
    lat1, lat2 = math.radians(p1[1]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = math.radians(p2[0] - p1[0])
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Tool 1: plan_route
# ---------------------------------------------------------------------------

def plan_route(G: nx.Graph, profile: dict, u: str, v: str) -> dict:
    weight = _make_weight(profile)
    try:
        cost, path = nx.single_source_dijkstra(G, u, target=v, weight=weight)
    except nx.NetworkXNoPath:
        return {"status": "no_traversable_surface",
                "profile": profile["id"], "from": u, "to": v}
    if cost is None:
        return {"status": "no_traversable_surface",
                "profile": profile["id"], "from": u, "to": v}

    edges = []
    total_length = 0.0
    ada_compliant = 0
    crossings = 0
    for a, b in zip(path, path[1:]):
        e = G[a][b]
        d = e.get("derived") or {}
        total_length += d.get("length_m") or 0
        if e.get("footway") == "crossing":
            crossings += 1
        rs = e.get("ext:running_slope_pct")
        if rs is not None and abs(float(rs)) <= 5.0:
            ada_compliant += 1
        edges.append({
            "u": a, "v": b,
            "length_m":    d.get("length_m"),
            "highway":     e.get("highway"),
            "footway":     e.get("footway"),
            "surface":     e.get("surface"),
            "incline":     e.get("incline"),
            "name":        e.get("name"),
            "curbramps":   d.get("curbramps"),
            "tactile_paving": d.get("tactile_paving"),
        })
    return {
        "status":         "ok",
        "profile":        profile["id"],
        "from":           u, "to": v,
        "total_length_m": round(total_length, 1),
        "edges":          edges,
        "n_edges":        len(edges),
        "n_crossings":    crossings,
        "ada_running_slope_compliant": ada_compliant,
        "total_cost":     round(float(cost), 1),
    }


# ---------------------------------------------------------------------------
# Tool 2: find_reachable (isochrone)
# ---------------------------------------------------------------------------

def find_reachable(G: nx.Graph, profile: dict, u: str, *,
                   time_budget_min: float = 10.0,
                   walking_speed_mps: float = 1.34) -> dict:
    """Walking speed default 1.34 m/s ≈ 4.8 km/h — a typical adult pace."""
    cost_budget_m = time_budget_min * 60.0 * walking_speed_mps
    weight = _make_weight(profile)

    lengths = nx.single_source_dijkstra_path_length(
        G, u, cutoff=cost_budget_m, weight=weight
    )
    return {
        "status":          "ok",
        "profile":         profile["id"],
        "from":            u,
        "time_budget_min": time_budget_min,
        "cost_budget_m":   round(cost_budget_m, 1),
        "n_reachable":     len(lengths),
        "node_costs":      lengths,  # nid -> metres
    }


# ---------------------------------------------------------------------------
# Tool 3: find_nearest (POI search not yet wired — placeholder showing nearest
# nodes within a cost budget; in v1 this'd consume the POI index)
# ---------------------------------------------------------------------------

def find_nearest_node_set(G: nx.Graph, profile: dict, u: str,
                          candidate_ids: set, *,
                          max_results: int = 5) -> dict:
    """Return the closest nodes from `candidate_ids` reachable from `u` under
    `profile`, by routing cost. Used as the kernel for find_nearest once a POI
    index is plugged in."""
    weight = _make_weight(profile)
    lengths = nx.single_source_dijkstra_path_length(G, u, weight=weight)
    hits = sorted(
        ((nid, lengths[nid]) for nid in candidate_ids if nid in lengths),
        key=lambda x: x[1]
    )[:max_results]
    return {
        "status":   "ok",
        "profile":  profile["id"],
        "from":     u,
        "results":  [{"node_id": n, "cost_m": round(c, 1)} for n, c in hits],
    }


# ---------------------------------------------------------------------------
# Tool 4: simulate_closure
# ---------------------------------------------------------------------------

def simulate_closure(G: nx.Graph, profile: dict, u: str, v: str,
                     closures: list) -> dict:
    """Compute baseline route, then route again with `closures` removed.

    `closures` can be a list of edge IDs (matched against `_id`), street names
    (matched against `name`, exact), or a list of (u, v) pairs.
    """
    base = plan_route(G, profile, u, v)

    # Build subgraph view that excludes closures
    edges_to_remove = set()
    for spec in closures:
        if isinstance(spec, tuple) and len(spec) == 2:
            edges_to_remove.add(tuple(sorted(spec)))
            continue
        for a, b, d in G.edges(data=True):
            if d.get("_id") == spec or d.get("name") == spec:
                edges_to_remove.add(tuple(sorted((a, b))))

    Gc = G.copy()
    for a, b in edges_to_remove:
        if Gc.has_edge(a, b):
            Gc.remove_edge(a, b)

    re_routed = plan_route(Gc, profile, u, v)

    delta = None
    if base.get("status") == "ok" and re_routed.get("status") == "ok":
        delta = {
            "delta_length_m":   round(re_routed["total_length_m"] - base["total_length_m"], 1),
            "delta_n_edges":    re_routed["n_edges"] - base["n_edges"],
        }

    return {
        "status":     "ok",
        "profile":    profile["id"],
        "from":       u, "to": v,
        "closures":   list(closures),
        "n_closed":   len(edges_to_remove),
        "baseline":   base,
        "rerouted":   re_routed,
        "delta":      delta,
    }


# ---------------------------------------------------------------------------
# Tool 5: compare_routes
# ---------------------------------------------------------------------------

def compare_routes(G: nx.Graph, profiles: list[dict], u: str, v: str) -> dict:
    rows = [plan_route(G, p, u, v) for p in profiles]
    return {
        "status":   "ok",
        "from":     u, "to": v,
        "profiles": [p["id"] for p in profiles],
        "results":  rows,
    }


# ---------------------------------------------------------------------------
# Tool 6: inspect_segment
# ---------------------------------------------------------------------------

def inspect_segment(G: nx.Graph, u: str, v: str) -> dict:
    if not G.has_edge(u, v):
        return {"status": "not_found", "u": u, "v": v}
    e = G[u][v]
    d = e.get("derived") or {}
    return {
        "status":      "ok",
        "u":           u, "v": v,
        "length_m":    d.get("length_m"),
        "highway":     e.get("highway"),
        "footway":     e.get("footway"),
        "surface":     e.get("surface"),
        "incline":     e.get("incline"),
        "running_slope_pct": e.get("ext:running_slope_pct"),
        "cross_slope_pct":   e.get("ext:cross_slope_pct"),
        "kerb":        e.get("ext:kerb"),
        "tactile_paving": d.get("tactile_paving"),
        "lit":         e.get("ext:lit"),
        "name":        e.get("name"),
        "borough":     e.get("ext:borough"),
        "osm_id":      e.get("ext:osm_id"),
        "ada_violations": e.get("ext:ada_violations"),
    }
