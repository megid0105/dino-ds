#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <lane_dir|lane_en.yaml>" >&2
  exit 2
fi

INPUT="$1"
if [ -d "$INPUT" ]; then
  LANE_DIR="$INPUT"
elif [ -f "$INPUT" ]; then
  LANE_DIR="$(dirname "$INPUT")"
else
  echo "ERROR: lane path not found: $INPUT" >&2
  exit 2
fi

LANE_DIR="$(cd "$LANE_DIR" && pwd -P)"
BASE_CFG="$LANE_DIR/lane_en.yaml"
if [ ! -f "$BASE_CFG" ]; then
  if [ -f "$LANE_DIR/lane_en.yaml" ]; then
    BASE_CFG="$LANE_DIR/lane_en.yaml"
  else
    echo "ERROR: lane_en.yaml not found in $LANE_DIR" >&2
    exit 2
  fi
fi

# Ensure venv exists (needed for PyYAML)
if [ ! -x "$ROOT/.venv/bin/python" ]; then
  ./scripts/run.sh --version >/dev/null
fi
PY="$ROOT/.venv/bin/python"

RUN_UUID="$("$PY" - <<'PY'
import uuid
print(uuid.uuid4().hex)
PY
)"

langs=(en zh-hk th zh-hant zh-hans pt-br es de fr it ja ko hi vi)

cfg_for_lang() {
  if [ "$1" = "en" ]; then
    if [ -f "$LANE_DIR/lane_en.yaml" ]; then
      echo "$LANE_DIR/lane_en.yaml"
    else
      echo "$LANE_DIR/lane_en.yaml"
    fi
  else
    echo "$LANE_DIR/lane_$1.yaml"
  fi
}

count_target_for_cfg() {
  "$PY" - "$1" <<'PY'
import sys
import yaml
from pathlib import Path

cfg = Path(sys.argv[1])
obj = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
te = obj.get("template_expand") if isinstance(obj.get("template_expand"), dict) else {}
ct = te.get("count_target") if isinstance(te.get("count_target"), int) and te.get("count_target") > 0 else obj.get("count_target")
if not isinstance(ct, int) or ct <= 0:
    raise SystemExit("ERROR: count_target missing or invalid in " + str(cfg))
print(ct)
PY
}

resolve_out_root() {
  "$PY" - "$1" "$LANE_DIR" <<'PY'
import sys
from pathlib import Path
import yaml

cfg = Path(sys.argv[1])
lane_dir = Path(sys.argv[2])
obj = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
out_root = lane_dir / "out"
od = obj.get("output_dir")
if isinstance(od, str) and od.strip():
    od_path = Path(od.strip())
    out_root = od_path if od_path.is_absolute() else (lane_dir / od_path)
print(out_root.resolve())
PY
}

train_paths=()
val_paths=()
test_paths=()
total_lines=0
out_root=""

for lang in "${langs[@]}"; do
  cfg="$(cfg_for_lang "$lang")"
  if [ ! -f "$cfg" ]; then
    echo "ERROR: missing config for $lang: $cfg" >&2
    exit 2
  fi
  ct="$(count_target_for_cfg "$cfg")"
  total_lines=$((total_lines + ct))

  echo "==> PROD sweep: $lang (count_target $ct)"
  DINO_DS_RUN_UUID="$RUN_UUID" DINO_DS_SKIP_OLLAMA=1 ./scripts/run.sh gate lane --config "$cfg" --limit "$ct"

  out_root="$(resolve_out_root "$cfg")"
  tef_dir="$out_root/dino-tef-${lang}-${ct}-${RUN_UUID}"
  train_path="$tef_dir/train.jsonl"
  val_path="$tef_dir/val.jsonl"
  test_path="$tef_dir/test.jsonl"
  if [ ! -f "$train_path" ]; then
    echo "ERROR: train.jsonl not found: $train_path" >&2
    exit 2
  fi
  train_paths+=("$train_path")
  if [ -f "$val_path" ]; then
    val_paths+=("$val_path")
  fi
  if [ -f "$test_path" ]; then
    test_paths+=("$test_path")
  fi
done

all_dir="$out_root/ALL/dino-tef-all-${total_lines}-${RUN_UUID}"
mkdir -p "$all_dir"
cat "${train_paths[@]}" > "$all_dir/train.jsonl"
shasum -a 256 "$all_dir/train.jsonl" | awk '{print $1}' > "$all_dir/train.jsonl.sha256"
if [ "${#val_paths[@]}" -gt 0 ]; then
  cat "${val_paths[@]}" > "$all_dir/val.jsonl"
  shasum -a 256 "$all_dir/val.jsonl" | awk '{print $1}' > "$all_dir/val.jsonl.sha256"
fi
if [ "${#test_paths[@]}" -gt 0 ]; then
  cat "${test_paths[@]}" > "$all_dir/test.jsonl"
  shasum -a 256 "$all_dir/test.jsonl" | awk '{print $1}' > "$all_dir/test.jsonl.sha256"
fi

echo "PROD sweep complete."
echo "RUN_UUID=$RUN_UUID"
echo "Combined train.jsonl: $all_dir/train.jsonl"
