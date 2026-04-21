r"""
Text benchmark suite v3 for local LLM evaluation.

Usage (standalone Ollama):
    python text_benchmark_v3.py --model gemma4:e2b
"""
from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from typing import Callable
from urllib import request

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e2b"
SEP = "=" * 72


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def first_int(value: str) -> int | None:
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else None


def generate(prompt: str, model: str, host: str) -> dict:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False})
    req = request.Request(
        f"{host}/api/generate",
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    with request.urlopen(req, timeout=240) as response:
        result = json.loads(response.read().decode("utf-8"))
    elapsed = round(time.time() - started, 1)
    eval_count = result.get("eval_count", 0)
    eval_duration = result.get("eval_duration", 0) / 1e9
    tok_s = round(eval_count / eval_duration, 1) if eval_duration > 0 else 0.0
    return {
        "response": result.get("response", "").strip(),
        "tok_s": tok_s,
        "elapsed": elapsed,
        "eval_count": eval_count,
    }


def chat(messages: list[dict], model: str, host: str) -> dict:
    payload = json.dumps({"model": model, "messages": messages, "stream": False})
    req = request.Request(
        f"{host}/api/chat",
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.time()
    with request.urlopen(req, timeout=240) as response:
        result = json.loads(response.read().decode("utf-8"))
    elapsed = round(time.time() - started, 1)
    message = result.get("message", {})
    return {"content": message.get("content", "").strip(), "elapsed": elapsed}


@dataclass
class TextTest:
    test_id: str
    name: str
    prompt: str | None
    validator: Callable[[str], tuple[int, str]]
    expected: str
    multi_turn: bool = False


# --- Validators ---

def exact_only(expected: str) -> Callable[[str], tuple[int, str]]:
    expected_norm = normalize_text(expected)

    def _validator(answer: str) -> tuple[int, str]:
        answer_norm = normalize_text(answer)
        if answer_norm == expected_norm:
            return 5, "exact"
        if expected_norm in answer_norm:
            return 3, "contains expected with extra text"
        return 1, "wrong"

    return _validator


def validate_q3(answer: str) -> tuple[int, str]:
    answer_norm = normalize_text(answer)
    checks = ["def flatten", "isinstance", "return"]
    bonus = "extend" in answer_norm or "append" in answer_norm
    score = sum(1 for item in checks if item in answer_norm)
    if score == 3 and bonus:
        return 5, "correct recursive flatten"
    if score >= 2:
        return 3, "partial implementation"
    return 1, "missing expected code features"


def validate_q4(answer: str) -> tuple[int, str]:
    answer_norm = normalize_text(answer)
    if "return seen" in answer_norm:
        return 5, "bug fix identified"
    if "seen" in answer_norm:
        return 3, "mentions seen but fix unclear"
    return 1, "wrong"


def validate_q5(answer: str) -> tuple[int, str]:
    compact = re.sub(r"\s+", "", answer.strip())
    if compact == '{"min":4,"max":42,"mean":18}':
        return 5, "exact json"
    try:
        parsed = json.loads(answer)
    except Exception:
        return 1, "not valid json"
    if parsed == {"min": 4, "max": 42, "mean": 18}:
        return 3, "correct values, formatting drift"
    return 1, "wrong values"


def validate_q6(answer: str) -> tuple[int, str]:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    bullet_lines = [line for line in lines if line.startswith("-") or line.startswith("*")]
    if len(bullet_lines) != 2:
        return 1, "did not return exactly 2 bullets"
    words_ok = all(len(re.findall(r"\b\w+\b", line)) < 16 for line in bullet_lines)
    topic_ok = "stack" in normalize_text(answer) and "heap" in normalize_text(answer)
    if words_ok and topic_ok:
        return 5, "constraints met"
    if topic_ok:
        return 3, "conceptually right, format drift"
    return 1, "weak or wrong"


def validate_q7(answer: str) -> tuple[int, str]:
    answer_norm = normalize_text(answer)
    has_estimate = "estimate:" in answer_norm
    has_confidence = "confidence:" in answer_norm
    found = first_int(answer)
    in_range = found is not None and 4000 <= found <= 6000
    has_unknown = "unknown" in answer_norm
    if has_estimate and has_confidence and "low" in answer_norm and (in_range or has_unknown):
        return 5, "good uncertainty calibration"
    if has_estimate and has_confidence:
        return 3, "format correct but content weak"
    return 1, "wrong format"


def validate_q8(answer: str) -> tuple[int, str]:
    answer_norm = normalize_text(answer)
    field_ok = "mechanical engineer" in answer_norm or "mechanical engineering" in answer_norm
    time_ok = "17:00" in answer and "2026-12-25" in answer
    if field_ok and time_ok:
        return 5, "context retained"
    if field_ok or time_ok:
        return 3, "partial context retention"
    return 1, "wrong"


def validate_q9(answer: str) -> tuple[int, str]:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    stepish = [line for line in lines if re.match(r"^(\d+\.|-|\*)", line)]
    helpful = any(
        term in normalize_text(answer)
        for term in ["patch", "pump", "tube", "valve", "lever", "inflate", "puncture", "sealant"]
    )
    if len(stepish) == 5 and helpful:
        return 5, "practical and formatted"
    if helpful:
        return 3, "helpful but format drift"
    return 1, "weak"


def validate_q10(answer: str) -> tuple[int, str]:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    if len(lines) >= 2 and normalize_text(lines[0]) != normalize_text(lines[1]):
        return 5, "two different translations"
    if len(lines) >= 2:
        return 3, "two lines but little semantic shift"
    return 1, "wrong"


TESTS = [
    TextTest(
        test_id="Q1",
        name="Time Arithmetic",
        prompt=(
            "A flight departs at 14:45. The flight duration is 7 hours 25 minutes. "
            "What is the arrival time in the same timezone? "
            "Reply in HH:MM 24-hour format only."
        ),
        validator=exact_only("22:10"),
        expected="22:10",
    ),
    TextTest(
        test_id="Q2",
        name="Constraint Logic",
        prompt=(
            "Fern, Greg, and Hana each own exactly one different pet: a cat, a dog, or a fish. "
            "Fern does not own the dog. Greg does not own the cat. "
            "Hana does not own the fish. Hana does not own the dog. "
            "Who owns the fish? Reply with the name only."
        ),
        validator=exact_only("Fern"),
        expected="Fern",
    ),
    TextTest(
        test_id="Q3",
        name="Code Writing",
        prompt=(
            "Write a Python function `flatten(nested: list) -> list` that recursively flattens "
            "a nested list of any depth. "
            "Example: [1, [2, [3, 4]], 5] -> [1, 2, 3, 4, 5]. "
            "No explanation. Return code only."
        ),
        validator=validate_q3,
        expected="recursive Python flatten function",
    ),
    TextTest(
        test_id="Q4",
        name="Code Debugging",
        prompt=(
            "This Python function is supposed to return a list with duplicates removed, "
            "but it has a bug. Find and fix it.\n\n"
            "def remove_duplicates(items: list) -> list:\n"
            "    seen = []\n"
            "    for item in items:\n"
            "        if item not in seen:\n"
            "            seen.append(item)\n"
            "    return items\n"
        ),
        validator=validate_q4,
        expected="return seen",
    ),
    TextTest(
        test_id="Q5",
        name="Format Fidelity",
        prompt=(
            "Compute min, max, and mean of these numbers: 4, 8, 15, 16, 23, 42. "
            'Reply as JSON only, with exactly these keys in this order: "min", "max", "mean". '
            "All values must be integers."
        ),
        validator=validate_q5,
        expected='{"min":4,"max":42,"mean":18}',
    ),
    TextTest(
        test_id="Q6",
        name="Technical Compression",
        prompt=(
            "Explain the difference between stack and heap memory in exactly 2 bullet points. "
            "Each bullet must be under 15 words."
        ),
        validator=validate_q6,
        expected="2 short bullets",
    ),
    TextTest(
        test_id="Q7",
        name="Uncertainty Calibration",
        prompt=(
            "What is the boiling point of osmium in degrees Celsius?\n"
            "Answer in this format only:\n"
            "estimate: <value or unknown>\n"
            "confidence: <low|medium|high>"
        ),
        validator=validate_q7,
        expected="estimate near 5012, low confidence",
    ),
    TextTest(
        test_id="Q8",
        name="Fixed-Date Context",
        prompt=None,
        validator=validate_q8,
        expected="mechanical engineer and 2026-12-25 17:00",
        multi_turn=True,
    ),
    TextTest(
        test_id="Q9",
        name="Practical Helpfulness",
        prompt="My bike tire is flat. What should I do? Give exactly 5 short numbered steps.",
        validator=validate_q9,
        expected="5 numbered steps, bike-related terms",
    ),
    TextTest(
        test_id="Q10",
        name="Semantic Nuance",
        prompt=(
            'Translate into Spanish: "I saw the man with the binoculars." '
            "Then translate it again so the sentence clearly implies the man is holding the binoculars. "
            "Give exactly two lines, one translation per line."
        ),
        validator=validate_q10,
        expected="two different Spanish translations",
    ),
]


def run_q8(model: str, host: str) -> tuple[str, float]:
    messages = [
        {"role": "user", "content": "My name is Kenji. I am a mechanical engineer. I live in Tokyo."}
    ]
    turn1 = chat(messages, model, host)
    messages.append({"role": "assistant", "content": turn1["content"]})
    messages.append({"role": "user", "content": "What is my profession?"})
    turn2 = chat(messages, model, host)
    messages.append({"role": "assistant", "content": turn2["content"]})
    messages.append(
        {"role": "user", "content": "If it is 2026-12-25 08:00 UTC, what local date and time is it for me?"}
    )
    turn3 = chat(messages, model, host)
    combined = f"Turn2: {turn2['content']}\nTurn3: {turn3['content']}"
    return combined, round(turn1["elapsed"] + turn2["elapsed"] + turn3["elapsed"], 1)


def run_benchmark(model: str, host: str, save: str = "") -> list[dict]:
    print(SEP)
    print(f"Text Benchmark v3 - {model}")
    print(SEP)
    print(f"Host: {host}")
    print()

    results: list[dict] = []
    for test in TESTS:
        print(f"Running {test.test_id} {test.name}...", end=" ", flush=True)
        if test.multi_turn:
            response, elapsed = run_q8(model, host)
            tok_s = 0.0
            tokens = 0
        else:
            result = generate(test.prompt or "", model, host)
            response = result["response"]
            elapsed = result["elapsed"]
            tok_s = result["tok_s"]
            tokens = result["eval_count"]
        score, note = test.validator(response)
        print(f"{score}/5")
        print(f"  Expected : {test.expected}")
        print(f"  Got      : {response[:80]}")
        print(f"  Tok/s    : {tok_s}")
        print(f"  Tokens   : {tokens}")
        print(f"  Elapsed  : {elapsed}s")
        print(f"  Note     : {note}")
        print()
        results.append(
            {
                "id": test.test_id,
                "name": test.name,
                "score": score,
                "tok_s": tok_s,
                "tokens": tokens,
                "elapsed": elapsed,
                "note": note,
                "response": response,
            }
        )

    print(SEP)
    print("Summary")
    print(SEP)
    print(f"{'ID':<5}{'Category':<24}{'Score':<8}{'Tok/s':<8}{'Tokens':<10}{'Note'}")
    print("-" * 72)
    single_turn = [r for r in results if r["tok_s"] > 0]
    for result in results:
        print(
            f"{result['id']:<5}{result['name']:<24}{result['score']:<8}"
            f"{result['tok_s']:<8}{result['tokens']:<10}{result['note']}"
        )
    print("-" * 72)
    average = round(sum(r["score"] for r in results) / len(results), 2)
    avg_toks = round(sum(r["tok_s"] for r in single_turn) / len(single_turn), 1) if single_turn else 0.0
    print(f"Average score: {average}/5")
    print(f"Average decode tok/s, single-turn only: {avg_toks}")
    if save:
        out = {
            "benchmark": "text-benchmark-v3",
            "date": time.strftime("%Y-%m-%d"),
            "model": model,
            "average_score": average,
            "avg_tok_s": avg_toks,
            "results": results,
        }
        with open(save, "w") as f:
            json.dump(out, f, indent=2)
        print(f"Saved results to: {save}")
    print()
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Text benchmark suite v3")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--save", default="", help="Path to save JSON results")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_benchmark(args.model, args.host, args.save)
