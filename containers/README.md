# Docker Images on Rimrock

All containers use `--runtime nvidia` for GPU access.

## Inference Runtimes

| Image | Tag | Size | Pulled | Status |
|---|---|---:|---|---|
| `rimrock/mlc-gemma4` | `latest` | ~25GB | 2026-04-21 | **Active** — custom build, Gemma 4 E2B support |
| `ghcr.io/nvidia-ai-iot/vllm` | `gemma4-jetson-orin` | 31.2GB | 2026-04-08 | Tested — dead end (see below) |
| `dustynv/mlc` | `0.20.0-r36.4.0` | 24.3GB | 2025-05-02 | Base for rimrock/mlc-gemma4 |
| `dustynv/onnxruntime` | `1.20.2-r36.4.0` | 17.4GB | 2025-02-18 | Not used — ORT built from source instead |
| `dustynv/llama_cpp` | `r36.4.0` | 13GB | 2025-01-31 | **Not used** — too old, no Gemma 4 support |
| `dustynv/tensorrt_llm` | `0.12-r36.4.0` | 27.9GB | 2024-11-13 | Not tested |

### `rimrock/mlc-gemma4:latest` — Custom Build (2026-04-21)

Built from source to add Gemma 4 E2B support. Based on `dustynv/mlc:0.20.0-r36.4.0` with a full TVM stack replacement.

**Benchmark result:** **33.1 tok/s** (Gemma 4 E2B q4f16_1, 256-token decode, SM87) vs llama-server baseline of 26–29 tok/s. ~20% faster. GPU memory: 3128 MB total (params 2512 + KV 346 + buffer 270).

