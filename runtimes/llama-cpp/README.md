# llama.cpp — llama-server

**Status: Production**

## Build

| | |
|---|---|
| Binary | `/opt/llama.cpp/build/bin/llama-server` |
| Build | 8664 (commit `9c699074c`) |
| Built from | source (local build on Rimrock) |
| Flash Attention | enabled (SM87 supported) |
| Gemma 4 support | yes — `gemma4` architecture, multimodal, per-layer embeddings |
| Nemotron-H support | yes |

> **Note:** `dustynv/llama_cpp:r36.4.0` (build 4579, Jan 2025) does NOT support Gemma 4 or Nemotron-H. Always use the locally built binary at `/opt/llama.cpp/build/bin/llama-server`.

## Production Config — Gemma 4 E2B Multimodal (current)

**Model:** sowilow Q4_K_M + E2B mmproj-F16  
**Context:** 32768  
**Multimodal:** text + vision (image)  
**Port:** 8424

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /opt/models/gemma4-e2b-q4km-compare/sowilow/gemma-4-e2b-it-q4_k_m.gguf \
  --mmproj /opt/models/gemma4-e2b-ud-q4xl-fresh/mmproj-F16.gguf \
  -ngl 99 -c 32768 -t 6 -tb 6 \
  --threads-http 1 -np 1 --no-cont-batching \
  -b 1024 -ub 1024 --flash-attn on \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --prio 2 --prio-batch 2 \
  --host 0.0.0.0 --port 8424
```

Startup script: [`start_llama.sh`](start_llama.sh)

### Memory at 32768 context

| Component | VRAM |
|---|---:|
| Model weights (CPU-mapped) | ~2152 MB |
| Model weights (GPU) | ~1417 MB |
| mmproj (vision encoder) | ~940 MB |
| KV cache (non-SWA, q8_0) | ~102 MB |
| KV cache (SWA, q8_0) | ~9.6 MB |
| Compute buffer | ~1037 MB |
| **Total RAM in use** | **~4.6 GB** |

Free RAM: ~2.6 GB. Thermally stable, low 50s°C under load.

### Performance

| Metric | Value |
|---|---:|
| Decode | ~26.2–26.5 tok/s |
| Prefill (text only) | ~185 tok/s |
| Prefill (with image) | ~162 tok/s |
| Image prompt tokens | ~292 tokens (320×240 JPEG) |

## Alternate Config — Nemotron-3-Nano-4B (quality-first)

```bash
/opt/llama.cpp/build/bin/llama-server \
  -m /opt/models/nemotron3-nano-4b/Nemotron3-Nano-4B-Q4_K_M.gguf \
  -ngl 99 -c 4096 -t 6 -tb 6 \
  --threads-http 1 -np 1 --no-cont-batching \
  -b 1024 -ub 512 --flash-attn on \
  --cache-type-k q4_0 --cache-type-v q4_0 \
  --prio 2 --prio-batch 2 \
  --cache-ram 0 \
  --host 0.0.0.0 --port 8424
```

~14.9 tok/s, 5.0/5 benchmark score.

## Systemd Service

Service file: `/etc/systemd/system/llama-server.service`

## Benchmark Request Settings (v3)

Used by benchmark scripts for reproducible cross-runtime comparisons:

```json
{
  "temperature": 0.1,
  "top_p": 0.9,
  "seed": 42,
  "repeat_penalty": 1.0,
  "stream": false
}
```

Per-question `max_tokens`: Q1–Q2: 64 | Q3–Q4: 256 | Q5: 64 | Q6: 128 | Q7: 64 | Q8: 128/turn | Q9: 512 | Q10: 256 | Q11: 512 | Q12: 128

## Context Window History

| Date | Context | Notes |
|---|---:|---|
| 2026-04-11 | 4096 | Original production config |
| 2026-04-21 | 32768 | Bumped — no speed penalty, 111MB KV cost |

## Known Failure Patterns

| Pattern | Severity | Mitigation |
|---|---|---|
| Q5 strict JSON (outputs fenced code block) | High | Add no-fence instruction + parser retry |
| Q8 DST-direction drift | Medium | Explicit fixed-date timezone validator |
| Q7 confidence miscalibration | Medium | Uncertainty-format validator in eval harness |
| Token bloat on open responses | Medium | Cap max_tokens, enforce concise format |
