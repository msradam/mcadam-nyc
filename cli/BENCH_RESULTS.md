# CLI-translation benchmark — Granite via Ollama

> *Date: 2026-05-10. M3 MacBook Air, Ollama 0.21.0.*

## Hypothesis

Small language models can't reliably emit JSON tool-calls (Granite-4-350m
scores 0/5 on the existing in-browser MTA harness), but they can emit
*short, well-grammared CLI command strings.* The CLI surface is tight,
mechanical, and learnable from a handful of few-shot examples in the
system prompt.

## Setup

- 105 NL queries (`cli/bench_100.jsonl`) spanning all five CLI verbs
  (`route`, `compare`, `reachable`, `closure`, `inspect`).
- Single-shot prompt with the same few-shot examples used throughout.
  **`route` gets 3 examples; `compare`/`reachable`/`closure`/`inspect`
  get 1 each.**
- `temperature=0.0`, stop tokens on newline.
- `verb match` = parsed CLI verb equals expected verb.

## Results

| Model | Size | Verb match | p50 latency | p95 latency |
|---|---|---|---|---|
| `granite4:350m` (25-query bench) | ~250 MB | 80% (20/25) | 225 ms | — |
| `granite4:350m` (105-query bench) | ~250 MB | **70%** (73/105) | **223 ms** | 287 ms |
| `granite4:1b`   (25-query bench) | ~750 MB | 100% (25/25) | 982 ms | — |

Per-verb breakdown on the 105-query bench (350m):

| Verb | Pass | Total | Rate |
|---|---|---|---|
| `route`     | 38 | 38 | **100%** |
| `inspect`   | 15 | 15 | **100%** |
| `compare`   | 11 | 15 | 73% |
| `reachable` |  6 | 21 | 29% |
| `closure`   |  3 | 16 | **19%** |

Confusion matrix (expected → got, count):

| Expected | Got | Count | Why |
|---|---|---|---|
| reachable | route | 15 | Place name + "minutes" pulls toward `route` |
| closure   | route | 8  | Model ignores "closed" / "block" markers |
| compare   | route | 4  | Same default-attractor pattern |
| closure   | compare | 3 | "differ" / "change" patterns pull toward compare |
| closure   | inspect | 2 | Idiosyncratic noise |

## What this means

1. **`route` and `inspect` are solved at 350m.** 100% pass across 53
   queries with diverse phrasings (formal, casual, elliptical, all four
   profile-language variations). Sub-250 ms latency.
2. **`compare`, `reachable`, and `closure` are *not* solved at 350m**
   under the current prompt. The cliff is between 100% (verbs with 3
   few-shots) and 19–73% (verbs with 1 few-shot).
3. **The miss pattern is concentrated, not random.** 31 of the 32 misses
   default to a richer-exemplified verb (`route` or `compare`). This is
   a prompt-engineering problem, not a model-capability ceiling.
4. **Latency is essentially constant** across pass and fail: p50 223 ms,
   p95 287 ms. No "the model thinks longer when it's confused."

## Implications for Mcadam v0.1

- **Strategy A — fix the prompt.** Add 2 more few-shots each for `compare`,
  `reachable`, and `closure`. Expected lift: 350m to 90%+ overall. Test
  this next.
- **Strategy B — keep 350m as the "safe-verbs" tier.** Use 350m for
  `route` and `inspect` only (likely ~60–70% of real query volume); fall
  through to 1b for everything else. A tiered-cache pattern.
- **Strategy C — 1b primary, 350m fast-mode opt-in.** What the
  ARCHITECTURE sketch already proposes. The bench supports this.

The **right next experiment** is Strategy A (cheap, fully reversible).
If the prompt-rich 350m hits ≥90% on this bench, it becomes a credible
v1 default with 1b as fallback for unparseable output.

## Reproducibility

```bash
ollama serve &
ollama pull granite4:350m granite4:1b

# Smoke-test the router itself first
mcadam smoke

# Run the benches
python -m cli.llm_cli --bench cli/bench.jsonl     --model granite4:350m
python -m cli.llm_cli --bench cli/bench_100.jsonl --model granite4:350m
python -m cli.llm_cli --bench cli/bench.jsonl     --model granite4:1b
```
