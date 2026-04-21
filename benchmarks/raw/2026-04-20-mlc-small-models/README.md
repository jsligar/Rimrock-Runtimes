# Raw Artifacts - MLC Small Model Sweep - 2026-04-20

These files are the raw benchmark outputs behind `benchmarks/mlc-small-models-2026-04-20.md`.

## Files

| File | Description |
|---|---|
| `smollm2-360m-mlc-rawspeed-ctx2048-prefill512.csv` | Raw speed for SmolLM2 360M |
| `smollm2-1.7b-mlc-rawspeed-ctx2048-prefill512.csv` | Raw speed for SmolLM2 1.7B |
| `smollm2-1.7b-mlc-text-benchmark-v2.json` | Text benchmark for SmolLM2 1.7B |
| `smollm2-1.7b-mlc-text-benchmark-v2-rerun-temps.json` | Re-run used during temperature observation |
| `gemma-3-1b-it-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv` | Raw speed for Gemma 3 1B q4f16_1 |
| `gemma-3-1b-it-q4f16_1-mlc-text-benchmark-v2-ctx2048.json` | Text benchmark for Gemma 3 1B q4f16_1 |
| `gemma-3-1b-it-q0f16-mlc-rawspeed-ctx2048-prefill512.csv` | Raw speed for Gemma 3 1B q0f16 |
| `gemma-3-1b-it-q0f16-mlc-text-benchmark-v2-ctx2048-prefill512.json` | Text benchmark for Gemma 3 1B q0f16 |
| `qwen3-8b-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv` | Raw speed for Qwen3 8B q4f16_1 |
| `qwen3-8b-q4f16_1-mlc-text-benchmark-v2-ctx2048-prefill512-tok96.json` | Text benchmark for Qwen3 8B q4f16_1 |

## Notes

- These artifacts are local MLC results from Rimrock, not cross-runtime rankings.
- The Qwen3 8B text run used `max_tokens=96`; visible `<think>` output consumed most of the answer budget.
- Gemma 3 4B did not produce a successful raw artifact because it failed at runtime; see `gemma-3-4b-mlc-failure-2026-04-20.md`.
