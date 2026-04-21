# Vision Benchmark — Rimrock 2026-04-21

**Model:** Gemma 4 E2B Q4_K_M (sowilow) + mmproj-F16  
**Runtime:** llama-server build 8664  
**Context:** 32768  
**Endpoint:** http://172.16.0.248:8424

## Multimodal Confirmed Working

Seamless multimodal confirmed functional on 2026-04-21 — first time tested with the production GGUF stack and mmproj loaded simultaneously.

### Test: Coastal Sunset Scene

Input: 320×240 JPEG (random landscape from picsum.photos)

| Metric | Value |
|---|---:|
| Prompt tokens | 292–293 |
| Decode speed | 26.2–26.5 tok/s |
| Prefill speed (with image) | 162 tok/s |
| Prefill speed (text only) | 185 tok/s |

**Model output:**
> "This image captures a dramatic sunset over the ocean, featuring vibrant red and orange reflections on the water and the silhouette of land on the horizon."

Accurate description — ocean, sunset, wet sand, land silhouette, color reflections all correctly identified.

## Key Findings

- **Decode speed unchanged by vision** — 26.2 tok/s with image matches text-only baseline. mmproj adds to prefill cost, not decode.
- **Image costs ~2.2s in prefill** — 292 prompt tokens at 162 tok/s vs 185 tok/s text-only.
- **`reasoning_content` separation works** — `thinking=false` in request cleanly routes internal reasoning to `reasoning_content` field and final answer to `content`.
- **Thinking runs before answering** — at low `max_tokens`, all budget consumed by `<think>` block before output. Set `max_tokens >= 400` for single-sentence responses.
- **mmproj memory cost: ~940MB** — loaded at startup, stays resident. No per-request allocation.

## Context Window Impact on KV Cache

| Context | Non-SWA KV | SWA KV | Total KV | RAM used |
|---|---:|---:|---:|---:|
| 4096 | 12.75 MB | 9.57 MB | 22 MB | ~5.3 GB |
| 16384 | 51.00 MB | 9.57 MB | 61 MB | ~5.1 GB |
| 32768 | 102.00 MB | 9.57 MB | 111 MB | ~4.6 GB |

No decode speed penalty observed at any context size. 32768 is the recommended production setting.

## Vision Suite v2 — Pending

Full structured vision benchmark (V1–V10) not yet run against the production multimodal stack on Rimrock. See [`vision-benchmark-suite-v2.md`](vision-benchmark-suite-v2.md) for the test suite definition.

Previous vision results from Justin-PC (Ollama, gemma4:e2b local):
- Original vision suite: 4.5/5
- Vision suite v2: 4.2/5 (main failures: selective counting V1, attribute counting V6)
