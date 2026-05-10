# Mcadam — design brief

> *A self-contained prompt for Claude Design (or a human designer). Includes brand premise, voice register, palette + type direction, key UI moments to design, and the deliverable list. Reads top to bottom.*

---

## The product, in one sentence

**Mcadam** is a local-first, privacy-respecting, natural-language pedestrian routing assistant for New York City. The model runs on the user's GPU. The router runs in the browser. After the first asset load, nothing about the user's query, location, or destination ever leaves the device.

## What you should know about the predecessor

This is a rebrand of `ariadne-nyc`, a hackathon prototype built for NYU CUSP's Code4City (April 2026). Ariadne's design language is **excellent** — masterful, in fact — and the right way to read this brief is *"keep what made Ariadne uniquely legible; pivot the register so it fits the new name and a longer-shelf-life product."*

What Ariadne did well, and we keep:

- **Defeated the chatbot silhouette.** Full-width query bar at the top (not a composer at the bottom). Numbered "RECORD" log instead of conversation bubbles. Empty-state foregrounds a working document rather than asking "how can I help you?". Read [`~/ariadne-nyc/design_handoff_v3/Disambiguation Plan.md`](../ariadne-nyc/design_handoff_v3/Disambiguation%20Plan.md) — the full reasoning is there. **All of this carries forward.**
- **Document-grade typography.** Roman numeral route headings (`I. WALK`, `II. TRANSFER`, `III. WALK`), dot-leader connections in distance tables, monospace timestamps, small-caps section labels.
- **Two-rail framing.** Header rail with date + version + active record, footer rail with system status, content slab between. Not "chat + map" — *console*.
- **Tone of authority.** Ariadne reads like a *Nautical Almanac*: "Surveyed Jul 25, 2026 · 14:14 EDT". The data is presented; the user consults the record. No cheery marketing voice.
- **Vertical title spine on slides.** "ARIADNE · NYC · FIVE-BOROUGH WAYFINDING" running floor-to-ceiling in muted nav.

What we **pivot**:

- **Register.** Ariadne reads as *civic-archival* — parchment cream, navy ink, thread-of-Theseus mythology underneath. Mcadam reads as **engineering / infrastructural** — graphite, asphalt, surveyor's notebook, Caltrans manual. Less "library reference" more "field engineer's logbook."
- **Palette.** Cream/navy → graphite/granite/cadmium-yellow. Material, geological, slightly cooler.
- **Typography.** DM Sans + DM Mono → **IBM Plex Sans + IBM Plex Mono**. Direct nod to IBM Granite (the model) and to engineering/spec-sheet provenance.
- **Mythology → materiality.** No more thread metaphor. Mcadam = the road-paving technique by John Loudon McAdam (Scottish engineer, 1820s). Aggregate. Graded. Compacted. The brand's metaphors come from *materials* — surface, kerb, tactile paving, grade — not stories.
- **From hackathon to product.** Ariadne's design supported a 5-min demo. Mcadam needs to support repeat use, demo at conferences, get screenshots in research papers, and look credible to NYC DOT.

---

## Brand premise

**Granite paves the substrate. Mcadam is the routing layer that rides on top.**

