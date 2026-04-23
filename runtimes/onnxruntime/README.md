# ONNX Runtime — CUDA EP

**Status: Ceiling hit — not in production**

All optimization levers exhausted. Best result: **33.0 tok/s** on Gemma 4 E2B q4f16 with CUDA Graph. Baseline llama-server runs ~26.3 tok/s on a quantized GGUF, but the ORT path uses full float16 weights (~4GB vs ~3GB).

## Build

| | |
|---|---|
| Version | ORT v1.24.4 |
| Built from | source (custom, CUDA EP + attempted TRT EP) |
| Wheel | `/opt/build/onnxruntime/build/Release/dist/` |
| Build log | `/opt/build/ort-build.log` |
| Build script | `/opt/build/build-ort.sh` |
| **Required env** | `PYTHONPATH=/opt/build/onnxruntime/build/Release` |

> pip ORT has no CUDA EP. Always use the local build via PYTHONPATH.

The `/sys/class/drm/card0` warning from `device_discovery` is a Jetson red herring — CUDA EP works correctly.

## Models on Disk

| File | Description |
|---|---|
| `decoder_no_attn_bias.onnx` | Base export, GQA attention_bias cleared |
| `decoder_l1_fused.onnx` | L1 session opts baked in |
| `decoder_l2_fused.onnx` | L2 transformer fusions applied |
| `decoder_l2_cuda_graph.onnx` | **BEST E2B** — CUDA Graph, 33.0 tok/s |
| `decoder_l2_sliced.onnx` | Split→Slice experiment (no gain) |
| `decoder_l2_fused_trt.onnx` | TRT EP patch attempt (dead end) |

Base path: `/opt/models/gemma4-e2b-q4f16-opt/`

E4B best: `/opt/models/gemma4-e4b-onnx/onnx/decoder_cuda_graph.onnx` — 18.82 tok/s

## Benchmark Scoreboard — E2B Final

| Config | P50 | inf/s | Notes |
|---|---:|---:|---|
| llama-server baseline | ~35ms | 29.0 | Q4_K_M via llama.cpp |
| L1 session opts only | 35.4ms | 28.2 | |
| L2 fusions + L4 IO binding | 34.1ms | 29.3 | |
| L1–L4 + L6 (cuDNN/TF32) | 34.2ms | 29.3 | |
| **L5 CUDA Graph** | **30.3ms** | **33.0** | **+13.8% vs llama.cpp** |

## Optimization Levers Applied (E2B)

| Level | Lever | Result |
|---|---|---|
| L1 | `graph_optimization_level=ORT_ENABLE_ALL` | Done |
| L1 | `execution_mode=ORT_SEQUENTIAL` | Done |
| L1 | `enable_cpu_mem_arena=False` | Done |
| L1 | `enable_mem_pattern=False` | Done |
| L2 | SkipSimplifiedLayerNorm Fusion | 35 fused |
| L2 | FastGelu Approximation | 70 fused |
| L2 | Attention Fusion | **Blocked** — variable head dims (256/512) |
| L2 | `optimizer.optimize_model()` offline | Done |
| L3 | KV Buffer Sharing | Done — minimal gain on unified memory |
| L4 | IO Binding + `run_with_iobinding()` | Done — 82% faster than CPU path |
| L5 | CUDA Graph | Done — 32 CPU nodes removed, constants baked |
| L6 | `use_tf32=True` | Done |
| L6 | `arena_extend_strategy=kNextPowerOfTwo` | Done |
| L6 | `cudnn_conv_algo_search=EXHAUSTIVE` | Done |
| L7 | TRT FP16 EP | **Dead end** — 0% TRT coverage (see below) |
| L8 | `convert_float_to_float16` | Done — 0 fp32 intermediates |
| L9 | Profiling | Done |

## CUDA Graph — Constants Baked (E2B)

32 CPU-fallback nodes removed. 7 decode-mode constants baked:

- `attn_mask_reformat/Expand/Cast/output_0` → INT32 `[[1]]`
- `attn_mask_reformat/Gather/Cast/output_0` → INT32 `2`
- `num_logits_to_keep/Unsqueeze/output_0` → INT64 `[-1]`
- 4× `t_dim/output_0` → INT64 `2`

## TRT EP — Confirmed Dead End

ORT 1.24.4 TRT EP installed and verified. **Result: 0% TRT kernel coverage on either model.**

All compute-heavy ops are ORT contrib ops with no TRT plugins:

| Op | % of compute | TRT coverage |
|---|---:|---|
| MatMulNBits | 19.8% | None — 4-bit custom op |
| SimplifiedLayerNormalization | 14.9% | None — fused ORT op |
| Split | 12.5% | Generic only |
| GroupQueryAttention | 3.3% | None — ORT contrib |
| FastGelu | 4.7% | None — fused ORT op |
| RotaryEmbedding | 3.5% | None — ORT contrib |

TRT EP can only run generic ONNX ops (Add, Mul, Transpose) which represent <1% of compute. **Do not attempt TRT EP again on these models.**

## Profiling Summary (L9)

- **99.6% CUDA, 0.4% CPU** — CPU fallback negligible
- **MatMulNBits: 6.31ms/step (19.8%)** — 242 calls/step at 26µs each. Hard ceiling with this ORT version.
- SimplifiedLayerNorm: 4.75ms/step (14.9%) — 207 unfused standalone LNs
- Split: 4.0ms/step (12.5%) — 36 calls × 111µs. Split→Slice replacement attempted, no gain.
- FusedMatMul+MatMul: 2.42ms/step (7.6%)
- GroupQueryAttention: 1.05ms/step (3.3%)

## Why 33.0 tok/s is the Hard Ceiling

MatMulNBits (4-bit quantized weight dequant) is the dominant op at 19.8% of compute. The original assumption was that ORT v1.24.4 simply predated the newer fpA/intB GEMM path, but the Rimrock checkout already contains those kernels and honors `ORT_FPA_INTB_GEMM=1`.

The actual blocker is the Gemma 4 E2B ONNX export format: all 242 `MatMulNBits` nodes use `bits=4` with `block_size=32`. ORT's fpA/intB fast path only enables for block sizes 64 or 128, so the optimized int4 GEMM kernels are ineligible for this model even though the runtime code is present.

`ORT_FPA_INTB_GEMM=1` was rechecked on Rimrock:

- on `decoder_l2_fused.onnx`, it breaks full CUDA graph partitioning
- on `decoder_l2_cuda_graph.onnx`, it still benchmarks at ~30.33ms / 32.97 inf/s, effectively identical to the 33.0 tok/s baseline

The next viable ORT path is not a simple rebuild. It requires a Gemma 4 export or quantization format that produces `MatMulNBits` nodes with a supported block size for fpA/intB GEMM, or a different runtime whose int4 kernels support block size 32.

## Misc Notes

- 8GB swapfile at `/swapfile` active during testing
- Ollama was inactive during ORT testing — no GPU memory contention
- E4B offline `optimizer.optimize_model()` failed with OOM (2.7GB model exceeds ~6GB Jetson budget)
