# ORT Inference Session Progress — 2026-04-19 / 2026-04-20
**Device:** Rimrock (Jetson Orin Nano Super 8GB, SM87, JetPack 6.2.2)  
**ORT Build:** v1.24.4, custom from source, CUDA EP + TRT EP (TRT EP confirmed dead end — see below)

---

## E2B Model: Gemma 4 E2B q4f16

### Files on Rimrock (E2B)
| File | Purpose |
|------|---------|
| `/opt/models/gemma4-e2b-q4f16-opt/decoder_no_attn_bias.onnx` | Original export — base model |
| `/opt/models/gemma4-e2b-q4f16-opt/decoder_l1_fused.onnx` | L1 session opts baked in |
| `/opt/models/gemma4-e2b-q4f16-opt/decoder_l2_fused.onnx` | L2 transformer fusions applied |
| `/opt/models/gemma4-e2b-q4f16-opt/decoder_l2_fused_trt.onnx` | TRT EP patch attempt (dead end) |
| `/opt/models/gemma4-e2b-q4f16-opt/decoder_l2_cuda_graph.onnx` | **BEST E2B** — CUDA Graph model |
| `/opt/models/gemma4-e2b-q4f16-opt/decoder_l2_sliced.onnx` | Split→Slice experiment (no gain) |
| `/opt/models/bench_level1.py` | L1 session opts benchmark |
| `/opt/models/bench_level3.py` | L3 KV buffer sharing benchmark |
| `/opt/models/bench_level4.py` | L4 IO binding benchmark |
| `/opt/models/bench_level5.py` | L5 CUDA graph benchmark |
| `/opt/models/bench_level9_profile.py` | L9 profiling script |
| `/opt/models/patch_split_to_slice.py` | Graph patch tool (Split→Slice, no gain) |
| `/opt/models/patch_gqa_attention_bias.py` | Clears GQA slot 9 (E2B) or slot 10 (E4B) |

### E2B Active Model: decoder_l2_cuda_graph.onnx
- All L1–L6 session options applied
- 35 SkipSimplifiedLayerNorm fusions, 70 FastGelu fusions, 70 Reshape removals
- float16 applied: 0 fp32 intermediate tensors
- 21 CPU-fallback shape nodes removed, 7 decode-mode constants baked:
  - attn_mask_reformat/Expand/Cast/output_0 → INT32 [[1]]
  - attn_mask_reformat/Gather/Cast/output_0 → INT32 2
  - num_logits_to_keep/Unsqueeze/output_0 → INT64 [-1]
  - 4x t_dim/output_0 → INT64 2

### E2B Lever Status

| Level | Lever | Status | Result |
|-------|-------|--------|--------|
| L1 | graph_optimization_level=ORT_ENABLE_ALL | Done | — |
| L1 | execution_mode=ORT_SEQUENTIAL | Done | — |
| L1 | enable_cpu_mem_arena=False | Done | — |
| L1 | enable_mem_pattern=False | Done | — |
| L2 | SkipSimplifiedLayerNorm Fusion | Done | 35 fused |
| L2 | FastGelu Approximation | Done | 70 fused |
| L2 | Attention Fusion | Blocked | Variable head dims (256/512) |
| L2 | EmbedLayerNorm | No match | Gemma 4 PLE differs |
| L2 | optimizer.optimize_model() offline | Done | decoder_l2_fused.onnx |
| L3 | KV Buffer Sharing | Done | 15 KV layers, minimal gain on unified mem |
| L4 | IO Binding + run_with_iobinding() | Done | 82% faster than CPU path |
| L5 | CUDA Graph | Done | 32 CPU nodes removed, constants baked |
| L6 | use_tf32=True | Done | In all sessions |
| L6 | arena_extend_strategy=kNextPowerOfTwo | Done | In all sessions |
| L6 | cudnn_conv_algo_search=EXHAUSTIVE | Done | In bench scripts |
| L6 | cudnn_conv_use_max_workspace=True | Done | In bench scripts |
| L6 | do_copy_in_default_stream=True | Done | In bench scripts |
| L7 | TRT FP16 EP | Dead end | All ops are ORT contrib ops — no TRT plugins |
| L8 | convert_float_to_float16 | Done | 0 fp32 intermediates |
| L9 | Profiling | Done | Results below |

### E2B Benchmark Scoreboard — FINAL

| Config | P50 | inf/s | Notes |
|--------|-----|-------|-------|
| llama-server baseline | ~35ms | 29.0 | Q4_K_M via llama.cpp |
| L1 only | 35.4ms | 28.2 | Session opts, no IO binding |
| L2+L4 | 34.1ms | 29.3 | Fusions + IO binding |
| L1-L4+L6 | 34.2ms | 29.3 | All levers pre-CUDA-graph |
| L5 CUDA Graph | 30.3ms | 33.0 | BEST — +13.8% vs llama.cpp |
| L9 profiler | 31.9ms | 31.3 | Profiler overhead included |