Two material things stacked: the model (Granite — the rock, IBM's LLM family) under your feet, and the path you take across it (Mcadam — the technique that lets you walk over crushed stone without sinking). The product *is* the surface you walk on. Privacy and edge-compute are the foundation; routing is the surface.

You can lean on this metaphor in the brand sheet, the empty-state copy, error messages, even the loading indicator (compaction, settling, grading). It should never be cute. It should always be load-bearing.

## Voice

**Like a USGS topographic-map legend. Like the back of a Caltrans road-design manual. Like the field notes of a civil engineer who's been doing curb-ramp surveys for thirty years.**

- Spare, declarative, precise. Numbers where numbers belong.
- Terms of art are used correctly: *kerb*, *running slope*, *tactile paving*, *cross slope*, *grade*. We don't dumb down. The interface respects that some users are accessibility researchers and city planners; novices learn by context.
- No first-person AI voice ("I found", "let me help you"). Mcadam doesn't talk; it *reports*. Outputs are presented as *records*, not *responses*.
- Timestamps always in `YYYY-MM-DD HH:MM TZ` form. Distances in metres (with feet in parens for the user-facing leg cues, US convention). Inclines as a signed percentage with two decimal places.
- Microcopy: a route is a **trace**. A failed route is **no traversable surface**, not "no path found." Closures are **interruptions**. The query log is the **work log** or **session record**. Profiles (distance / wheelchair / low-vision) are **traversal profiles**.

## Palette direction

Goal: cooler than Ariadne's parchment. Material. The pavement under a streetlight at dusk.

```
--bg          oklch(0.965 0.005 250)    /* near-white, faint cool cast — concrete in shade */
--bg-2        oklch(0.945 0.006 250)    /* lift / panel surface */
--surface     oklch(0.99  0.003 250)    /* card */
--ink         oklch(0.18  0.010 250)    /* graphite — primary text */
--ink-2       oklch(0.32  0.010 250)
--muted       oklch(0.50  0.008 250)
--subtle      oklch(0.65  0.006 250)
--rule        oklch(0.78  0.006 250)
--border      oklch(0.88  0.005 250)
--primary     oklch(0.28  0.022 250)    /* basalt — buttons, key chrome */
--primary-on  oklch(0.97  0.005 250)
--accent      oklch(0.78  0.18  85)     /* CADMIUM YELLOW — road-line, construction. Single use, high salience. */
--route       oklch(0.40  0.14  255)    /* deep slate-blue for the active route trace */
--warn        oklch(0.65  0.20  35)     /* brake-light orange-red for closures, ADA violations */
--ada-bad     oklch(0.55  0.20  25)
--ada-ok      oklch(0.62  0.16  155)    /* mild teal-green */
```

Cadmium yellow is the brand's punctuation. Used for: the active query in the work-log, the active-record header rule, an "ATTN" tag, the construction-tape pattern in loading states. **Use it sparingly.** The palette is otherwise quiet — almost monochromatic graphite — and the yellow earns its salience by being rare.

The route trace is *not* yellow. Active routes draw in `--route` (slate-blue). Closures draw in `--warn` (brake-red). Yellow is for *system attention*, not data.

## Typography

- **Sans:** IBM Plex Sans. (Loaded weights: 300 / 400 / 500 / 600 / 700.)
- **Mono:** IBM Plex Mono. (400 / 500 / 600.)
- **Optional display:** IBM Plex Sans Condensed for the title spine and rail labels — gives a tighter, more industrial feel than full-width Plex.

Why Plex: it's IBM's, ships open under SIL OFL, and ties Mcadam to Granite at the typographic level. Plex has a slightly more engineered character than DM Sans (less geometric warmth, more terminal-blueprint feel). It also ships with extensive language coverage and works in the small caps and tabular figures we need.

Type rules:

- **Tabular figures everywhere** that holds numbers (distances, slopes, timestamps). `font-feature-settings: "tnum" 1;`.
- **Small-caps for labels.** `font-variant-caps: all-small-caps;` on rail labels, section dividers, profile chips. Real Plex small caps preferred; if absent, use `letter-spacing: 0.18em; text-transform: uppercase; font-size: 0.72em;`.
- **Roman numeral route headings.** `I.`, `II.`, `III.` in 10px Plex Mono small caps preceding step groups.
- **Dot leaders** between cue text and right-aligned distance: `cue ····· 240 m`. Use the `text-decoration-style: dotted` trick or a CSS `::after` flex spacer.

## Iconography

- **Schematic, not pictographic.** A curb ramp is a 3-segment line schematic with a slope arrow. A crossing is a zebra-stripe glyph. A subway-ADA station is the wheelchair-in-square mark. Avoid soft, illustrative shapes; favor pen-plotter line work.
- **Line weights:** 1.25 px for fine schematic detail, 2 px for primary glyphs, 3 px for emphatic strokes (the cadmium-yellow attention pip).
- **A small set of "material" glyphs** as accents: aggregate dots (`∴`), a slope wedge, a kerb cross-section, a tactile-paving dot grid. Used for a single tasteful detail in the rail, never as decoration.

## Key UI moments to design

Six. Each gets a target screenshot.

### 1. **Empty state ("ROUTE NOT YET TRACED")**
The product before the first query. The map shows the five-borough silhouette with comfort-resource dots (cooling centers, ADA stations, accessible restrooms) at low opacity. The query bar runs full-width across the top. Below it, an active-record panel reads:

> *Mcadam is a working reference for accessible movement through New York. Pavement, surveyed; routes, traced.*
>
> Type a query above to consult the record.

Below that, three example queries as `→`-led footnotes. **No avatars. No "ready to help." No CTA buttons.**

The bottom rail shows: build version, OSW data version + timestamp, network indicator (`● local — no traffic`).

### 2. **Active query in flight ("TRACING")**
The user has typed a query and pressed return. The query bar is locked. A subtle compaction animation runs — three small graphite bars animating in sequence, like a vibratory plate compactor settling fresh asphalt. Loading text: `TRACING · DISTANCE PROFILE · 460,051 EDGES`.

### 3. **Active record (route returned)**
The dominant moment. The active record panel reads as a *survey card*:

```
RECORD 03 · 2026-05-10 14:17 EDT                                  [active]
─────────────────────────────────────────────────────────────────────────
PENN STATION → GRAND CENTRAL                            DISTANCE PROFILE
1.96 km · 28 segments · 24 min · max grade 0.4%

I. WALK · West 33rd Street
   ›  step out onto sidewalk           ········· concrete, 3.0 m wide
   ›  cross 8th Avenue                 ········· marked, lowered kerb
   ›  east 240 m to 7th Av             ········· lit, ada compliant

II. WALK · 7th Avenue
   ›  north 320 m, west sidewalk       ·········  no obstructions
   ...

ADA · 12 of 28 segments meet running-slope ≤5%; 23 of 28 meet cross-slope ≤2%.
SOURCE · opensidewalks-nyc 0.3.0-nyc.1 · OSW v0.3 conformant
```

The map foregrounds the route in `--route` slate-blue, with curb-ramp interfaces dotted in `--ada-ok` teal where compliant and `--ada-bad` red where they fail thresholds.

### 4. **Profile comparison ("compare distance vs wheelchair")**
A two-column record. Same origin/destination, two profiles, two routes. Tabbed micro-rail at the top. Distances and edges in tabular figures. The map renders both routes simultaneously, distance in `--route`, wheelchair in cadmium yellow (this is the one place yellow is used for data — *because it's literally announcing the difference*).

The under-table reads:

> *Wheelchair traversal adds 280 m and 5 min. The distance profile passes through 4 segments without curb ramps; wheelchair routing avoids them.*

### 5. **Closure simulation ("simulate closure of Broadway between 42nd and 47th")**
The urban-planner / civic-engineer view. Map shows a hatched red overlay on the closed segment. Two routes: the baseline in muted slate, the rerouted path in cadmium yellow + heavier line weight. A delta panel:

```
INTERRUPTION · BROADWAY · 42 ST → 47 ST
DELTA · +320 m · +4 min · +6 segments
WHEELCHAIR · NO TRAVERSABLE SURFACE
```

This screen is the case for funding the project. It's what gets shown to NYC DOT.

### 6. **Segment inspector (tap a sidewalk on the map)**
Pull-out drawer from the right. The panel reads as a single-segment survey card:

```
SEGMENT n_312002→n_294199
─────────────────────────
LENGTH      23.7 m
SUBCLASS    sidewalk (footway)
SURFACE     concrete
INCLINE     +0.16 %
KERB·u_id   lowered, tactile paving present
KERB·v_id   raised, no tactile paving         [non-compliant]
SOURCE      OSM 1020674693
SURVEYED    2026-04-24
```

Material report. No editorializing.

## Out of scope for design v1

- Splash / marketing site. Engineer first.
- Onboarding flow, tutorial overlays. The product is self-explanatory in the engineering register.
- Dark mode. Defer; the graphite-on-near-white *is* the look. Dark is later, and it should feel like reading a survey at night under a sodium lamp — not just inverted.
- Branded illustrations / mascots. None. The product's brand asset is its own UI.

## Deliverables (asking Claude Design / a designer)

In priority order:

1. **Brand sheet** — one tabloid-format page or a 1280×1600 spec card. Logo (wordmark only — Plex Mono, lowercase `mcadam`, with a single cadmium-yellow underscore as the brand mark), palette tokens, type stack, voice rules, four sample microcopy lines, the "Granite paves; Mcadam routes" elevator paragraph.
2. **Design tokens** as JSON or CSS custom-properties — palette, type, spacing scale, radii (use 0 / 2 / 4 px only — no soft pill shapes), elevation, motion durations.
3. **Six key-moment mockups** at 1280×800 (desktop) and 390×844 (mobile/iPhone 14 Pro). Listed above.
4. **Component sketches** for: query bar, work-log row, active-record card, segment inspector drawer, route map (with style tokens), bottom system rail, profile-tab micro-rail.
5. **Map style** — a MapLibre style JSON tuned to the palette. Buildings rendered in `--bg-2` with a 1-px `--rule` outline, water in a slightly cooler shade, streets in white, sidewalks deemphasized until a route renders, then sidewalks-on-route lift to `--route`.
6. **One slide-deck cover** in the new register, paralleling Ariadne's `cover.png`. Title in lowercase Plex Mono. Subtitle in small caps. Cadmium-yellow rule under it. Vertical title spine in Plex Mono Condensed. The dominant visual is a screenshot of mockup #5 (closure simulation), framed as a survey plate.

## Reference points (for vibes calibration)

- USGS 7.5-minute topographic quadrangle map legend.
- Caltrans Highway Design Manual, 2023 edition, table of contents pages.
- The MTA Blue Book (transit infrastructure inventory).
- IBM's design language documentation (the Carbon Design System reference site, specifically the data-table pages).
- SF/BART system-status panels (the ones at station entrances, not the marketing site).
- *NOT* Apple Maps. *NOT* Google Maps. *NOT* Citymapper. *NOT* Komoot. None of those have the right register.
- Echo of Ariadne's vibe in: monospace-led civic-archival rigor. *But* graphite-cool, not parchment-warm.

## Naming conventions

- Product: **Mcadam**, lowercase in code (`mcadam`), capitalized in prose.
- Pedestrian network artifact: **opensidewalks-nyc** (separate, public-good — not a Mcadam sub-brand).
- A computed route is a **trace**.
- The session log is the **work log**.
- A traversal preference is a **profile**: `distance`, `wheelchair`, `low_vision`, `child_safe`. Always lowercase in display.
- A query that returned no route reads **NO TRAVERSABLE SURFACE** (not "no path"). All caps in this exact phrase.
- Errors are **FAULTS** with a numeric code. (Plex Mono.) Example: `FAULT 14 · GRAPH NOT YET LOADED · retry in 2 s`.

## Closing note

The Ariadne design is one of the best small-app design languages I've seen written down. The Mcadam pivot is not a downgrade or a replacement — it's a *register shift*, the way you'd hand a book design from a poetry chapbook to a topographic atlas, both rigorously typeset, both serious, but for different shelves. The bones (top query bar, work log not chat, foregrounded document, two-rail framing, no chatbot affordances) are kept. The voice and material are different.

Lean into the engineer's-notebook vibe and the granite/road metaphor will carry the rest.
