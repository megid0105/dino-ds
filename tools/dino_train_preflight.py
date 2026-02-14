#!/usr/bin/env python3
"""
DinoDS train.jsonl quality preflight.

Fails fast if assistant_response looks like:
- numeric spam (many long digit tokens)
- anchor dumps (>=6 digit tokens in a row)
- field-dump fragments (too many ultra-short sentences)
This is designed to stop "QC-cheating" outputs before you upload to QC.

Usage:
  python3 tools/dino_train_preflight.py /path/to/train.jsonl
"""
import argparse, json, re, sys
from pathlib import Path

NUM_TOKEN = re.compile(r"\b\d{2,}\b")              # 2+ digit token
LONG_NUM_TOKEN = re.compile(r"\b\d{5,}\b")         # 5+ digits
MANY_NUMS_IN_ROW = re.compile(r"(?:\b\d{2,}\b[ \t]+){6,}\b\d{2,}\b")
SHORT_SENTENCE = re.compile(r"[A-Za-z\u00C0-\u024F\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u3040-\u30FF\u4E00-\u9FFF]+")

def is_field_dump(text: str) -> bool:
    # Heuristic: lots of tiny sentences separated by '.' and few verbs.
    parts = [p.strip() for p in re.split(r"[.\n]", text) if p.strip()]
    if len(parts) < 6:
        return False
    tiny = sum(1 for p in parts if len(p.split()) <= 4 and len(p) <= 24)
    return tiny >= 4

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl_path")
    ap.add_argument("--max_bad", type=int, default=0, help="Allow up to N bad lines (default 0)")
    args = ap.parse_args()

    p = Path(args.jsonl_path)
    bad = []
    total = 0

    with p.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                obj = json.loads(line)
            except Exception:
                bad.append((i, "invalid_json", ""))
                continue
            text = obj.get("assistant_response") or obj.get("messages", [{}])[-1].get("content", "")
            if not isinstance(text, str):
                continue

            if MANY_NUMS_IN_ROW.search(text):
                bad.append((i, "numeric_dump", text[:200]))
                continue
            if len(LONG_NUM_TOKEN.findall(text)) >= 3:
                bad.append((i, "long_numeric_tokens>=3", text[:200]))
                continue
            if is_field_dump(text):
                bad.append((i, "field_dump", text[:200]))
                continue

    if bad and len(bad) > args.max_bad:
        print(f"FAIL: {len(bad)} bad lines out of {total}")
        for i, reason, snippet in bad[:20]:
            print(f"- line {i}: {reason}: {snippet!r}")
        sys.exit(2)

    print(f"PASS: {total} lines checked; bad={len(bad)} (allowed={args.max_bad})")

if __name__ == "__main__":
    main()
