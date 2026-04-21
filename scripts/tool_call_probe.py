#!/usr/bin/env python3
"""Small JSON/tool-discipline probe for OpenAI-compatible local servers."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib import request


@dataclass(frozen=True)
class Case:
    name: str
    prompt: str
    expected_tool: str | None
    required_args: dict[str, Any]


CASES = [
    Case(
        name="weather_tool",
        prompt="Use a tool if needed. What is the weather in Auckland tomorrow?",
        expected_tool="get_weather",
        required_args={"location": "Auckland"},
    ),
    Case(
        name="memory_lookup",
        prompt="Use a tool if needed. What did I say my favorite benchmark model was?",
        expected_tool="search_memory",
        required_args={"query": "favorite benchmark model"},
    ),
    Case(
        name="known_fact_no_tool",
        prompt="Use a tool only if needed. What is 2 + 2?",
        expected_tool=None,
        required_args={},
    ),
]

SYSTEM = """You are testing tool calling discipline.
Return exactly one JSON object and no markdown.
Schema:
{"tool": string|null, "arguments": object, "answer": string|null}
Available tools:
- get_weather(location: string, date: string|null)
- search_memory(query: string)
- store_memory(key: string, value: string)
If no tool is needed, set tool to null and answer directly.
"""


def post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_content(response: dict[str, Any]) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"unexpected response shape: {response}") from exc


def parse_json_object(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def score_case(case: Case, obj: dict[str, Any] | None) -> tuple[int, str]:
    if obj is None:
        return 0, "invalid_json"
    if obj.get("tool") != case.expected_tool:
        return 1, f"wrong_tool:{obj.get('tool')!r}"
    args = obj.get("arguments", {})
    if not isinstance(args, dict):
        return 2, "arguments_not_object"
    for key, expected in case.required_args.items():
        actual = str(args.get(key, ""))
        if str(expected).lower() not in actual.lower():
            return 3, f"missing_arg:{key}"
    return 5, "pass"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8424/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=160)
    parser.add_argument("--save", default="")
    args = parser.parse_args()

    url = args.base_url.rstrip("/") + "/chat/completions"
    results = []
    for case in CASES:
        started = time.time()
        response = post_json(
            url,
            {
                "model": args.model,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": case.prompt},
                ],
                "temperature": 0,
                "max_tokens": args.max_tokens,
            },
            args.timeout,
        )
        text = extract_content(response)
        obj = parse_json_object(text)
        score, note = score_case(case, obj)
        result = {
            "name": case.name,
            "score": score,
            "note": note,
            "response": text,
            "parsed": obj,
            "elapsed": round(time.time() - started, 3),
        }
        results.append(result)
        print(f"{case.name}: {score}/5 {note}")

    average = round(sum(item["score"] for item in results) / len(results), 2)
    payload = {"model": args.model, "average_score": average, "results": results}
    print(f"Average: {average}/5")

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
