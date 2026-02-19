#!/usr/bin/env bash
# Source this file from package root to enable bare commands:
#   source ./dino-shell.sh
#
# After sourcing, both styles work:
#   ./dino-ds run lane_03
#   run lane_03
#
# And lane tokens can be called directly:
#   lane_03_en --limit 20

if [[ -n "${BASH_SOURCE[0]-}" ]]; then
  _DINO_SHELL_SRC="${BASH_SOURCE[0]}"
elif [[ -n "${ZSH_VERSION-}" ]]; then
  _DINO_SHELL_SRC="${(%):-%x}"
else
  _DINO_SHELL_SRC="$0"
fi

ROOT="$(cd "$(dirname "$_DINO_SHELL_SRC")" && pwd -P)"
unset _DINO_SHELL_SRC

export PATH="$ROOT:$PATH"
alias dino-ds="$ROOT/dino-ds"

_dino_exec() {
  "$ROOT/dino-ds" "$@"
}

# Common top-level commands as bare commands.
_DINO_BARE_CMDS=(
  help
  run
  qc
  validate
  lint
  build
  split
  pack
  export
  gate
  golden
  sources
  fixtures
  smoke
  set_validator_level
  validator_level_set
  validator_level_check
  validator_level_reset
  qc_report_dir_set
  qc_report_dir_check
  qc_report_dir_reset
  set_output_dir
  lane_output_dir_set
  output_dir_check
  output_dir_reset
  reset_output_dir
)

for _dino_cmd in "${_DINO_BARE_CMDS[@]}"; do
  eval "${_dino_cmd}() { _dino_exec ${_dino_cmd} \"\$@\"; }"
done
unset _dino_cmd
unset _DINO_BARE_CMDS

_dino_try_lane_token() {
  local cmd="$1"
  shift || true
  if [[ "$cmd" == lane_[0-9] || "$cmd" == lane_[0-9][0-9] || "$cmd" == lane_[0-9]_* || "$cmd" == lane_[0-9][0-9]_* ]]; then
    _dino_exec "$cmd" "$@"
    return $?
  fi
  return 127
}

# Support bare lane tokens like `lane_03_en` or `lane_03`.
if [[ -n "${BASH_VERSION-}" ]]; then
  command_not_found_handle() {
    _dino_try_lane_token "$@"
    local rc=$?
    if [[ $rc -ne 127 ]]; then
      return $rc
    fi
    echo "bash: $1: command not found" >&2
    return 127
  }
elif [[ -n "${ZSH_VERSION-}" ]]; then
  command_not_found_handler() {
    _dino_try_lane_token "$@"
    local rc=$?
    if [[ $rc -ne 127 ]]; then
      return $rc
    fi
    echo "zsh: command not found: $1" >&2
    return 127
  }
fi
