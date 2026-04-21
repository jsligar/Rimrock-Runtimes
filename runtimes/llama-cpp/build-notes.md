# llama.cpp Build Notes

## Active Build

| | |
|---|---|
| Binary | `/opt/llama.cpp/build/bin/llama-server` |
| Build number | 8664 |
| Commit | `9c699074c97191754c8a966298f84c79f90fce38` |
| Commit date | 2026-04-04 |
| Source | `https://github.com/ggml-org/llama.cpp` |
| Source path | `/opt/llama.cpp/` |

## Why a Custom Build

The published `dustynv/llama_cpp:r36.4.0` container (build 4579, January 2025) does not support:
- Gemma 4 architecture (`gemma4` GGUF type)
- Nemotron-H architecture
- Recent flash attention improvements for SM87

Build 8664 was compiled from the April 2026 tip of the llama.cpp repo to get Gemma 4 support and the latest Jetson-compatible optimizations.

## Build Command

```bash
cd /opt/llama.cpp
cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=87 \
  -DLLAMA_CURL=OFF
cmake --build build --config Release -j$(nproc)
```

Key flags:
- `DGGML_CUDA=ON` — enables CUDA backend (required for GPU offload)
- `DCMAKE_CUDA_ARCHITECTURES=87` — targets SM87 (Jetson Orin Nano Super Ampere)
- `DLLAMA_CURL=OFF` — disables curl dependency (not needed on this device)

## Features Confirmed Working

- Gemma 4 E2B / E4B (`gemma4` architecture)
- Nemotron-3-Nano-4B (`nemotronh` architecture)
- Flash attention (`--flash-attn on`) — SM87 supported
- Multimodal / mmproj (`--mmproj`) — vision encoder loading
- CUDA KV cache quantization (`--cache-type-k q8_0`, `q4_0`)
- GPU priority (`--prio`, `--prio-batch`)
- Reasoning control (`--reasoning off`, `--reasoning-budget`, `--reasoning-format`)
- Sliding window attention (Gemma 4 hybrid SWA/full layers)

## Notable Recent Commits in This Build

- `9c699074` — Fix undefined timing measurement errors in server context
- `650bf14e` — Read `final_logit_softcapping` for Gemma 4
- `d01f6274` — Respect specified tag in common

## Do Not Use

`dustynv/llama_cpp:r36.4.0` (build 4579) — predates Gemma 4 support entirely. Will fail to load any `gemma4` GGUF.
