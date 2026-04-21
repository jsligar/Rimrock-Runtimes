#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import time
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib import request


DEFAULT_HOST = "http://172.16.0.248:8424"
DEFAULT_MODEL = "gemma-4-E2B-it-UD-Q4_K_XL.gguf"
MEMORY_HOST = "http://172.16.0.248:8001"
THINKING = "off"

SYSTEM_PROMPT = (
    "You are a precise assistant with a persistent memory palace. "
    "Follow these rules every session:\n\n"
    "1. SEARCH BEFORE ANSWERING: For questions involving hardware registers, pin numbers, board identifiers, "
    "timezone conversions, or any fact you are not fully certain of — call mempalace_search FIRST.\n\n"
    "2. REMEMBER WHAT YOU LEARN: Whenever a question reveals a concept, correction, or piece of knowledge "
    "you did not previously have in memory — call mempalace_add_drawer to store it. "
    "Use a descriptive wing and room. Write the content as 'Remember this: ...' followed by the full concept. "
    "Do this even if you got the answer right — if the reasoning path was non-obvious, store it.\n\n"
    "3. DIRECT ANSWERS for straightforward logic, arithmetic, and coding you can answer confidently.\n\n"
    "You may call tools as many times as needed before producing your final answer."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "mempalace_search",
            "description": "Search your memory palace for concepts, facts, and knowledge relevant to a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "wing": {"type": "string", "description": "Optional: filter by wing (e.g. 'reasoning', 'hardware')"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mempalace_kg_query",
            "description": "Query the knowledge graph for facts about a specific concept or entity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Concept or entity to look up"},
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mempalace_add_drawer",
            "description": "Store a concept, correction, or piece of knowledge into your memory palace for future sessions. Use this whenever you learn something worth remembering.",
            "parameters": {
                "type": "object",
                "properties": {
                    "wing": {"type": "string", "description": "Category wing (e.g. 'reasoning', 'hardware', 'geography')"},
                    "room": {"type": "string", "description": "Topic room slug (e.g. 'time-arithmetic', 'lora-sx1262')"},
                    "content": {"type": "string", "description": "Full concept content starting with 'Remember this:'"},
                },
                "required": ["wing", "room", "content"],
            },
        },
    },
]


