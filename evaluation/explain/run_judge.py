#!/usr/bin/env python3
"""Run the OR-Space Explain judge through an OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", type=Path, default=Path(__file__).with_name("judge_prompt.md"))
    parser.add_argument("--base-url")
    parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    parser.add_argument("--max-completion-tokens", type=int, default=4000)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("Install the optional judge client with: pip install openai") from exc
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set")
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if args.base_url:
        client_kwargs["base_url"] = args.base_url
    client = OpenAI(**client_kwargs)

    prompt = args.prompt.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    completed: set[str] = set()
    if args.output.exists():
        completed = {str(row.get("instance_id")) for row in load_rows(args.output)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8") as output:
        for payload in load_rows(args.inputs):
            instance_id = str(payload["instance_id"])
            if instance_id in completed:
                continue
            last_error: Exception | None = None
            for attempt in range(args.retries):
                try:
                    response = client.chat.completions.create(
                        model=args.model,
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                        ],
                        temperature=0.0,
                        max_completion_tokens=args.max_completion_tokens,
                        response_format={"type": "json_object"},
                    )
                    content = response.choices[0].message.content or ""
                    judgment = json.loads(content)
                    judgment.update(
                        {
                            "instance_id": instance_id,
                            "judge_model": args.model,
                            "judge_prompt_sha256": prompt_hash,
                        }
                    )
                    output.write(json.dumps(judgment, ensure_ascii=False, sort_keys=True) + "\n")
                    output.flush()
                    break
                except Exception as exc:  # noqa: BLE001 - preserve resumable batch behavior
                    last_error = exc
                    if attempt + 1 < args.retries:
                        time.sleep(2**attempt)
            else:
                raise RuntimeError(f"Judge failed for {instance_id}: {last_error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
