# MLC-LLM Gemma 4 E2B Build Plan

## Goal

Run Gemma 4 E2B under MLC-LLM on Rimrock (CUDA SM87) to target ~35–50 tok/s vs the current llama-server baseline of ~26–29 tok/s.

MLC achieves 62.3 tok/s on Gemma 3 1B q4f16_1. Gemma 4 E2B is 2B params — even at half throughput that beats the current ceiling.

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

## What Has Been Built (artifacts on disk)

All artifacts are at `/opt/tvm-gemma4/build/` and `/opt/mlc-gemma4-build/`:

| Artifact | Path | Status |
|---|---|---|
| `libtvm_runtime.so` | `/opt/tvm-gemma4/build/libtvm_runtime.so` | Built ✓ |
| `libtvm.so` | `/opt/tvm-gemma4/build/libtvm.so` | Built ✓ (wrong ABI for base container) |
| `libtvm_ffi.so` | `/opt/tvm-gemma4/build/lib/libtvm_ffi.so` | Built ✓ |
| `libtvm_ffi_testing.so` | `/opt/tvm-gemma4/build/lib/libtvm_ffi_testing.so` | Built ✓ |
| `tvm_ffi.core.cpython-310.so` | `/opt/mlc-gemma4-build/tvm_ffi/core.cpython-310-aarch64-linux-gnu.so` | Built ✓ |
| Source: tvm-gemma4 | `/opt/tvm-gemma4/` | Cloned ✓ (branch `prep/gemma4-e2b-support`) |
| Source: mlc-llm-gemma4 | `/opt/mlc-llm-gemma4/` | Cloned ✓ (branch `prep/gemma4-e2b-text-only`) |

cmake build was configured with:
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

## Full Source Build Plan

### Option A — Wait for Upstream Merge (Recommended if PRs merge within ~1 week)

