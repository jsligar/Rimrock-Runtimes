#!/usr/bin/env bash
set -euo pipefail

DATA="${DATA:-/home/jsligar/jetson-containers/data}"
MLC_CACHE="${MLC_CACHE:-/home/jsligar/jetson-containers/data/models/mlc/root_cache}"
MLC_PACKAGE="${MLC_PACKAGE:-/home/jsligar/jetson-containers/packages/llm/mlc}"
NAS="${NAS:-/mnt/claude-nas}"
ADAPTER="${ADAPTER:-/home/jsligar/mlc_text_benchmark_from_nas.py}"
IMAGE="${IMAGE:-dustynv/mlc:0.20.0-r36.4.0}"

run_raw() {
  local model="$1"
  local tokens="$2"
  local prompts="$3"
  local save="$4"

  sudo docker run --rm --runtime nvidia --network host --ipc host \
    -v "$DATA:/data" \
    -v "$MLC_CACHE:/root/.cache/mlc_llm" \
    -v "$MLC_PACKAGE:/test" \
    -w /test \
    "$IMAGE" \
    python3 benchmark.py \
      --model "$model" \
      --max-new-tokens "$tokens" \
      --max-num-prompts "$prompts" \
      --prompt /data/prompts/completion_16.json \
      --max-context-len 2048 \
      --prefill-chunk-size 512 \
      --save "/data/benchmarks/$save"
}

run_text() {
  local model="$1"
  local tokens="$2"
  local save="$3"

  sudo docker run --rm --runtime nvidia --network host --ipc host \
    -v "$DATA:/data" \
    -v "$MLC_CACHE:/root/.cache/mlc_llm" \
    -v "$NAS:/mnt/claude-nas:ro" \
    -v "$ADAPTER:/bench/mlc_text_benchmark_from_nas.py:ro" \
    -w /bench \
    "$IMAGE" \
    python3 /bench/mlc_text_benchmark_from_nas.py \
      --model "$model" \
      --nas-path /mnt/claude-nas \
      --max-tokens "$tokens" \
      --context-window 2048 \
      --prefill-chunk-size 512 \
      --save "/data/benchmarks/$save"
}

run_raw HF://dusty-nv/SmolLM2-360M-Instruct-q4f16_ft-MLC 128 4 smollm2-360m-mlc-rawspeed-ctx2048-prefill512.csv
run_raw HF://dusty-nv/SmolLM2-1.7B-Instruct-q4f16_ft-MLC 128 4 smollm2-1.7b-mlc-rawspeed-ctx2048-prefill512.csv
run_text HF://dusty-nv/SmolLM2-1.7B-Instruct-q4f16_ft-MLC 192 smollm2-1.7b-mlc-text-benchmark-v2.json

run_raw HF://mlc-ai/gemma-3-1b-it-q4f16_1-MLC 128 4 gemma-3-1b-it-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv
run_text HF://mlc-ai/gemma-3-1b-it-q4f16_1-MLC 192 gemma-3-1b-it-q4f16_1-mlc-text-benchmark-v2-ctx2048.json

run_raw HF://mlc-ai/gemma-3-1b-it-q0f16-MLC 128 4 gemma-3-1b-it-q0f16-mlc-rawspeed-ctx2048-prefill512.csv
run_text HF://mlc-ai/gemma-3-1b-it-q0f16-MLC 128 gemma-3-1b-it-q0f16-mlc-text-benchmark-v2-ctx2048-prefill512.json

run_raw HF://mlc-ai/Qwen3-8B-q4f16_1-MLC 96 2 qwen3-8b-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv
run_text HF://mlc-ai/Qwen3-8B-q4f16_1-MLC 96 qwen3-8b-q4f16_1-mlc-text-benchmark-v2-ctx2048-prefill512-tok96.json
