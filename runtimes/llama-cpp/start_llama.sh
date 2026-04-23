#!/usr/bin/env bash
# Gemma 4 E2B multimodal launcher for locally built llama.cpp (build 8664+).
# Defaults are tuned for Rimrock single-user latency and can be overridden via env vars.
set -euo pipefail

LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-/opt/llama.cpp/build/bin/llama-server}"
MODEL="${MODEL:-/opt/models/gemma4-e2b-q4km-compare/sowilow/gemma-4-e2b-it-q4_k_m.gguf}"
MMPROJ="${MMPROJ:-/opt/models/gemma4-e2b-ud-q4xl-fresh/mmproj-F16.gguf}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8424}"
LOG="${LOG:-/tmp/llama-server-gemma4.log}"

# Core Gemma runtime knobs.
NGL="${NGL:-99}"
CTX="${CTX:-32768}"
THREADS="${THREADS:-6}"
THREADS_BATCH="${THREADS_BATCH:-6}"
THREADS_HTTP="${THREADS_HTTP:-1}"
PARALLEL="${PARALLEL:-1}"
BATCH="${BATCH:-1024}"
UBATCH="${UBATCH:-1024}"
CACHE_K="${CACHE_K:-q8_0}"
CACHE_V="${CACHE_V:-q8_0}"
PRIO="${PRIO:-2}"
PRIO_BATCH="${PRIO_BATCH:-2}"
FLASH_ATTN="${FLASH_ATTN:-on}"

# Optional reasoning controls for newer Gemma-capable builds.
REASONING="${REASONING:-off}"
REASONING_BUDGET="${REASONING_BUDGET:--1}"
REASONING_FORMAT="${REASONING_FORMAT:-none}"

if [[ ! -x "$LLAMA_SERVER_BIN" ]]; then
  echo "Missing or non-executable llama-server: $LLAMA_SERVER_BIN" >&2
  exit 1
fi

if [[ ! -f "$MODEL" ]]; then
  echo "Missing model GGUF: $MODEL" >&2
  exit 1
fi

if [[ ! -f "$MMPROJ" ]]; then
  echo "Missing mmproj GGUF: $MMPROJ" >&2
  exit 1
fi

echo "Starting Gemma 4 server"
echo "  bin:      $LLAMA_SERVER_BIN"
echo "  model:    $MODEL"
echo "  mmproj:   $MMPROJ"
echo "  host:port $HOST:$PORT"
echo "  ctx/ngl   $CTX / $NGL"
echo "  log:      $LOG"

exec "$LLAMA_SERVER_BIN" \
  -m "$MODEL" \
  --mmproj "$MMPROJ" \
  -ngl "$NGL" -c "$CTX" -t "$THREADS" -tb "$THREADS_BATCH" \
  --threads-http "$THREADS_HTTP" -np "$PARALLEL" --no-cont-batching \
  -b "$BATCH" -ub "$UBATCH" --flash-attn "$FLASH_ATTN" \
  --cache-type-k "$CACHE_K" --cache-type-v "$CACHE_V" \
  --prio "$PRIO" --prio-batch "$PRIO_BATCH" \
  --reasoning "$REASONING" --reasoning-budget "$REASONING_BUDGET" --reasoning-format "$REASONING_FORMAT" \
  --host "$HOST" --port "$PORT" \
  2>&1 | tee "$LOG"
