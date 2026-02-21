#!/usr/bin/env bash

# Guard: this wrapper is executable, not source-able.
_DINO_WRAPPER_SOURCED=0
if [[ -n "${BASH_VERSION-}" ]]; then
  if [[ "${BASH_SOURCE[0]-$0}" != "$0" ]]; then
    _DINO_WRAPPER_SOURCED=1
  fi
elif [[ -n "${ZSH_VERSION-}" ]]; then
  case "${ZSH_EVAL_CONTEXT-}" in
    *:file) _DINO_WRAPPER_SOURCED=1 ;;
  esac
fi
if [[ "$_DINO_WRAPPER_SOURCED" -eq 1 ]]; then
  echo "ERROR: do not source ./dino-ds" >&2
  echo "Use this instead: source ./dino-shell.sh" >&2
  return 1 2>/dev/null || exit 1
fi
unset _DINO_WRAPPER_SOURCED

set -euo pipefail

if [[ -n "${BASH_SOURCE[0]-}" ]]; then
  _DINO_WRAPPER_SELF="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION-}" ]]; then
  _DINO_WRAPPER_SELF="${(%):-%x}"
else
  _DINO_WRAPPER_SELF="$0"
fi
ROOT="$(cd "$(dirname "$_DINO_WRAPPER_SELF")" && pwd -P)"
unset _DINO_WRAPPER_SELF
BIN="$ROOT/dino-ds-bin"

LANGS=(en zh-hk th zh-hant zh-hans pt-br es de fr it ja ko hi vi)
LANG_SUFFIX_ORDER=(zh-hans zh-hant zh-hk pt-br en th es de fr it ja ko hi vi)

# Keep operator settings local to this package by default.
if [[ -z "${DINO_DS_TOOL_CONFIG_PATH:-}" ]]; then
  export DINO_DS_TOOL_CONFIG_PATH="$ROOT/.dino_ds_tool_config.json"
fi

usage() {
  cat >&2 <<'USAGE'
usage:
  ./dino-ds lane_XX_<lang> [--teacher] [--rule 0X] [--limit N] [--seed N]   # run one language config
  ./dino-ds lane_XX [--teacher] [--rule 0X] [--limit N] [--seed N]          # run lane_en.yaml
  ./dino-ds run lane_XX [--teacher] [--rule 0X] [--seed N]                  # full 14-lang prod sweep + combine
  ./dino-ds qc lane_XX_<lang> [--teacher] [--rule 0X] [--seed N]            # single-language QC run (QC limit)
  ./dino-ds qc lane_XX [--teacher] [--rule 0X] [--seed N]                   # full 14-lang QC sweep + combine

compat aliases:
  ./dino-ds lane_XX run [--teacher] [--rule 0X]
  ./dino-ds lane_XX qc  [--teacher] [--rule 0X]

flags:
  --teacher
    Force teacher runtime rewrite for this invocation only.
    Uses lane teacher config (provider/model/prompt/policy).
    If lane sampling is 0, it is lifted for this run.
    Requires reachable Ollama + model.
  --rule 01|02|03
    Override validator strictness for this run only.
  --limit N
    Cap generated rows for single-lane run; QC sweep uses fixed per-language limits.
  --seed N
    Deterministic seed override for the run.

pass-through:
  ./dino-ds help                               # command reference
  ./dino-ds help quickstart                    # one-screen operator flow
  ./dino-ds help spec lane_XX                  # lane-specific validator contract
  ./dino-ds help validator                     # strictness/profile help
  ./dino-ds help run                           # run/qc flags and examples
  ./dino-ds help paths                         # output dir settings
  ./dino-ds help prompts                       # system/teacher prompt files
  ./dino-ds validator_level_set 01|02|03       # save default strictness
  ./dino-ds validator_level_check              # show active strictness
  ./dino-ds validator_level_reset              # reset strictness to default behavior
  ./dino-ds qc_report_dir_set <path>           # set QC markdown output directory
  ./dino-ds qc_report_dir_check                # show QC markdown output directory
  ./dino-ds qc_report_dir_reset                # reset QC markdown output directory
  ./dino-ds set_output_dir <path>              # set all-lane dataset output base path
  ./dino-ds set_output_dir lane_xx <path>      # set one-lane dataset output path
  ./dino-ds output_dir_check [lane_xx]         # show effective dataset output path
  ./dino-ds reset_output_dir [lane_xx]         # reset dataset output path(s)
  ./dino-ds validate ... | lint ... | build ... | split ... | pack ... | export ... | gate ...

optional shell setup (for bare commands):
  source ./dino-shell.sh
  help
  run lane_03
  validator_level_check
  lane_03_en --limit 20
USAGE
}

if [[ ! -x "$BIN" ]]; then
  echo "ERROR: dino-ds-bin not found or not executable at: $BIN" >&2
  exit 1
fi

uuid_hex() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr 'A-Z' 'a-z' | tr -d '-'
    return
  fi
  printf "%s%x" "$(date +%s)" "$$"
}

