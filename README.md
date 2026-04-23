# Rimrock Runtimes

Inference runtime testing, benchmark results, and production configs for **Rimrock** — a Jetson Orin Nano Super 8GB running local AI workloads.

## Hardware

| | |
|---|---|
| Device | Jetson Orin Nano Super 8GB |
| SoC | SM87 (Ampere) |
| RAM | 8GB LPDDR5 unified (7.43GB usable to CUDA) |
| Storage | 915GB NVMe |
| JetPack | 6.2.2 |
| CUDA | 12.6 |
| cuDNN | 9.3 |
| TensorRT | 10.3 |
| IP | 172.16.0.248 |
| Inference port | 8424 |

## Power / Performance State

Best results use the custom `RIMROCK_TOKENS` power profile with all clocks locked:

```bash
sudo nvpmodel -m 2
sudo jetson_clocks
echo 1 | sudo tee /sys/kernel/debug/bpmp/debug/clk/emc/state
echo 1 | sudo tee /sys/kernel/debug/bpmp/debug/clk/emc/mrq_rate_locked
echo 1 | sudo tee /sys/kernel/debug/bpmp/debug/bwmgr/bwmgr_halt
echo 3199000000 | sudo tee /sys/kernel/debug/bpmp/debug/clk/emc/rate
```

- CPU: 1728 MHz (locked)
- GPU: ~1020 MHz (locked)
- EMC: 3199 MHz (locked)

## Current Production Setup

| Role | Model | Runtime | CTX | KV Cache | Tok/s | Score |
|---|---|---|---:|---|---:|---:|
| **Primary** | Gemma 4 E2B Q4_K_M (sowilow) | llama-server build 8664 | 131072 | turbo4 | ~28 | 5.04/10 |

Text + vision capable (mmproj loaded). Context window: **131072** (model ceiling, n_ctx_train=131072) as of 2026-04-22.

Startup script: [`runtimes/llama-cpp/start_llama.sh`](runtimes/llama-cpp/start_llama.sh)

## Runtimes Evaluated

| Runtime | Status | Notes |
|---|---|---|
| [llama.cpp llama-server](runtimes/llama-cpp/) | **Production** | Build 8664, GGUF, multimodal |
| [ONNX Runtime](runtimes/onnxruntime/) | Tested — ceiling hit | 33.0 tok/s max, MatMulNBits bottleneck |
| [MLC-LLM](runtimes/mlc/) | Tested — not competitive | GGUF stack wins on this hardware |
| vLLM 0.19.0 | Dead end | embed_tokens_per_layer OOM on 8GB unified memory |

## Benchmark Summary

Full results: [`benchmarks/master-results-2026-04-08.md`](benchmarks/master-results-2026-04-08.md)

### v3 Harness (2026-04-22, 12-question suite, weighted)

| Label | CTX | KV Cache | Score | Tok/s |
|---|---:|---|---:|---:|
| llama-server-turbo4-128k | 131072 | turbo4 | **5.04/10** | 28.06 |
| llama-server-turbo4 | 32768 | turbo4 | **5.04/10** | ~28 |
| llama-server-q8 | 32768 | q8_0 | **5.04/10** | ~28 |

Score is flat across all context sizes and KV types — model ceiling on this task suite, not a hardware limit. Turbo4 KV and Q8_0 KV are effectively identical in throughput and quality at these context sizes.

### v1 Harness (legacy, 5-point scale)

| Model | Runtime | Avg Score | Tok/s |
|---|---|---:|---:|
| Nemotron-3-Nano-4B Q4_K_M | llama-server | **5.0/5** | 14.9 |
| Gemma 4 E2B Q4_K_M (sowilow) | llama-server | **4.6/5** | 26.3 |
| Gemma 4 E2B IQ4_XS | llama-server | 4.4/5 | 28.7 |
| Gemma 4 E2B Q4_K_M (bartowski) | llama-server | 4.4/5 | 25.8 |
| Gemma 4 E4B Q3_K_M | llama-server | 4.4/5 | 10.5 |
| Gemma 4 E2B (ORT CUDA Graph) | ONNX Runtime | not scored | 33.0 |
| Qwen2.5-3B q4f16 | MLC-LLM | 3.8/5 | — |
| Phi-4-mini Q4_K_M | llama-server | 3.4/5 | 12.9 |

## Repository Layout

```
runtimes/
  llama-cpp/      production runtime — configs, startup script, build notes
  onnxruntime/    ORT CUDA EP investigation — all levers, profiling, final state
  mlc/            MLC-LLM evaluation results (gemma4 e2b, nemotron-nano-4b, small models)
benchmarks/
  master-results-2026-04-08.md         consolidated legacy leaderboard
  mlc-runtime-2026-04-09.md
  ort-progress-2026-04-19.md
  ort-profile-gemma4-e2b.md
  mlc-small-models-2026-04-20.md
  mlc-gemma4-e2b-2026-04-21.md
  vision-results-2026-04-21.md
  benchmark-report-*-20260422-*.md     v3 harness runs (q8, turbo4, turbo4-128k)
  raw/2026-04-20-mlc-small-models/     raw CSV/JSON artifacts + exact commands
  raw/2026-04-21-mlc-gemma4-text/      MLC gemma4 text benchmark raw data
models/
  README.md       what's on disk at /opt/models/, paths, quant notes
scripts/
  benchmark_v3_rimrock.py              v3 benchmark harness (12-question, weighted)
  run_mlc_small_model_sweep.sh         rerun April 20 MLC sweep
  tool_call_probe.py                   lightweight OpenAI-compatible tool discipline probe
```
