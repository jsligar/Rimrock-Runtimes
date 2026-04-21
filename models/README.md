# Models on Disk

All models live under `/opt/models/` on Rimrock.

## Active / Production

| Path | Format | Size | Notes |
|---|---|---:|---|
| `gemma4-e2b-q4km-compare/sowilow/gemma-4-e2b-it-q4_k_m.gguf` | GGUF Q4_K_M | 3.18 GiB | **Primary production model** — 4.6/5 at 26.3 tok/s |
| `gemma4-e2b-ud-q4xl-fresh/mmproj-F16.gguf` | GGUF FP16 | 940 MB | **Vision encoder** for E2B multimodal |
| `nemotron3-nano-4b/` | GGUF Q4_K_M | — | Quality-first model — 5.0/5 at 14.9 tok/s |

## Gemma 4 E2B Variants

| Path | Quant | Size | Score | Tok/s | Notes |
|---|---|---:|---:|---:|---|
| `gemma4-e2b-q4km-compare/sowilow/` | Q4_K_M | 3.18 GiB | 4.6/5 | 26.3 | Best publisher build |
| `gemma4-e2b-q4km-compare/bartowski/` | Q4_K_M | 3.18 GiB | 4.4/5 | 25.8 | |
| `gemma4-e2b-q4km-compare/daniloreddy/` | Q4_K_M | 3.18 GiB | 4.4/5 | 26.4 | Q7 calibration regression |
| `gemma4-e2b-q4km-compare/lmstudio-community/` | Q4_K_M | 3.18 GiB | 4.2/5 | 26.4 | Weakest publisher build |
| `gemma4-e2b-ud-q4xl-fresh/gemma-4-E2B-it-UD-Q4_K_XL.gguf` | UD-Q4_K_XL | 3.9 GiB | — | — | Unsloth dynamic quant |
| `gemma4-e2b-uncensored/` | Q4_K_M | 3.2 GiB | — | — | |
| `gemma4-e2b-q4_0/` | Q4_0 | 3.2 GiB | — | — | |
| `gemma4-e2b-q8/` | Q8_0 | 7.0 GiB | 4.4/5 | 18 | High RAM pressure — unsafe for mixed workloads |
| `gemma4-e2b/gemma-4-E2B-it-Q4_K_M.gguf` | Q4_K_M | 3.0 GiB | — | — | Used for ORT/vLLM testing |
| `gemma4-e2b/gemma-4-E2B-it-IQ4_XS.gguf` | IQ4_XS | 2.8 GiB | 4.4/5 | 28.7 | Fast but no quality edge |

## Gemma 4 E4B

| Path | Quant | Size | Notes |
|---|---|---:|---|
| `gemma4-e4b/gemma-4-E4B-it-UD-Q4_K_XL.gguf` | UD-Q4_K_XL | ~13 GiB dir | Primary E4B file |
| `gemma4-e4b/mmproj-F16.gguf` | FP16 | 945 MB | Vision encoder for E4B |

## ONNX Models (Gemma 4 E2B q4f16)

Base path: `/opt/models/gemma4-e2b-q4f16-opt/`

| File | Description |
|---|---|
| `decoder_no_attn_bias.onnx` | Base export |
| `decoder_l1_fused.onnx` | L1 session opts baked |
| `decoder_l2_fused.onnx` | L2 transformer fusions |
| `decoder_l2_cuda_graph.onnx` | **Best** — CUDA Graph, 33.0 tok/s |
| `decoder_l2_sliced.onnx` | Split→Slice experiment (no gain) |
| `decoder_l2_fused_trt.onnx` | TRT EP attempt (dead end) |

E4B ONNX path: `/opt/models/gemma4-e4b-onnx/onnx/`

## Quant Comparison Notes

From dedicated flavor benchmark (ctx=8192):

| Quant | Score | Tok/s | Key Finding |
|---|---:|---:|---|
| Q3_K_M | 4.6/5 | 15 | Best score-per-GB; DST handling strong |
| IQ4_XS | 4.2/5 | 27 | Fast but no quality edge over Q4_K_M |
| **Q4_K_M** | **4.4/5** | **27** | **Best practical balance — daily use pick** |
| Q5_K_M | 4.4/5 | 24 | Marginal quality gain, meaningful speed cost |
| Q6_K | 4.6/5 | 20 | Best quality, too slow for interactive use |
| Q8_0 | 4.4/5 | 18 | Uses 7.1GB (93% of RAM) — unsafe for mixed loads |

Q5 strict JSON failure is a model behavior, not a quant artifact — it fails across all quants.
