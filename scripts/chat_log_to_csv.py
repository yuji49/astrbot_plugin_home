#!/usr/bin/env python3
"""Parse chat log TXT files into Question/Answer CSV pairs."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

CHUNK_SIZE = 10_000

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

SYSTEM_RECORD_START = re.compile(r"^\s*\[系统记录")
SYSTEM_METADATA_LINE = re.compile(
    r"^(?:"
    r"触发查询[:：]|歌曲[:：]|歌手(?:/作者)?[:：]|作者[:：]|"
    r"网易云|分享方式[:：]|别名[:：]|专辑[:：]|歌词节选[:：]?|"
    r"原始链接[:：]|注意[:：]|"
    r"https?://|"
    r"[^\s：]{1,30}ID[:：]|"
    r"\s*$"
    r")",
)
SYSTEM_TAG_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\[图片:.*?\]", re.DOTALL), ""),
    (re.compile(r"\[reply:\d+\]", re.IGNORECASE), ""),
    (re.compile(r"\[photo:[\s\S]*?\]", re.IGNORECASE), ""),
    (re.compile(r"\[📞视频通话\]\s*"), ""),
    (re.compile(r"\[引用消息[^\]]*\][\s\S]*?\[/引用消息\]"), ""),
    (re.compile(r"\[引用消息[\s\S]*?\]"), ""),
    (re.compile(r"\[系统提示[\s\S]*?\]"), ""),
    (re.compile(r"\[语音消息\]\s*"), ""),
    (re.compile(r"\[系统记录[^\]]*\]"), ""),
)
STANDALONE_SYSTEM_TAG = re.compile(
    r"\[[^\[\]\n]*(?:"
    r"[:：]|系统|记录|图片|photo|reply|语音|视频|引用|提示|雷达|抖音|小红书|"
    r"网易云|监控|插件|主动消息|回复\s*\d|http"
    r")[^\[\]\n]*\]",
    re.IGNORECASE,
)


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


def _looks_like_system_continuation(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if SYSTEM_METADATA_LINE.match(stripped):
        return True
    if stripped.startswith("["):
        return True
    if re.match(r"^[\s　]*[^\s：]{1,30}[:：]", stripped):
        return True
    if len(stripped) <= 40 and not re.search(r"[。！？?!?，,.]", stripped):
        return True
    return False


def _strip_system_record_blocks(text: str) -> str:
    lines = text.split("\n")
    result: list[str] = []
    skip_block = False

    for line in lines:
        stripped = line.strip()
        if SYSTEM_RECORD_START.match(stripped):
            skip_block = True
            continue

        if skip_block:
            if not stripped:
                continue
            if re.match(r"^注意[:：]", stripped):
                skip_block = False
                continue
            if _looks_like_system_continuation(line):
                continue
            skip_block = False

        if not skip_block:
            result.append(line)

    return "\n".join(result)


def _apply_system_tag_patterns(text: str) -> str:
    for pattern, replacement in SYSTEM_TAG_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_content(text: str) -> str:
    """Remove plugin/system junk from a Question or Answer body."""
    cleaned = _strip_system_record_blocks(text.strip())
    cleaned = _apply_system_tag_patterns(cleaned)
    cleaned = REPLY_TAG.sub("", cleaned)
    cleaned = BLOCK_TAG.sub("", cleaned)
    cleaned = HTML_TAG.sub("", cleaned)
    cleaned = STANDALONE_SYSTEM_TAG.sub("", cleaned)
    cleaned = _normalize_whitespace(cleaned)
    return cleaned


def _extract_qa_pairs(messages: list[dict[str, str]]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    index = 0

    while index < len(messages):
        message = messages[index]
        if message["role"] != "user":
            index += 1
            continue

        question = clean_content(message["content"])
        if "[主动消息-无用户输入]" in message["content"]:
            index += 2 if index + 1 < len(messages) and messages[index + 1]["role"] == "assistant" else 1
            continue

        if index + 1 >= len(messages) or messages[index + 1]["role"] != "assistant":
            index += 1
            continue

        answer = clean_content(messages[index + 1]["content"])
        if question and answer:
            pairs.append((question, answer))

        index += 2

    return pairs


def parse_chat_log(text: str) -> list[tuple[str, str]]:
    """Parse raw chat log text and return (question, answer) pairs."""
    return _extract_qa_pairs(_parse_messages(text))


def _write_single_csv(pairs: list[tuple[str, str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(["Question", "Answer"])
        writer.writerows(pairs)


def write_qa_csv(
    pairs: list[tuple[str, str]],
    output_path: Path,
    chunk_size: int = CHUNK_SIZE,
) -> list[Path]:
    """Write QA pairs to CSV, splitting into part files when chunk_size is exceeded."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not pairs:
        _write_single_csv(pairs, output_path)
        return [output_path]

    if len(pairs) <= chunk_size:
        _write_single_csv(pairs, output_path)
        return [output_path]

    written: list[Path] = []
    stem = output_path.stem
    suffix = output_path.suffix or ".csv"
    parent = output_path.parent

    for part_index, start in enumerate(range(0, len(pairs), chunk_size), start=1):
        chunk = pairs[start : start + chunk_size]
        part_path = parent / f"{stem}_part{part_index}{suffix}"
        _write_single_csv(chunk, part_path)
        written.append(part_path)

    return written


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
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=CHUNK_SIZE,
        help=f"Max QA pairs per CSV file (default: {CHUNK_SIZE})",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    output_path = args.output or args.input.with_name(f"{args.input.stem}_qa.csv")
    text = args.input.read_text(encoding="utf-8")
    pairs = parse_chat_log(text)
    written_paths = write_qa_csv(pairs, output_path, chunk_size=args.chunk_size)

    if len(written_paths) == 1:
        print(f"Extracted {len(pairs)} QA pair(s) -> {written_paths[0]}")
    else:
        print(f"Extracted {len(pairs)} QA pair(s) -> {len(written_paths)} file(s):")
        for path in written_paths:
            print(f"  - {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
