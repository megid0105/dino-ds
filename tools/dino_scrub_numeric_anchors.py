#!/usr/bin/env python3

"""
Scrub numeric-anchor spam from DinoDS lane YAML files.

What it does (YAML-only):
- Removes any slot bank whose key name starts with "anchor" (anchor, anchor_1, anchor_pack, etc.)
- Removes any scalar slot bank items that are digits-only (e.g., "33", "57467140")
- Removes "{anchor...}" placeholders from any string templates (q_template/a_skeleton/etc.)
- Writes a .bak backup next to each YAML before overwriting

Usage:
  python3 tools/dino_scrub_numeric_anchors.py lanes/lane_03_think_mode
  python3 tools/dino_scrub_numeric_anchors.py lanes/lane_04_quick_mode --dry-run
"""
import argparse
import re
from pathlib import Path

try:
    import yaml  # PyYAML
except Exception as e:
    raise SystemExit("PyYAML is required. Install with: pip install pyyaml") from e

DIGITS_ONLY_RE = re.compile(r"^\d{2,}$")  # 2+ digits
ANCHOR_KEY_RE = re.compile(r"^anchor", re.IGNORECASE)
ANCHOR_PLACEHOLDER_RE = re.compile(r"\{anchor[^}]*\}", re.IGNORECASE)

def scrub_strings(obj):
    """Recursively remove {anchor...} placeholders from strings."""
    if isinstance(obj, str):
        # Remove anchor placeholders and collapse extra spaces
        s = ANCHOR_PLACEHOLDER_RE.sub("", obj)
        s = re.sub(r"[ \t]{2,}", " ", s)
        s = re.sub(r" +\n", "\n", s)
        return s.strip() if s.strip() else s
    if isinstance(obj, list):
        return [scrub_strings(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub_strings(v) for k, v in obj.items()}
    return obj

def scrub_slot_banks(slot_banks: dict):
    """Remove anchor banks and digits-only scalar items."""
    if not isinstance(slot_banks, dict):
        return slot_banks

    new_banks = {}
    removed_keys = []
    removed_digit_items = 0

    for key, bank in slot_banks.items():
        if ANCHOR_KEY_RE.match(str(key)):
            removed_keys.append(key)
            continue

        # If bank is a list of scalars/dicts
        if isinstance(bank, list):
            new_list = []
            for item in bank:
                if isinstance(item, str) and DIGITS_ONLY_RE.match(item.strip()):
                    removed_digit_items += 1
                    continue
                new_list.append(item)
            new_banks[key] = new_list
        else:
            new_banks[key] = bank

    return new_banks, removed_keys, removed_digit_items

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lane_dir", help="Path to lane folder containing lane_*.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    lane_dir = Path(args.lane_dir)
    if not lane_dir.exists():
        raise SystemExit(f"Lane dir not found: {lane_dir}")

    yaml_files = sorted(lane_dir.glob("lane_*.yaml"))
    if not yaml_files:
        raise SystemExit(f"No lane_*.yaml files found under {lane_dir}")

    for yp in yaml_files:
        raw = yp.read_text(encoding="utf-8", errors="ignore")
        data = yaml.safe_load(raw)

        # Locate slot_banks
        te = data.get("template_expand", {})
        slot_banks = te.get("slot_banks", {})

        scrubbed_banks, removed_keys, removed_digit_items = scrub_slot_banks(slot_banks)

        te["slot_banks"] = scrubbed_banks
        data["template_expand"] = te

        # Scrub {anchor...} placeholders everywhere
        data = scrub_strings(data)

        # Write backup + overwrite
        print(f"\n== {yp} ==")
        print(f"removed slot_banks keys: {removed_keys if removed_keys else 'none'}")
        print(f"removed digits-only items: {removed_digit_items}")

        if args.dry_run:
            continue

        bak = yp.with_suffix(yp.suffix + ".bak")
        if not bak.exists():
            bak.write_text(raw, encoding="utf-8")
        yp.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print("\nDone.")
    print("Next: rebuild lane EN, then run QC. If templates still produce 'field dumps', fix a_skeleton to output real sentences + bullets.")
if __name__ == "__main__":
    main()
