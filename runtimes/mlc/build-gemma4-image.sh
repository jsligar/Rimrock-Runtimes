#!/usr/bin/env bash
# Rebuild rimrock/mlc-gemma4:latest from existing on-disk build artifacts.
# Assumes Steps 1-5 of gemma4-build-plan.md are already complete.
# All build artifacts must exist on the host before running this script.
set -euo pipefail

BUILD_CTX=/opt/mlc-gemma4-build
TVM_BUILD=/opt/tvm-gemma4/build
MLC_BUILD=/opt/mlc-llm-gemma4/build
TVM_SRC=/opt/tvm-gemma4
MLC_SRC=/opt/mlc-llm-gemma4

# ── Verify required artifacts ────────────────────────────────────────────────
check() {
  if [[ ! -e "$1" ]]; then
    echo "MISSING: $1" >&2
    exit 1
  fi
}
check "$TVM_BUILD/libtvm.so"
check "$TVM_BUILD/libtvm_runtime.so"
check "$TVM_BUILD/lib/libtvm_ffi.so"
check "$TVM_BUILD/lib/libtvm_ffi_testing.so"
check "$BUILD_CTX/tvm_ffi/core.cpython-310-aarch64-linux-gnu.so"
check "$MLC_BUILD/libmlc_llm.so"
check "$MLC_BUILD/libmlc_llm_module.so"

# ── Stage artifacts into build context ───────────────────────────────────────
echo "Staging artifacts into $BUILD_CTX ..."

TARGET_RPATH_TVM="/usr/local/lib/python3.10/dist-packages/tvm_ffi:/usr/local/cuda-12.6/lib64"
TARGET_RPATH_MLC="/usr/local/lib/python3.10/dist-packages/tvm:/usr/local/lib/python3.10/dist-packages/tvm_ffi"

# tvm_ffi shared libs
cp "$TVM_BUILD/lib/libtvm_ffi.so" "$BUILD_CTX/libtvm_ffi.so"
cp "$TVM_BUILD/lib/libtvm_ffi_testing.so" "$BUILD_CTX/libtvm_ffi_testing.so"

# tvm shared libs (patchelf rpath to container install path)
cp "$TVM_BUILD/libtvm.so" "$BUILD_CTX/libtvm.so"
cp "$TVM_BUILD/libtvm_runtime.so" "$BUILD_CTX/libtvm_runtime.so"
patchelf --set-rpath "$TARGET_RPATH_TVM" "$BUILD_CTX/libtvm.so"
patchelf --set-rpath "$TARGET_RPATH_TVM" "$BUILD_CTX/libtvm_runtime.so"

# mlc-llm shared libs (patchelf rpath to container install path)
cp "$MLC_BUILD/libmlc_llm.so" "$BUILD_CTX/libmlc_llm.so"
cp "$MLC_BUILD/libmlc_llm_module.so" "$BUILD_CTX/libmlc_llm_module.so"
patchelf --set-rpath "$TARGET_RPATH_MLC" "$BUILD_CTX/libmlc_llm.so"
patchelf --set-rpath "$TARGET_RPATH_MLC" "$BUILD_CTX/libmlc_llm_module.so"

# Python packages (sync from source trees)
rsync -a --delete "$TVM_SRC/python/tvm/" "$BUILD_CTX/tvm_python/"
rsync -a --delete "$TVM_SRC/3rdparty/tvm-ffi/python/tvm_ffi/" "$BUILD_CTX/tvm_ffi/"
# restore the compiled Cython extension after rsync
cp "$BUILD_CTX/tvm_ffi/core.cpython-310-aarch64-linux-gnu.so" "$BUILD_CTX/tvm_ffi/core.cpython-310-aarch64-linux-gnu.so" 2>/dev/null || true
rsync -a --delete "$MLC_SRC/python/mlc_llm/" "$BUILD_CTX/mlc_llm_python/"

# ── Build Docker image ────────────────────────────────────────────────────────
echo "Building rimrock/mlc-gemma4:latest ..."
sudo docker build -t rimrock/mlc-gemma4:latest "$BUILD_CTX"

echo ""
echo "Build complete. Run sanity check:"
echo "  sudo docker run --rm --runtime nvidia rimrock/mlc-gemma4:latest python3 -c \""
echo "    import tvm_ffi; print('tvm_ffi:', tvm_ffi.__version__)"
echo "    import tvm; print('tvm:', tvm.__version__)"
echo "    from tvm import tirx; print('tirx OK')"
echo "    from mlc_llm.model.model import MODELS"
echo "    print('gemma4 registered:', 'gemma4' in MODELS)"
echo "  \""
