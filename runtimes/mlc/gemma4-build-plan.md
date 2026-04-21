# MLC-LLM Gemma 4 E2B Build Plan

## Goal

Run Gemma 4 E2B under MLC-LLM on Rimrock (CUDA SM87) to target ~35–50 tok/s vs the current llama-server baseline of ~26–29 tok/s.

MLC achieves 62.3 tok/s on Gemma 3 1B q4f16_1. Gemma 4 E2B is 2B params — even at half throughput that beats the current ceiling.

## Status (2026-04-21)

| Step | Task | Status |
|---|---|---|
| 1 | Install build deps | ✓ Done |
| 2 | Clone PR branches | ✓ Done |
| 3 | Build full TVM stack (libtvm.so, libtvm_runtime.so, libtvm_ffi.so) | ✓ Done |
| 4 | Build tvm_ffi Python extension (core.cpython-310.so) | ✓ Done |
| 5 | Build mlc-llm C++ (libmlc_llm.so, libmlc_llm_module.so) | ✓ Done |
| 6 | Build Docker image `rimrock/mlc-gemma4:latest` | ✓ Done (2026-04-21) |
| 7 | Sanity check (tvm_ffi, tvm, tirx, gemma4 model registered) | ✓ Passed |
| 8 | Download pre-quantized weights (welcoma/gemma-4-E2B-it-q4f16_1-MLC) | ✓ Done (2.5GB, 46 shards) |
| 9 | SM87 CUDA compile (`mlc_llm compile`) | ⏳ In progress / needs rerun |
| 10 | Benchmark vs llama-server baseline | ⬜ Pending lib-sm87.so |

## Upstream PR Status (as of 2026-04-21)

Both required PRs are **DRAFT**:

