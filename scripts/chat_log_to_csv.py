#!/usr/bin/env python3
"""Parse chat log TXT files into Question/Answer CSV pairs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

TIMESTAMP_LINE = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\](.*)$",
    re.MULTILINE,
)
USER_HEADER = re.compile(r"User(?:\[[^\]]*\])?:\s*(.*)", re.DOTALL)
ASSISTANT_HEADER = re.compile(r"Assistant:\s*(.*)", re.DOTALL)
REPLY_TAG = re.compile(r"^\[回复 \d+\]\s*")
BLOCK_TAG = re.compile(
    r"<(?:voice|quoted_message)[^>]*>.*?</(?:voice|quoted_message)>",
    re.DOTALL | re.IGNORECASE,
)
HTML_TAG = re.compile(r"<[^>]+>")


def _extract_user_content(header_rest: str) -> str | None:
    match = USER_HEADER.search(header_rest)
    if not match:
        return None
    return match.group(1) or ""


def _extract_assistant_content(header_rest: str) -> str | None:
    match = ASSISTANT_HEADER.search(header_rest)
    if not match:
        return None
    return match.group(1) or ""


def _classify_message(header_rest: str) -> tuple[str | None, str]:
    """Return (role, initial_content) where role is 'user', 'assistant', or None."""
    if re.search(r"User\[|User:", header_rest):
        return "user", _extract_user_content(header_rest) or ""
    if "Assistant:" in header_rest:
        return "assistant", _extract_assistant_content(header_rest) or ""
    return None, ""


def _parse_messages(text: str) -> list[dict[str, str]]:
    matches = list(TIMESTAMP_LINE.finditer(text))
    messages: list[dict[str, str]] = []

    for index, match in enumerate(matches):
        timestamp = match.group(1)
        header_rest = match.group(2)
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        continuation = text[body_start:body_end].rstrip("\n")

        role, initial = _classify_message(header_rest)
        if role is None:
            continue

        parts = [initial]
        if continuation:
            parts.append(continuation)
        content = "\n".join(part for part in parts if part).strip()

        messages.append({"role": role, "timestamp": timestamp, "content": content})

    return messages


def _clean_answer(text: str) -> str:
    cleaned = REPLY_TAG.sub("", text.strip())
    cleaned = BLOCK_TAG.sub("", cleaned)
    cleaned = HTML_TAG.sub("", cleaned)
    return cleaned.strip()


def _extract_qa_pairs(messages: list[dict[str, str]]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    index = 0

    while index < len(messages):
        message = messages[index]
        if message["role"] != "user":
            index += 1
            continue

        question = message["content"]
        if "[主动消息-无用户输入]" in question:
            index += 2 if index + 1 < len(messages) and messages[index + 1]["role"] == "assistant" else 1
            continue

        if index + 1 >= len(messages) or messages[index + 1]["role"] != "assistant":
            index += 1
            continue

        answer = _clean_answer(messages[index + 1]["content"])
        if question and answer:
            pairs.append((question, answer))

        index += 2

    return pairs


def parse_chat_log(text: str) -> list[tuple[str, str]]:
    """Parse raw chat log text and return (question, answer) pairs."""
    return _extract_qa_pairs(_parse_messages(text))


def write_qa_csv(pairs: list[tuple[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(["Question", "Answer"])
        writer.writerows(pairs)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean chat logs and export User/Assistant pairs to CSV."
    )
    parser.add_argument("input", type=Path, help="Path to the source TXT chat log")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Path to output CSV (default: <input_stem>_qa.csv)",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    output_path = args.output or args.input.with_name(f"{args.input.stem}_qa.csv")
    text = args.input.read_text(encoding="utf-8")
    pairs = parse_chat_log(text)
    write_qa_csv(pairs, output_path)

    print(f"Extracted {len(pairs)} QA pair(s) -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
