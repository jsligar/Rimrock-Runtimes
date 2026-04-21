# Rimrock Testing Report - 2026-04-20

## Scope

This report summarizes the model testing done on Rimrock on April 20, 2026, with emphasis on:

- runtime/backend used
- model variants tested
- raw speed and text benchmark results
- fit/stability findings
- practical recommendations

Raw evidence and exact rerun commands are preserved under:

- [`benchmarks/raw/2026-04-20-mlc-small-models/`](raw/2026-04-20-mlc-small-models/)
- [`benchmarks/raw/2026-04-20-mlc-small-models/commands.md`](raw/2026-04-20-mlc-small-models/commands.md)
- [`scripts/run_mlc_small_model_sweep.sh`](../scripts/run_mlc_small_model_sweep.sh)

## Hardware / system state used for testing

- Device: Jetson Orin Nano class system ("Rimrock")
- Power profile: custom `RIMROCK_TOKENS`
- CPU: locked to max (`1728 MHz`)
- GPU: locked to max for the active power mode (`~1020 MHz`)
- EMC: locked to `3199 MHz`
- Thermal result during monitored run: healthy, roughly low 60s C peak, no obvious throttling observed

## Runtimes tested today

### 1. MLC-LLM

This was the only runtime actually benchmarked today.

- Runtime path: `dustynv/mlc:0.20.0-r36.4.0`
- Execution mode: Docker with NVIDIA runtime
- Benchmark styles used:
  - raw speed benchmark via `benchmark.py`
  - text benchmark via local wrapper `mlc_text_benchmark_from_nas.py`
- Benchmark source for text eval: Claude NAS `text_benchmark_v2.py`

### 2. Other runtimes

Other runtimes were discussed as future options, but not benchmarked today:

- TensorRT / TensorRT-LLM
- Ollama
- llama.cpp

So the results below should be read as **MLC-on-Rimrock results**, not a general model ranking across all runtimes.

## Test matrix

| Model | Quant | Runtime | Context / Prefill | Fit | Raw decode tok/s | Text score | Notes |
|---|---|---|---|---|---:|---:|---|
| SmolLM2-360M-Instruct | q4f16_ft | MLC | 2048 / 512 | Yes | 169.6 | not run | Extremely fast, poor quality |
| SmolLM2-1.7B-Instruct | q4f16_ft | MLC | 2048 / 512 | Yes | 69.3 | 2.0/5 | Fast, weak benchmark quality |
| Gemma 3 1B IT | q4f16_1 | MLC | 2048 / default test ctx 2048 | Yes | 62.3 | 3.0/5 | Best practical result today |
| Gemma 3 1B IT | q0f16 | MLC | 2048 / 512 | Yes | 43.8 | 3.0/5 | Fits, but slower with no benchmark gain |
| Gemma 3 4B IT | q4f16_1 | MLC | attempted | Runtime failure | n/a | n/a | Tokenizer/runtime mismatch in this stack |
| Qwen3 8B | q4f16_1 | MLC | 2048 / 512 | Yes | 14.8 | 2.4/5 | Fits only with tighter settings; `<think>` output hurt results |

## Detailed results

### SmolLM2-360M-Instruct q4f16_ft

- Model: `HF://dusty-nv/SmolLM2-360M-Instruct-q4f16_ft-MLC`
- Runtime: MLC
- Raw speed:
  - decode: `169.65 tok/s`
  - peak memory: `2487 MB`
- Practical read:
  - useful for raw speed and thermal probing
  - not useful as a quality model

Artifact:

- [`raw/2026-04-20-mlc-small-models/smollm2-360m-mlc-rawspeed-ctx2048-prefill512.csv`](raw/2026-04-20-mlc-small-models/smollm2-360m-mlc-rawspeed-ctx2048-prefill512.csv)

### SmolLM2-1.7B-Instruct q4f16_ft

- Model: `HF://dusty-nv/SmolLM2-1.7B-Instruct-q4f16_ft-MLC`
- Runtime: MLC
- Raw speed:
  - decode: `69.28 tok/s`
  - peak memory: `3368 MB`
- Text benchmark:
  - average score: `2.0/5`
  - average single-turn decode: `68.9 tok/s`
- Practical read:
  - solid speed
  - benchmark quality too weak for a serious default assistant

Artifacts:

- [`raw/2026-04-20-mlc-small-models/smollm2-1.7b-mlc-rawspeed-ctx2048-prefill512.csv`](raw/2026-04-20-mlc-small-models/smollm2-1.7b-mlc-rawspeed-ctx2048-prefill512.csv)
- [`raw/2026-04-20-mlc-small-models/smollm2-1.7b-mlc-text-benchmark-v2.json`](raw/2026-04-20-mlc-small-models/smollm2-1.7b-mlc-text-benchmark-v2.json)
- [`raw/2026-04-20-mlc-small-models/smollm2-1.7b-mlc-text-benchmark-v2-rerun-temps.json`](raw/2026-04-20-mlc-small-models/smollm2-1.7b-mlc-text-benchmark-v2-rerun-temps.json)

### Gemma 3 1B IT q4f16_1

- Model: `HF://mlc-ai/gemma-3-1b-it-q4f16_1-MLC`
- Runtime: MLC
- Raw speed:
  - decode: `62.27 tok/s`
  - peak memory: `3504 MB`
- Text benchmark:
  - average score: `3.0/5`
  - average single-turn decode: `62.9 tok/s`
