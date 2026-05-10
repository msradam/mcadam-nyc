# Mcadam — architecture sketch

> *Status: sketch, dated 2026-05-10. Not a spec. Reactable.*

## What it is

**Mcadam is a local-first, privacy-respecting, natural-language pedestrian routing assistant for New York City.** The model runs on the user's GPU. The router runs in the user's browser. The data is fetched once, cached in IndexedDB, and never re-contacts a server. The query, the location, the destination — none of it leaves the device.

The name honors **John Loudon McAdam** (Scottish engineer, 1756–1836), who invented the road-paving technique of laying compacted, graded crushed stone of uniform size — the basis of every modern paved road. *Tarmacadam* (later *tarmac*) is the same technique with tar binding the aggregate; both words are McAdam tributes. **Granite** (IBM's small-LLM family) paves the substrate; **Mcadam** is the routing layer riding on top. The brand is geological, infrastructural, pragmatic — *aggregate*, *surface*, *grade*.

The role split:

- **`opensidewalks-nyc`** is the public-good data artifact. ODbL-1.0. Anyone can use it for whatever — academic research, a competitor product, a city's own portal. Not Mcadam's moat.
- **Mcadam** is the unique edge-compute story: a runnable browser app where the entire pipeline (NL → tool dispatch → routing → map render) executes locally, with zero network calls after first load.

## What it isn't

- Not a chat interface. The Ariadne disambiguation work (full-width query bar, numbered query log, ROMAN numeral route headings) carries forward. Mcadam is a *routing terminal*, not "AI on a map."
- Not a server. Mapbox-style hosted routing is out of scope. If we expose a server-side fallback, it's a Docker recipe in the repo, not a hosted endpoint we operate.
- Not a multi-modal trip planner. Pedestrian-first. Transit integration via Minotor (already in Ariadne) is opt-in, not the headline.

## Stack overview (top down)

```
┌──────────────────────────────────────────────────────────────────┐
│  UI shell · SvelteKit + Svelte 5 · MapLibre GL + PMTiles        │
│  IBM Plex Sans + Plex Mono · graphite/granite palette           │
├──────────────────────────────────────────────────────────────────┤
│  Tool dispatcher · closed vocabulary · constrained JSON output  │
│   plan_route · find_reachable · find_nearest                    │
│   simulate_closure · compare_routes · inspect_segment           │
├──────────────────────────────────────────────────────────────────┤
│  LLM tier (WebLLM, WebGPU) — port from ~/granite-web             │
│   ▸ Granite-4.0-1B   (q4f32_1, WebGPU) — primary, 5/5 harness   │
│   ▸ Granite-4.0-1B   (Q3_K_M GGUF / wllama) — non-WebGPU fall   │
├──────────────────────────────────────────────────────────────────┤
│  Routing core · Rust → WASM · OSW-aware Dijkstra                │
│   CSR layout · bidirectional · pluggable cost-profile JSON      │
├──────────────────────────────────────────────────────────────────┤
│  Data · IndexedDB-cached on first load                          │
│   ▸ opensidewalks-nyc release-pinned (ODbL-1.0)                 │
│   ▸ POI / comfort / address indexes (nyc-pois, nyc-comfort)     │
│   ▸ PMTiles vector basemap                                      │
└──────────────────────────────────────────────────────────────────┘
                  ↑ first load only — then offline
```

## Pivots from Ariadne

| Concern | Ariadne (today) | Mcadam (proposed) |
|---|---|---|
| Pedestrian schema | Bespoke `nyc-pedestrian.bin` | Canonical OSW v0.3 (consume `opensidewalks-nyc` releases) |
| Routing engine | Bespoke Rust router | Rust router rewrite, OSW-native cost-profile JSON |
| Reference engine | n/a | Match cost weights against AccessMap's published Bolten et al. wheelchair model |
| LLM | Granite-4-1B (q4f32) via Ariadne template | **Granite-4-1B via the `~/granite-web` port; same model, same protocol, OSW-grounded tools** |
| Tool calling | String-templated prompts | **Constrained JSON-Schema decoding** (the missing ingredient last time) |
| Voice (UI) | Civic-record / archival | Engineering-notebook / specification-sheet |
| Brand register | Greek-myth thread (Ariadne, labyrinth) | Geological-infrastructural (granite, aggregate, road) |
| Identity | Hackathon artifact | Shippable product |

The router rewrite, the schema migration, and the LLM downgrade are the three load-bearing changes. Everything else flows from those.

## Tool catalog (closed vocabulary, ~6)

The LLM never generates free-form text directly. It maps a user utterance to one of these JSON tool calls. A tool's schema is its contract.

```ts
// 1. Point-to-point pedestrian route
plan_route({
  from:    Place | LatLon,
  to:      Place | LatLon,
  profile: "distance" | "wheelchair" | "low_vision" | "child_safe",
  options?: { avoid_crossings_without_curbramp?: bool, max_incline_pct?: number }
})

// 2. Isochrone — everything reachable in N minutes
find_reachable({
  from:        Place | LatLon,
  time_budget: Duration,
  profile:     RoutingProfile
})

// 3. Closest POI of a category, with route attached
find_nearest({
  from:     Place | LatLon,
  category: "cooling_center" | "library" | "restroom" | "subway_ada" | ...,
  profile:  RoutingProfile,
  max_results?: 1..10
})

// 4. The urban-planning what-if
simulate_closure({
  closures: [ EdgeRef | StreetName | Polygon ],
  baseline: { from: Place, to: Place, profile: RoutingProfile },
  // returns: baseline_route, rerouted_route, delta_time, delta_distance
})

// 5. Profile comparison — accessibility audit lens
compare_routes({
  from: Place, to: Place,
  profiles: ["distance", "wheelchair"]
})

// 6. Show me the ADA story for this segment
inspect_segment({
  segment: EdgeRef | LatLon
  // returns: incline, surface, kerb, tactile_paving, ada_violations
})
```

Each tool resolves to deterministic Rust→WASM calls. The LLM's only job is *intent → tool selection + argument fill*.

## LLM tier — Granite-4 via the existing port

**Granite-4 (350M and 1B) was already ported to WebLLM/WebGPU in `~/granite-web` (April 2026).** That port is the substrate; Mcadam consumes it. Measured numbers on M3 MacBook Air, Chrome, IndexedDB-cached:

| Model | Quant | Decode | Prefill | Tool-call reliability |
|---|---|---|---|---|
| **Granite-4.0-1B** | q4f32_1 (WebGPU) | 20–30 tok/s | 50–60 tok/s | **5/5 on the existing tool-call harness** |
| Granite-4.0-1B GGUF | Q3_K_M (wllama / WASM) | 1–2 tok/s ST · 8 tok/s MT | — | 5/5 (Bonbibi harness) |
| Granite-4.0-350M | q4f16_1 (WebGPU) | ~80 tok/s | ~170 tok/s | **0/5 — confirmed unreliable** |

**Decision:** Granite-4-1B (q4f32_1) is Mcadam's primary tier. The 350M variant is *not* in the v1 plan despite the speed advantage — the existing harness shows it doesn't tool-call reliably on M3, and we don't ship a brittle local model just to claim "350m on edge." Honor the data.

**Fallback path:** wllama GGUF for non-WebGPU devices. Slower (~8 tok/s multi-thread) but the protocol is identical and proven on Bonbibi (the sibling Raspberry-Pi-5 humanitarian-register project).

**Patterns inherited from `~/granite-web`:**
- Granite-native `<tool_call>` XML tool-calling through WebLLM (not the chat-template hack)
- A governed FSM around tool selection (auditable state transitions, not free generation)
- Audit trail: every tool call logged with raw model output + parsed args + dispatched function — drops out as a survey-card record
- WASM (wllama) fallback is the same model in a different runtime

**Tool catalog:** the six tools below. Tight, closed vocabulary; each with ≤6 fields. Classification, not generation.

**Honest test bar before merging:** 80% pass on a 30-query NYC-pedestrian benchmark spanning all six tools, on the existing harness pattern from `~/granite-web`. The harness already exists; we extend it.

## Routing engine — why we rewrite (and not Valhalla / GraphHopper)

Pivot research verdicts (2026-05-10):

- **Unweaver** is frozen and uses 2022-era Python idioms. Patching it is dead weight; it's also keyed on coordinate-derived node IDs which fight our OSW topology unification. **AccessMap has no public modernised fork.**
- **GraphHopper 11** (released **October 2025**) is the strongest non-rewrite fit. Its `custom_models` JSON DSL exposes `average_slope`, `max_slope`, `surface`, and lets you add custom *encoded values* like `kerb_ramp` per edge. That maps cleanly onto OSW. **But** the path to using it is OSW → osmizer → OSM XML → PBF → GraphHopper, which is a four-step lossy pipeline and lands us back on a JVM server. **Document as the recommended server-side option for users who want one. Not Mcadam's primary.**
- **Valhalla 3.7.0** (April 2026, with a live GSoC-2026 pedestrian-routing track suggesting future fit) is the runner-up. Same OSW→PBF caveats. C++ server. Same not-our-primary call.
- **OSRM** is too coarse for accessibility costing. Out.
- **Pure Rust → WASM** is the unique edge-compute play. Pivot research confirms **no public production-grade in-browser pedestrian router** exists at 460k-edge scale today. We're not duplicating an existing artifact; we're occupying a vacant ecological niche. Build size estimate: ~100-200 KB compiled (Rust+CSR+bidirectional Dijkstra → wasm-bindgen). Full OSW awareness, full control, the browser-only pitch.

The cost-profile JSON should mirror Unweaver's profile-*.json shape so Mcadam profiles are interoperable with any Unweaver consumer that comes along later. Wheelchair weights should match published AccessMap research (Bolten, Caspi, Hosseini) where defensible.

**Server-side fallback:** ship a `docker-compose.yml` recipe in the repo that stands up GraphHopper 11 with a Mcadam-shaped custom_model targeting `kerb_ramp`, `average_slope`, `surface`. Documented but not operated by us. Users who want server-grade routing on the OSW dataset have a one-command path.

## Tools/router contract

The router exposes a single WASM entry point per tool. Each function takes a typed JSON struct (matching the LLM tool schema), runs the underlying Dijkstra/A*/isochrone/comparison logic, and returns a JSON result with:

- `geometry`: GeoJSON LineString/Polygon for the map
- `metrics`: total length, time, edge count, ADA-violation count, max incline encountered
- `narrative`: a structured description (turn-by-turn cues + materiality notes — "concrete sidewalk, lowered curb, tactile paving present")

The narrative is *generated by the router*, not by the LLM. The LLM's only job is dispatch. The narrative comes from the data.

## Repo layout (proposed)

```
mcadam-nyc/
├── README.md
├── ARCHITECTURE.md            ← this file
├── DESIGN_BRIEF.md            ← brand + design Claude prompt (sibling)
├── app/                       SvelteKit frontend (port from ariadne, restyle)
│   ├── src/
│   │   ├── lib/
│   │   │   ├── components/   IBM Plex + graphite tokens
│   │   │   ├── adapters/     LLM tool-call layer
│   │   │   └── stores/
│   │   └── routes/
│   └── static/
├── router/                    Rust → WASM pedestrian router
│   ├── src/
│   │   ├── graph/            CSR graph from OSW
│   │   ├── profile/          cost-profile JSON loader
│   │   ├── shortest_path/    bidirectional Dijkstra
│   │   ├── reachable/        isochrone
│   │   └── lib.rs            wasm-bindgen exports
│   └── Cargo.toml
├── tools/                     LLM tool schemas (single source of truth)
│   ├── plan_route.json
│   ├── find_reachable.json
│   ├── ...
│   └── schemas.test.ts        contract tests vs router
├── data/                      gitignored — IndexedDB-cached at runtime
├── pipeline/                  small build scripts (PMTiles, POI index)
├── scripts/                   dev tooling
├── docs/
│   ├── BRAND.md
│   ├── DESIGN_LANGUAGE.md
│   └── adr/                   architecture decisions log
└── pyproject.toml
```

## Out of scope for v1

- Multi-modal (subway/bus integration) — defer to v1.1
- User accounts, saved trips, history sync — antithetical to the privacy story
- Multi-city (only NYC). The pipeline can scale to other OSW-conformant cities, but Mcadam-the-product is NYC-pinned.
- Server-rendered routes, telemetry, A/B testing — none of it.

## Open questions (resolve in pivot research, then ADR)

1. **WebLLM Granite-4-350m availability:** is the 350m variant in the prebuilt MLC model registry? If not, what's the compile path?
2. **Constrained decoding latency:** does grammar-constrained generation slow Granite-4-350m enough to matter on M-series?
3. **PMTiles size budget:** how large is the styled basemap for NYC? Do we ship raster PMTiles or vector?
4. **Routing-profile cost weights:** start from AccessMap's published Bolten weights or derive from the OSW data + DOT slope distributions?
5. **Service-worker offline strategy:** opportunistic vs strict? (Strict aligns with the privacy pitch.)

## Phasing

- **Phase 1 — substrate (this week).** Stand up `mcadam-nyc/router/` (Rust→WASM). Pull `opensidewalks-nyc` v0.3.0-nyc.1 release as a build dep. Implement plan_route + find_reachable on the giant component. CLI test harness only, no UI.
- **Phase 2 — LLM tier.** Wire Granite-4-350m via WebLLM with constrained JSON decoding. Six-tool catalog. Bench against a 30-query NYC-pedestrian benchmark. Decision gate: does 350m hit 80%? If not, drop to 1B.
- **Phase 3 — UI.** Port Ariadne shell, replace tokens with Mcadam design (see `DESIGN_BRIEF.md`). Wire the router's narrative output into the active-record panel.
- **Phase 4 — privacy hardening.** Service worker, IndexedDB cache, offline indicator. Confirm zero network calls post-boot.
- **Phase 5 — release.** Public Hugging Face Space, README, demo gif. Announce alongside `opensidewalks-nyc`.

## License

Apache-2.0 for code. Data consumed (opensidewalks-nyc) is ODbL-1.0; no derived database is shipped from Mcadam.
