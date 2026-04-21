# Benchmark Methodology

## Text Benchmark v2

12-question suite covering reasoning, coding, format fidelity, and context retention. Each question has a fixed ground truth and a weighted score.

### Questions

| ID | Category | max_tokens | Weight | What it tests |
|---|---|---:|---:|---|
| Q1 | Time arithmetic | 64 | 1.0 | Multi-step time calculation |
| Q2 | Constraint logic | 64 | 1.0 | Deductive reasoning with constraints |
| Q3 | Code writing | 256 | 1.0 | Functional code generation |
| Q4 | Code debugging | 256 | 1.0 | Bug identification and fix |
| Q5 | Strict JSON output | 64 | 1.5 | Format fidelity — raw JSON, no fences |
| Q6 | Unit conversion | 128 | 1.0 | Multi-step arithmetic |
| Q7 | Calibrated uncertainty | 64 | 1.5 | Confidence on genuinely unknown facts |
| Q8 | Fixed-date context | 128/turn | 1.0 | DST/timezone handling with given date |
| Q9 | Multi-step reasoning | 512 | 1.5 | Extended logical chain |
| Q10 | Summarization | 256 | 0.5 | Concise accurate summary |
| Q11 | Structured output | 512 | 1.25 | Format + correctness combined |
| Q12 | Calibrated uncertainty 2 | 128 | 1.5 | Second confidence calibration task |

### Scoring

- `5/5` (old scale) or `10/10` (v3 scale): exact correct answer in expected format
- `3/5` or `7/10`: answer contains correct token but adds noise or misses formatting
- `1/5` or `1-4/10`: wrong answer or major format failure

### Request Settings (for reproducibility)

```json
{
  "temperature": 0.1,
  "top_p": 0.9,
  "seed": 42,
  "repeat_penalty": 1.0,
  "stream": false
}
```

`seed` and `repeat_penalty` must be set explicitly — Ollama and llama-server defaults differ.

### Known Failure Patterns

| Pattern | ID | Impact |
|---|---|---|
| Strict JSON format (fenced block instead of raw) | Q5 | Breaks downstream parsers |
| DST-direction or context-time drift | Q8 | Wrong timezone answers |
| Overconfident on unknown facts | Q7, Q12 | False precision |
| Token bloat on open responses | Q3, Q9–Q11 | Higher latency |

Q5 strict JSON failure is a **model behavior**, not a quantization artifact. It fails across all tested quants of Gemma 4 E2B.

---

## Vision Benchmark v2

10-question suite with deterministic ground truth. All test images are synthetically generated (no ambiguous real-world photos).

See [`vision-benchmark-suite-v2.md`](vision-benchmark-suite-v2.md) for full test definitions.

### Scoring

- `5`: exact answer
- `3`: answer contains right token but adds noise or misses formatting
- `1`: wrong answer

### Known Failure Patterns

| Pattern | Tests | Notes |
|---|---|---|
| Selective counting (count X, ignore Y) | V1, V6 | Model counts all objects, ignores attribute filter |
| OCR character confusion | V3, V10 | I/l confusion in certain fonts |

---

## Hardware State for Benchmarks

All results assume:
- Power mode: `RIMROCK_TOKENS` (nvpmodel ID=3)
- CPU: locked 1728 MHz
- GPU: locked 1020 MHz
- EMC: locked 3199 MHz via bpmp

Results from other clock states are not comparable. See [`../power/README.md`](../power/README.md).
