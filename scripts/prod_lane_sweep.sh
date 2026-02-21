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

sanitize_qc_token() {
  raw="${1:-}"
  fallback="${2:-unknown}"
  raw="${raw//-/_}"
  raw="$(printf "%s" "$raw" | sed -E 's/[^A-Za-z0-9_]+/_/g; s/_+/_/g; s/^_+//; s/_+$//')"
  if [ -z "$raw" ]; then
    raw="$fallback"
  fi
  printf "%s\n" "$raw"
}

resolve_qc_report_dir() {
  qd="${DINO_DS_QC_REPORT_DIR:-}"
  if [ -z "$qd" ]; then
    printf "%s\n" "$ROOT/output QC report"
    return
  fi
  case "$qd" in
    /*) printf "%s\n" "$qd" ;;
    *) printf "%s\n" "$PWD/$qd" ;;
  esac
}

latest_qc_report_for_lang() {
  lane_safe="$1"
  lang="$2"
  run_uuid="$3"
  qc_dir="$4"
  lang_safe="$(sanitize_qc_token "$lang" "unknown")"
  pattern="QC_${lane_safe}_${lang_safe}_${run_uuid}_*.md"
  if [ -d "$qc_dir" ]; then
    report_path="$(find "$qc_dir" -maxdepth 1 -type f -name "$pattern" | sort | tail -n 1)"
  else
    report_path=""
  fi
  if [ -z "$report_path" ] && [ "$qc_dir" != "$ROOT" ]; then
    report_path="$(find "$ROOT" -maxdepth 1 -type f -name "$pattern" | sort | tail -n 1)"
  fi
  printf "%s\n" "$report_path"
}

qc_report_status_for_file() {
  p="$1"
  if [ -z "$p" ] || [ ! -f "$p" ]; then
    printf "%s\n" "MISSING"
    return
  fi
  if grep -Eq '^\|[[:space:]]*[^|]+[[:space:]]*\|[[:space:]]*FAIL[[:space:]]*\|' "$p"; then
    printf "%s\n" "FAIL"
    return
  fi
  if grep -Eq '^\|[[:space:]]*[^|]+[[:space:]]*\|[[:space:]]*WARN[[:space:]]*\|' "$p"; then
    printf "%s\n" "WARN"
    return
  fi
  printf "%s\n" "PASS"
}

write_combined_qc_report() {
  mode="$1"
  lane_dir="$2"
  run_uuid="$3"
  all_dir="$4"
  lane_id="$(basename "$lane_dir")"
  lane_safe="$(sanitize_qc_token "$lane_id" "lane")"
  qc_dir="$(resolve_qc_report_dir)"
  mkdir -p "$qc_dir"
  date_ymd="$(date +%F)"
  report_path="$qc_dir/QC_${lane_safe}_all_${run_uuid}_${date_ymd}.md"

  pass_n=0
  warn_n=0
  fail_n=0
  missing_n=0

  {
    echo "# QC Report — ${lane_id} — all"
    echo ""
    echo "## Sweep Metadata"
    echo "- lane_id: \`${lane_id}\`"
    echo "- language slice: \`all\`"
    echo "- run_id: \`${run_uuid}\`"
    echo "- sweep_mode: \`${mode}\`"
    echo "- date: \`${date_ymd}\`"
    echo "- combined_train_jsonl: \`${all_dir}/train.jsonl\`"
    echo ""
    echo "## Language Reports"
    echo "| Language | Status | Report |"
    echo "| --- | --- | --- |"
    for lang in "${langs[@]}"; do
      rp="$(latest_qc_report_for_lang "$lane_safe" "$lang" "$run_uuid" "$qc_dir")"
      st="$(qc_report_status_for_file "$rp")"
      case "$st" in
        PASS) pass_n=$((pass_n + 1)) ;;
        WARN) warn_n=$((warn_n + 1)) ;;
        FAIL) fail_n=$((fail_n + 1)) ;;
        *) missing_n=$((missing_n + 1)) ;;
      esac
      if [ -n "$rp" ]; then
        rp_cell="\`${rp}\`"
      else
        rp_cell="-"
      fi
      echo "| \`${lang}\` | ${st} | ${rp_cell} |"
    done
    echo ""
    echo "## Totals"
    echo "- pass_languages: \`${pass_n}\`"
    echo "- warn_languages: \`${warn_n}\`"
    echo "- fail_languages: \`${fail_n}\`"
    echo "- missing_languages: \`${missing_n}\`"
    echo ""
    echo "## Notes"
    echo "- This report aggregates per-language QC markdown outputs for the same run_id."
  } > "$report_path"

  printf "%s\n" "$report_path"
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

combined_qc_report="$(write_combined_qc_report "prod" "$LANE_DIR" "$RUN_UUID" "$all_dir")"

echo "PROD sweep complete."
echo "RUN_UUID=$RUN_UUID"
echo "Combined train.jsonl: $all_dir/train.jsonl"
echo "Combined QC report: $combined_qc_report"