| PR | Repo | What it adds | State |
|---|---|---|---|
| [mlc-ai/relax #346](https://github.com/mlc-ai/relax/pull/346) | TVM/Relax runtime | KV cache fix, partial-rotary RoPE, tirx module | DRAFT |
| [mlc-ai/mlc-llm #3485](https://github.com/mlc-ai/mlc-llm/pull/3485) | mlc-llm | `Gemma4ForCausalLM`, loader, preset, model registration | DRAFT |

Author: MakotoUwu (Oleksandr Tsepukh). Both branches publicly accessible on the fork.

## Why a Full Source Build is Required

**Attempted:** Surgical patch of `dustynv/mlc:0.20.0-r36.4.0` — replace `libtvm.so`, `libtvm_runtime.so`, inject new Python modules.

**Why it fails:** The PR introduces `tvm_ffi` — an entirely new C++/Python FFI layer that replaces TVM's old `_ffi` C API. The base container's:
- `libtvm.so` exports `TVMGetLastError` and the legacy C API
- `python/tvm/_ffi/` Python layer uses `ctypes` to call the legacy API
- `libmlc_llm.so` was compiled against the legacy ABI

The new `tirx` module uses `tvm_ffi` object registration (`tvm/ffi/reflection/registry.h`), which is incompatible with the old system. There is no way to graft `tirx` onto the base container without replacing the entire TVM stack.

**Conclusion:** Must build the full stack from source.

## What Is on Disk (as of 2026-04-21)

### Build Sources
| Source | Path | Branch |
|---|---|---|
| TVM (relax PR) | `/opt/tvm-gemma4/` | `prep/gemma4-e2b-support` |
| MLC-LLM (mlc-llm PR) | `/opt/mlc-llm-gemma4/` | `prep/gemma4-e2b-text-only` |
| Docker build context | `/opt/mlc-gemma4-build/` | — |

### Built Artifacts
| Artifact | Path | Notes |
|---|---|---|
| `libtvm.so` | `/opt/tvm-gemma4/build/libtvm.so` | 74MB, full TVM with tirx module |
| `libtvm_runtime.so` | `/opt/tvm-gemma4/build/libtvm_runtime.so` | 5MB |
| `libtvm_ffi.so` | `/opt/tvm-gemma4/build/lib/libtvm_ffi.so` | 1.8MB |
| `libtvm_ffi_testing.so` | `/opt/tvm-gemma4/build/lib/libtvm_ffi_testing.so` | |
| `tvm_ffi.core.cpython-310.so` | `/opt/mlc-gemma4-build/tvm_ffi/core.cpython-310-aarch64-linux-gnu.so` | Cython ext |
| `libmlc_llm.so` | `/opt/mlc-llm-gemma4/build/libmlc_llm.so` | 18MB |
| `libmlc_llm_module.so` | `/opt/mlc-llm-gemma4/build/libmlc_llm_module.so` | |

### Weights
| Item | Path | Notes |
|---|---|---|
| Pre-quantized weight shards | `/opt/models/gemma4-e2b-q4f16-mlc/` | 2.5GB, 46 shards, q4f16_1 |
| Compiled model lib | `/opt/models/gemma4-e2b-q4f16-mlc/lib-sm87.so` | **pending** |

## cmake Flags

### TVM
```bash
cmake -B build \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DUSE_LLVM=OFF \
  -DUSE_OPENCL=OFF \
  -DBUILD_STATIC_RUNTIME=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DTVM_FFI_BUILD_PYTHON_MODULE=ON
```

### MLC-LLM
```bash
TVM_SOURCE_DIR=/opt/tvm-gemma4 cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DUSE_FLASHINFER=OFF
```

**Known issue:** Built without LLVM (`USE_LLVM=OFF`). The `mlc_llm compile` command requires `--host aarch64-linux-gnu` to bypass LLVM auto-detection of the host target triple.

## Build Issues Encountered and Resolved

| Issue | Root Cause | Fix |
|---|---|---|
| `tvm-ffi` submodule missing | Not initialized on clone | `git submodule update --init --recursive 3rdparty/tvm-ffi` |
| `TVMFFITestingDummyTarget` undefined in `core.so` | Symbol lives in `libtvm_ffi_testing.so`, not in `libtvm_ffi.so` | Compiled `testing.cc` into `.o` and linked directly into `core.so` |
| `tirx.Buffer` type not registered | `tirx` compiled into `libtvm.so` (full compiler), not `libtvm_runtime.so` | Built full `tvm` target, added `libtvm.so` to Docker image |
| `TVMGetLastError` undefined | New TVM replaced legacy C API with `tvm_ffi` | Replaced entire TVM Python package (`tvm_python`) |
| `pytest` not found | `tvm/__init__.py` → `meta_schedule` → `rpc` → `tvm.testing` → `pytest` | `RUN pip3 install pytest` in Dockerfile |
| `base64.h` path hardcoded in mlc-llm | `image_utils.cc` includes `../../3rdparty/tvm/src/support/base64.h` | `ln -s /opt/tvm-gemma4 /opt/mlc-llm-gemma4/3rdparty/tvm` |
| `cargo` not found | Rust required for tokenizers-cpp in mlc-llm cmake | `curl https://sh.rustup.rs \| sh -s -- -y --profile minimal` |
| LLVM host triple detection fails | TVM built with `USE_LLVM=OFF` | Use `--host aarch64-linux-gnu` flag in `mlc_llm compile` |
| `pip install` fails in Docker build | Container's PyPI index `pypi.jetson-ai-lab.dev` unreachable | Abandoned pip, COPY Python package files directly |
| `tvm_ffi` dist-info missing | `libinfo.py` calls `importlib.metadata.distribution("apache-tvm-ffi")` | Created fake dist-info dir with METADATA/RECORD, COPY'd into image |

## Step 9 — SM87 CUDA Compile

Run inside the custom image:
```bash
sudo docker run --rm --runtime nvidia \
  -v /opt/models/gemma4-e2b-q4f16-mlc:/weights \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm compile /weights \
    --device cuda \
    --host aarch64-linux-gnu \
    --opt O3 \
    --output /weights/lib-sm87.so
```

Expected output: `/opt/models/gemma4-e2b-q4f16-mlc/lib-sm87.so` (~30–80MB CUDA fat binary)

If this fails with workgroup/thread count errors, add: `--overrides "max_num_threads=128"`

## Step 10 — Benchmark

```bash
sudo docker run --rm --runtime nvidia \
  -v /opt/models/gemma4-e2b-q4f16-mlc:/weights \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm bench /weights \
    --device cuda \
    --generate-length 256
```

Target: beat llama-server baseline of **26–29 tok/s**. Expected: **35–50 tok/s**.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| SM87 compile fails (workgroup tuning) | Medium | Blocks Step 9 | `--overrides "max_num_threads=128"` |
| KV cache correctness issue at runtime | Low | Silent wrong output | Verify with known-good prompt |
| PRs merge before we finish | Low | Makes this moot | Switch to official container when available |

## Decision Point

**If mlc-ai/mlc-llm #3485 merges:** Stop custom build path, wait for `dustynv/mlc` to ship a new container. Zero risk path.

**If we want it now:** Steps 1–8 complete. Only Step 9 (CUDA compile) and Step 10 (benchmark) remain.

## References

- [mlc-ai/relax PR #346](https://github.com/mlc-ai/relax/pull/346)
- [mlc-ai/mlc-llm PR #3485](https://github.com/mlc-ai/mlc-llm/pull/3485)
- [welcoma/gemma-4-E2B-it-q4f16_1-MLC](https://huggingface.co/welcoma/gemma-4-E2B-it-q4f16_1-MLC) — pre-quantized weights source
- MLC runtime overview: [`../../containers/README.md`](../../containers/README.md)
- llama-server baseline: [`../../benchmarks/ort-progress-2026-04-19.md`](../../benchmarks/ort-progress-2026-04-19.md)
- Rebuild script: [`build-gemma4-image.sh`](build-gemma4-image.sh)
