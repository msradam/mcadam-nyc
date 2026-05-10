"""Smoke battery — runs the full six-tool catalog against a fixed set of
NYC landmark pairs and reports a pass/fail table.

This is the CLI-only programmatic test suite the user asked for. Run via:

    mcadam smoke

Acceptance bar (provisional, redline):
  - distance profile: 9 / 10 OD pairs return Ok
  - wheelchair profile: 7 / 10 (some genuinely have no wheelchair route)
  - segment inspector: 100% (any randomly-selected edge in the giant)
  - isochrone: returns >100 reachable nodes from any Manhattan landmark
  - closure simulation: returns a finite delta when closing one street
  - profile compare: returns at least one Ok result
"""

from __future__ import annotations

import time
from pathlib import Path

import networkx as nx
from rich.console import Console
from rich.table import Table
from rich import box

from .loader import load_graph, snap_to_giant
from .cost   import load_profile
from .router import (
    plan_route, find_reachable, simulate_closure, compare_routes,
    inspect_segment,
)


LANDMARKS = {
    "Penn Station":          (40.7506, -73.9935),
    "Grand Central":         (40.7527, -73.9772),
    "Times Square":          (40.7580, -73.9855),
    "Empire State Building": (40.7484, -73.9857),
    "Union Square":          (40.7359, -73.9911),
    "Washington Sq Park":    (40.7308, -73.9973),
    "Brooklyn Bridge MN":    (40.7115, -74.0028),
    "DUMBO":                 (40.7033, -73.9888),
    "Atlantic Av-Barclays":  (40.6840, -73.9778),
    "Williamsburg Bridge MN":(40.7155, -73.9810),
    "Williamsburg Bridge BK":(40.7128, -73.9650),
    "Court Sq Queens":       (40.7470, -73.9445),
    "LIC Hunters Pt":        (40.7424, -73.9534),
}

ROUTES = [
    ("Penn Station",          "Grand Central"),
    ("Times Square",          "Empire State Building"),
    ("Union Square",          "Washington Sq Park"),
    ("Brooklyn Bridge MN",    "DUMBO"),
    ("Atlantic Av-Barclays",  "DUMBO"),
    ("Williamsburg Bridge MN","Williamsburg Bridge BK"),
    ("Court Sq Queens",       "LIC Hunters Pt"),
    ("Empire State Building", "DUMBO"),
    ("Grand Central",         "Washington Sq Park"),
    ("Penn Station",          "Times Square"),
]

PROFILES_DIR = Path(__file__).parent / "profiles"


def _resolve(name, G, coords):
    lat, lon = LANDMARKS[name]
    return snap_to_giant(coords, G, lon, lat)


def run_smoke_battery(osw: Path, console: Console):
    console.rule("[bold]MCADAM · SMOKE BATTERY[/bold]")
    t0 = time.time()
    G, coords = load_graph(osw, log=lambda *_: None)  # silent load
    console.print(f"[dim]loaded graph in {time.time()-t0:.1f}s · "
                  f"{G.number_of_nodes():,} nodes · "
                  f"{G.number_of_edges():,} edges[/dim]")

    distance   = load_profile(PROFILES_DIR / "distance.json")
    wheelchair = load_profile(PROFILES_DIR / "wheelchair.json")
    low_vision = load_profile(PROFILES_DIR / "low_vision.json")

    # Snap once
    snapped = {}
    for name in {n for pair in ROUTES for n in pair}:
        nid, d = _resolve(name, G, coords)
        snapped[name] = (nid, d)

    results = {"distance": [], "wheelchair": [], "low_vision": []}

    # 1: plan_route — 10 pairs × 3 profiles
    table = Table(title="plan_route", box=box.MINIMAL,
                  header_style="bold")
    for col in ("route", "distance", "wheelchair", "low_vision"):
        table.add_column(col)
    for src, dst in ROUTES:
        u, _ = snapped[src]; v, _ = snapped[dst]
        cells = [f"{src} → {dst}"]
        for prof_id, prof in (("distance", distance),
                              ("wheelchair", wheelchair),
                              ("low_vision", low_vision)):
            tt = time.time()
            r = plan_route(G, prof, u, v)
            dt = (time.time() - tt) * 1000
            results[prof_id].append(r)
            if r["status"] == "ok":
                cells.append(f"{r['total_length_m']:.0f} m / {r['n_edges']}e ({dt:.0f}ms)")
            else:
                cells.append(f"[red]NO[/red] ({dt:.0f}ms)")
        table.add_row(*cells)
    console.print(table)

    # 2: pass-rate summary
    summary = Table(box=box.MINIMAL, header_style="bold")
    for col in ("profile", "ok", "total", "pct"):
        summary.add_column(col)
    for prof_id in ("distance", "wheelchair", "low_vision"):
        ok = sum(1 for r in results[prof_id] if r.get("status") == "ok")
        total = len(results[prof_id])
        summary.add_row(prof_id, str(ok), str(total),
                        f"{100*ok/total:.0f}%")
    console.print(summary)

    # 3: isochrone — Manhattan
    u, _ = snapped["Union Square"]
    console.print(f"\n[bold]find_reachable[/bold] · Union Square · 10 min · distance")
    iso = find_reachable(G, distance, u, time_budget_min=10)
    console.print(f"  {iso['n_reachable']:,} nodes within "
                  f"{iso['cost_budget_m']:.0f} m cost budget")

    # 4: closure simulation — close West 33rd Street near Penn
    console.print(f"\n[bold]simulate_closure[/bold] · Penn → Grand Central, "
                  f"close 'West 33rd Street'")
    u, _ = snapped["Penn Station"]; v, _ = snapped["Grand Central"]
    closure = simulate_closure(G, distance, u, v, ["West 33rd Street"])
    if closure["delta"]:
        console.print(f"  baseline:  {closure['baseline']['total_length_m']:.0f} m, "
                      f"{closure['baseline']['n_edges']} segs")
        console.print(f"  rerouted:  {closure['rerouted']['total_length_m']:.0f} m, "
                      f"{closure['rerouted']['n_edges']} segs")
        console.print(f"  delta:     {closure['delta']['delta_length_m']:+.0f} m, "
                      f"{closure['delta']['delta_n_edges']:+d} segs")
        console.print(f"  edges closed: {closure['n_closed']}")
    else:
        console.print(f"  [yellow]baseline or rerouted failed[/yellow]")

    # 5: compare profiles
    console.print(f"\n[bold]compare_routes[/bold] · Penn → Grand Central · "
                  f"distance vs wheelchair")
    cmp_ = compare_routes(G, [distance, wheelchair],
                          snapped["Penn Station"][0],
                          snapped["Grand Central"][0])
    for r in cmp_["results"]:
        if r["status"] == "ok":
            console.print(f"  {r['profile']:<11} {r['total_length_m']:>7.0f} m "
                          f"{r['n_edges']:>4} segs")
        else:
            console.print(f"  {r['profile']:<11} [red]NO TRAVERSABLE SURFACE[/red]")

    # 6: inspect a segment
    sample_edge = next(iter(G.edges()))
    console.print(f"\n[bold]inspect_segment[/bold] · {sample_edge[0]} → {sample_edge[1]}")
    seg = inspect_segment(G, *sample_edge)
    console.print(f"  length={seg['length_m']} m · "
                  f"highway={seg['highway']} · "
                  f"surface={seg['surface']} · "
                  f"curbramps={'✓' if (seg.get('tactile_paving') or seg.get('kerb')) else '—'}")

    console.rule(f"[dim]{time.time()-t0:.1f}s total[/dim]")
