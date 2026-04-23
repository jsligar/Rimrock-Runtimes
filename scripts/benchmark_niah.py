#!/usr/bin/env python3
"""
Needle-in-a-Haystack (NIAH) Long Context Benchmark
====================================================
Tests whether the model actually uses long context — not just accepts large CTX.

Questions:
  Q1  Needle retrieval     — exact string buried in filler
  Q2  Cross-context math   — two facts from opposite ends, requires arithmetic
  Q3  Instruction drift    — early formatting rule obeyed after massive filler
  Q4  Contradiction/recency — stale vs updated fact, latest must win

For each question, runs at multiple context depths defined by --sizes.
Reports: pass/fail, actual response, elapsed time, tok/s.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib import request

DEFAULT_HOST  = "http://172.16.0.248:8424"
DEFAULT_MODEL = "gemma-4-e2b-it-q4_k_m.gguf"
DEFAULT_SIZES = [4096, 16384, 32768, 65536, 131072]

# ---------------------------------------------------------------------------
# Filler generator
# ---------------------------------------------------------------------------

_FILLER_SENTENCES = [
    "The diagnostic subsystem completed its sweep without anomalies.",
    "All sensor readings remain within nominal operating bounds.",
    "The thermal profile of sector four shows no deviation from baseline.",
    "Firmware version 3.1.7 has been validated against the test matrix.",
    "The memory allocator released 2048 bytes back to the heap.",
    "Checksum verification passed on all transmitted data frames.",
    "The scheduler placed task 0x4A into the ready queue.",
    "Bus arbitration resolved in favor of device node twelve.",
    "The watchdog timer was refreshed at cycle boundary 0xFF00.",
    "Log entry 8841: no faults recorded in the previous interval.",
    "Power rail B settled at 3.299 V within the 1% tolerance window.",
    "Cache invalidation completed for address range 0x8000–0x9FFF.",
    "The state machine transitioned from IDLE to ACTIVE on trigger pulse.",
    "Acknowledgement received from remote node after 14 ms round-trip.",
    "Peripheral DMA transfer completed: 512 bytes moved to buffer.",
]

_WORDS_PER_SENTENCE = 12  # rough average
_TOKENS_PER_WORD    = 1.3  # rough token/word ratio for this filler


def _filler_tokens_approx(n_sentences: int) -> int:
    return int(n_sentences * _WORDS_PER_SENTENCE * _TOKENS_PER_WORD)


def make_filler(target_tokens: int) -> str:
    """Return a block of filler text ≈ target_tokens long."""
    sentences_needed = max(1, int(target_tokens / (_WORDS_PER_SENTENCE * _TOKENS_PER_WORD)))
    lines = []
    for i in range(sentences_needed):
        lines.append(_FILLER_SENTENCES[i % len(_FILLER_SENTENCES)])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _build_q1(target_tokens: int, needle_offset_fraction: float = 0.1) -> tuple[str, str]:
    """
    Q1 — Needle retrieval.
    Buries 'The control code is: 7XQ-419-BETA' at needle_offset_fraction into filler.
    Returns (user_message, expected_answer).
    """
    overhead = 80  # approximate tokens for wrapper + question
    filler_tokens = max(0, target_tokens - overhead)
    needle_pos = int(filler_tokens * needle_offset_fraction)
    before = make_filler(needle_pos)
    after  = make_filler(filler_tokens - needle_pos)
    needle = "The control code is: 7XQ-419-BETA"
    content = (
        f"{before}\n\n"
        f"[SYSTEM NOTE] {needle}\n\n"
        f"{after}\n\n"
        f"--- END OF DOCUMENT ---\n\n"
        f"What was the control code mentioned earlier in the document?"
    )
    return content, "7XQ-419-BETA"


def _build_q2(target_tokens: int) -> tuple[str, str]:
    """
    Q2 — Cross-context math.
    Pump A info at start, pump B info shortly after, runtime at the very end.
    Answer: (12+18)*15 = 450 L
    """
    overhead = 120
    filler_tokens = max(0, target_tokens - overhead)
    # Early block: ~5% in
    early_end  = int(filler_tokens * 0.05)
    # Late block: ~90% in
    late_start = int(filler_tokens * 0.90)
    mid = late_start - early_end

    before_early = make_filler(early_end)
    middle       = make_filler(mid)
    after_late   = make_filler(filler_tokens - late_start)

    content = (
        f"{before_early}\n\n"
        f"[SPEC SHEET — Fluid Systems]\n"
        f"Pump A flow rate: 12 L/min\n"
        f"Pump B flow rate: 18 L/min\n\n"
        f"{middle}\n\n"
        f"[OPERATIONS LOG]\n"
        f"The system runs both pumps simultaneously for 15 minutes.\n\n"
        f"{after_late}\n\n"
        f"--- END OF DOCUMENT ---\n\n"
        f"Based on the spec sheet and operations log above, "
        f"what is the total volume of fluid moved during the run? "
        f"Reply with the number only, in litres. No explanation."
    )
    return content, "450"


def _build_q3(target_tokens: int) -> tuple[str, str]:
    """
    Q3 — Instruction drift.
    Places formatting rule at the very start, then dumps filler.
    """
    overhead = 80
    filler_tokens = max(0, target_tokens - overhead)
    filler = make_filler(filler_tokens)
    content = (
        f"[IMPORTANT INSTRUCTION — READ BEFORE ANYTHING ELSE]\n"
        f"Always answer in exactly 3 words. No more, no less.\n\n"
        f"{filler}\n\n"
        f"--- END OF DOCUMENT ---\n\n"
        f"Explain why the sky appears blue."
    )
    # Any 3-word answer counts as pass
    return content, "__THREE_WORDS__"


def _build_q4(target_tokens: int) -> tuple[str, str]:
    """
    Q4 — Contradiction/recency.
    Stale IP early, updated IP late. Correct answer = 10.0.0.5
    """
    overhead = 100
    filler_tokens = max(0, target_tokens - overhead)
    early_end  = int(filler_tokens * 0.05)
    late_start = int(filler_tokens * 0.92)
    mid = late_start - early_end

    before_early = make_filler(early_end)
    middle       = make_filler(mid)
    after_late   = make_filler(filler_tokens - late_start)

    content = (
        f"{before_early}\n\n"
        f"[NETWORK CONFIG v1]\n"
        f"The server IP is 192.168.1.10\n\n"
        f"{middle}\n\n"
        f"[NETWORK CONFIG v2 — UPDATE]\n"
        f"Update: The server IP has changed to 10.0.0.5\n\n"
        f"{after_late}\n\n"
        f"--- END OF DOCUMENT ---\n\n"
        f"What is the current server IP address?"
    )
    return content, "10.0.0.5"


QUESTIONS = {
    "Q1": ("Needle Retrieval",      _build_q1),
    "Q2": ("Cross-Context Math",    _build_q2),
    "Q3": ("Instruction Drift",     _build_q3),
    "Q4": ("Contradiction/Recency", _build_q4),
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score(qid: str, response: str, expected: str) -> tuple[bool, str]:
    r = response.strip()
    if qid == "Q1":
        passed = "7XQ-419-BETA" in r
        return passed, "7XQ-419-BETA" if passed else "missing needle"
    if qid == "Q2":
        # look for 450 anywhere (could be "450 L", "450 litres", etc.)
        passed = bool(re.search(r"\b450\b", r))
        return passed, "450 L" if passed else f"got: {r[:80]}"
    if qid == "Q3":
        words = r.split()
        passed = len(words) == 3
        return passed, f"{len(words)} words: '{r[:60]}'"
    if qid == "Q4":
        has_new = "10.0.0.5" in r
        has_old = "192.168.1.10" in r
        if has_new and not has_old:
            return True, "10.0.0.5 (correct)"
        if has_old and not has_new:
            return False, "192.168.1.10 (stale)"
        if has_new and has_old:
            return False, "both IPs present — ambiguous"
        return False, f"neither IP found: {r[:80]}"
    return False, "unknown qid"


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def chat(host: str, model: str, user_content: str, max_tokens: int = 200, timeout: int = 300) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_content}],
        "stream": False,
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": max_tokens,
    }
    req = request.Request(
        f"{host}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode())
    elapsed = time.perf_counter() - t0

    usage   = data.get("usage", {})
    timings = data.get("timings", {})
    completion_tokens = usage.get("completion_tokens", 0)
    predicted_ms      = timings.get("predicted_ms", 0)
    prompt_ms         = timings.get("prompt_ms", 0)
    prompt_tokens     = usage.get("prompt_tokens", 0)

    tok_s = round(completion_tokens / (predicted_ms / 1000), 2) if completion_tokens and predicted_ms else None
    prefill_tok_s = round(prompt_tokens / (prompt_ms / 1000), 1) if prompt_tokens and prompt_ms else None

    return {
        "content":       data["choices"][0]["message"].get("content", "").strip(),
        "elapsed_s":     round(elapsed, 2),
        "tok_s":         tok_s,
        "prefill_tok_s": prefill_tok_s,
        "prompt_tokens": prompt_tokens,
        "output_tokens": completion_tokens,
        "prompt_ms":     round(prompt_ms / 1000, 1),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="NIAH Long Context Benchmark")
    parser.add_argument("--host",  default=DEFAULT_HOST)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sizes", nargs="+", type=int, default=DEFAULT_SIZES,
                        help="Context sizes to test (tokens)")
    parser.add_argument("--questions", nargs="+", default=list(QUESTIONS.keys()),
                        choices=list(QUESTIONS.keys()),
                        help="Which questions to run (default: all)")
    parser.add_argument("--out-dir", default="benchmarks",
                        help="Directory to write results JSON")
    parser.add_argument("--runtime-label", default="llama-server",
                        help="Tag for the runtime being tested")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"niah-results-{args.runtime_label}-{timestamp}.json"

    print(f"NIAH Benchmark — {args.runtime_label}")
    print(f"Host:  {args.host}")
    print(f"Model: {args.model}")
    print(f"Sizes: {args.sizes}")
    print(f"Questions: {args.questions}")
    print()

    results: list[dict] = []

    for qid in args.questions:
        qname, builder = QUESTIONS[qid]
        print(f"{'='*60}")
        print(f"{qid} — {qname}")
        print(f"{'='*60}")

        for ctx_size in args.sizes:
            print(f"  ctx={ctx_size:>7,} tokens ... ", end="", flush=True)
            try:
                user_content, expected = builder(ctx_size)
                req_timeout = max(300, ctx_size // 50)
                result = chat(args.host, args.model, user_content, timeout=req_timeout)
                passed, detail = score(qid, result["content"], expected)

                status = "PASS ✓" if passed else "FAIL ✗"
                print(f"{status}  {result['prompt_tokens']:>7} prompt tokens  "
                      f"prefill={result['prefill_tok_s']} t/s  "
                      f"decode={result['tok_s']} t/s  "
                      f"elapsed={result['elapsed_s']}s")
                print(f"           detail: {detail}")

                results.append({
                    "qid":            qid,
                    "question":       qname,
                    "target_ctx":     ctx_size,
                    "actual_prompt_tokens": result["prompt_tokens"],
                    "passed":         passed,
                    "detail":         detail,
                    "response":       result["content"][:300],
                    "elapsed_s":      result["elapsed_s"],
                    "tok_s":          result["tok_s"],
                    "prefill_tok_s":  result["prefill_tok_s"],
                    "prompt_ms":      result["prompt_ms"],
                    "output_tokens":  result["output_tokens"],
                })

            except Exception as e:
                print(f"ERROR: {e}")
                results.append({
                    "qid": qid, "question": qname,
                    "target_ctx": ctx_size, "passed": False,
                    "detail": f"exception: {e}", "error": str(e),
                })

        print()

    # Summary table
    print(f"{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Q':<4} {'CTX':>8} {'Pass':<6} {'Prefill t/s':>12} {'Decode t/s':>11} {'Detail'}")
    print(f"{'-'*4} {'-'*8} {'-'*6} {'-'*12} {'-'*11} {'-'*30}")
    for r in results:
        if "error" in r:
            print(f"{r['qid']:<4} {r['target_ctx']:>8,}  ERROR   {r['error'][:50]}")
            continue
        mark = "✓" if r["passed"] else "✗"
        pre  = f"{r['prefill_tok_s']}" if r.get("prefill_tok_s") else "—"
        dec  = f"{r['tok_s']}"          if r.get("tok_s")         else "—"
        print(f"{r['qid']:<4} {r['target_ctx']:>8,}  {mark:<6} {pre:>12} {dec:>11}  {r['detail'][:50]}")

    # Pass rate per question
    print()
    for qid in args.questions:
        qruns = [r for r in results if r["qid"] == qid and "error" not in r]
        passed = sum(1 for r in qruns if r["passed"])
        print(f"  {qid}: {passed}/{len(qruns)} passed")

    # Write JSON
    out_path.write_text(json.dumps({
        "meta": {
            "timestamp": timestamp,
            "runtime_label": args.runtime_label,
            "host": args.host,
            "model": args.model,
            "sizes": args.sizes,
            "questions": args.questions,
        },
        "results": results,
    }, indent=2))
    print(f"\nResults: {out_path}")


if __name__ == "__main__":
    main()
