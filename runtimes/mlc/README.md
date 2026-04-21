# MLC-LLM

**Status: Not competitive on this hardware**

Tested twice — April 9 (3B class models) and April 20 (1B–8B class models). The GGUF/llama-server stack outperforms MLC by 0.8–1.0 quality points at equivalent parameter counts.

## Container

```
dustynv/mlc:0.20.0-r36.4.0
```

This image is approximately 12 months old (as of 2026-04-20). The published Docker Hub tag has not been refreshed. The jetson-containers repo pins commit `f35b0fb` (labeled `# 5/1/2025`) with TVM 0.22.0.

**Known issue:** Extended vocab tokens (IDs above 262144) crash the runtime with:
```
InternalError: token_id < token_table_.size() (262207 vs. 262145)
```
This affects Gemma 3 4B and likely other models with special token vocab > 262144. Requires a newer container build to fix.

## April 9 Results — 3B Class Models

Container: `dustynv/mlc:0.20.0-r36.4.0`  
Benchmark: `text_benchmark_v2.py` (OpenAI-compatible chat endpoint)  
Server port: 8424, JIT cache: `/opt/models/mlc/jit_cache/`

| Model | MLC ID | Score | Notes |
|---|---|---:|---|
| Qwen2.5-3B-Instruct | `HF://mlc-ai/Qwen2.5-3B-Instruct-q4f16_1-MLC` | **3.8/5** | Best MLC result |
| Llama-3.2-3B-Instruct | `HF://mlc-ai/Llama-3.2-3B-Instruct-q4f16_1-MLC` | 3.6/5 | Server mode OOM; used `--mode local` |
| Gemma-2-2B-IT | `HF://mlc-ai/gemma-2-2b-it-q4f16_1-MLC` | 3.2/5 | Server mode OOM; used `--mode local` |
| TinyLlama-1.1B | `HF://mlc-ai/TinyLlama-1.1B-Chat-v1.0-q4f16_1-MLC` | 2.8/5 | Baseline |
| Phi-3.5-mini-instruct | `HF://mlc-ai/Phi-3.5-mini-instruct-q4f16_1-MLC` | OOM | Fully OOM even in `--mode local` |

Overhead note: JIT compilation adds ~5 min first-run per model; subsequent runs use disk cache.

## April 20 Results — Small Models

Container: `dustynv/mlc:0.20.0-r36.4.0`  
Benchmark styles: raw speed via `benchmark.py` + text via `mlc_text_benchmark_from_nas.py`  
Hardware state: CPU 1728 MHz, GPU ~1020 MHz, EMC 3199 MHz
Raw artifacts and exact commands: [`../../benchmarks/raw/2026-04-20-mlc-small-models/`](../../benchmarks/raw/2026-04-20-mlc-small-models/)

| Model | Quant | Decode tok/s | Text Score | Notes |
|---|---|---:|---:|---|
| SmolLM2-360M-Instruct | q4f16_ft | **169.6** | not run | Fastest; output quality too poor |
| SmolLM2-1.7B-Instruct | q4f16_ft | 69.3 | 2.0/5 | Fast, weak quality |
| Gemma 3 1B IT | q4f16_1 | 62.3 | **3.0/5** | Best result this session |
| Gemma 3 1B IT | q0f16 | 43.8 | 3.0/5 | Fits but slower, no quality gain |
| Gemma 3 4B IT | q4f16_1 | — | — | Runtime failure (tokenizer mismatch) |
| Qwen3 8B | q4f16_1 | 14.8 | 2.4/5 | Fits with tight settings; `<think>` output hurt scores |

### April 20 Thermal

Peak temps ~low 60s°C, no throttling observed. Performance limits are runtime/model behavior, not thermals.

## Comparison vs GGUF

| Model | Runtime | Score |
|---|---|---:|
| Gemma 4 E2B Q4_K_M (sowilow) | llama-server | **4.6/5** |
| Nemotron-3-Nano-4B Q4_K_M | llama-server | **5.0/5** |
| Qwen2.5-3B q4f16 | MLC-LLM | 3.8/5 |
| Llama-3.2-3B q4f16 | MLC-LLM | 3.6/5 |
| Gemma 3 1B q4f16_1 | MLC-LLM | 3.0/5 |

## Why MLC Lost

1. GGUF llama-server outperforms by ~0.8–1.0 quality points at equivalent parameter counts on this hardware
2. 3B+ models OOM in server mode; require `--mode local`
3. Container is ~12 months old — tokenizer bugs, missing model support
4. `<think>` output in Qwen3 consumed token budget and damaged benchmark scores

## Why MLC Has Potential (Future)

The `cutlass_fpA_intB_gemm` kernel in mlc-ai/relax 3rdparty (from TLC-pack/FasterTransformer lineage) uses a GEMV path (`weightOnlyBatchedGemvBs1Int4b.cu`) optimized for batch=1 decode that dispatches on `sm_ >= 80 && sm_ <= 150` — covering SM87. This is the same kernel family ORT is missing. A fresh MLC container with Gemma 4 E2B support (mlc-ai/relax PR #346 + mlc-llm PR #3485) would be the most direct path to beating llama-server throughput.

## Blockers for Future MLC Testing

- Need to rebuild container from jetson-containers repo (pinned at `f35b0fb`)
- Gemma 4 E2B not yet in published MLC model registry
- Gemma 3 4B tokenizer bug in current container
