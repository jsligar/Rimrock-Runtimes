# Unified Model Benchmark Report (Claude NAS)

Generated: 2026-04-08
Scope: Consolidated text, thinking/tools, and vision benchmark data from Claude NAS benchmark markdown reports.

## Source Inventory

Primary benchmark reports consolidated:

- benchmark-report-gemma4-e2b-local-2026-04-03.md
- benchmark-report-gemma4-e2b-rimrock-2026-04-04.md
- benchmark-report-gemma4-e2b-rimrock-2026-04-04-ctx8192.md
- benchmark-report-gemma4-e4b-rimrock-2026-04-04.md
- benchmark-report-gemma4-e2b-flavors-rimrock-2026-04-04.md
- benchmark-report-gemma4-e2b-q4km-publishers-rimrock-2026-04-07.md
- benchmark-report-gemma4-e2b-sowilow-tuning-rimrock-2026-04-07.md
- benchmark-report-gemma4-iq4xs-rimrock-llamaserver-2026-04-07.md
- benchmark-report-nemotron3-nano-4b-rimrock-2026-04-07.md
- benchmark-report-nemotron3-nano-4b-tuning-rimrock-2026-04-07.md
- benchmark-report-phi4-mini-rimrock-2026-04-07.md
- model-benchmarks-v2.md
- model-benchmarks.md
- vision-benchmarks-v2.md
- vision-benchmarks.md

## Executive Summary

- Best text quality on Rimrock: Nemotron-3-Nano-4B (5.0/5), but slower at about 14.9 tok/s.
- Best speed-quality balance on Rimrock: Gemma 4 E2B Q4_K_M variants, especially sowilow build (4.6/5 at about 26.3 tok/s).
- Most consistent recurring failure across Gemma runs: Q5 strict JSON format fidelity (fenced JSON output).
- Strongest practical deployment split:
  - Quality-first default: Nemotron-3-Nano-4B
  - Latency-first fallback: Gemma4 E2B sowilow
- Phi-4-mini is not competitive in this test set on Rimrock (3.4/5, 12.9 tok/s).

## Unified Text Benchmark Leaderboard (v2)

| Model / Build | Machine | Runtime | Context | Avg Score | Avg Tok/s | Output Tokens | Q5 JSON | Q8 Fixed-Date Context | Notes |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| nemotron3-nano-4b | Rimrock | llama-server | 4096 | 5.0 | 14.88 | 1946 | 5 | 5 | Best text quality, exact JSON pass, calibrated uncertainty |
| gemma4-e2b-sowilow (Q4_K_M) | Rimrock | llama-server | 8192 | 4.6 | 26.34 | 4724 | 1 | 5 | Best Gemma publisher build in comparison |
| gemma4:e2b (local baseline) | Justin-PC | Ollama | n/a | 4.6 | 30.36 | 4894 | 1 | 5 | Strong local baseline |
| gemma4-e2b-bartowski (Q4_K_M) | Rimrock | llama-server | 8192 | 4.4 | 25.76 | 5030 | 1 | 3 | Slower among compared Q4_K_M builds |
| gemma4-e2b-daniloreddy (Q4_K_M) | Rimrock | llama-server | 8192 | 4.4 | 26.37 | 5060 | 1 | 5 | Q7 calibration regression (high confidence unknown) |
| gemma4-e2b:iq4xs | Rimrock | llama-server | 4096 | 4.4 | 28.70 | 5082 | 1 | 3 | Fast, but context/timezone miss persists |
| gemma4:e2b Q4_K_M (run 2026-04-04) | Rimrock | llama-server | 4096 | 4.4 | 25.9 | 6202 | 5 | 3 | Strong coding and logic; DST-direction miss |
| gemma4:e2b Q4_K_M (run 2026-04-04) | Rimrock | llama-server | 8192 | 4.4 | 27.4 | 5802 | 1 | 3 | Better Q10 than 4096 run; Q5 regressed |
| gemma4:e4b Q3_K_M | Rimrock | llama-server | 8192 | 4.4 | 10.5 | 4934 | 1 | 5 | Matches score but much slower than E2B |
| gemma4-e2b-lmstudio (Q4_K_M) | Rimrock | llama-server | 8192 | 4.2 | 26.40 | 5163 | 1 | 3 | Weakest of publisher comparison |
| phi4-mini | Rimrock | llama-server | 8192 | 3.4 | 12.88 | 617 | 1 | 3 | Not competitive in this suite |

