#!/usr/bin/env bash
# Build MLC weights + compiled lib for nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1
# on Rimrock (Jetson Orin Nano 8GB, SM87, aarch64, CUDA 12.6).
#
# Run this ON Rimrock (not on the dev machine).
#
# Prerequisites:
#   - rimrock/mlc-gemma4:latest image is available
#   - HF weights downloaded to HF_SRC (see step 0 below)
#
# Outputs:
#   /opt/models/nemotron-nano-4b-mlc/
#       params_shard_*.bin       — quantized q4f16_1 weights
#       mlc-chat-config.json     — runtime config
#       tokenizer.*              — tokenizer files
#       lib-sm87.so              — compiled CUDA kernel library for SM87
#
# Usage: sudo bash build-nemotron.sh
set -euo pipefail

HF_SRC="/opt/models/nemotron-nano-4b-hf"
MLC_OUT="/opt/models/nemotron-nano-4b-mlc"
QUANT="q4f16_1"
TARGET="cuda:0"
CONTEXT_WINDOW=4096
PREFILL_CHUNK=1024
MAX_BATCH=1

# Conservative opt flags for SM87:
#   - faster_transformer=1  (fused attention kernels, stable on Ampere)
#   - cudagraph=1           (reduces kernel launch overhead)
#   - flashinfer=0          (FlashInfer build in this image is unstable)
#   - cutlass=0             (gates on sm_90a/sm_100a, no benefit here)
#   - cublas_gemm=0         (only applies to fp32/fp8 paths, not q4f16_1)
OPT="faster_transformer=1;cudagraph=1;flashinfer=0;cutlass=0;cublas_gemm=0"

IMAGE="rimrock/mlc-gemma4:latest"

echo "=== Step 0: verify HF source weights exist ==="
if [[ ! -d "$HF_SRC" ]]; then
  echo ""
  echo "HF weights not found at $HF_SRC."
  echo "Download first:"
  echo ""
  echo "  huggingface-cli download nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1 \\"
  echo "    --local-dir $HF_SRC"
  echo ""
  exit 1
fi
echo "Source weights found at $HF_SRC"

echo ""
echo "=== Step 1: convert_weight (quantize to $QUANT) ==="
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
    --sliding-window-size -1 \
    -o /mlc-out

echo ""
echo "=== Step 3: compile ==="
sudo docker run --rm \
  --runtime nvidia \
  -v "$MLC_OUT":/mlc-out \
  "$IMAGE" \
  python3 -m mlc_llm compile /mlc-out/mlc-chat-config.json \
    --device "$TARGET" \
    --quantization "$QUANT" \
    --opt "$OPT" \
    --overrides "max_batch_size=${MAX_BATCH}" \
    -o /mlc-out/lib-sm87.so

echo ""
echo "=== Build complete ==="
echo "Output: $MLC_OUT"
echo "Library: $MLC_OUT/lib-sm87.so"
echo ""
echo "Sanity check:"
echo "  sudo docker run --rm --runtime nvidia \\"
echo "    -v $MLC_OUT:/weights \\"
echo "    $IMAGE \\"
echo "    python3 -c 'from mlc_llm import MLCEngine; e = MLCEngine(\"/weights\", model_lib=\"/weights/lib-sm87.so\", mode=\"interactive\", device=\"cuda\"); e.terminate(); print(\"OK\")'"