### E2B Profiling Findings (L9)
- 99.6% CUDA, 0.4% CPU — CPU fallback negligible
- MatMulNBits: 6.31ms/step (19.8%) — TRT EP cannot touch (custom op)
- SimplifiedLayerNorm: 4.75ms/step (14.9%)
- FusedMatMul+MatMul: 2.42ms/step (7.6%)
- GroupQueryAttention: 1.05ms/step (3.3%)
- FastGelu: 1.51ms/step (4.7%) — already fused

---

## E4B Model: Gemma 4 E4B q4f16

### Files on Rimrock (E4B)
| File | Purpose |
|------|---------|
| `/opt/models/gemma4-e4b-onnx/onnx/decoder_model_merged_q4f16.onnx` | Original export |
| `/opt/models/gemma4-e4b-onnx/onnx/embed_tokens_q4f16.onnx` | Embedding model (input_ids → inputs_embeds + per_layer_inputs) |
| `/opt/models/gemma4-e4b-onnx/onnx/decoder_no_attn_bias.onnx` | GQA slot 10 cleared (attention_bias removed) |
| `/opt/models/gemma4-e4b-onnx/onnx/decoder_cuda_graph.onnx` | BEST E4B — CUDA Graph model |
| `/opt/models/patch_gqa_attention_bias.py` | Clears GQA attention_bias slot |
| `/opt/models/patch_e4b_cuda_graph.py` | Bakes 32 CPU nodes as constants for CUDA graph |
| `/opt/models/bench_e4b_cuda_graph.py` | E4B CUDA graph benchmark |

### E4B Architecture
- 1615 nodes (1583 after CUDA graph patch)
- 24 KV pairs; global attention layers {5, 11, 17, 23} (KV dim 512); others (KV dim 256)
- Inputs: inputs_embeds[b,s,2560], attention_mask[b,total_seq], position_ids[b,s],
  num_logits_to_keep[], per_layer_inputs[b,s,42,256], 24x KV pairs
- Takes inputs_embeds (not input_ids) — requires embed_tokens_q4f16.onnx as prefix

### E4B CUDA Graph Patch
32 CPU-fallback nodes removed, 8 decode-mode constants baked (batch=1, seq=1, total_seq=2):
- attn_mask_reformat/Expand/Cast/output_0 → INT32 [[1]]
- attn_mask_reformat/Gather/Cast/output_0 → INT32 2
- num_logits_to_keep/Unsqueeze/output_0 → INT64 [-1]
- layers.{5,11,17,23}/t_dim/output_0 → INT64 2
- shared_donor.22/mask/t_dim/output_0 → INT64 2
- Dead gqa_attention_bias subgraph (8 nodes) removed

### E4B Lever Status

| Level | Lever | Status | Result |
|-------|-------|--------|--------|
| L1 | graph_optimization_level=ORT_ENABLE_ALL | Done | Session-level |
| L1 | execution_mode=ORT_SEQUENTIAL | Done | — |
| L1 | enable_cpu_mem_arena=False | Done | — |
| L1 | enable_mem_pattern=False | Done | — |
| L2 | optimizer.optimize_model() offline | OOM | 2.7GB model exceeds ~6GB Jetson budget |
| L4 | IO Binding + run_with_iobinding() | Done | Baseline 58.7ms |
| L5 | CUDA Graph | Done | 32 CPU nodes removed, constants baked |
| L6 | use_tf32=True | Done | In session |
| L6 | arena_extend_strategy=kNextPowerOfTwo | Done | In session |

### E4B Benchmark Scoreboard — FINAL

| Config | P50 | inf/s | Notes |
|--------|-----|-------|-------|
| L4 IO binding (baseline) | 58.7ms | 17.05 | decoder_no_attn_bias.onnx |
| L5 CUDA Graph | 53.1ms | 18.82 | BEST — -9.5% vs L4 |

---

## TRT EP — Confirmed Dead End

ORT 1.24.4 TRT EP installed and verified. Result: 0% TRT coverage on either model.

All compute-heavy ops are ORT contrib ops with no TRT plugins:
- MatMulNBits — 4-bit quantized matmul, no TRT kernel
- GroupQueryAttention — ORT contrib GQA, no TRT plugin
- SkipSimplifiedLayerNormalization — fused ORT op, no TRT plugin
- FastGelu — fused ORT op, no TRT plugin
- RotaryEmbedding — ORT contrib, no TRT plugin

TRT EP can only run generic ONNX ops (Add, Mul, Transpose, etc.) which represent <1% of compute.
Do not attempt TRT EP again on these models.

---

## Key Runtime Notes
- PYTHONPATH=/opt/build/onnxruntime/build/Release required — pip ORT has no CUDA EP
- device_discovery warning about /sys/class/drm/card0 is Jetson red herring — CUDA EP works
- decoder_optimized.onnx (old, E2B) is broken — GQA+attention_bias incompatible
- Ollama: inactive. memory-mcp Docker: running (CPU only, no GPU impact)
- 8GB swapfile at /swapfile: active
- ORT build log: /opt/build/ort-build.log; build script: /opt/build/build-ort.sh
