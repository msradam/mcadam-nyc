"""Cost-profile evaluator. JSON-driven so the same profile JSON works in
Python prototype today and in the eventual Rust → WASM router.

A profile has two parts:
  blocks      - list of conditions that, if matched, mean the edge is impassable
                under this profile. Cost = None.
  weights     - { base: <field>, multipliers: [{if: cond, factor: f}, ...] }
                Cost = base * product(matching factors)

Conditions are tiny pattern-match objects:
  {highway_eq: "steps"}          - properties["highway"] == "steps"
  {footway_eq: "crossing"}       - properties["footway"] == "crossing"
  {curbramps_false: true}        - !curbramps (treats null as false)
  {tactile_paving_false: true}   - !tactile_paving
  {lit_false: true}              - !lit
  {surface_in: ["gravel", ...]}  - surface in the list
  {incline_pct_gt: 8.3}          - 100 * abs(incline) > 8.3 (or signed > X)
  {incline_pct_lt: -10.0}

Multiple keys in the same `if:` are AND'd. Lists of `blocks` or
`multipliers` represent OR (any block triggers; all matching multipliers apply).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def load_profile(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def _match(cond: dict, edge: dict, derived: dict) -> bool:
    """Return True if the edge satisfies all keys in `cond`."""
    for k, v in cond.items():
        if k == "highway_eq":
            if edge.get("highway") != v:
                return False
        elif k == "footway_eq":
            if edge.get("footway") != v:
                return False
        elif k == "surface_in":
            if edge.get("surface") not in v:
                return False
        elif k == "curbramps_false":
            if v and derived.get("curbramps"):
                return False
        elif k == "tactile_paving_false":
            if v and derived.get("tactile_paving"):
                return False
        elif k == "lit_false":
            if v and edge.get("ext:lit"):
                return False
        elif k == "incline_pct_gt":
            inc = edge.get("incline")
            if inc is None:
                return False
            if abs(float(inc) * 100) <= float(v):
                return False
        elif k == "incline_pct_lt":
            inc = edge.get("incline")
            if inc is None:
                return False
            if float(inc) * 100 >= float(v):
                return False
        else:
            # Unknown key: treat as no-match. Conservative.
            return False
    return True


def edge_cost(profile: dict, edge: dict, derived: dict) -> Optional[float]:
    """Compute the cost of traversing `edge` under `profile`.

    Returns None if the edge is blocked, else a positive float.
    `derived` carries computed-once-per-edge fields (length_m, curbramps, ...).
    """
    for blk in profile.get("blocks", []) or []:
        if _match(blk.get("if", {}), edge, derived):
            return None

    base_field = profile.get("weights", {}).get("base", "length")
    if base_field == "length":
        base = derived.get("length_m")
    else:
        base = edge.get(base_field)
    if base is None:
        return None

    cost = float(base)
    for mul in profile.get("weights", {}).get("multipliers", []) or []:
        if _match(mul.get("if", {}), edge, derived):
            cost *= float(mul.get("factor", 1.0))
    return cost
