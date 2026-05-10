"""Natural-language → mcadam CLI translator (Ollama).

Hypothesis: small models can't reliably JSON-tool-call, but they *can* emit
short, well-grammared CLI command strings. The CLI surface is tiny and
mechanical; this is transliteration, not reasoning.

Usage:
    mcadam-nl "wheelchair route from Penn to Grand Central"
    mcadam-nl --model granite4:8b --execute "what can I walk to from Union Sq in 15 min"
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from textwrap import dedent

import requests


OLLAMA = "http://127.0.0.1:11434"

# The whole CLI surface, hand-written for the prompt. Concise > exhaustive.
SYSTEM = dedent("""\
    You translate natural-language pedestrian-routing queries into a single
    `mcadam` CLI command. Output ONLY the command, no explanation, no quotes
    around the whole line, no markdown.

    Available verbs and arguments:

    1. mcadam route ORIGIN DEST --profile P
       Plan a single pedestrian route. P is one of: distance, wheelchair, low_vision.

    2. mcadam compare ORIGIN DEST --profiles distance,wheelchair
       Compare two profiles on the same route.

    3. mcadam reachable ORIGIN --minutes N --profile P
       Show what's reachable on foot in N minutes.

    4. mcadam closure ORIGIN DEST --close-name "STREET NAME" --profile P
       What-if: close a named street and replan.

    5. mcadam inspect U_NODE V_NODE
       Inspect ADA properties of one segment by node IDs (e.g. n_312002 n_294199).

    Place names like "Penn Station", "Grand Central", "Times Square",
    "Brooklyn Bridge MN", etc. should be quoted as a single argument.

    PROFILE DEFAULTS:
    - if user mentions wheelchair / accessible / step-free / curb cut → wheelchair
    - if user mentions blind / low vision / tactile / audible → low_vision
    - otherwise → distance

    Examples:

    Q: get me from Penn Station to Grand Central
    A: mcadam route "Penn Station" "Grand Central" --profile distance

    Q: wheelchair-friendly walk from Times Square to the Empire State Building
    A: mcadam route "Times Square" "Empire State Building" --profile wheelchair

    Q: what's reachable on foot from Union Square in 10 minutes
    A: mcadam reachable "Union Square" --minutes 10 --profile distance

    Q: how does wheelchair routing differ from distance from Penn to Grand Central?
    A: mcadam compare "Penn Station" "Grand Central" --profiles distance,wheelchair

    Q: if Broadway is closed near Times Square, how do I get from Times Square to the Empire State?
    A: mcadam closure "Times Square" "Empire State Building" --close-name "Broadway" --profile distance

    Q: inspect segment n_312002 to n_294199
    A: mcadam inspect n_312002 n_294199

    Q: low-vision route from Washington Square Park to Union Square
    A: mcadam route "Washington Sq Park" "Union Square" --profile low_vision

    Now translate the next query.
