# Exact Commands - MLC Small Model Sweep - 2026-04-20

Run from Rimrock. These commands use the same persistent MLC cache and benchmark data layout used during the session.

## Common paths

```bash
DATA=/home/jsligar/jetson-containers/data
MLC_CACHE=/home/jsligar/jetson-containers/data/models/mlc/root_cache
MLC_PACKAGE=/home/jsligar/jetson-containers/packages/llm/mlc
NAS=/mnt/claude-nas
ADAPTER=/home/jsligar/mlc_text_benchmark_from_nas.py
IMAGE=dustynv/mlc:0.20.0-r36.4.0
```

## SmolLM2 360M raw speed

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$MLC_PACKAGE:/test" \
  -w /test \
  "$IMAGE" \
  python3 benchmark.py \
    --model HF://dusty-nv/SmolLM2-360M-Instruct-q4f16_ft-MLC \
    --max-new-tokens 128 \
    --max-num-prompts 4 \
    --prompt /data/prompts/completion_16.json \
    --max-context-len 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/smollm2-360m-mlc-rawspeed-ctx2048-prefill512.csv
```

## SmolLM2 1.7B raw speed

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$MLC_PACKAGE:/test" \
  -w /test \
  "$IMAGE" \
  python3 benchmark.py \
    --model HF://dusty-nv/SmolLM2-1.7B-Instruct-q4f16_ft-MLC \
    --max-new-tokens 128 \
    --max-num-prompts 4 \
    --prompt /data/prompts/completion_16.json \
    --max-context-len 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/smollm2-1.7b-mlc-rawspeed-ctx2048-prefill512.csv
```

## SmolLM2 1.7B text benchmark

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$NAS:/mnt/claude-nas:ro" \
  -v "$ADAPTER:/bench/mlc_text_benchmark_from_nas.py:ro" \
  -w /bench \
  "$IMAGE" \
  python3 /bench/mlc_text_benchmark_from_nas.py \
    --model HF://dusty-nv/SmolLM2-1.7B-Instruct-q4f16_ft-MLC \
    --nas-path /mnt/claude-nas \
    --max-tokens 192 \
    --context-window 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/smollm2-1.7b-mlc-text-benchmark-v2.json
```

## Gemma 3 1B q4f16_1 raw speed

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$MLC_PACKAGE:/test" \
  -w /test \
  "$IMAGE" \
  python3 benchmark.py \
    --model HF://mlc-ai/gemma-3-1b-it-q4f16_1-MLC \
    --max-new-tokens 128 \
    --max-num-prompts 4 \
    --prompt /data/prompts/completion_16.json \
    --max-context-len 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/gemma-3-1b-it-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv
```

## Gemma 3 1B q4f16_1 text benchmark

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$NAS:/mnt/claude-nas:ro" \
  -v "$ADAPTER:/bench/mlc_text_benchmark_from_nas.py:ro" \
  -w /bench \
  "$IMAGE" \
  python3 /bench/mlc_text_benchmark_from_nas.py \
    --model HF://mlc-ai/gemma-3-1b-it-q4f16_1-MLC \
    --nas-path /mnt/claude-nas \
    --max-tokens 192 \
    --context-window 2048 \
    --save /data/benchmarks/gemma-3-1b-it-q4f16_1-mlc-text-benchmark-v2-ctx2048.json
```

## Gemma 3 1B q0f16 raw speed

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$MLC_PACKAGE:/test" \
  -w /test \
  "$IMAGE" \
  python3 benchmark.py \
    --model HF://mlc-ai/gemma-3-1b-it-q0f16-MLC \
    --max-new-tokens 128 \
    --max-num-prompts 4 \
    --prompt /data/prompts/completion_16.json \
    --max-context-len 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/gemma-3-1b-it-q0f16-mlc-rawspeed-ctx2048-prefill512.csv
```

## Gemma 3 1B q0f16 text benchmark

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$NAS:/mnt/claude-nas:ro" \
  -v "$ADAPTER:/bench/mlc_text_benchmark_from_nas.py:ro" \
  -w /bench \
  "$IMAGE" \
  python3 /bench/mlc_text_benchmark_from_nas.py \
    --model HF://mlc-ai/gemma-3-1b-it-q0f16-MLC \
    --nas-path /mnt/claude-nas \
    --max-tokens 128 \
    --context-window 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/gemma-3-1b-it-q0f16-mlc-text-benchmark-v2-ctx2048-prefill512.json
```

## Qwen3 8B q4f16_1 raw speed

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$MLC_PACKAGE:/test" \
  -w /test \
  "$IMAGE" \
  python3 benchmark.py \
    --model HF://mlc-ai/Qwen3-8B-q4f16_1-MLC \
    --max-new-tokens 96 \
    --max-num-prompts 2 \
    --prompt /data/prompts/completion_16.json \
    --max-context-len 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/qwen3-8b-q4f16_1-mlc-rawspeed-ctx2048-prefill512.csv
```

## Qwen3 8B q4f16_1 text benchmark

```bash
sudo docker run --rm --runtime nvidia --network host --ipc host \
  -v "$DATA:/data" \
  -v "$MLC_CACHE:/root/.cache/mlc_llm" \
  -v "$NAS:/mnt/claude-nas:ro" \
  -v "$ADAPTER:/bench/mlc_text_benchmark_from_nas.py:ro" \
  -w /bench \
  "$IMAGE" \
  python3 /bench/mlc_text_benchmark_from_nas.py \
    --model HF://mlc-ai/Qwen3-8B-q4f16_1-MLC \
    --nas-path /mnt/claude-nas \
    --max-tokens 96 \
    --context-window 2048 \
    --prefill-chunk-size 512 \
    --save /data/benchmarks/qwen3-8b-q4f16_1-mlc-text-benchmark-v2-ctx2048-prefill512-tok96.json
```