Watch [mlc-ai/mlc-llm #3485](https://github.com/mlc-ai/mlc-llm/pull/3485). When merged, a new `dustynv/mlc` container will eventually ship with Gemma 4 support natively. Zero custom build effort.

### Option B — Full Source Build Now

Build the entire TVM + MLC stack from the PR branches. Estimated time: 2–3h on Rimrock.

#### Prerequisites

```bash
# Disk: need ~10GB free in /opt
df -h /opt

# RAM: stop llama-server first
sudo systemctl stop llama-server

# Verify CUDA
nvcc --version  # expect 12.6
```

#### Step 1 — Install build dependencies

```bash
sudo apt-get install -y \
  build-essential cmake git python3-dev \
  patchelf ninja-build
pip3 install cython setuptools wheel scikit-build-core
```

#### Step 2 — Clone sources (already done)

```bash
# tvm-gemma4 already at /opt/tvm-gemma4 (branch prep/gemma4-e2b-support)
# mlc-llm-gemma4 already at /opt/mlc-llm-gemma4 (branch prep/gemma4-e2b-text-only)

# Verify
git -C /opt/tvm-gemma4 log --oneline -1
git -C /opt/mlc-llm-gemma4 log --oneline -1
```

#### Step 3 — Build full TVM stack (already partially done)

All targets already built. Verify:
```bash
ls -lh /opt/tvm-gemma4/build/libtvm.so          # 74MB
ls -lh /opt/tvm-gemma4/build/libtvm_runtime.so  # 5MB
ls -lh /opt/tvm-gemma4/build/lib/libtvm_ffi.so  # 1.8MB
ls -lh /opt/tvm-gemma4/build/lib/libtvm_ffi_testing.so
```

If missing, rebuild:
```bash
cd /opt/tvm-gemma4
cmake --build build --target tvm tvm_runtime tvm_ffi_testing -j$(nproc)
```

#### Step 4 — Build tvm_ffi Python package (already done)

The Cython `core.cpython-310.so` is at `/opt/mlc-gemma4-build/tvm_ffi/`.

If missing, rebuild:
```bash
TVMFFI_INC=/opt/tvm-gemma4/3rdparty/tvm-ffi
PY_INC=$(python3 -c "import sysconfig; print(sysconfig.get_path('include'))")
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}{sys.version_info.minor}')")

# Generate C++ from Cython
python3 -m cython --cplus \
  ${TVMFFI_INC}/python/tvm_ffi/cython/core.pyx \
  -o /tmp/tvm_ffi_core.cpp \
  --module-name "tvm_ffi.core"

# Compile testing.o (needed for TVMFFITestingDummyTarget symbol)
g++ -O2 -fPIC -std=c++17 \
  -DTVM_FFI_DLL_EXPORT_INCLUDE_METADATA=1 \
  -I${TVMFFI_INC}/include \
  -I${TVMFFI_INC}/3rdparty/dlpack/include \
  -c ${TVMFFI_INC}/src/ffi/testing/testing.cc \
  -o /tmp/tvm_ffi_testing.o

# Compile core extension (testing symbols baked in)
g++ -O2 -shared -fPIC -std=c++17 \
  -I${TVMFFI_INC}/include \
  -I${TVMFFI_INC}/3rdparty/dlpack/include \
  -I${TVMFFI_INC}/python/tvm_ffi/cython \
  -I${PY_INC} \
  -L/opt/tvm-gemma4/build/lib \
  -ltvm_ffi \
  /tmp/tvm_ffi_core.cpp /tmp/tvm_ffi_testing.o \
  -o /opt/mlc-gemma4-build/tvm_ffi/core.cpython-${PY_VER}-aarch64-linux-gnu.so \
  -Wl,-rpath,/usr/local/lib/python3.10/dist-packages/tvm_ffi
```

#### Step 5 — Build mlc-llm C++ backend against new TVM

This is the step NOT yet done. Must build `libmlc_llm.so` and `mlc_llm_module.so` from the PR branch against the new TVM.

```bash
cd /opt/mlc-llm-gemma4

mkdir -p build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DUSE_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DTVM_HOME=/opt/tvm-gemma4 \
  -DMLC_LLM_INSTALL_STATIC_LIB=OFF \
  2>&1 | tail -10

cmake --build . -j$(nproc) 2>&1 | tee /tmp/mlc-llm-build.log
```

Expected output: `build/libmlc_llm.so`, `build/mlc_llm_module.so`

**Risk:** mlc-llm's cmake may not know about `tvm_ffi` as a separate package. May need to pass `-DTVM_FFI_HOME=/opt/tvm-gemma4/3rdparty/tvm-ffi`.

#### Step 6 — Build Docker image with full stack

```dockerfile
FROM dustynv/mlc:0.20.0-r36.4.0

# New TVM shared libraries
COPY libtvm.so /usr/local/lib/python3.10/dist-packages/tvm/libtvm.so
COPY libtvm_runtime.so /usr/local/lib/python3.10/dist-packages/tvm/libtvm_runtime.so

# tvm_ffi — new FFI layer
COPY tvm_ffi/ /usr/local/lib/python3.10/dist-packages/tvm_ffi/
COPY libtvm_ffi.so /usr/local/lib/python3.10/dist-packages/tvm_ffi/libtvm_ffi.so
COPY libtvm_ffi_testing.so /usr/local/lib/python3.10/dist-packages/tvm_ffi/libtvm_ffi_testing.so
COPY apache_tvm_ffi_dist_info/ /usr/local/lib/python3.10/dist-packages/apache_tvm_ffi-0.20.0.dist-info/

# New TVM Python package (replaces old tvm Python layer entirely)
COPY tvm_python/ /usr/local/lib/python3.10/dist-packages/tvm/

# New mlc-llm C++ backend
COPY libmlc_llm.so /usr/local/lib/python3.10/dist-packages/mlc_llm/libmlc_llm.so
COPY mlc_llm_module.so /usr/local/lib/python3.10/dist-packages/mlc_llm/mlc_llm_module.so

# New mlc-llm Python package (Gemma 4 model files)
COPY mlc_llm_python/ /usr/local/lib/python3.10/dist-packages/mlc_llm/
```

#### Step 7 — Sanity check

```bash
sudo docker run --rm --runtime nvidia rimrock/mlc-gemma4:latest python3 -c "
import tvm_ffi; print('tvm_ffi:', tvm_ffi.__version__)
import tvm; print('tvm:', tvm.__version__)
from tvm import tirx; print('tirx OK')
from mlc_llm.model.model import MODELS
print('gemma4 registered:', 'gemma4' in MODELS)
print('ALL CHECKS PASSED')
"
```

#### Step 8 — Weight conversion

```bash
HF_TOKEN=$(cat ~/.cache/huggingface/token)

sudo docker run --rm --runtime nvidia \
  -v /opt/models:/models \
  -e HF_TOKEN=$HF_TOKEN \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm convert_weight \
    google/gemma-4-e2b-it \
    --quantization q4f16_1 \
    --output /models/gemma4-e2b-q4f16-mlc
```

Expected: ~15–20 min, ~4GB output.

#### Step 9 — SM87 CUDA compile (the untested step)

```bash
sudo docker run --rm --runtime nvidia \
  -v /opt/models:/models \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm compile \
    /models/gemma4-e2b-q4f16-mlc \
    --device cuda \
    --opt O3 \
    --output /models/gemma4-e2b-q4f16-mlc/lib.so
```

If this fails with workgroup/thread count errors, add: `--overrides "max_num_threads=128"`

#### Step 10 — Benchmark

```bash
sudo docker run --rm --runtime nvidia \
  -v /opt/models:/models \
  rimrock/mlc-gemma4:latest \
  python3 -m mlc_llm bench \
    /models/gemma4-e2b-q4f16-mlc \
    --device cuda \
    --generate-length 256
```

Target: beat llama-server baseline of **26–29 tok/s**. Expected: **35–50 tok/s**.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| mlc-llm cmake can't find tvm_ffi | Medium | Blocks Step 5 | Pass `-DTVM_FFI_HOME` explicitly |
| mlc-llm C++ ABI incompatibility with new TVM | Low | Blocks Step 5 | Both built from same source tree |
| SM87 compile fails (untested path) | Medium | Blocks Step 9 | `max_num_threads=128` tuning |
| Weight conversion OOM | Low | Blocks Step 8 | E2B is 2B params, q4f16 fits |
| PRs merge before we finish | Low | Makes this moot | Switch to official container |

## Decision Point

**If mlc-ai/mlc-llm #3485 merges within ~1 week:** Stop here, wait for `dustynv/mlc` to ship a new container. Zero risk path.

**If we want it now:** Proceed to Step 5 (mlc-llm C++ build). Estimated 1–2h additional build time.

## References

- [mlc-ai/relax PR #346](https://github.com/mlc-ai/relax/pull/346)
- [mlc-ai/mlc-llm PR #3485](https://github.com/mlc-ai/mlc-llm/pull/3485)
- [welcoma/gemma-4-E2B-it-q4f16_1-MLC](https://huggingface.co/welcoma/gemma-4-E2B-it-q4f16_1-MLC) — WebGPU reference artifact from same PRs
- MLC runtime overview: [`README.md`](README.md)
- llama-server baseline: [`../../benchmarks/ort-progress-2026-04-19.md`](../../benchmarks/ort-progress-2026-04-19.md)