Notes:
- Output token totals are from reported run totals where available, or summed from per-question rows where reported.
- Q8 is the fixed-date context retention task in the v2 suite.

## Gemma E2B Quantization Flavor Matrix (Rimrock)

Data from the dedicated flavor comparison report.

### Context 8192

| Quant | Avg Score | Tok/s | Size | Peak RAM | Q7 | Q8 |
|---|---:|---:|---:|---:|---:|---:|
| Q3_K_M | 4.6 | 15 | 2.4 GB | about 4 GB | 5 | 5 |
| IQ4_XS | 4.2 | 27 | 2.8 GB | about 4.5 GB | 3 | 3 |
| Q4_K_M | 4.4 | 27 | 3.0 GB | about 4.7 GB | 5 | 3 |
| Q5_K_M | 4.4 | 24 | 3.2 GB | about 5 GB | 5 | 3 |
| Q6_K | 4.6 | 20 | 4.2 GB | about 6 GB | 5 | 5 |
| Q8_0 | 4.4 | 18 | 4.8 GB | 7.1 GB (93%) | 5 | 3 |

### Context 4096

| Quant | Avg Score | Tok/s | Q7 | Q8 | Key Read |
|---|---:|---:|---:|---:|---|
| Q3_K_M | 4.4 | 15 | 5 | 3 | Stable quality floor above IQ2 |
| IQ4_XS | 4.4 | 27 | 5 | 3 | Fast but no quality edge over Q4_K_M |
| Q4_K_M | 4.4 | 27 | 5 | 3 | Daily-use balance pick |
| Q5_K_M | 4.6 | 24 | 5 | 5 | Best 4096 quality in this subset |
| Q6_K | 4.4 | 20 | 5 | 3 | Slower, no net advantage at 4096 |
| Q8_0 | 4.2 | 18 | 3 | 3 | Memory-heavy and lower score |
| UD-IQ2_M | 3.4 | 20 | 5 | 3 | Quality floor collapse at near 2-bit |

Key flavor conclusions:
- Q5 strict JSON failure is model behavior across quants, not solved by quant choice.
- DST handling (Q8) differentiates quants more than expected.
- Q4_K_M remains the best practical balance for interactive use on Rimrock.
- Q8_0 profile is unsafe for mixed workloads due to high RAM pressure.

## Publisher Build Comparison (Gemma4 E2B Q4_K_M)

| Build | Avg | Tok/s | Output Tokens | Strengths | Weaknesses |
|---|---:|---:|---:|---|---|
| sowilow | 4.6 | 26.34 | 4724 | Best score in batch, least bloat, Q8 pass | Q5 still fails |
| bartowski | 4.4 | 25.76 | 5030 | Stable overall | Q8 DST miss |
| daniloreddy | 4.4 | 26.37 | 5060 | Q8 pass | Q7 confidence calibration miss |
| lmstudio-community | 4.2 | 26.40 | 5163 | Similar speed | Q4 debugging drift + Q8 miss |

Recommendation from this batch: use sowilow as the default Q4_K_M publisher build.

## Nemotron Deep-Dive

Model: NVIDIA-Nemotron-3-Nano-4B-Q4_K_M

- Best score in current Rimrock sweep: 5.0/5.
- Speed: about 14.9 tok/s (slower than tuned Gemma E2B at about 26.3 tok/s).
- Output compactness: much lower token bloat than Gemma runs.
- Reproducibility: seeded rerun under nsys held 5.0/5.

Best server profile observed:

- -ngl 99
- -c 4096
- -t 6 -tb 6
- --threads-http 1
- -np 1 --no-cont-batching
- -b 1024 -ub 512
- --flash-attn on
- --cache-type-k q4_0 --cache-type-v q4_0
- --prio 2 --prio-batch 2
- --cache-ram 0

Tuning note:
- Lower-temperature profile (temp 0.05, top_p 0.9, seed 42) reduced quality to 4.8/5 due to Q8 regression.
- Keep default benchmark sampling (temp 0.1, top_p 0.9).

## Gemma E2B Tuning Summary (sowilow)

Best stable runtime profile on Rimrock:

- -ngl 99
- -t 6 -tb 6
- --threads-http 1
- -np 1 --no-cont-batching
- -b 1024 -ub 1024
- --flash-attn on
- --cache-type-k q8_0 --cache-type-v q8_0
- --prio 2 --prio-batch 2
- --cache-ram 0

