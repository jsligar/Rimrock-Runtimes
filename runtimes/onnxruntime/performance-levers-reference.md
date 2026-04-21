# ONNX Runtime Performance Levers
**Rimrock Jetson Orin Nano Super — Gemma 4 E2B/E4B Inference Reference**

**Hardware:** SM87 (Ampere), 8GB LPDDR5, 102 GB/s bandwidth, JetPack 6.2.2 / CUDA 12.6 / cuDNN 9.3 / TensorRT 10.3
**Baseline:** 29 tok/s on E2B Q4_K_M via llama-server (~32% of theoretical 102 GB/s bandwidth ceiling). Runtime overhead is the bottleneck, not hardware.

| L# | Lever | Category | What It Does | Impact | Cost | Notes for Rimrock / Gemma 4 |
|----|-------|----------|--------------|--------|------|----------------------------|
| 1 | `graph_optimization_level = ORT_ENABLE_ALL` | Session Option | Constant folding, dead node elimination, op fusion | Medium | Free | Set at session creation. Default in official packages but verify when building from source. |
| 1 | `execution_mode = ORT_SEQUENTIAL` | Session Option | Eliminates inter-op thread contention on single-stream decode | Low | Free | Better than ORT_PARALLEL for LLM decode. No overhead from thread coordination. |
| 1 | `enable_cpu_mem_arena = False` | Session Option | Reduces RAM usage on unified memory device | Low | Free | On Orin's shared CPU/GPU memory, this matters more than discrete GPU systems. Small latency tradeoff. |
| 1 | `enable_mem_pattern = False` | Session Option | Required for dynamic-shape models | Low | Free | Gemma 4 KV cache changes shape every decode step. Mem pattern optimization breaks on dynamic shapes. |
| 1 | `optimized_model_filepath` | Session Option | Save fused graph to disk, skip optimization on next load | Low (startup) | Free | Run once to bake fusions. Load the saved .onnx directly every subsequent restart. |
| 2 | Attention Fusion | Graph Fusion | Merges Q/K/V matmuls + reshape + transpose + softmax into single Attention contrib op | High | Low | Pattern-matches exact subgraph structure. May fail on Gemma 4 variable head dims (256/512). Check with Netron after. |
| 2 | SkipLayerNormalization Fusion | Graph Fusion | Merges residual Add + LayerNorm into one fused op | Medium | Low | Reduces memory round-trips between ops. Applied per-layer so 35x benefit across Gemma 4 decoder. |
| 2 | BiasGelu / FastGelu Fusion | Graph Fusion | Merges bias Add + GELU activation; FastGelu uses tanh approximation | Medium | Low | FastGelu approximation has negligible quality impact on quantized models. Enable `enable_gelu_approximation=True`. |
| 2 | EmbedLayerNorm Fusion | Graph Fusion | Merges embedding lookup + LayerNorm | Low-Medium | Low | Particularly relevant for Gemma 4 PLE (Per-Layer Embeddings) — each layer has its own embedding table. |
| 2 | `optimizer.optimize_model()` offline | Graph Fusion | Run transformer optimizer tool once, save fused model | High (compound) | Low | Use `model_type='gpt2'`, `opt_level=2`, `use_gpu=True`, `only_onnxruntime=False`. Converts to fp16 in same pass. |
| 3 | GroupQueryAttention (GQA) op | Attention Kernel | Flash Attention V2 kernel for grouped-query attention patterns | Very High | Medium | Check Netron: if decoder uses raw MatMul attention nodes, run graph optimizer to fuse to GQA. Gemma 4 KV sharing (15 pairs / 35 layers) maps directly. |
| 3 | Past-Present KV Buffer Sharing | Memory | Bind present KV cache to past KV cache buffers — no new allocation per step | Very High | Medium | Pre-allocate max-context KV buffers once. Write in-place every decode step. Eliminates per-step memory allocation which is likely a large part of the 68% bandwidth gap. |
| 3 | Flash Attention V2 (SM80+) | Attention Kernel | Tiled attention computation — never materializes full N×N attention matrix | High | Medium | SM87 (Orin Nano Super Ampere) is SM80-compatible. Flash attn fwd hdim128 kernels visible in your build log — confirming they compiled. |
| 4 | IO Binding — `bind_ortvalue_input` | Memory Transfer | Bind inputs to GPU memory buffers, eliminate CPU→GPU copy per decode step | High | Medium | Required prerequisite for CUDA Graph. On Orin unified memory, copies still have latency overhead from cache coherency even though CPU/GPU share physical RAM. |
| 4 | IO Binding — `bind_output` to CUDA | Memory Transfer | Pre-allocate output logits on GPU, eliminate GPU→CPU copy per step | High | Medium | Default ORT behavior copies logits to CPU after every `run()`. With IO binding, logits stay on GPU until you explicitly pull the argmax/sample result. |
| 4 | `run_with_iobinding()` | Memory Transfer | Replace `session.run()` with bound version in decode loop | High | Low | Single line change once bindings are set up. Compound effect across hundreds of decode steps per generation. |
| 5 | `enable_cuda_graph = True` | CUDA Graph | Capture entire GPU kernel sequence once, replay without CPU launch overhead | Medium | High | Requires IO binding + fixed shapes. Decode step `input_ids` is always `[1,1]` — eligible. KV tensors grow, use pre-allocated max-length buffers or separate graph IDs per context bucket. |
| 5 | `gpu_graph_id` in RunOptions | CUDA Graph | Multiple graph IDs for different input shape configurations | Medium | High | Allows prefill (variable length) and decode (fixed `[1,1]`) to each have their own captured graph. Prefill graph less useful since shape varies. |
| 5 | First run captures, subsequent runs replay | CUDA Graph | One-time expensive capture; all subsequent runs are fast replays | Medium | High | First `Run()` allocates CUDA memory + captures graph. Latency is high. Token 2 onwards uses replay — this is where the gain materializes. |
| 6 | `use_tf32 = True` | CUDA EP Option | TF32 precision on Ampere tensor cores — faster matmuls at slightly reduced mantissa | Medium | Free | SM87 supports TF32. For a q4f16 model the precision difference is negligible — already quantized. Free throughput on matmul-heavy layers. |
| 6 | `arena_extend_strategy = kNextPowerOfTwo` | CUDA EP Option | Pre-allocates memory in power-of-two increments to reduce allocator calls | Low-Medium | Free | Reduces fragmentation and allocation overhead during decode. Pairs well with KV buffer sharing. |
| 6 | `cudnn_conv_algo_search = EXHAUSTIVE` | CUDA EP Option | One-time exhaustive cuDNN kernel search — finds optimal algorithm for each Conv op | Low-Medium | One-time | Vision encoder benefits most (Conv ops). Decoder attention layers less so. Result cached by cuDNN across sessions. |
| 6 | `cudnn_conv_use_max_workspace = True` | CUDA EP Option | Allow cuDNN to use maximum workspace for algorithm selection | Low | Free | More workspace = better algorithm candidates during EXHAUSTIVE search. Default True since ORT 1.14. |
| 6 | `do_copy_in_default_stream = True` | CUDA EP Option | Synchronize copies with compute stream | Low | Free | Prevents race conditions between copy and compute operations. Safer default. |
| 6 | `gpu_mem_limit` | CUDA EP Option | Hard cap on CUDA memory arena size | Protective | Free | Set to 6GB for E4B on 8GB Orin. Prevents OOM from arena growing unbounded during long sessions. |
| 7 | `trt_fp16_enable = True` | TRT EP Option | FP16 TensorRT engines — uses Tensor Cores for fused ops | High (partial) | TRT build | Biggest TRT lever on Ampere. Partial coverage expected — Gemma 4 variable head dims cause some layers to fall back to CUDA EP. |
| 7 | `trt_engine_cache_enable` + path | TRT EP Option | Persist compiled TRT engines to NVMe | Zero perf / startup time | Free | No runtime performance gain. Prevents 60+ second TRT rebuild on every restart. Point to `/local/rimrock/trt_cache`. |
| 7 | `trt_timing_cache_enable` + path | TRT EP Option | Cache layer timing data across TRT builds | Build time only | Free | Speeds up subsequent TRT engine builds when model changes. Separate from engine cache. |
| 7 | `trt_max_workspace_size = 2GB` | TRT EP Option | TRT workspace for intermediate buffers during engine optimization | Medium | Free | More workspace = TRT can consider more fusion strategies. 2GB is safe on 8GB Orin with E4B loaded. |
| 7 | `trt_build_heuristics_enable = True` | TRT EP Option | Use heuristics to reduce TRT build time with minimal perf loss | Build time | Free | Faster first-run TRT compilation. Perf within ~5% of full optimization. Good tradeoff for Jetson. |
| 7 | `trt_auxiliary_streams = 0` | TRT EP Option | Minimize auxiliary CUDA streams for optimal memory usage | Low | Free | 0 = use heuristics for stream count. Reduces memory overhead from multiple concurrent streams. |
| 8 | Save optimized model to disk | Offline Opt | Serialize fused graph post-optimization, load directly next session | Startup time | Free | Set `sess_options.optimized_model_filepath` before first load. Load the `.onnx` path directly afterwards to skip optimization entirely. |
| 8 | Run transformer optimizer CLI offline | Offline Opt | `python -m onnxruntime.transformers.optimizer` — full fusion pass outside inference | High (compound) | Low | More fusion options than online optimization. Produces a new `.onnx` with fused nodes baked in. Run once, use permanently. |
| 8 | `convert_float_to_float16()` in optimizer | Offline Opt | Cast fp32 nodes to fp16 in the fused graph | Medium | Low | q4f16 model may still have fp32 scaffolding nodes. This catches them. Run after `optimize_model()`. |
| 9 | `enable_profiling = True` | Profiling | Per-op timing JSON output — identifies actual bottlenecks | Diagnostic | Free | Run 20 decode steps with profiling on. Open JSON in `chrome://tracing`. Look for: ops not on CUDA EP, high-latency unfused nodes, copy overhead. Do this BEFORE pulling other levers. |
| 9 | `log_severity_level = 0` (verbose) | Profiling | Shows which ops are placed on which EP | Diagnostic | Free | `SessionOptions().log_severity_level = 0`. Logs every op placement decision. Reveals which Gemma 4 ops fall back from TRT to CUDA to CPU. |
| 9 | `onnxruntime_perf_test` tool | Profiling | Built CLI benchmarking tool — test specific EP configs without writing inference code | Diagnostic | Free | Built alongside ORT. Use `-e tensorrt` or `-e cuda` flags. Measures latency/throughput directly. Good for A/B comparing EP stacks. |