lane_dir_for_token() {
  local token="$1"
  if [[ -d "$ROOT/lanes/$token" ]]; then
    printf "%s\n" "$ROOT/lanes/$token"
    return 0
  fi

  if [[ "$token" =~ ^lane_([0-9]{1,2})(_.+)?$ ]]; then
    local n
    n="${BASH_REMATCH[1]}"
    local prefix
    printf -v prefix "lane_%02d" "$n"
    local matches=()
    while IFS= read -r d; do
      matches+=("$d")
    done < <(find "$ROOT/lanes" -maxdepth 1 -type d -name "${prefix}_*" | sort)
    if [[ ${#matches[@]} -eq 1 ]]; then
      printf "%s\n" "${matches[0]}"
      return 0
    fi
    if [[ ${#matches[@]} -gt 1 ]]; then
      echo "ERROR: ambiguous lane token '$token' (matches: ${matches[*]})" >&2
      return 2
    fi
  fi

  echo "ERROR: lane not found for token '$token'" >&2
  return 2
}

parse_lane_lang_token() {
  local token="$1"
  local base="$token"
  local lang=""

  for l in "${LANG_SUFFIX_ORDER[@]}"; do
    local suffix="_${l}"
    if [[ "$token" == *"$suffix" ]]; then
      base="${token%$suffix}"
      lang="$l"
      break
    fi
  done

  if [[ -z "$lang" ]]; then
    lang="en"
  fi
  printf "%s|%s\n" "$base" "$lang"
}

token_has_lang_suffix() {
  local token="$1"
  for l in "${LANG_SUFFIX_ORDER[@]}"; do
    local suffix="_${l}"
    if [[ "$token" == *"$suffix" ]]; then
      return 0
    fi
  done
  return 1
}

cfg_for_lane_lang() {
  local lane_dir="$1"
  local lang="$2"
  local cfg="$lane_dir/lane_${lang}.yaml"
  if [[ "$lang" == "en" ]]; then
    cfg="$lane_dir/lane_en.yaml"
  fi
  if [[ ! -f "$cfg" ]]; then
    echo "ERROR: missing config for lang '$lang': $cfg" >&2
    return 2
  fi
  printf "%s\n" "$cfg"
}

sha256_sidecar() {
  local f="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}' > "${f}.sha256"
    return
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$f" | awk '{print $1}' > "${f}.sha256"
    return
  fi
  echo "WARN: no shasum/sha256sum found; skipping sha256 sidecar for $f" >&2
}

latest_tef_dir_for_run_lang() {
  local lang="$1"
  local run_uuid="$2"
  find "$ROOT" -type d -name "dino-tef-${lang}-*-${run_uuid}" | sort | tail -n 1
}

qc_limit_for_lang() {
  case "$1" in
    en) echo 200 ;;
    zh-hk|th) echo 150 ;;
    *) echo 100 ;;
  esac
}

run_sweep() {
  local mode="$1"   # prod|qc
  local lane_token="$2"
  shift 2

  local lane_dir
  lane_dir="$(lane_dir_for_token "$lane_token")"

  local run_uuid
  run_uuid="$(uuid_hex)"

  local train_paths=()
  local val_paths=()
  local test_paths=()
  local failed_langs=()
  local total_lines=0
  local out_root=""

  for lang in "${LANGS[@]}"; do
    local cfg
    if ! cfg="$(cfg_for_lane_lang "$lane_dir" "$lang")"; then
      if [[ "$mode" == "qc" ]]; then
        failed_langs+=("$lang")
        continue
      fi
      exit 2
    fi

    local gate_args=(gate lane --config "$cfg")
    if [[ "$mode" == "qc" ]]; then
      gate_args+=(--limit "$(qc_limit_for_lang "$lang")")
      echo "==> QC sweep: $lang (limit $(qc_limit_for_lang "$lang"))"
    else
      echo "==> PROD sweep: $lang (full count_target)"
    fi
    if ! DINO_DS_RUN_UUID="$run_uuid" "$BIN" "${gate_args[@]}" "$@"; then
      if [[ "$mode" == "qc" ]]; then
        echo "WARN: gate failed for $lang; skipping this language in ALL bundle." >&2
        failed_langs+=("$lang")
        continue
      fi
      echo "ERROR: gate failed for $lang (prod sweep aborts)." >&2
      exit 1
    fi

    local tef_dir
    tef_dir="$(latest_tef_dir_for_run_lang "$lang" "$run_uuid")"
    if [[ -z "$tef_dir" ]]; then
      if [[ "$mode" == "qc" ]]; then
        echo "WARN: missing TEF dir for $lang run_uuid=$run_uuid; skipping." >&2
        failed_langs+=("$lang")
        continue
      fi
      echo "ERROR: missing TEF dir for $lang run_uuid=$run_uuid" >&2
      exit 1
    fi

    local train_path="$tef_dir/train.jsonl"
    local val_path="$tef_dir/val.jsonl"
    local test_path="$tef_dir/test.jsonl"
    if [[ ! -f "$train_path" ]]; then
      if [[ "$mode" == "qc" ]]; then
        echo "WARN: missing train.jsonl for $lang at $train_path; skipping." >&2
        failed_langs+=("$lang")
        continue
      fi
      echo "ERROR: missing train.jsonl for $lang at $train_path" >&2
      exit 1
    fi

    train_paths+=("$train_path")
    if [[ -f "$val_path" ]]; then
      val_paths+=("$val_path")
    fi
    if [[ -f "$test_path" ]]; then
      test_paths+=("$test_path")
    fi

    local n
    n="$(wc -l < "$train_path" | tr -d ' ')"
    total_lines=$((total_lines + n))

    if [[ -z "$out_root" ]]; then
      out_root="$(dirname "$tef_dir")"
    fi
  done

  if [[ ${#train_paths[@]} -eq 0 ]]; then
    echo "ERROR: no successful language outputs were produced." >&2
    exit 2
  fi

  local all_dir="$out_root/ALL/dino-tef-all-${total_lines}-${run_uuid}"
  mkdir -p "$all_dir"
  cat "${train_paths[@]}" > "$all_dir/train.jsonl"
  sha256_sidecar "$all_dir/train.jsonl"
  if [[ ${#val_paths[@]} -gt 0 ]]; then
    cat "${val_paths[@]}" > "$all_dir/val.jsonl"
    sha256_sidecar "$all_dir/val.jsonl"
  fi
  if [[ ${#test_paths[@]} -gt 0 ]]; then
    cat "${test_paths[@]}" > "$all_dir/test.jsonl"
    sha256_sidecar "$all_dir/test.jsonl"
  fi

  if [[ "$mode" == "qc" ]]; then
    echo "QC sweep complete."
  else
    echo "PROD sweep complete."
  fi
  echo "RUN_UUID=$run_uuid"
  echo "Combined train.jsonl: $all_dir/train.jsonl"

  if [[ ${#failed_langs[@]} -gt 0 ]]; then
    echo "FAILED_LANGS=${failed_langs[*]}" >&2
    exit 1
  fi
}

run_single() {
  local lane_lang_token="$1"
  shift
  local parsed
  parsed="$(parse_lane_lang_token "$lane_lang_token")"
  local lane_token="${parsed%%|*}"
  local lang="${parsed##*|}"

  local lane_dir
  lane_dir="$(lane_dir_for_token "$lane_token")"
  local cfg
  cfg="$(cfg_for_lane_lang "$lane_dir" "$lang")"

  exec "$BIN" gate lane --config "$cfg" "$@"
}

run_single_qc() {
  local lane_lang_token="$1"
  shift
  local parsed
  parsed="$(parse_lane_lang_token "$lane_lang_token")"
  local lane_token="${parsed%%|*}"
  local lang="${parsed##*|}"

  local lane_dir
  lane_dir="$(lane_dir_for_token "$lane_token")"
  local cfg
  cfg="$(cfg_for_lane_lang "$lane_dir" "$lang")"
  local limit
  limit="$(qc_limit_for_lang "$lang")"

  echo "==> QC single: $lang (limit $limit)"
  exec "$BIN" gate lane --config "$cfg" --limit "$limit" "$@"
}

if [[ $# -eq 0 ]]; then
  usage
  exit 1
fi

case "$1" in
  help)
    shift
    "$BIN" help "$@"
    cat <<'NOTE'

Bare command mode (package root):
  source ./dino-shell.sh

After sourcing, dino-ds commands can be called bare in this shell session:
  help
  run lane_01
  qc lane_01
  validator_level_check
  lane_03_en --limit 20

If you open a new terminal, source ./dino-shell.sh again.
NOTE
    ;;
  run)
    shift
    [[ $# -ge 1 ]] || { usage; exit 1; }
    run_sweep "prod" "$1" "${@:2}"
    ;;
  qc)
    shift
    [[ $# -ge 1 ]] || { usage; exit 1; }
    if token_has_lang_suffix "$1"; then
      run_single_qc "$1" "${@:2}"
    else
      run_sweep "qc" "$1" "${@:2}"
    fi
    ;;
  lane_*)
    token="$1"
    if [[ "${2:-}" == "run" ]]; then
      shift 2
      run_sweep "prod" "$token" "$@"
      exit
    fi
    if [[ "${2:-}" == "qc" ]]; then
      shift 2
      if token_has_lang_suffix "$token"; then
        run_single_qc "$token" "$@"
      else
        run_sweep "qc" "$token" "$@"
      fi
      exit
    fi
    shift
    run_single "$token" "$@"
    ;;
  set_validator_level|validator_level_set|validator_level_check|validator_level_reset|qc_report_dir_set|qc_report_dir_check|qc_report_dir_reset|set_output_dir|reset_output_dir|lane_output_dir_set|output_dir_check|output_dir_reset|validate|lint|build|split|pack|export|gate|golden|sources|fixtures|smoke)
    exec "$BIN" "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac
