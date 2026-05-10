"""Mcadam CLI — terminal-only routing tools.

Examples:

    # Plan a route between two named landmarks (snapped to the giant component)
    mcadam route "Penn Station" "Grand Central" --profile distance
    mcadam route "Penn Station" "Grand Central" --profile wheelchair

    # Compare two profiles on the same OD pair
    mcadam compare "Times Square" "Empire State Building" \\
        --profiles distance,wheelchair

    # Isochrone — what's reachable in 10 minutes
    mcadam reachable "Union Square" --minutes 10 --profile distance

    # Inspect a single segment by node IDs
    mcadam inspect n_312002 n_294199

    # What-if closure — close a named street, replan
    mcadam closure "Penn Station" "Grand Central" \\
        --close-name "West 33rd Street" --profile distance

    # End-to-end smoke battery (10 routes × 2 profiles)
    mcadam test
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.text import Text

from .loader import load_graph, snap_to_giant
from .cost  import load_profile
from .router import (
    plan_route,
    find_reachable,
    simulate_closure,
    compare_routes,
    inspect_segment,
)


# ---------- defaults ----------

DEFAULT_OSW = Path.home() / "opensidewalks-nyc/output/nyc-osw.geojson"
PROFILES_DIR = Path(__file__).parent / "profiles"

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
    "Prospect Park":         (40.6602, -73.9690),
    "Williamsburg Bridge MN":(40.7155, -73.9810),
    "Williamsburg Bridge BK":(40.7128, -73.9650),
    "Court Sq Queens":       (40.7470, -73.9445),
    "LIC Hunters Pt":        (40.7424, -73.9534),
    "Yankee Stadium":        (40.8296, -73.9262),
    "161 St-Yankee Stadium": (40.8275, -73.9282),
}

console = Console()


# ---------- shared option block ----------

def _shared_options(f):
    f = click.option(
        "--osw", type=Path, default=DEFAULT_OSW,
        show_default=True,
        help="Path to the OSW v0.3 FeatureCollection.",
    )(f)
    f = click.option(
        "--profile", "profile_id", default="distance",
        show_default=True,
        help="Routing profile id: distance | wheelchair | low_vision",
    )(f)
    return f


def _resolve_profile(pid: str) -> dict:
    p = PROFILES_DIR / f"{pid}.json"
    if not p.exists():
        click.echo(f"unknown profile: {pid}", err=True); sys.exit(2)
    return load_profile(p)


def _resolve_endpoint(arg: str, G, node_coords) -> tuple[str, float]:
    """Resolve a CLI endpoint to a node id and snap distance.

    Accepts:
      - a known landmark name (case-insensitive substring match against LANDMARKS)
      - a node id like "n_131685"
      - a "lat,lon" pair
    """
    if arg.startswith("n_"):
        if arg in node_coords:
            return arg, 0.0
    if "," in arg:
        try:
            a, b = (x.strip() for x in arg.split(","))
            lat, lon = float(a), float(b)
            return snap_to_giant(node_coords, G, lon, lat)
        except ValueError:
            pass
    # Landmark substring match
    for name, (lat, lon) in LANDMARKS.items():
        if arg.lower() in name.lower():
            return snap_to_giant(node_coords, G, lon, lat)
    click.echo(f"can't resolve endpoint: {arg}", err=True); sys.exit(2)


# ---------- rendering ----------

def _render_route(r: dict, *, label: str = "RECORD"):
    if r["status"] != "ok":
        console.print(Panel(
            Text(f"NO TRAVERSABLE SURFACE — {r['profile']} profile",
                 style="bold red"),
            box=box.MINIMAL, border_style="red"))
        return

    title = (
        f"{label} · {r['profile'].upper()} PROFILE\n"
        f"{r['from']} → {r['to']}"
    )
    body  = (
        f"{r['total_length_m']:>8.1f} m   length\n"
        f"{r['n_edges']:>8d}   segments\n"
        f"{r['n_crossings']:>8d}   crossings on path\n"
        f"{r['ada_running_slope_compliant']:>8d}   segments meet ADA running-slope (≤5%)\n"
        f"{r['total_cost']:>8.1f}   profile cost units"
    )
    console.print(Panel(body, title=title, box=box.HEAVY,
                        border_style="grey50", title_align="left"))


def _render_segments_table(r: dict, *, n: int = 10):
    if r["status"] != "ok":
        return
    t = Table(box=box.MINIMAL, show_header=True, header_style="bold",
              padding=(0, 1))
    for col in ("#", "u", "v", "len_m", "subclass", "surface",
                "incl%", "curb", "name"):
        t.add_column(col)
    for i, e in enumerate(r["edges"][:n], start=1):
        sub = (
            "crossing" if e.get("footway") == "crossing"
            else "sidewalk" if e.get("footway") == "sidewalk"
            else e.get("highway") or "?"
        )
        t.add_row(
            str(i),
            (e.get("u") or "")[-8:],
            (e.get("v") or "")[-8:],
            f"{e.get('length_m') or 0:.1f}",
            sub,
            e.get("surface") or "—",
            f"{(e.get('incline') or 0)*100:+.2f}",
            "✓" if e.get("curbramps") else "—",
            (e.get("name") or "")[:24],
        )
    if len(r["edges"]) > n:
        t.add_row("…", "", "", "", "", "", "", "",
                  f"+{len(r['edges'])-n} more segments")
    console.print(t)


# ---------- commands ----------

@click.group()
@click.version_option()
def cli():
    """Mcadam — terminal pedestrian routing on the OSW NYC graph."""
    pass


@cli.command()
@click.argument("origin")
@click.argument("destination")
@_shared_options
def route(origin, destination, osw, profile_id):
    """Plan a single route from ORIGIN to DESTINATION."""
    G, coords = load_graph(osw)
    profile   = _resolve_profile(profile_id)
    u, du     = _resolve_endpoint(origin, G, coords)
    v, dv     = _resolve_endpoint(destination, G, coords)
    console.print(f"[dim]snap origin={du:.0f}m  destination={dv:.0f}m[/dim]")
    t0 = time.time()
    r = plan_route(G, profile, u, v)
    console.print(f"[dim]dijkstra: {(time.time()-t0)*1000:.0f}ms[/dim]")
    _render_route(r)
    _render_segments_table(r)


@cli.command()
@click.argument("origin")
@click.argument("destination")
@click.option("--profiles", default="distance,wheelchair",
              help="Comma-separated profile ids.")
@click.option("--osw", type=Path, default=DEFAULT_OSW, show_default=True)
def compare(origin, destination, profiles, osw):
    """Compare multiple profiles on the same origin/destination."""
    G, coords = load_graph(osw)
    profs = [_resolve_profile(p.strip()) for p in profiles.split(",") if p.strip()]
    u, _ = _resolve_endpoint(origin, G, coords)
    v, _ = _resolve_endpoint(destination, G, coords)
    out = compare_routes(G, profs, u, v)
    for r in out["results"]:
        _render_route(r, label="RECORD")
    # Side-by-side delta vs first profile
    base = out["results"][0]
    if base.get("status") == "ok":
        for r in out["results"][1:]:
            if r.get("status") != "ok":
                console.print(f"[bold red]{r['profile']}: NO TRAVERSABLE SURFACE[/bold red]")
                continue
            dl  = r["total_length_m"] - base["total_length_m"]
            dn  = r["n_edges"] - base["n_edges"]
            console.print(
                f"[bold yellow]{r['profile']:<11}[/bold yellow] vs "
                f"[bold]{base['profile']}[/bold]: "
                f"Δlength {dl:+.1f} m, Δsegments {dn:+d}"
            )


@cli.command()
@click.argument("origin")
@click.option("--minutes", type=float, default=10.0, show_default=True,
              help="Walking time budget.")
@_shared_options
def reachable(origin, minutes, osw, profile_id):
    """Isochrone — show how many graph nodes are reachable in MINUTES."""
    G, coords = load_graph(osw)
    profile = _resolve_profile(profile_id)
    u, du = _resolve_endpoint(origin, G, coords)
    console.print(f"[dim]snap={du:.0f}m[/dim]")
    t0 = time.time()
    r = find_reachable(G, profile, u, time_budget_min=minutes)
    console.print(f"[dim]dijkstra: {(time.time()-t0)*1000:.0f}ms[/dim]")
    title = (f"REACHABLE · {r['profile'].upper()} · {minutes:.0f} min budget"
             f" ({r['cost_budget_m']:.0f} m at 4.8 km/h)")
    body = (
        f"{r['n_reachable']:>8d}   nodes reachable\n"
        f"{(r['n_reachable']/G.number_of_nodes())*100:>8.2f}   % of graph\n"
    )
    console.print(Panel(body, title=title, box=box.HEAVY,
                        border_style="grey50", title_align="left"))


@cli.command()
@click.argument("u_id")
@click.argument("v_id")
@click.option("--osw", type=Path, default=DEFAULT_OSW, show_default=True)
def inspect(u_id, v_id, osw):
    """Inspect the ADA story for a single segment by node IDs."""
    G, _ = load_graph(osw)
    r = inspect_segment(G, u_id, v_id)
    if r["status"] != "ok":
        console.print(f"[red]segment not found: {u_id}→{v_id}[/red]")
        return
    rows = [
        ("u",                r["u"]),
        ("v",                r["v"]),
        ("length",           f"{r['length_m']} m"),
        ("subclass",         f"{r['highway']} / {r['footway'] or '—'}"),
        ("surface",          r["surface"] or "—"),
        ("incline",          f"{(r['incline'] or 0)*100:+.2f}%"),
        ("running slope",    f"{r['running_slope_pct']}%" if r['running_slope_pct'] else "—"),
        ("cross slope",      f"{r['cross_slope_pct']}%"   if r['cross_slope_pct']   else "—"),
        ("kerb",             r["kerb"] or "—"),
        ("tactile paving",   "yes" if r["tactile_paving"] else "—"),
        ("lit",              r["lit"] or "—"),
        ("name",             r["name"] or "—"),
        ("borough",          r["borough"] or "—"),
        ("OSM id",           r["osm_id"] or "—"),
        ("ADA violations",   r["ada_violations"] or "—"),
    ]
    t = Table(box=box.MINIMAL, show_header=False, padding=(0, 1))
    t.add_column(style="bold"); t.add_column()
    for k, v in rows:
        t.add_row(k, str(v))
    console.print(Panel(t, title=f"SEGMENT {u_id}→{v_id}",
                        box=box.HEAVY, border_style="grey50",
                        title_align="left"))


@cli.command()
@click.argument("origin")
@click.argument("destination")
@click.option("--close-name", "close_names", multiple=True,
              help="Close all edges with this exact `name` property.")
@click.option("--close-edge", "close_edges", multiple=True,
              help="Close edges by their `_id` field.")
@_shared_options
def closure(origin, destination, close_names, close_edges, osw, profile_id):
    """What-if: close some edges/streets and replan."""
    G, coords = load_graph(osw)
    profile = _resolve_profile(profile_id)
    u, _ = _resolve_endpoint(origin, G, coords)
    v, _ = _resolve_endpoint(destination, G, coords)
    closures = list(close_names) + list(close_edges)
    if not closures:
        click.echo("no closures specified (--close-name / --close-edge)", err=True)
        sys.exit(2)
    out = simulate_closure(G, profile, u, v, closures)
    console.print(f"[dim]closures: {closures}, edges removed: {out['n_closed']}[/dim]")
    _render_route(out["baseline"], label="BASELINE")
    _render_route(out["rerouted"], label="REROUTED")
    if out["delta"]:
        d = out["delta"]
        console.print(
            f"[bold yellow]INTERRUPTION DELTA[/bold yellow] · "
            f"Δlength {d['delta_length_m']:+.1f} m · "
            f"Δsegments {d['delta_n_edges']:+d}"
        )


@cli.command()
@click.option("--osw", type=Path, default=DEFAULT_OSW, show_default=True)
def smoke(osw):
    """Run a 10-route × 2-profile smoke battery."""
    from .smoke import run_smoke_battery
    run_smoke_battery(osw=osw, console=console)


def main():
    cli()


if __name__ == "__main__":
    main()
