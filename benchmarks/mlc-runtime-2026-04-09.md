# MLC LLM Runtime Benchmark — Rimrock Jetson AGX Orin
**Date:** 2026-04-09  
**Host:** jsligar@172.16.0.248 (Rimrock)  
**Hardware:** Jetson AGX Orin-class, 7.4GB unified RAM, aarch64, L4T R36.5.0, CUDA 12.6, sm_87  
**Runtime:** MLC LLM v0.20.0 via dustynv/mlc:0.20.0-r36.4.0  
**Benchmark:** text_benchmark_v2.py (OpenAI-compatible chat endpoint)  
**MLC server port:** 8424 (local mode, JIT cache at /opt/models/mlc/jit_cache/)

---

## Model Results

| Model | MLC ID | Params | Score | Notes |
|-------|--------|--------|-------|-------|
| Qwen2.5-3B-Instruct | HF://mlc-ai/Qwen2.5-3B-Instruct-q4f16_1-MLC | 3B | **3.8/5** | Best MLC result |
| Llama-3.2-3B-Instruct | HF://mlc-ai/Llama-3.2-3B-Instruct-q4f16_1-MLC | 3B | 3.6/5 | Server mode OOM; ran --mode local |
| Gemma-2-2B-IT | HF://mlc-ai/gemma-2-2b-it-q4f16_1-MLC | 2B | 3.2/5 | Server mode OOM; ran --mode local |
| TinyLlama-1.1B | HF://mlc-ai/TinyLlama-1.1B-Chat-v1.0-q4f16_1-MLC | 1.1B | 2.8/5 | Baseline |
| Phi-3.5-mini-instruct | HF://mlc-ai/Phi-3.5-mini-instruct-q4f16_1-MLC | 3.8B | OOM | OOM even in --mode local; skipped |

---

## Key Findings

- **MLC best:** Qwen2.5-3B at 3.8/5 — competitive but does not beat existing GGUF leaders
- **MLC overhead:** JIT compilation adds ~5 min first-run per model; subsequent runs use disk cache
- **Memory pressure:** 3B+ models in server mode OOM on 7.4GB; `--mode local` required for 3B models
- **4B class models (Phi-3.5-mini):** Fully OOM even in local mode — not viable on this hardware with MLC

---

## Comparison vs GGUF (from MODEL_BENCHMARKS_MASTER_2026-04-08.md)

| Model | Runtime | Score |
|-------|---------|-------|
| Gemma 4 E2B (sowilow Q4_K_M) | llama-server (GGUF) | **4.6/5** |
| Nemotron3-Nano-4B Q4_K_M | llama-server (GGUF) | **5.0/5** |
| Qwen2.5-3B MLC q4f16 | MLC LLM | 3.8/5 |
| Llama-3.2-3B MLC q4f16 | MLC LLM | 3.6/5 |
| Gemma-2-2B MLC q4f16 | MLC LLM | 3.2/5 |
| TinyLlama-1.1B MLC q4f16 | MLC LLM | 2.8/5 |

---

## Verdict

MLC LLM runtime is **not competitive** with llama-server GGUF on this hardware. The GGUF stack outperforms by ~0.8–1.0 points at equivalent parameter counts. Gemma 4 E2B sowilow (GGUF, llama-server build 8664) remains the production default.

**Note:** `dustynv/llama_cpp:r36.4.0` (build 4579, Jan 2025) does NOT support Gemma 4 or Nemotron-H architectures — use the locally built `/opt/llama.cpp/build/bin/llama-server` (build 8664) instead.

---

## Production Config (Restored)

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /opt/models/gemma4-e2b-q4km-compare/sowilow/gemma-4-e2b-it-q4_k_m.gguf \
  -ngl 99 -c 8192 -t 6 -tb 6 --threads-http 1 -np 1 --no-cont-batching \
  -b 1024 -ub 1024 --flash-attn on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --prio 2 --prio-batch 2 \
  --host 0.0.0.0 --port 8424
```

Startup script: `/tmp/start_llama.sh` on Rimrock  
Log: `/tmp/llama-server.log`
