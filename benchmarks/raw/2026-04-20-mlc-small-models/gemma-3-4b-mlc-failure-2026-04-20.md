# Gemma 3 4B MLC Failure - 2026-04-20

## Model

`HF://mlc-ai/gemma-3-4b-it-q4f16_1-MLC`

## Runtime

`dustynv/mlc:0.20.0-r36.4.0`

## Result

The model downloaded and compiled far enough that memory did not appear to be the first blocker. Generation then failed with a tokenizer/runtime mismatch.

## Key error

```text
InternalError: token_id < token_table_.size() (262207 vs. 262145)
```

## Interpretation

This was not a clean out-of-memory failure. The current MLC container/runtime appears unable to handle one or more token IDs emitted by this Gemma 3 4B package.

Practical outcome: Gemma 3 4B was not usable in the April 20 MLC test path on Rimrock.

## Follow-up

Re-test only after one of these changes:

- rebuild MLC from a newer `mlc-ai/mlc-llm` and `mlc-ai/relax` stack
- use a newer Jetson-compatible MLC container
- test the same model family through llama.cpp/GGUF or another backend