- Practical read:
  - best overall balance of speed, fit, and usable output from today
  - still imperfect on arithmetic, formatting, and date/context retention

Artifacts:

- [`raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv`](raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv)
- [`raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q4f16_1-mlc-text-benchmark-v2-ctx2048.json`](raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q4f16_1-mlc-text-benchmark-v2-ctx2048.json)

### Gemma 3 1B IT q0f16

- Model: `HF://mlc-ai/gemma-3-1b-it-q0f16-MLC`
- Runtime: MLC
- Raw speed:
  - decode: `43.76 tok/s`
  - peak memory: `4867 MB`
- Text benchmark:
  - average score: `3.0/5`
  - average single-turn decode: `43.9 tok/s`
- Practical read:
  - this is the largest Gemma 3 1B variant tested that still fit cleanly
  - no quality win versus q4f16_1 in this benchmark
  - worse speed and higher memory, so not the preferred 1B Gemma variant here

Artifacts:

- [`raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q0f16-mlc-rawspeed-ctx2048-prefill512.csv`](raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q0f16-mlc-rawspeed-ctx2048-prefill512.csv)
- [`raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q0f16-mlc-text-benchmark-v2-ctx2048-prefill512.json`](raw/2026-04-20-mlc-small-models/gemma-3-1b-it-q0f16-mlc-text-benchmark-v2-ctx2048-prefill512.json)

### Gemma 3 4B IT q4f16_1

- Model attempted: `HF://mlc-ai/gemma-3-4b-it-q4f16_1-MLC`
- Runtime: MLC
- Status: failed during generation/runtime use
- Practical read:
  - memory looked potentially workable
  - blocked by tokenizer/runtime mismatch in current MLC path on this device
  - not a usable result today
- Failure note: [`raw/2026-04-20-mlc-small-models/gemma-3-4b-mlc-failure-2026-04-20.md`](raw/2026-04-20-mlc-small-models/gemma-3-4b-mlc-failure-2026-04-20.md)

### Qwen3 8B q4f16_1

- Model: `HF://mlc-ai/Qwen3-8B-q4f16_1-MLC`
- Runtime: MLC
- Raw speed:
  - decode: `14.76 tok/s`
  - peak memory: about `7167 MB` process usage in the raw run
- Text benchmark:
  - average score: `2.4/5`
  - average single-turn decode: `14.8 tok/s`
- Practical read:
  - it fits only with constrained settings
  - visible `<think>` output consumed budget and damaged benchmark scores
  - likely has more reasoning/tool potential than the 1B models, but the current MLC behavior makes it a poor daily driver on this box

Artifacts:

- [`raw/2026-04-20-mlc-small-models/qwen3-8b-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv`](raw/2026-04-20-mlc-small-models/qwen3-8b-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv)
- [`raw/2026-04-20-mlc-small-models/qwen3-8b-q4f16_1-mlc-text-benchmark-v2-ctx2048-prefill512-tok96.json`](raw/2026-04-20-mlc-small-models/qwen3-8b-q4f16_1-mlc-text-benchmark-v2-ctx2048-prefill512-tok96.json)

## Thermal / stability notes

- The machine stayed thermally healthy during monitored testing.
- Peak temperatures were around the low 60s C.
- No obvious thermal throttling was seen during the monitored SmolLM2 run.
- Current performance limits appear to be driven more by:
  - model size
  - runtime efficiency
  - quant / memory behavior
  - backend-specific issues
  than by thermals.

## What we found

### Best practical model today

`Gemma 3 1B IT q4f16_1` on MLC.

Why:

- fits comfortably
- much faster than Qwen3 8B
- clearly more usable than the SmolLM2 models
- no quality advantage from moving Gemma 3 1B to q0f16

### Fastest model today

`SmolLM2-360M-Instruct q4f16_ft`

Why it is not the recommendation:

- output quality is too poor for real use

### Most ambitious model that still fit

`Qwen3-8B q4f16_1`

Why it is not the recommendation:

- only about `14.8 tok/s`
- benchmark output was polluted by internal thinking text
- current runtime path is too slow and messy for daily use

### Biggest blocker above 1B

Not just memory.

Today’s results suggest the bigger blockers are:

- runtime/backend behavior in MLC
- tokenizer/runtime incompatibilities on some model variants
- output-path behavior such as exposed thinking traces

## Recommendations

### Keep as current practical default

- `Gemma 3 1B IT q4f16_1` on MLC

### Keep for raw speed probing only

- `SmolLM2-360M-Instruct q4f16_ft`

### Keep as a larger-model experiment, not default

- `Qwen3-8B q4f16_1`

### Next worthwhile directions

1. Test a better-supported 2B to 4B model in MLC.
2. Re-test Gemma/Qwen on a different backend, especially TensorRT/TensorRT-LLM if available.
3. Build a small local tool-calling benchmark, since today’s text benchmark only partially predicts tool use.
4. If Qwen remains interesting, suppress or avoid visible `<think>` output before scoring it again.

Initial tool-discipline probe scaffold: [`scripts/tool_call_probe.py`](../scripts/tool_call_probe.py). It has not yet been run against these MLC models.

## Bottom line

For today’s actual Rimrock testing, the winning configuration was:

- runtime: `MLC-LLM`
- model: `Gemma 3 1B IT q4f16_1`

It gave the best balance of fit, speed, and usable output on this machine under the tested settings.
