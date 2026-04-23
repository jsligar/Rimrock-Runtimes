#!/usr/bin/env bash
# Build MLC weights + compiled lib for nvidia/Llama-3.1-Nemotron-Nano-8B-v1
# on Rimrock (Jetson Orin Nano 8GB, SM87, aarch64, CUDA 12.6).
#
# Usage: sudo bash build-nemotron-8b.sh
set -euo pipefail

MODEL_ID="nvidia/Llama-3.1-Nemotron-Nano-8B-v1"
HF_SRC="/opt/models/nemotron-nano-8b-hf"
MLC_OUT="/opt/models/nemotron-nano-8b-mlc"
QUANT="q4f16_1"
DEVICE="cuda:0"
CONTEXT_WINDOW=4096
PREFILL_CHUNK=1024
MAX_BATCH=1

# Conservative/stable profile for SM87.
OPT="faster_transformer=1;cudagraph=1;flashinfer=0;cutlass=0;cublas_gemm=0"
IMAGE="rimrock/mlc-gemma4:latest"

echo "=== Step 0: ensure HF source weights exist ==="
if [[ ! -f "$HF_SRC/config.json" ]]; then
  echo "Downloading $MODEL_ID to $HF_SRC ..."
  sudo docker run --rm \
    -v /opt/models:/opt/models \
    "$IMAGE" \
    python3 - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="nvidia/Llama-3.1-Nemotron-Nano-8B-v1",
    local_dir="/opt/models/nemotron-nano-8b-hf",
    local_dir_use_symlinks=False,
    resume_download=True,
)
print("HF_DOWNLOAD_OK")
PY
fi

if [[ ! -f "$HF_SRC/config.json" ]]; then
  echo "ERROR: expected $HF_SRC/config.json after download" >&2
  exit 1
fi

echo ""
echo "=== Step 1: convert_weight ($QUANT) ==="
sudo docker run --rm \
  --runtime nvidia \
  -v "$HF_SRC":/hf-src:ro \
  -v "$MLC_OUT":/mlc-out \
  "$IMAGE" \
  python3 -m mlc_llm convert_weight /hf-src \
    --quantization "$QUANT" \
    -o /mlc-out

echo ""
echo "=== Step 2: gen_config ==="
sudo docker run --rm \
  --runtime nvidia \
  -v "$HF_SRC":/hf-src:ro \
  -v "$MLC_OUT":/mlc-out \
  "$IMAGE" \
  python3 -m mlc_llm gen_config /hf-src \
    --quantization "$QUANT" \
    --conv-template llama-3_1 \
    --context-window-size "$CONTEXT_WINDOW" \
    --prefill-chunk-size "$PREFILL_CHUNK" \
    -o /mlc-out

echo ""
echo "=== Step 3: compile ==="
sudo docker run --rm \
  --runtime nvidia \
  -v "$MLC_OUT":/mlc-out \
  "$IMAGE" \
  python3 -m mlc_llm compile /mlc-out/mlc-chat-config.json \
    --device "$DEVICE" \
    --quantization "$QUANT" \
    --opt "$OPT" \
    --overrides "max_batch_size=${MAX_BATCH}" \
    -o /mlc-out/lib-sm87.so

echo ""
echo "=== Build complete ==="
ls -lh "$MLC_OUT/lib-sm87.so" "$MLC_OUT/mlc-chat-config.json"
du -sh "$MLC_OUT"
