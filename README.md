# mcadam

Local-first, privacy-respecting, natural-language pedestrian routing for New York City.

> *Status: scaffolding. CLI prototype in place; browser app + LLM tier next.*
> See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the technical sketch and [`DESIGN_BRIEF.md`](DESIGN_BRIEF.md) for the design language.

## CLI quickstart

```bash
uv venv && source .venv/bin/activate
uv pip install -e .

# Route between landmarks
mcadam route "Penn Station" "Grand Central" --profile distance
mcadam route "Penn Station" "Grand Central" --profile wheelchair

# Compare profiles
mcadam compare "Times Square" "Empire State Building" \
  --profiles distance,wheelchair

# Smoke battery
mcadam smoke
```

The CLI consumes the OSW v0.3 artifact published at
[`opensidewalks-nyc`](https://github.com/msradam/opensidewalks-nyc) (default
path: `~/opensidewalks-nyc/output/nyc-osw.geojson`).

## Naming

Honors **John Loudon McAdam** (Scottish road engineer, 1756–1836) — the
*macadam* paving technique, *tarmac(adam)*, every paved road since. **Granite**
(IBM's small-LLM family) paves the substrate; **mcadam** is the routing layer
riding on top.
