#!/bin/bash
# Nemotron-3-Nano-4B — quality-first, text-only, ctx=4096
# 5.0/5 benchmark score at ~14.9 tok/s
# Use when structured output correctness matters more than speed

MODEL=/opt/models/nemotron3-nano-4b/Nemotron3-Nano-4B-Q4_K_M.gguf
LOG=/tmp/llama-server.log

exec /opt/llama.cpp/build/bin/llama-server \
  -m "$MODEL" \
  -ngl 99 -c 4096 -t 6 -tb 6 \
  --threads-http 1 -np 1 --no-cont-batching \
  -b 1024 -ub 512 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --prio 2 --prio-batch 2 \
  --cache-ram 0 \
  --host 0.0.0.0 --port 8424 \
  2>&1 | tee "$LOG"
