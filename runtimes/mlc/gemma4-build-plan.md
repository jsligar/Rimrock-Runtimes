# MLC-LLM Gemma 4 E2B Build Plan

## Goal

Run Gemma 4 E2B under MLC-LLM on Rimrock (CUDA SM87) to target ~35–50 tok/s vs the current llama-server baseline of ~26–29 tok/s.

MLC achieves 62.3 tok/s on Gemma 3 1B q4f16_1. Gemma 4 E2B is 2× the parameters — even at half throughput that beats the current ceiling.

## Status

Both required upstream PRs are **DRAFT** as of 2026-04-21:

| PR | Repo | What it adds |
|---|---|---|
| [mlc-ai/relax #346](https://github.com/mlc-ai/relax/pull/346) | TVM/Relax runtime | KV cache routing fix for hybrid SWA/full attention; partial-rotary RoPE for Gemma 4 full-attention layers |
| [mlc-ai/mlc-llm #3485](https://github.com/mlc-ai/mlc-llm/pull/3485) | mlc-llm | `Gemma4ForCausalLM`, `gemma4_loader.py`, `gemma4_e2b_it` preset, model registration |

Both PRs are from the same author (MakotoUwu). Validation was done on the WebGPU path. CUDA/SM87 compile is the untested step.

## Why a C++ rebuild is required

The relax PR changes `src/runtime/vm/paged_kv_cache.cc`. Without it, `ReserveAppendLengthInSeq` runs after the aux-data loop on the `append_before_attn_=false` path. Gemma 4's intra-prefill cross-attention (layers 15–34 reading K/V written by layers 13/14) sees `page_indices->shape[0] == 0` and skips the entire computation — writing uninitialized memory to the KV output. The result is garbage, not just wrong output.

The existing `dustynv/mlc:0.20.0-r36.4.0` container has no TVM source. `libtvm_runtime.so` lives at:
```
/usr/local/lib/python3.10/dist-packages/tvm/libtvm_runtime.so
```
We replace only this file. The full TVM compiler/LLVM stack does not need to be rebuilt.

## What is Python-only (no rebuild needed)

These files can be patched directly into the container:

**From mlc-ai/mlc-llm PR #3485** (all new files):
- `python/mlc_llm/model/gemma4/__init__.py`
- `python/mlc_llm/model/gemma4/gemma4_loader.py`
- `python/mlc_llm/model/gemma4/gemma4_model.py`
- `python/mlc_llm/model/model.py` (registers `gemma4`)
- `python/mlc_llm/model/model_preset.py` (`gemma4_e2b_it` preset)
- `python/mlc_llm/support/auto_target.py`

**From mlc-ai/relax PR #346** (Python only):
- `python/tvm/relax/frontend/nn/llm/position_embedding.py`
- `python/tvm/tirx/build.py`

**Not needed for CUDA** (WebGPU/WASM only):
- `src/target/target_kind.cc` (WebGPU shared-memory registration)
- `web/emcc/wasm_runtime.cc`
- `web/src/runtime.ts`

## Build Steps

### Step 1 — Build libtvm_runtime.so

Clone the relax PR branch and build runtime-only (no LLVM, no TVM compiler):

```bash
cd /opt
git clone --depth 1 --branch prep/gemma4-e2b-text-only \
  https://github.com/MakotoUwu/relax.git tvm-gemma4

cd tvm-gemma4
mkdir build && cd build
cmake .. \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DUSE_LLVM=OFF \
  -DUSE_OPENCL=OFF \
  -DBUILD_STATIC_RUNTIME=OFF

cmake --build . --target tvm_runtime -j$(nproc)
```

Expected: ~45 min, ~3–4 GB RAM peak. Output: `build/libtvm_runtime.so`.

> If the PR branch does not exist on MakotoUwu's fork, check the PR diff and apply manually:
> `gh pr diff 346 --repo mlc-ai/relax > /tmp/relax-gemma4.patch`
> then clone `mlc-ai/relax@mlc` and `git apply /tmp/relax-gemma4.patch`

### Step 2 — Build custom Docker image

```dockerfile
FROM dustynv/mlc:0.20.0-r36.4.0

# Replace runtime with Gemma 4 patched version
COPY libtvm_runtime.so /usr/local/lib/python3.10/dist-packages/tvm/libtvm_runtime.so

# Patch mlc-llm Python files (gemma4 model)
RUN pip install --no-deps --upgrade \
  git+https://github.com/MakotoUwu/mlc-llm.git@prep/gemma4-e2b-text-only

# Patch relax Python files
COPY position_embedding.py \
  /usr/local/lib/python3.10/dist-packages/tvm/relax/frontend/nn/llm/position_embedding.py
COPY tirx_build.py \
  /usr/local/lib/python3.10/dist-packages/tvm/tirx/build.py
```

### Step 3 — Convert model weights

```bash
sudo docker run --rm --runtime nvidia -v /opt/models:/models \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm convert_weight \
    google/gemma-4-e2b-it \
    --quantization q4f16_1 \
    --output /models/gemma4-e2b-q4f16-mlc
```

Requires HuggingFace token for gated model access:
```bash
-e HF_TOKEN=$(cat ~/.cache/huggingface/token)
```

### Step 4 — Compile for CUDA SM87

```bash
sudo docker run --rm --runtime nvidia -v /opt/models:/models \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm compile \
    /models/gemma4-e2b-q4f16-mlc \
    --device cuda \
    --opt O3 \
    --output /models/gemma4-e2b-q4f16-mlc/lib.so
```

This is the untested step — WebGPU-validated only. SM87 compile may expose issues.

### Step 5 — Benchmark

```bash
sudo docker run --rm --runtime nvidia -v /opt/models:/models \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm bench \
    /models/gemma4-e2b-q4f16-mlc \
    --device cuda \
    --prompt "What is the capital of France?" \
    --generate-length 256
```

Compare against llama-server baseline: **~26–29 tok/s**.

## Expected Outcome

| Config | Expected tok/s | Notes |
|---|---:|---|
| llama-server Q4_K_M (current baseline) | 26–29 | Confirmed |
| ORT CUDA Graph (ceiling) | 33 | Hard ceiling — MatMulNBits bottleneck |
| MLC Gemma 4 E2B q4f16_1 (target) | 35–50 | Based on Gemma 3 1B scaling |

## Risk Factors

| Risk | Likelihood | Mitigation |
|---|---|---|
| PR branch not publicly accessible on fork | Medium | Apply patch from `gh pr diff` to `mlc-ai/relax@mlc` |
| SM87 compile fails (untested path) | Medium | Debug compiler errors; may need `max_num_threads` tuning |
| Runtime .so ABI mismatch after rebuild | Low | Use same cmake flags as container's original build |
| Weight conversion OOM (PLE tables) | Low | E2B is 2B params; should fit at q4f16 |

## References

- [mlc-ai/relax PR #346](https://github.com/mlc-ai/relax/pull/346) — TVM runtime prerequisites
- [mlc-ai/mlc-llm PR #3485](https://github.com/mlc-ai/mlc-llm/pull/3485) — Gemma 4 model implementation
- [welcoma/gemma-4-E2B-it-q4f16_1-MLC](https://huggingface.co/welcoma/gemma-4-E2B-it-q4f16_1-MLC) — WebGPU-compiled reference (same PRs, different target)
- [`../mlc/README.md`](README.md) — MLC runtime overview for Rimrock
