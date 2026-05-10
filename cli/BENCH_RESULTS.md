# CLI-translation benchmark — Granite via Ollama

> *Date: 2026-05-10. M3 MacBook Air, Ollama 0.21.0.*
> *Bench file: `cli/bench_100.jsonl` (105 queries, all 5 CLI verbs).*

## Hypothesis

Small language models can't reliably emit JSON tool-calls (Granite-4-350m
scores 0/5 on the existing in-browser MTA harness), but they can emit
*short, well-grammared CLI command strings.* The CLI surface is tight,
mechanical, and learnable from a handful of few-shot examples in the
system prompt.

## Headline result

| Model | Verb match | p50 latency | p95 latency | Wall (105 q) |
|---|---|---|---|---|
| `granite4:350m` | **77%** (81/105) | 247 ms | 327 ms | 26 s |
| `granite4:1b`   | **100%** (105/105) | 863 ms | 1206 ms | 94 s |

The hypothesis lands. **1B is production-ready** on the CLI-translation
task — perfect verb selection across all five verbs, sub-second latency.
350m is faster but plateaus at 77% under prompt engineering alone.

## Per-verb breakdown (operational prompt v5)

| Verb | 350m | 1B |
|---|---|---|
| `route`     | 100% (38/38) | 100% (38/38) |
| `inspect`   | 100% (15/15) | 100% (15/15) |
| `compare`   | 53% (8/15)   | 100% (15/15) |
| `reachable` | 48% (10/21)  | 100% (21/21) |
| `closure`   | 62% (10/16)  | 100% (16/16) |

350m is solved on `route` and `inspect` — saturated, sub-250 ms. The
remaining failures are all on the three "structured" verbs.

350m confusion (operational prompt):

| Expected | Got | Count |
|---|---|---|
| reachable | route | 11 |
| compare   | route | 7 |
| closure   | route | 5 |
| closure   | compare | 1 |

## Prompt iteration log (350m)

| v | Examples | route | compare | reachable | closure | inspect | overall |
|---|---|---|---|---|---|---|---|
| v1 (small bench, 25q) | 1 each | 100% | 75% | 50% | 50% | 100% | **80%** |
| v1 (big bench, 105q) | 1 each | 100% | 73% | 29% | 19% | 100% | **70%** |
| v2 | 3 each | 100% | 60% | 48% | 44% | 100% | **75%** |
| v3 (rules-first) | 1 each + rules | 100% | 60% | 14% | 31% | 93% | 66% |
| v4 (1 compare, 3 r/c) | mixed | 100% | 33% | 43% | 56% | 93% | 71% |
| **v5 (operational)** | balanced | **100%** | 53% | 48% | 62% | **100%** | **77%** |
| v6 (more reachable) | 5 reachable | 97% | 60% | 43% | 62% | 93% | 75% |

Lessons:

1. **Small bench (25q) overstates by ~10 points.** Use 105q for ranking.
2. **More examples ≠ better.** v6 had more reachable examples but
   regressed everywhere else. 350m has a finite attention budget; extra
   examples in one verb steal from others.
3. **Rules don't help (v3).** The model pattern-matches; abstract
   decision rules consume tokens without giving exemplars to imitate.
4. **Diversity > count for `compare`.** v5 added compare examples with
   varied signal verbs ("vs", "differ", "side by side", "how much
   longer") and recovered most of the v4 regression.
5. **`reachable→route` is the most stubborn confusion.** 11 cases. The
   structural pattern "X minutes from Y" looks like route to the model
   despite multiple counter-examples. May need fine-tuning to clear.

## Architecture decision the bench supports

- **Default tier: Granite-4-1B.** 100% on the bench, sub-second
  latency. Ship as the primary local-LLM tier in Mcadam.
- **Optional fast mode: Granite-4-350m for `route` + `inspect` only.**
  53/53 = 100% on those two verbs (likely ~60–70% of real query volume),
  at 247 ms p50. For all other verb-flavored queries, fall through to 1B.
- **No JSON Schema decoding needed.** The CLI grammar is the schema.

## Reproducibility

```bash
ollama serve &
ollama pull granite4:350m granite4:1b

# Smoke-test the router itself first
mcadam smoke

# Run the benches
python -m cli.llm_cli --bench cli/bench_100.jsonl --model granite4:350m
python -m cli.llm_cli --bench cli/bench_100.jsonl --model granite4:1b
```