def call_tool(name: str, args: dict[str, Any]) -> str:
    url = f"{MEMORY_HOST}/{name}"
    req = request.Request(
        url,
        data=json.dumps(args).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)})


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def chat(host: str, model: str, messages: list[dict[str, str]], max_tokens: int) -> dict[str, Any]:
    # Prepend system prompt if not already present
    full_messages = messages
    if not messages or messages[0].get("role") != "system":
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    total_tokens = 0
    total_ms = 0.0
    started = time.perf_counter()

    # Tool-calling loop — runs until model stops calling tools
    for _ in range(5):  # max 5 tool rounds
        payload = {
            "model": model,
            "messages": full_messages,
            "tools": TOOLS,
            "tool_choice": "auto",
            "stream": False,
            "temperature": 0.1,
            "top_k": 40,
            "top_p": 0.9,
            "min_p": 0.05,
            "seed": 42,
            "repeat_penalty": 1.0,
            "max_tokens": max_tokens,
        }
        req = request.Request(
            f"{host}/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read().decode("utf-8"))

        timings = data.get("timings", {})
        usage = data.get("usage", {})
        total_tokens += usage.get("completion_tokens", 0)
        total_ms += timings.get("predicted_ms", 0)

        message = data["choices"][0]["message"]
        finish_reason = data["choices"][0].get("finish_reason", "stop")
        tool_calls = message.get("tool_calls") or []

        if not tool_calls or finish_reason != "tool_calls":
            break

        # Execute each tool call and append results
        full_messages = full_messages + [{"role": "assistant", "tool_calls": tool_calls, "content": message.get("content") or ""}]
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            fn_args = json.loads(tc["function"]["arguments"])
            print(f"    [tool] {fn_name}({fn_args})", flush=True)
            result = call_tool(fn_name, fn_args)
            full_messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    elapsed = time.perf_counter() - started
    tok_s = round(total_tokens / (total_ms / 1000), 2) if total_tokens and total_ms else None
    return {
        "content": message.get("content", "").strip(),
        "elapsed_s": round(elapsed, 3),
        "ttft_ms": None,
        "tok_s": tok_s,
        "output_tokens": total_tokens,
        "raw": data,
    }


def score_exact(answer: str, expected: str) -> tuple[float, str]:
    if answer.strip() == expected:
        return 10, "none"
    if normalize(answer) == normalize(expected):
        return 8, "format_drift"
    return 1, "confident_wrong"


def strip_fences(answer: str) -> str:
    value = answer.strip()
    if value.startswith("```"):
        value = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", value)
        value = re.sub(r"\s*```$", "", value)
    return value.strip()


def validate_q3(answer: str) -> tuple[float, str]:
    text = strip_fences(answer)
    if "```" in answer or "explanation" in normalize(answer):
        return 7, "format_drift"
    try:
        tree = ast.parse(text)
        ns: dict[str, Any] = {}
        exec(compile(tree, "<q3>", "exec"), ns)
        fn = ns.get("group_even_runs")
        if not callable(fn):
            return 2, "confident_wrong"
        cases = [
            ([2, 4, 7, 8, 10, 3, 6], [[2, 4], [8, 10], [6]]),
            ([1, 3, 5], []),
            ([2, 4, 6], [[2, 4, 6]]),
            ([2, 1, 4, 5, 6, 8], [[2], [4], [6, 8]]),
        ]
        if all(fn(inp) == out for inp, out in cases):
            return (10 if "def group_even_runs(nums: list[int]) -> list[list[int]]" in text else 9), "none"
        return 4, "confident_wrong"
    except Exception:
        return 2, "format_drift"


def validate_q4(answer: str) -> tuple[float, str]:
    text = strip_fences(answer)
    try:
        tree = ast.parse(text)
        ns: dict[str, Any] = {}
        exec(compile(tree, "<q4>", "exec"), ns)
        fn = ns.get("word_counts")
        if not callable(fn):
            return 2, "confident_wrong"
        if fn(["Red", "red", "BLUE"]) != {"red": 2, "blue": 1}:
            return 3, "confident_wrong"
        if ".split" in text or "import " in text:
            return 8, "format_drift"
        return 10 if "item.lower()" in text else 8, "none"
    except Exception:
        return 2, "format_drift"


def validate_q5(answer: str) -> tuple[float, str]:
    if answer.strip() == '{"red":3,"blue":1,"green":1}':
        return 10, "none"
    if "```" in answer:
        return 2, "format_drift"
    try:
        parsed = json.loads(answer)
    except Exception:
        return 1, "format_drift"
    if parsed == {"red": 3, "blue": 1, "green": 1}:
        return 7, "format_drift"
    return 1, "confident_wrong"


def validate_q6(answer: str) -> tuple[float, str]:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    bullets = [line for line in lines if line.startswith(("-", "*"))]
    if len(bullets) != 2:
        return 3, "format_drift"
    under_limit = all(len(re.findall(r"\b[\w'-]+\b", line)) < 14 for line in bullets)
    content = normalize(answer)
    accurate = "tcp" in content and "udp" in content and (
        ("connection" in content or "reliable" in content) and ("fast" in content or "unreliable" in content or "connectionless" in content)
    )
    if under_limit and accurate:
        return 10, "none"
    if accurate:
        return 7, "verbosity"
    return 3, "confident_wrong"


def validate_q7(answer: str) -> tuple[float, str]:
    lines = [line.strip() for line in answer.lower().splitlines() if line.strip()]
    if len(lines) != 2 or not lines[0].startswith("estimate:") or not lines[1].startswith("confidence:"):
        return 3, "format_drift"
    estimate = lines[0].split(":", 1)[1].strip()
    confidence = lines[1].split(":", 1)[1].strip()
    if confidence == "high":
        return 1, "confident_wrong"
    if estimate == "unknown" and confidence == "low":
        return 7, "none"
    match = re.search(r"-?\d+(?:\.\d+)?", estimate)
    if match and confidence == "low":
        value = float(match.group(0))
        if 620 <= value <= 730:
            return 9, "none"
        return 2, "confident_wrong"
    if confidence in {"low", "medium"}:
        return 5, "format_drift"
    return 2, "format_drift"


def validate_q8(answer: str) -> tuple[float, str]:
    text = normalize(answer)
    has_field = "marine biology" in text
    has_time = "2026-07-02" in text and "03:00" in text
    if has_field and has_time:
        return 10, "none"
    if has_field or has_time:
        return 5, "confident_wrong"
    return 1, "confident_wrong"


def validate_q9(answer: str) -> tuple[float, str]:
    if "```" in answer:
        return 2, "format_drift"
    try:
        parsed = json.loads(answer)
    except Exception:
        return 2, "format_drift"
    if not isinstance(parsed, list) or len(parsed) != 3:
        return 3, "format_drift"
    valid_keys = all(list(item.keys()) == ["rank", "cause", "confidence", "urgency"] for item in parsed if isinstance(item, dict))
    valid_enums = all(
        isinstance(item, dict)
        and item.get("confidence") in {"low", "medium", "high"}
        and item.get("urgency") in {"monitor", "soon", "immediate"}
        for item in parsed
    )
    causes = " ".join(str(item.get("cause", "")).lower() for item in parsed if isinstance(item, dict))
    has_afm = "afm" in causes or "lifter" in causes
    has_hpfp = "hpfp" in causes or "fuel pump" in causes or "cam lobe" in causes
    has_injector = "injector" in causes and ("bank 2" in causes or "bank two" in causes)
    if valid_keys and valid_enums and has_afm and has_hpfp and has_injector:
        return 10, "none"
    if valid_keys and valid_enums and (has_afm or has_hpfp or has_injector):
        return 7, "none"
    if valid_keys and valid_enums:
        return 4, "confident_wrong"
    return 3, "format_drift"


def validate_q10(answer: str) -> tuple[float, str]:
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    if len(lines) < 2:
        return 3, "format_drift"
    text = normalize(answer)
    has_french = "je n'ai jamais dit" in text or "je n ai jamais dit" in text
    has_emphasis = any(marker in answer for marker in ["**", "_", "elle", "ELLE", "Elle"]) and len(set(lines[:2])) > 1
    if has_french and has_emphasis:
        return 10, "none"
    if has_french:
        return 5, "format_drift"
    return 2, "confident_wrong"


def validate_q11(answer: str) -> tuple[float, str]:
    text = strip_fences(answer)
    low = normalize(text)
    score = 0.0
    if "[env:" in low:
        score += 1
    if "framework = arduino" in low:
        score += 1.5
    if "upload_protocol = esptool" in low:
        score += 1
    if "monitor_speed = 115200" in low:
        score += 1
    if re.search(r"board\s*=\s*[^\\n]*(esp32s3|s3)", low):
        score += 1.5
    pins = {
        "NSS": r"(sx1262_)?(nss|cs)\s*=?\s*7\b",
        "RST": r"(sx1262_)?(rst|reset)\s*=?\s*8\b",
        "BUSY": r"(sx1262_)?busy\s*=?\s*9\b",
        "DIO1": r"(sx1262_)?dio1\s*=?\s*14\b",
    }
    found_pins = sum(1 for pattern in pins.values() if re.search(pattern, low))
    score += found_pins
    if "```" in answer or any(x in low for x in ["here is", "explanation"]):
        return min(score, 7), "format_drift"
    if score >= 10:
        return 10, "none"
    if found_pins < 4:
        return min(score, 5), "confident_wrong"
    return min(score, 8), "format_drift"


def validate_q12(answer: str) -> tuple[float, str]:
    low = normalize(answer)
    if "unknown" in low or "datasheet" in low:
        return 7, "none"
    values = [value.lower() for value in re.findall(r"0x[0-9a-fA-F]+", answer)]
    if "0x39" in values:
        return 1, "confident_wrong"
    has_reg = "0x0740" in values
    has_public = "0x3444" in values or ("0x34" in values and "0x44" in values)
    has_private = "0x1424" in values or ("0x14" in values and "0x24" in values)
    if has_reg and has_public and has_private:
        return 10, "none"
    if "0x34" in values and not has_public:
        return 2, "confident_wrong"
    if any(values):
        return 1, "confident_wrong"
    return 0, "confident_wrong"


TESTS: list[dict[str, Any]] = [
    {"id": "Q1", "name": "Time Arithmetic", "weight": 1.0, "max_tokens": 64, "validator": lambda a: score_exact(a, "11:11"), "messages": [{"role": "user", "content": "A job starts at 09:35. Task 1 takes 17 minutes, then there is an 8 minute break.\nTask 2 takes 24 minutes, then another 8 minute break. Task 3 takes 39 minutes.\nWhat time does the job finish? Reply in HH:MM 24-hour format only."}]},
    {"id": "Q2", "name": "Constraint Logic", "weight": 1.0, "max_tokens": 64, "validator": lambda a: score_exact(a, "Anna"), "messages": [{"role": "user", "content": "Anna, Ben, and Cara each own one different pet: a cat, a dog, and a fish.\nAnna does not own the cat. Ben does not own the dog. Cara does not own the fish.\nBen does not own the cat. Who owns the dog? Reply with the name only."}]},
    {"id": "Q3", "name": "Code Writing", "weight": 1.0, "max_tokens": 256, "validator": validate_q3, "messages": [{"role": "user", "content": "Write a Python function `group_even_runs(nums: list[int]) -> list[list[int]]`\nthat returns consecutive runs of even numbers from the input, preserving order.\nExample: [2, 4, 7, 8, 10, 3, 6] -> [[2, 4], [8, 10], [6]]\nNo explanation. Return code only."}]},
    {"id": "Q4", "name": "Code Debugging", "weight": 1.0, "max_tokens": 256, "validator": validate_q4, "messages": [{"role": "user", "content": "This Python function is supposed to count words case-insensitively, but it has a bug.\nFind and fix it. Return corrected code only. Do not add comments or explanation.\n\ndef word_counts(items):\n    counts = {}\n    for item in items:\n        key = item.lower\n        counts[key] = counts.get(key, 0) + 1\n    return counts"}]},
    {"id": "Q5", "name": "Format Fidelity", "weight": 1.5, "max_tokens": 64, "validator": validate_q5, "messages": [{"role": "user", "content": "Count the words in this string: \"red blue red green red\"\nRespond with only a JSON object. No markdown code fences. No explanation.\nNo extra text before or after. Compact format with no whitespace between tokens.\nUse exactly these keys in this order: \"red\", \"blue\", \"green\""}]},
    {"id": "Q6", "name": "Technical Compression", "weight": 1.0, "max_tokens": 128, "validator": validate_q6, "messages": [{"role": "user", "content": "Explain the difference between TCP and UDP in exactly 2 bullet points.\nEach bullet must be under 14 words."}]},
    {"id": "Q7", "name": "Uncertainty Calibration", "weight": 1.5, "max_tokens": 64, "validator": validate_q7, "messages": [{"role": "user", "content": "What is the boiling point of francium in degrees Celsius?\nAnswer in this format only:\nestimate: <value or unknown>\nconfidence: <low|medium|high>"}]},
    {"id": "Q9", "name": "Diagnostic Triage", "weight": 1.5, "max_tokens": 512, "validator": validate_q9, "messages": [{"role": "user", "content": "A vehicle reports the following symptoms:\n- Prolonged crank on cold start (3-4 seconds before firing)\n- Intermittent lean condition on Bank 2 only\n- Random misfire at highway cruise speed\n- No audible lifter tick\n\nRespond with a JSON array of the top 3 probable causes, ranked by likelihood.\nNo markdown fences. No explanation outside the JSON.\nEach object must have exactly these keys: \"rank\", \"cause\", \"confidence\", \"urgency\"\nconfidence: low | medium | high\nurgency: monitor | soon | immediate"}]},
    {"id": "Q10", "name": "Semantic Nuance", "weight": 0.5, "max_tokens": 256, "validator": validate_q10, "messages": [{"role": "user", "content": "Translate this sentence into French:\n\"I never said she stole my money.\"\nThen translate it again, but this time emphasize the word \"she\"."}]},
    {"id": "Q11", "name": "PlatformIO ESP32-S3", "weight": 1.25, "max_tokens": 512, "validator": validate_q11, "messages": [{"role": "user", "content": "Write a platformio.ini configuration for the LILYGO T-Beam Supreme with an\nESP32-S3 and SX1262 LoRa radio at 915MHz.\nInclude: correct board ID, framework, upload protocol, serial monitor baud rate,\nand build flags defining SX1262 NSS, RST, BUSY, and DIO1 pins.\nReturn the ini file content only. No explanation."}]},
    {"id": "Q12", "name": "SX1262 Hardware Register", "weight": 1.5, "max_tokens": 128, "validator": validate_q12, "messages": [{"role": "user", "content": "The SX1262 LoRa transceiver is configured via SPI register writes.\nWhat is the register address for LoRa sync word configuration,\nand what byte values set public LoRa network sync word versus\nprivate network sync word? Give exact hex values only.\nNo explanation."}]},
]


def run_q8(host: str, model: str) -> dict[str, Any]:
    messages = [{"role": "user", "content": "My name is Maya. I work in marine biology. I live in Auckland."}]
    turn1 = chat(host, model, messages, 128)
    messages.append({"role": "assistant", "content": turn1["content"]})
    messages.append({"role": "user", "content": "What field do I work in?"})
    turn2 = chat(host, model, messages, 128)
    messages.append({"role": "assistant", "content": turn2["content"]})
    messages.append({"role": "user", "content": "If it is 2026-07-01 15:00 UTC, what local date and time is it for me?"})
    turn3 = chat(host, model, messages, 256)
    combined = f"Turn2: {turn2['content']}\nTurn3: {turn3['content']}"
    score, failure = validate_q8(combined)
    return {
        "id": "Q8",
        "name": "Fixed-Date Context Retention",
        "weight": 1.0,
        "response": combined,
        "score": score,
        "failure_mode": failure,
        "ttft_ms": None,
        "tok_s": None,
        "output_tokens": sum(x.get("output_tokens") or 0 for x in [turn1, turn2, turn3]),
        "elapsed_s": round(sum(x["elapsed_s"] for x in [turn1, turn2, turn3]), 3),
    }


def build_report(host: str, model: str, results: list[dict[str, Any]]) -> str:
    raw_avg = round(sum(r["score"] for r in results) / len(results), 2)
    weighted_avg = round(sum(r["score"] * r["weight"] for r in results) / sum(r["weight"] for r in results), 2)
    total_tokens = sum((r.get("output_tokens") or 0) for r in results)
    speed_values = [r["tok_s"] for r in results if r.get("tok_s")]
    avg_tok_s = round(sum(speed_values) / len(speed_values), 2) if speed_values else None
    failures = [f"{r['failure_mode']}:{r['id']}" for r in results if r["failure_mode"] != "none"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = [
        "# Gemma 4 E2B UD-Q4_K_XL — Benchmark v3 Results",
        "",
        f"Run: `{now}`",
        f"Model: `{model}`",
        "Machine: `rimrock`",
        "Runtime: `llama-server`",
        f"Host: `{host}`",
        f"Thinking: `{THINKING}`",
        f"Tools: `mempalace_search, mempalace_kg_query`",
        f"Raw average: `{raw_avg}/10`",
        f"Weighted average: `{weighted_avg}/10`",
        f"Output tokens: `{total_tokens}`",
        f"Average tok/s: `{avg_tok_s}`",
        f"Failure modes: `{', '.join(failures) if failures else 'none'}`",
        "",
        "| ID | Score | Weight | Tok/s | Tokens | Failure Mode |",
        "|----|-------|--------|-------|--------|--------------|",
    ]
    for r in results:
        header.append(
            f"| {r['id']} | {r['score']} | {r['weight']} | {r.get('tok_s')} | {r.get('output_tokens')} | {r['failure_mode']} |"
        )
    details = ["", "## Responses", ""]
    for r in results:
        details.extend([
            f"### {r['id']} — {r['name']}",
            "",
            f"Score: `{r['score']}/10`  ",
            f"Failure mode: `{r['failure_mode']}`  ",
            f"Elapsed: `{r.get('elapsed_s')}s`  ",
            f"Tokens: `{r.get('output_tokens')}`  ",
            "",
            "```text",
            r["response"],
            "```",
            "",
        ])
    return "\n".join(header + details)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out-dir", default="/mnt/claude-nas")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    for test in TESTS[:7]:
        print(f"Running {test['id']} {test['name']}...", flush=True)
        result = chat(args.host, args.model, test["messages"], test["max_tokens"])
        score, failure = test["validator"](result["content"])
        results.append({**test, **result, "response": result["content"], "score": score, "failure_mode": failure})
        print(f"  {score}/10 {failure}", flush=True)

    print("Running Q8 Fixed-Date Context Retention...", flush=True)
    q8 = run_q8(args.host, args.model)
    results.append(q8)
    print(f"  {q8['score']}/10 {q8['failure_mode']}", flush=True)

    for test in TESTS[7:]:
        print(f"Running {test['id']} {test['name']}...", flush=True)
        result = chat(args.host, args.model, test["messages"], test["max_tokens"])
        score, failure = test["validator"](result["content"])
        results.append({**test, **result, "response": result["content"], "score": score, "failure_mode": failure})
        print(f"  {score}/10 {failure}", flush=True)

    for r in results:
        r.pop("validator", None)
        r.pop("messages", None)
        r.pop("raw", None)

    out_dir = Path(args.out_dir)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_path = Path("/tmp") / f"benchmark-v3-rimrock-tools-{stamp}.json"
    report_path = Path("/tmp") / f"benchmark-report-gemma4-e2b-ud-q4xl-rimrock-v3-tools-{stamp}.md"
    raw_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    report_path.write_text(build_report(args.host, args.model, results), encoding="utf-8")
    final_raw = out_dir / raw_path.name
    final_report = out_dir / report_path.name
    final_raw.write_text(raw_path.read_text(encoding="utf-8"), encoding="utf-8")
    final_report.write_text(report_path.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"RAW={final_raw}")
    print(f"REPORT={final_report}")


if __name__ == "__main__":
    main()