""")

VALID_VERBS = {"route", "compare", "reachable", "closure", "inspect"}


def call_ollama(model: str, query: str, *, temperature: float = 0.0) -> tuple[str, float]:
    payload = {
        "model": model,
        "system": SYSTEM,
        "prompt": f"Q: {query}\nA: ",
        "stream": False,
        "options": {"temperature": temperature, "stop": ["\n", "Q:"]},
    }
    t0 = time.time()
    r = requests.post(f"{OLLAMA}/api/generate", json=payload, timeout=120)
    dt = time.time() - t0
    r.raise_for_status()
    out = r.json().get("response", "").strip()
    return out, dt


def parse_and_validate(line: str) -> tuple[bool, str, list[str]]:
    """Return (ok, reason, argv). argv excludes the leading 'mcadam'."""
    line = line.strip()
    # Strip common LLM ornaments
    if line.startswith("```"):
        line = line.strip("`").strip()
    line = line.removeprefix("$ ").strip()

    try:
        argv = shlex.split(line)
    except ValueError as e:
        return False, f"shlex error: {e}", []

    if not argv:
        return False, "empty output", []
    if argv[0] != "mcadam":
        return False, f"first token is {argv[0]!r}, expected 'mcadam'", argv
    if len(argv) < 2:
        return False, "no verb", argv
    if argv[1] not in VALID_VERBS:
        return False, f"unknown verb: {argv[1]}", argv
    return True, "", argv[1:]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("query", nargs="*", help="Natural-language query.")
    ap.add_argument("--model", default="granite4:350m",
                    help="Ollama model id.")
    ap.add_argument("--execute", action="store_true",
                    help="Run the parsed command via subprocess.")
    ap.add_argument("--bench", type=str, default=None,
                    help="Run a benchmark file (newline-delimited JSON of "
                         "{q, expect_verb}) and print pass/fail.")
    args = ap.parse_args()

    if args.bench:
        run_bench(args.bench, model=args.model)
        return

    if not args.query:
        ap.error("query required (or use --bench)")

    q = " ".join(args.query)
    print(f"Q: {q}")
    raw, dt = call_ollama(args.model, q)
    print(f"→ ({dt*1000:.0f}ms, {args.model})")
    print(f"   {raw!r}")
    ok, reason, argv = parse_and_validate(raw)
    if not ok:
        print(f"   PARSE FAIL: {reason}")
        sys.exit(1)
    full = ["mcadam"] + argv
    print(f"   PARSED: {' '.join(shlex.quote(a) for a in full)}")

    if args.execute:
        print()
        # Use the venv's mcadam
        import os
        venv_bin = os.path.expanduser("~/mcadam-nyc/.venv/bin/mcadam")
        cp = subprocess.run([venv_bin] + argv, check=False)
        sys.exit(cp.returncode)


def run_bench(path: str, model: str):
    print(f"BENCH · {path} · {model}")
    print("─" * 70)
    cases = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cases.append(json.loads(line))

    from collections import Counter
    n_pass_verb  = 0
    n_pass_exec  = 0
    times = []
    by_verb_total = Counter()
    by_verb_pass  = Counter()
    confusion     = Counter()  # (expected, got)
    for i, case in enumerate(cases, start=1):
        q = case["q"]
        expect_verb = case["expect_verb"]
        by_verb_total[expect_verb] += 1
        raw, dt = call_ollama(model, q)
        times.append(dt)
        ok, reason, argv = parse_and_validate(raw)
        verb = argv[0] if (ok and argv) else None
        verb_pass = (verb == expect_verb)
        if verb_pass:
            n_pass_verb += 1
            by_verb_pass[expect_verb] += 1
        else:
            confusion[(expect_verb, verb or "(invalid)")] += 1

        # Optional execution check — does the parsed command return Ok?
        exec_pass = None
        if ok and case.get("expect_ok"):
            try:
                import os
                venv_bin = os.path.expanduser("~/mcadam-nyc/.venv/bin/mcadam")
                cp = subprocess.run(
                    [venv_bin] + argv,
                    capture_output=True, text=True, timeout=30,
                )
                exec_pass = (cp.returncode == 0)
                if exec_pass:
                    n_pass_exec += 1
            except Exception:
                exec_pass = False

        verdict = "✓" if verb_pass else "✗"
        exec_marker = ""
        if exec_pass is True:
            exec_marker = " ✓exec"
        elif exec_pass is False:
            exec_marker = " ✗exec"
        print(f"{verdict}{exec_marker} [{dt*1000:>5.0f}ms] {q}")
        if not verb_pass:
            print(f"   want={expect_verb} got={verb!r} reason={reason or 'wrong verb'}")
            print(f"   raw={raw!r}")

    print("─" * 70)
    n = len(cases)
    n_exec_attempted = sum(1 for c in cases if c.get("expect_ok"))
    print(f"verb match:    {n_pass_verb}/{n} = {100*n_pass_verb/n:.0f}%")
    if n_exec_attempted:
        print(f"exec returns Ok: {n_pass_exec}/{n_exec_attempted} "
              f"= {100*n_pass_exec/n_exec_attempted:.0f}%")
    print(f"avg latency:   {sum(times)/len(times)*1000:.0f}ms  "
          f"(p50={sorted(times)[len(times)//2]*1000:.0f}ms, "
          f"p95={sorted(times)[int(0.95*len(times))]*1000:.0f}ms)")

    # Per-verb pass rate
    print()
    print(f"{'verb':<11}{'pass':>6}{'total':>7}{'rate':>7}")
    for v in sorted(by_verb_total):
        t = by_verb_total[v]; p = by_verb_pass[v]
        print(f"  {v:<10}{p:>6}{t:>7}{100*p/t:>6.0f}%")

    if confusion:
        print()
        print("Confusion (expected -> got):")
        for (exp, got), c in confusion.most_common():
            print(f"  {exp:<10} -> {got:<10} {c}")


if __name__ == "__main__":
    main()
