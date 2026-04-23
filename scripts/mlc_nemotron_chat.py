#!/usr/bin/env python3
"""Interactive CLI chat with nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1 via MLC.

Settings tuned for Rimrock (Jetson Orin Nano 8GB, SM87):
  - 4096 context window
  - 1024 prefill chunk  (must match value baked into lib-sm87.so at compile time)
  - temperature 0.1     (deterministic, matches benchmark baseline)
  - 1024 max tokens/response
"""
from __future__ import annotations

import argparse

from mlc_llm import MLCEngine
from mlc_llm.serve import EngineConfig

MODEL = "/weights"
MODEL_LIB = "/weights/lib-sm87.so"
DEFAULT_MAX_TOKENS = 1024
CONTEXT_WINDOW = 4096
PREFILL_CHUNK = 1024
TEMPERATURE = 0.1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"Max tokens per response (default: {DEFAULT_MAX_TOKENS})")
    parser.add_argument("--context", type=int, default=CONTEXT_WINDOW,
                        help=f"Context window size (default: {CONTEXT_WINDOW})")
    parser.add_argument("--temperature", type=float, default=TEMPERATURE,
                        help=f"Sampling temperature (default: {TEMPERATURE})")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--model-lib", default=MODEL_LIB)
    args = parser.parse_args()

    cfg = EngineConfig(
        max_num_sequence=1,
        max_single_sequence_length=args.context,
        prefill_chunk_size=PREFILL_CHUNK,
    )
    engine = MLCEngine(args.model, model_lib=args.model_lib, mode="interactive",
                       device="cuda", engine_config=cfg)

    print(f"Nemotron Nano 4B  |  ctx {args.context}  |  max {args.max_tokens} tok/resp  |  temp {args.temperature}")
    print("Commands: /exit  /reset  /ctx  (Ctrl-C also exits)")
    print()

    history: list[dict] = []

    try:
        while True:
            try:
                user_input = input(">>> ").strip()
            except EOFError:
                break
            if not user_input:
                continue
            if user_input == "/exit":
                break
            if user_input == "/reset":
                history.clear()
                print("[context cleared]")
                continue
            if user_input == "/ctx":
                total = sum(len(m["content"].split()) for m in history)
                print(f"[turns: {len(history)}  approx words in history: {total}]")
                continue

            history.append({"role": "user", "content": user_input})

            response_text = ""
            for chunk in engine.chat.completions.create(
                messages=history,
                model=args.model,
                stream=True,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            ):
                delta = chunk.choices[0].delta.content or ""
                print(delta, end="", flush=True)
                response_text += delta
            print()

            history.append({"role": "assistant", "content": response_text})
    except KeyboardInterrupt:
        print()

    engine.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
