# ORT Profile Summary — Gemma 4 E2B q4f16 decoder
**Date:** 2026-04-19  
**Model:** decoder_l2_fused.onnx (L1+L2 fusions applied)  
**Config:** CUDA EP, IO binding, TF32, FastGelu, SkipSimplifiedLayerNorm, 20 decode steps @ step=1

## EP Breakdown
| EP | ms/step | % |
|----|---------|---|
| CUDA | 31.72ms | 99.6% |
| CPU  |  0.14ms |  0.4% |

CPU ops: Concat, GreaterOrEqual, Range (attention mask subgraph) — too small to matter

## Top 20 Ops by Time
| Op | ms/step | % | us/call | count/step |
|----|---------|---|---------|------------|
| MatMulNBits | 6.31 | 19.8% | 26.1 | 242 |
| SimplifiedLayerNormalization | 4.75 | 14.9% | 22.9 | 207 |
| Split | 4.00 | 12.5% | 111.1 | 36 |
| Mul | 2.35 | 7.4% | 21.7 | 108 |
| FastGelu | 1.51 | 4.7% | 21.5 | 70 |
| Add | 1.49 | 4.7% | 21.0 | 71 |
| Transpose | 1.47 | 4.6% | 28.2 | 52 |
| FusedMatMul | 1.41 | 4.4% | 61.4 | 23 |
| Reshape | 1.36 | 4.3% | 11.0 | 123 |
| Where | 1.13 | 3.6% | 29.1 | 39 |
| RotaryEmbedding | 1.13 | 3.5% | 22.5 | 50 |
| GroupQueryAttention | 1.05 | 3.3% | 87.6 | 12 |
| MatMul | 1.01 | 3.2% | 43.9 | 23 |
| SkipSimplifiedLayerNormalization | 0.87 | 2.7% | 24.9 | 35 |
| Softmax | 0.51 | 1.6% | 22.0 | 23 |
| Squeeze | 0.36 | 1.1% | 10.3 | 35 |
| Concat (CPU) | 0.19 | 0.6% | 27.0 | 7 |
| Range | 0.12 | 0.4% | 29.8 | 4 |
| MemcpyToHost | 0.12 | 0.4% | 114.6 | 1 |
| GreaterOrEqual | 0.11 | 0.3% | 26.7 | 4 |

## Key Findings

### Bottlenecks
1. **MatMulNBits (19.8%)** — quantized weight decode, 242 calls/step at 26µs each. TRT FP16 EP is the only path to faster kernels here.
2. **SimplifiedLayerNormalization (14.9%)** — 207 unfused standalone LNs at 22.9µs. Only 35 were fused to SkipSimplifiedLN. More aggressive fusion pass needed.
3. **Split (12.5%, 111µs/call)** — disproportionately slow. 36 calls/step × 111µs = 4ms. KV/head splitting. Possible reshape+split→slice replacement.

### Already Good
- FastGelu fused (✅ 70 nodes)
- SkipSimplifiedLayerNorm fused (✅ 35 nodes)  
- 99.6% on CUDA EP — CPU fallback is negligible
- CUDA graph blocked by 11 CPU ops but they only cost 0.14ms/step — not worth rebuild just for this

### Build Additions Worth Targeting
- **TRT EP** (`--use_tensorrt`) — primary target for MatMulNBits
- Investigate Split → Slice replacement to eliminate 4ms/step
- More SkipLN coverage if possible

## Scoreboard (all levers applied so far)
| Config | P50 | inf/s |
|--------|-----|-------|
| llama-server baseline | ~35ms | 29.0 |
| L1 (session opts) | 35.4ms | 28.2 |
| L2+L4 (fusions + IO bind) | 34.1ms | 29.3 |
| L1–L4+L6 (+ cuDNN/TF32) | 34.2ms | 29.3 |
| L9 profiled per-step | 31.9ms | 31.3 |

Note: L9 profiler overhead inflates wall-clock vs actual inference. 31.9ms is profiler-adjusted.