---

## Priority Order

**Profile first (L9) → Transformer graph fusions offline (L2/L8) → IO Binding (L4) → Check GQA/Flash Attn in exported graph (L3) → TF32 (L6) → CUDA Graph on decode step (L5) → TRT FP16 where coverage exists (L7)**

---

## Key Gemma 4 Caveats

- Variable head dims (256/512) may break Attention fusion pattern matching.
- KV sharing (15 pairs / 35 layers) must be handled manually in raw ORT session loop.
- `trt_cuda_graph_enable` blocked on Jetson Orin per NVIDIA docs — use CUDA EP graph instead.

---

## Current Status (2026-04-19)

- ORT v1.24.4 built from source with CUDA EP — wheel at `/opt/build/onnxruntime/build/Release/dist/`
- Use `PYTHONPATH=/opt/build/onnxruntime/build/Release` (pip ORT has no CUDA EP)
- `device_discovery` warning about `/sys/class/drm/card0` is a Jetson red herring — CUDA EP works
- **L4 achieved:** IO binding benchmark — 34.4ms / 29.03 inf/s (vs 193.6ms CPU baseline = 82% faster)
- **L5 blocked:** CUDA graph fails — 11 CPU fallback nodes in attention mask subgraph prevent full graph capture
- Next: profiling pass (L9), then offline transformer optimizer fusions (L2/L8)