**What was replaced:**
- `libtvm.so` + `libtvm_runtime.so` — rebuilt from [mlc-ai/relax PR #346](https://github.com/mlc-ai/relax/pull/346) (`prep/gemma4-e2b-support` branch). Adds KV cache fix for hybrid SWA/full attention and `tirx` module.
- `libtvm_ffi.so` + `tvm_ffi` Python package — new FFI layer introduced in this TVM branch, completely replaces the old `tvm._ffi` C API.
- Full `tvm` Python package — from same branch (no `_ffi` layer in new package). Patched to register `target.target_has_feature` stub (LLVM function, needed by VectorizeLoop pass).
- `libmlc_llm.so` + `libmlc_llm_module.so` — rebuilt from [mlc-ai/mlc-llm PR #3485](https://github.com/mlc-ai/mlc-llm/pull/3485) (`prep/gemma4-e2b-text-only` branch) against new TVM.
- Full `mlc_llm` Python package — from same branch (includes `Gemma4ForCausalLM`, `gemma4_loader.py`, `gemma4_e2b_it` preset).

**TVM source patches applied:**
- `src/tirx/analysis/verify_memory.cc` — skip `VerifyMemory` for loop-free scalar GPU functions (Gemma 4's 0-D `zeros` init kernels have no thread bindings; all-thread idempotent writes are correct).

**Build artifacts on disk:**
| Artifact | Path |
|---|---|
| TVM source (relax PR branch) | `/opt/tvm-gemma4/` |
| MLC-LLM source (PR branch) | `/opt/mlc-llm-gemma4/` |
| Docker build context | `/opt/mlc-gemma4-build/` |
| Built `libtvm.so` | `/opt/tvm-gemma4/build/libtvm.so` (97MB) |
| Built `libmlc_llm.so` | `/opt/mlc-llm-gemma4/build/libmlc_llm.so` (18MB) |
| Pre-quantized weights | `/opt/models/gemma4-e2b-q4f16-mlc/` (2.5GB, q4f16_1) |
| Compiled model lib | `/opt/models/gemma4-e2b-q4f16-mlc/lib-sm87.so` (38MB) ✓ |

**cmake flags used:**

TVM (requires `llvm-15-dev` on host):
```bash
sudo apt-get install -y llvm-15-dev
cmake -B build -DUSE_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DUSE_LLVM="llvm-config-15" -DUSE_THRUST=ON \
  -DUSE_OPENCL=OFF -DBUILD_STATIC_RUNTIME=OFF \
  -DCMAKE_BUILD_TYPE=Release -DTVM_FFI_BUILD_PYTHON_MODULE=ON
```

MLC-LLM:
```bash
TVM_SOURCE_DIR=/opt/tvm-gemma4 cmake -B build \
  -DCMAKE_BUILD_TYPE=Release -DUSE_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 -DUSE_FLASHINFER=OFF
```

**Rebuild script:** [`../runtimes/mlc/build-gemma4-image.sh`](../runtimes/mlc/build-gemma4-image.sh)

**Full build history:** [`../runtimes/mlc/gemma4-build-plan.md`](../runtimes/mlc/gemma4-build-plan.md)

### `ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin` — Dead End

vLLM 0.19.0, TRANSFORMERS 5.5.0, purpose-built for Gemma 4 on Jetson Orin. Investigated thoroughly in April 2026.

**Blockers:**

1. **V1 engine subprocess memory isolation** — vLLM V1 forks EngineCore as a separate process. Parent CUDA context (~1.86GB) already allocated before subprocess checks free memory. Subprocess sees only 3.45–3.55GB free vs 5.38GB the parent sees. `VLLM_USE_V1=0` env var is ignored (always V1 in 0.19.0).

2. **GGUF loader missing gemma4** — `gguf.MODEL_ARCH_NAMES` only goes to `gemma3`. The gemma4 GGUF has new tensor names (`inp_gate`, `layer_output_scale`, `per_layer_*`) incompatible with a gemma3 alias. Can't safely use GGUF path.

3. **Native HF + BitsAndBytes OOM** — Gemma 4's `embed_tokens_per_layer` (per-layer embedding tables: 262144 vocab × 35 layers) allocates ~4.5GB at float16 before quantization applies. Crashes CUDA allocator inside EngineCore subprocess with `NVML_SUCCESS == r INTERNAL ASSERT FAILED`.

**Conclusion:** vLLM is not viable for Gemma 4 E2B on 8GB unified memory with this architecture. The per-layer embedding design is the hard blocker regardless of quantization method.

### TODO: Review `maarifa-vllm-jetson-orin` as SM87 Patch Reference

Reference repo: <https://github.com/jdelacasa/maarifa-vllm-jetson-orin>

Why it matters:

- Builds vLLM `0.19.0` for Jetson Orin / SM87 from `dustynv/vllm:r36.4-cu129-24.04`
- Patches vLLM and flash-attn CMake arch lists to include `8.7+PTX`
- Works around Jetson-specific `torch 2.8.0` vs vLLM `0.19.x` compatibility issues
- Handles Tegra `libcuda.so.1` preload problems in the entrypoint
- Filters unsupported Jetson/aarch64 CUDA requirements during build

Do **not** run the compose file as-is on Rimrock:

- It targets AGX Orin-class memory, not Orin Nano 8GB
- Default model is `Qwen/Qwen3.5-35B-A3B-GPTQ-Int4`
- Default context/batch settings are `44000`, far beyond Rimrock's safe budget
- Build time is expected to be multiple hours

Safe exploration plan for Rimrock:

1. Treat the repo as a patch reference, not a ready runtime.
2. Extract the SM87 CMake, flash-attn, torch compatibility, and `libcuda` preload patches.
3. Build only in a disposable Docker image with adequate disk space.
4. Test with a small 1B-3B model first.
5. Use strict low-memory settings:
   - `--max-model-len 2048`
   - `--max-num-seqs 1`
   - `--gpu-memory-utilization 0.45`
   - no large default MoE or 35B-class model
6. Re-check whether vLLM V1 EngineCore subprocess memory isolation still leaves too little visible GPU memory.

Success criterion:

- A small instruct model serves through vLLM on Rimrock without EngineCore OOM and produces a measured decode rate. Anything else remains a build-patch reference only.

### GitHub Search Terms for Runtime Dead Ends

Use these searches when looking for repos that may push past Rimrock's current blockers:

```text
Jetson Orin Nano TensorRT-LLM int4
Jetson Orin Nano llama.cpp CUDA graph
Jetson Orin Nano CUTLASS int4 GEMV
SM87 int4 weight only GEMV
CUDA weightOnlyBatchedGemvBs1Int4b
Jetson Orin Nano MLC LLM build
mlc-llm Jetson Orin Nano CUDA 12.6
TensorRT-LLM Jetson Orin Nano 8GB
Gemma 3 GGUF Jetson Orin
Qwen3 GGUF Jetson Orin
Jetson Orin Nano TensorRT-LLM INT4 Llama Qwen Gemma
MLC LLM Jetson CUDA 12.6 SM87
vLLM Jetson Orin sm_87 0.19
vLLM Jetson Orin Nano 8GB
flash-attn sm_87 Jetson
Marlin GPTQ sm_87 Jetson
ONNX Runtime MatMulNBits CUDA custom kernel
```

Prioritize repos with exact commands, model IDs, quantization, power mode, context length, memory usage, and raw tok/s logs. Deprioritize generic Jetson demos, vision-only repos, old JetPack 4/Xavier material, or claims without raw artifacts.

### `dustynv/mlc:0.20.0-r36.4.0` — Not Competitive

MLC-LLM v0.20.0. Published ~May 2025, approximately 12 months old at time of testing.

**Known issues:**
- Extended vocab tokens (IDs > 262144) crash: `InternalError: token_id < token_table_.size() (262207 vs. 262145)` — affects Gemma 3 4B and similar models
- Gemma 4 E2B not in model registry
- `<think>` tokens from Qwen3 expose internal reasoning and consume token budget

Best result: Qwen2.5-3B at 3.8/5 (vs llama-server Gemma 4 E2B at 4.6/5). See [`../benchmarks/mlc-runtime-2026-04-09.md`](../benchmarks/mlc-runtime-2026-04-09.md) and [`../benchmarks/mlc-small-models-2026-04-20.md`](../benchmarks/mlc-small-models-2026-04-20.md).

### `dustynv/llama_cpp:r36.4.0` — Do Not Use

Build 4579, January 2025. Does **not** support Gemma 4 or Nemotron-H architectures. Use the locally built binary at `/opt/llama.cpp/build/bin/llama-server` (build 8664) instead.

### `dustynv/onnxruntime:1.20.2-r36.4.0`

Not used for inference testing — ORT v1.24.4 was built from source to get a newer CUDA EP. The dustynv image ships ORT 1.20.2 which predates several optimizations tested.

### `dustynv/tensorrt_llm:0.12-r36.4.0`

Not tested. TRT-LLM is a potential future path for MatMulNBits acceleration (the kernel exists in TRT-LLM lineage), but has not been evaluated on this device.

---

## Services

| Image | Tag | Size | Purpose | Status |
|---|---|---:|---|---|
| `open-webui-workhorse-deploy-memory-mcp` | `latest` | 1.3GB | memory-mcp service on port 8001 | **Running** |
| `open-webui-deploy-memory-mcp` | `latest` | 695MB | Older memory-mcp build | Inactive |
| `open-webui-deploy-filesystem-mcp` | `latest` | 695MB | Filesystem MCP | Inactive |
| `open-webui-deploy-github-mcp` | `latest` | 695MB | GitHub MCP | Inactive |
| `open-webui-deploy-lab-tools` | `latest` | 275MB | Lab tools | Inactive |
| `ghcr.io/open-webui/open-webui` | `main` | 6.03GB | OpenWebUI — **migrated to WORKHORSE** | Inactive on Rimrock |

`memory-mcp` runs CPU-only, no GPU impact. OpenWebUI was migrated off Rimrock to WORKHORSE to free RAM.

---

## Base / Build Images

| Image | Tag | Size | Notes |
|---|---|---:|---|
| `xformers` | `r36.5.tegra-aarch64-cu126-22.04-pybind11` | 19.3GB | Top of xformers jetson-containers build chain |
| `xformers` | `0.0.36-...-onnxruntime_1.19.2` | 32.6GB | xformers + ORT 1.19.2 layer |
| `nvcr.io/nvidia/l4t-jetpack` | `r36.4.0` | 15.5GB | NVIDIA L4T JetPack base |
| `dustynv/ollama` | `r36.4-cu129-24.04` | 13.2GB | Ollama (inactive — service stopped) |
| `dustynv/ollama` | `0.6.8-r36.4-cu126-22.04` | 15.4GB | Ollama older build |
| `ubuntu` | `22.04` | 109MB | Base |
| `nvidia/cuda` | `12.6.0-base-ubuntu22.04` | 333MB | CUDA base |
| `nvcr.io/nvidia/l4t-base` | `r36.2.0` | 1.1GB | L4T base (older) |

The `xformers` build chain (29 image layers, ~17–33GB each) was built locally via jetson-containers. These are intermediate build artifacts from the ORT/xformers investigation.

---

## Running Containers

```bash
sudo docker ps
```

```
NAMES        IMAGE                                    STATUS
memory-mcp   open-webui-workhorse-deploy-memory-mcp   Up (CPU only, port 8001)
```

---

## Launch Examples

### MLC (text inference)
```bash
sudo docker run --rm --runtime nvidia \
  -v /opt/models/mlc:/opt/models/mlc \
  dustynv/mlc:0.20.0-r36.4.0 \
  python3 -m mlc_llm serve HF://mlc-ai/Qwen2.5-3B-Instruct-q4f16_1-MLC \
  --host 0.0.0.0 --port 8424
```

### vLLM (not viable — documented for reference)
```bash
sudo docker run --rm --runtime nvidia \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -v /opt/models:/opt/models:ro \
  ghcr.io/nvidia-ai-iot/vllm:gemma4-jetson-orin \
  python3 -m vllm.entrypoints.openai.api_server \
  --model google/gemma-4-e2b-it \
  --port 8424
# Fails: EngineCore subprocess sees only 3.45GB free GPU memory
```