Observed behavior:
- Throughput ceiling remained around 26.3 to 26.5 tok/s regardless of aggressive flag tweaks.
- Latency changes mainly track output token count, not decode ceiling.
- 8192 context provided strongest quality balance in this tuning run.
- 65536 context was surprisingly affordable for this model but somewhat wordier.

## Gemma E4B vs E2B

- E4B Q3_K_M on Rimrock: 4.4/5 at about 10.5 tok/s.
- E2B Q4_K_M on Rimrock: 4.4/5 at about 27 tok/s.
- Practical outcome: E2B offers similar score at about 2.6x speed advantage on this hardware.
- E4B did fix the Q8 DST-direction issue in the cited run, but still failed Q5 strict JSON and regressed on Q7 confidence calibration.

## Phi-4-mini Result

- Score: 3.4/5.
- Speed: about 12.9 tok/s.
- Stability caveat: required --flash-attn off on this llama.cpp build.
- Major misses: Q2 logic, Q5 format fidelity, Q7 calibration, and Q8 context robustness.

Conclusion: not recommended for this benchmark target compared to Gemma E2B or Nemotron.

## Vision Benchmark Consolidation

### Vision suite (original)

| Model | Machine | Avg | Notes |
|---|---|---:|---|
| gemma4:e2b | Justin-PC | 4.5 | V3 OCR confusion (I/l) |
| Gemma 4 E2B Q6_K | Rimrock | 5.0 | Perfect score |
| Gemma 4 E4B UD-Q4_K_XL | Rimrock | 5.0 | Perfect score |

### Vision suite v2

- Reported detailed v2 score available for gemma4:e2b local run: 4.2/5.
- Main failure pattern in that run: selective and attribute-based counting (V1 and V6).
- OCR, table lookup, and structured reading tasks remained strong.

## Thinking and Tools Consolidation

From benchmark records:

- Gemma4 E2B local (v2 thinking/tools):
  - Thinking plain: 4/6
  - Thinking enabled: 6/6
  - Tools: 4/7 with over-calling known-fact queries
- Earlier suite records also show model-level tool over-triggering patterns (TL4 and TL5 style misses) across Gemma families.

Practical read:
- Thinking mode can materially help exact-answer reasoning in selected tasks.
- Tool discipline remains a known weak spot versus answer correctness.

## Cross-Run Failure Pattern Index

| Pattern | Models Affected | Severity | Operational Impact | Suggested Mitigation |
|---|---|---|---|---|
| Q5 fenced JSON instead of strict raw JSON | Most Gemma runs | High | Breaks parsers and downstream automation | Add strict output parser/retry and hard no-fence instruction |
| Q8 DST-direction or context-time conversion drift | Several Gemma builds, phi4-mini | Medium | Time-sensitive task errors | Add explicit fixed-date timezone conversion post-check |
| Q7 confidence miscalibration for unknowns | Some Gemma variants, phi4-mini | Medium | Overconfident uncertain answers | Add uncertainty-format validator in eval harness |
| Tool over-triggering for known facts | Gemma runs in tool tests | Medium | Extra latency/API calls | Add tool-router guardrails and post-hoc rejection |
| Token bloat on open responses | Gemma variants | Medium | Higher latency and cost | Cap max tokens, tune sampling, enforce concise format |

## Recommended Production Profiles

### 1) Quality-First

- Model: nemotron3-nano-4b
- Runtime profile: 4096 q4_0 KV tuned profile
- Use when: structured output correctness and benchmark-grade precision matter most

### 2) Latency-First

- Model: gemma4-e2b-sowilow (Q4_K_M)
- Runtime profile: tuned single-slot llama-server profile at 8192 context
- Use when: interactive speed is the top priority and occasional strict-format retries are acceptable

### 3) Not Recommended as Primary

- phi4-mini on current Rimrock stack
- Reason: lower score and weaker reliability on key benchmark constraints

## Final Consolidated Conclusion

- The benchmark evidence supports a two-model strategy on Rimrock:
  - Nemotron for best correctness and structure adherence.
  - Gemma E2B sowilow for best responsiveness.
- The largest quality risks are now concentrated in format fidelity and deterministic time-context handling, not raw coding or baseline reasoning.
- If the benchmark suite is used as a deployment gate, enforce automatic checks for Q5-style strict formatting and Q8-style fixed-date timezone correctness.

