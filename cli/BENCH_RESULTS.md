# CLI-translation benchmark — Granite via Ollama

> *Date: 2026-05-10. M3 MacBook Air, Ollama 0.21.0.*

## Hypothesis

Small language models can't reliably emit JSON tool-calls (Granite-4-350m
scores 0/5 on the existing in-browser MTA harness), but they can emit
*short, well-grammared CLI command strings.* The CLI surface is tight,
mechanical, and learnable from a handful of few-shot examples in the
system prompt.

## Setup

- 25 NL queries spanning all five CLI verbs (`route`, `compare`,
  `reachable`, `closure`, `inspect`).
- Single-shot prompt with five few-shot examples.
- `temperature=0.0`, stop tokens on newline.
- `verb match` = parsed CLI verb equals expected verb.
- `exec Ok` = parsed command runs end-to-end against the real OSW graph
  and returns a successful route (only checked when the route was
  expected to be feasible).

## Results

| Model | Size | Verb match | Exec Ok | Avg latency |
|---|---|---|---|---|
| `granite4:350m`  | ~250 MB | **80%** (20/25) | 68% (13/19) | **225ms** |
| `granite4:1b`    | ~750 MB | **100%** (25/25) | 89% (17/19) | 982ms |

## What this means

1. **350m IS deployable for NL→CLI translation**, contradicting the
   earlier "0/5 on tool calling" finding. CLI translation is a different
   task; the model's strengths play to it.
2. **1b is essentially perfect** at verb selection and ~89% on
   end-to-end. The two exec failures are real routing constraints
   (wheelchair-blocked sidewalks), not LLM bridge errors.
3. **Sub-second latency on edge.** 225 ms with 350m on M3 is the
   "instant" feel threshold. 1B at ~1s is still acceptable.

## Failure modes (350m)

- 4/5 verb misses were `reachable` and `closure`, both of which had
  only 1 few-shot example. Adding 2 more examples per verb is the
  obvious fix and almost certainly closes the gap.
- 1 case ("Show distance and low_vision *options*…") interpreted
  "options" as a `--profile` qualifier rather than a comparison signal.

## Implications for Mcadam

- **The CLI is the API.** The browser app can be a thin wrapper that
  calls `mcadam <verb> ...` over an in-process bridge.
- **350m is a fast tier; 1b is a quality tier.** Strategy: speculative
  pattern — 350m emits, 1b validates if the parse is ambiguous. Or
  just: ship 1b as primary, 350m if user enables "fast mode."
- **No JSON Schema decoding needed.** The CLI grammar is the schema.
  This sidesteps the entire grammar-constrained-decoding apparatus.

## Reproducibility

```bash
ollama serve &
ollama pull granite4:350m granite4:1b
mcadam smoke                         # validate router first
python -m cli.llm_cli --bench cli/bench.jsonl --model granite4:1b
python -m cli.llm_cli --bench cli/bench.jsonl --model granite4:350m
```
