#!/bin/bash
# Gemma 4 E2B — multimodal (text + vision), ctx=32768
# Model: sowilow Q4_K_M | mmproj: E2B mmproj-F16
# 26+ tok/s decode, flash-attn, KV q8_0, port 8424

MODEL=/opt/models/gemma4-e2b-q4km-compare/sowilow/gemma-4-e2b-it-q4_k_m.gguf
MMPROJ=/opt/models/gemma4-e2b-ud-q4xl-fresh/mmproj-F16.gguf
LOG=/tmp/llama-server.log

exec /opt/llama.cpp/build/bin/llama-server \
  -m "$MODEL" \
  --mmproj "$MMPROJ" \
  -ngl 99 -c 32768 -t 6 -tb 6 \
  --threads-http 1 -np 1 --no-cont-batching \
  -b 1024 -ub 1024 --flash-attn on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --prio 2 --prio-batch 2 \
  --host 0.0.0.0 --port 8424 \
  2>&1 | tee "$LOG"
