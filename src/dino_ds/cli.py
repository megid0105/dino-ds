from __future__ import annotations

import argparse
import sys
import json
import traceback
from pathlib import Path
import re
import os
import uuid

import hashlib
import subprocess
import zipfile

import yaml

from . import __version__
from . import exit_codes as ec

from .commands import validate_cmd, lint_cmd, sources_cmd, fixtures_cmd
from .commands import build_cmd, split_cmd, pack_cmd, golden_cmd, stubs
from .contracts.v16_lane_contracts import ALLOWED_LABEL_KEYS


_CONTEXT_RE = re.compile(r"\bcontext\b|conversation so far|conversation:", re.IGNORECASE)


def _labels_allowlist_v16() -> list[str]:
    allow = set(ALLOWED_LABEL_KEYS)
    for k in ("messages", "user_message", "assistant_response", "system_prompt_id", "sample_id", "id", "target_base"):
        allow.discard(k)
    return sorted(allow)


def _run_uuid() -> str:
    rid = os.environ.get("DINO_DS_RUN_UUID", "").strip()
    if rid:
        return rid
    return uuid.uuid4().hex


def _lane_language_tag(
    lane_obj: dict[str, object],
    te_base: dict[str, object],
    base_row: dict[str, object],
) -> str:
    # Prefer explicit language keys; fall back to template_expand.slot_banks.language if it is a single value.
    for v in (lane_obj.get("language"), te_base.get("language"), base_row.get("language")):
        if isinstance(v, str) and v.strip():
            return v.strip()
    te = lane_obj.get("template_expand")
    if isinstance(te, dict):
        slot_banks = te.get("slot_banks")
        if isinstance(slot_banks, dict):
            langs = slot_banks.get("language")
            if isinstance(langs, list) and len(langs) == 1 and isinstance(langs[0], str) and langs[0].strip():
                return langs[0].strip()
    return "en"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dino-ds")
    p.add_argument("--version", action="version", version=f"dino-ds {__version__}")

    sub = p.add_subparsers(dest="cmd", required=True)

    # P0 hard gates
    pv = sub.add_parser("validate", help="Validate config against schema(s)")
    pv.add_argument("--schema", required=False, default="lane")  # invalid schema must return exit=6
    pv.add_argument("--config", required=True)

    pl = sub.add_parser("lint", help="Run local lint gates (no-network)")
    pl.add_argument("--qa-jsonl", required=False, default=None)
    pl.add_argument("--pct-jsonl", required=False, default=None)

    # P1: build lane (+ stub build qa for now)
    pb = sub.add_parser("build", help="Build datasets")
    bsub = pb.add_subparsers(dest="build_cmd", required=True)

    bl = bsub.add_parser("lane", help="Build a lane dataset -> JSONL")
    bl.add_argument("--config", required=True)
    bl.add_argument("--out", required=True)
    bl.add_argument("--seed", required=False, default="0")
    bl.add_argument("--limit", required=False, default=None)

    bq = bsub.add_parser("qa", help="Build QA dataset (NYI in P1)")
    bq.add_argument("--config", required=True)
    bq.add_argument("--out", required=True)
    bq.add_argument("--seed", required=False, default="0")

    # P1: split / pack
    ps = sub.add_parser("split", help="Split JSONL -> train/val/test")
    ps.add_argument("--in", dest="in_path", required=True)
    ps.add_argument("--outdir", required=True)
    ps.add_argument("--seed", required=False, default="0")
    ps.add_argument("--train", required=False, default="0.9")
    ps.add_argument("--val", required=False, default="0.05")
    ps.add_argument("--test", required=False, default="0.05")
    ps.add_argument("--min-per-nonzero-split", required=False, default="0")

    pp = sub.add_parser("pack", help="Emit dataset_manifest.json (sha256/rows)")
    pp.add_argument("--indir", required=True)
    pp.add_argument("--out", required=True)

    # P3: export (train-ready formats)
    pe = sub.add_parser("export", help="Export train-ready formats")
    esub = pe.add_subparsers(dest="export_cmd", required=True)

    eq = esub.add_parser("qwen", help="Export label-standard JSONL -> Qwen chat JSONL")
    eq.add_argument("--indir", required=True, help="Directory containing train/val/test.jsonl")
    eq.add_argument("--outdir", required=True, help="Output directory for exported JSONL")
    eq.add_argument("--system", required=False, default="", help="System prompt ID (key in system_prompt_registry.json)")
    eq.add_argument("--system-file", required=False, default=None, help="Path to a text file containing the system prompt ID")
    eq.add_argument(
        "--target-base",
        dest="target_base",
        required=False,
        default="",
        help="Override target_base for TEF output when input records are missing target_base",
    )
    eq.add_argument("--keep-labels", action="store_true", help="Include label fields under a `labels` object")
    eq.add_argument("--include-id", action="store_true", help="Include sample_id as `id` in the exported record")

    # Gate (single-entrypoint teammate workflow): validate -> build -> split -> export -> pack -> proofs -> zip
    pgate = sub.add_parser("gate", help="Run end-to-end lane gate (no-network)")
    gsub2 = pgate.add_subparsers(dest="gate_cmd", required=True)

    gl = gsub2.add_parser("lane", help="Gate a lane end-to-end and produce uploadable zip")
    gl.add_argument("--config", required=True)
    gl.add_argument("--limit", required=False, default=None)
    gl.add_argument("--seed", required=False, default="0")
    # P2: golden
    pg = sub.add_parser("golden", help="Golden suite ops")
    gsub = pg.add_subparsers(dest="golden_cmd", required=True)

    gg = gsub.add_parser("gen", help="Generate golden_eval.jsonl (CPU-only)")
    gg.add_argument("--out", required=True)
    gg.add_argument("--count", required=False, default="400")
    gg.add_argument("--seed", required=False, default="0")

    gr = gsub.add_parser("run", help="Run golden eval (structure-only for engine=none)")
    gr.add_argument("--engine", required=False, default="none", choices=["none", "dino", "dino_pro"])
    gr.add_argument("--golden", required=True)

    # PCT addendum
    psr = sub.add_parser("sources", help="SourcePack ops")
    ss = psr.add_subparsers(dest="sources_cmd", required=True)
    sv = ss.add_parser("verify", help="Verify SourcePack manifest + sha256")
    sv.add_argument("--manifest", required=True)

    pfr = sub.add_parser("fixtures", help="ToolReplayFixture ops")
    fs = pfr.add_subparsers(dest="fixtures_cmd", required=True)
    fv = fs.add_parser("verify", help="Verify fixture manifest + sha256")
    fv.add_argument("--manifest", required=True)

    sub.add_parser("smoke", help="Quick smoke test (NYI)")

    return p


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_sha256_sidecar(path: Path) -> Path:
    digest = _sha256_file(path)
    side = Path(str(path) + ".sha256")
    side.write_text(digest + "\n", encoding="utf-8")
    return side


def _git_sha() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        s = out.decode("utf-8").strip()
        return s if s else "unknown"
    except Exception:
        return "unknown"


def _canonicalize_target_base(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    aliases = {
        "dino_4b": "dino_qwen4b",
        "dinoPro-7b": "dinoPro_qwen7b",
        "dinoPro-qwen7b": "dinoPro_qwen7b",
    }
    s2 = aliases.get(s, s)
    return s2


def _require_allowed_target_base(tb: str) -> tuple[bool, str]:
    # Hard-ban qa/test in trainer-facing TEF
    banned = {"qa", "test"}
    if tb in banned:
        return False, f"target_base is banned: {tb}"
    allowed = {"dino_qwen4b", "dinoPro_qwen7b"}
    if tb not in allowed:
        return False, f"target_base not allowed: {tb} (allowed: {sorted(allowed)})"
    return True, ""


def _export_qwen_tef_v1(
    *,
    indir: Path,
    outdir: Path,
    system_prompt_id: str,
    registry: dict[str, str],
    split_name: str,
    target_base: str,
    labels_allowlist: list[str],
) -> int:
    """Export split JSONL -> dino-tef-v1 strict rows.

    Output keys include: sample_id, id, target_base, messages, user_message, assistant_response,
    and all allowlisted label fields copied to the top level (no nested labels object).
    Messages roles/order: system -> user -> assistant
    """
    in_path = indir / f"{split_name}.jsonl"
    if not in_path.exists():
        print(f"ERROR: input split not found: {in_path}", file=sys.stderr)
        return 2

    out_path = outdir / f"{split_name}.jsonl"
    tmp_path = outdir / f".{split_name}.jsonl.tmp"

    if not isinstance(registry, dict) or not registry:
        print("ERROR: system prompt registry is empty or invalid", file=sys.stderr)
        return 2

    wrote = 0
    try:
        with in_path.open("r", encoding="utf-8") as fin, tmp_path.open("w", encoding="utf-8") as fout:
            for line_no, line in enumerate(fin, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception as e:
                    print(f"ERROR: bad JSON at {in_path}:{line_no}: {e}", file=sys.stderr)
                    return 2

                # Resolve ids
                sample_id = None
                if isinstance(rec.get("sample_id"), str) and rec.get("sample_id").strip():
                    sample_id = rec.get("sample_id").strip()
                elif isinstance(rec.get("id"), str) and rec.get("id").strip():
                    sample_id = rec.get("id").strip()
                if not sample_id:
                    print(f"ERROR: missing sample_id/id at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                rec_id = None
                if isinstance(rec.get("id"), str) and rec.get("id").strip():
                    rec_id = rec.get("id").strip()
                else:
                    # If id not present, set it to sample_id (still stable and non-empty)
                    rec_id = sample_id

                # Build messages (system prompt resolved by system_prompt_id + registry)
                msgs: list[dict[str, str]] = []
                spid = ""
                rec_spid = rec.get("system_prompt_id")
                if isinstance(rec_spid, str) and rec_spid.strip():
                    spid = rec_spid.strip()
                elif isinstance(system_prompt_id, str) and system_prompt_id.strip():
                    spid = system_prompt_id.strip()

                if not spid:
                    print(f"ERROR: missing system_prompt_id at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                system_text = registry.get(spid, "")
                if not system_text:
                    print(f"ERROR: unknown system_prompt_id '{spid}' at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                msgs.append({"role": "system", "content": system_text})

                rec_messages = rec.get("messages")
                system_extra = ""
                user_text = rec.get("user_message")
                if not (isinstance(user_text, str) and user_text.strip()):
                    user_text = rec.get("user_prompt")
                assistant_text = rec.get("assistant_response")

                if isinstance(rec_messages, list) and rec_messages:
                    if len(rec_messages) < 3:
                        print(f"ERROR: messages must be [system,user,assistant] at {in_path}:{line_no}", file=sys.stderr)
                        return 2
                    m0, m1, m2 = rec_messages[0], rec_messages[1], rec_messages[2]
                    if not (
                        isinstance(m0, dict)
                        and isinstance(m1, dict)
                        and isinstance(m2, dict)
                        and m0.get("role") == "system"
                        and m1.get("role") == "user"
                        and m2.get("role") == "assistant"
                    ):
                        print(f"ERROR: messages must be [system,user,assistant] at {in_path}:{line_no}", file=sys.stderr)
                        return 2
                    sys_content = m0.get("content")
                    if isinstance(sys_content, str) and sys_content.strip():
                        system_extra = sys_content.strip()
                    if not (isinstance(user_text, str) and user_text.strip()):
                        ucontent = m1.get("content")
                        if isinstance(ucontent, str) and ucontent.strip():
                            user_text = ucontent
                    if not (isinstance(assistant_text, str) and assistant_text.strip()):
                        acontent = m2.get("content")
                        if isinstance(acontent, str) and acontent.strip():
                            assistant_text = acontent

                if not (isinstance(user_text, str) and user_text.strip()):
                    print(f"ERROR: missing user_message/user_prompt at {in_path}:{line_no}", file=sys.stderr)
                    return 2
                if not (isinstance(assistant_text, str) and (assistant_text.strip() or assistant_text == "")):
                    print(f"ERROR: missing assistant_response at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                user_content = user_text.strip()
                if system_extra and _CONTEXT_RE.search(system_extra):
                    user_content = system_extra + "\n\n" + user_content

                msgs.append({"role": "user", "content": user_content})
                msgs.append({"role": "assistant", "content": assistant_text.strip()})

                # Enforce role order presence
                roles = [m.get("role") for m in msgs if isinstance(m, dict)]
                if roles.count("system") > 1:
                    print(f"ERROR: multiple system messages at {in_path}:{line_no}", file=sys.stderr)
                    return 2
                if "user" not in roles or "assistant" not in roles:
                    print(f"ERROR: messages missing user/assistant roles at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                # Build compact labels (must be non-empty)
                labels: dict[str, object] = {}
                src_labels = rec.get("labels")
                if isinstance(src_labels, dict) and src_labels:
                    labels = {
                        k: v
                        for k, v in src_labels.items()
                        if k in labels_allowlist and k != "messages" and isinstance(v, (str, int, float, bool))
                    }
                    # Normalize strings
                    for k, v in list(labels.items()):
                        if isinstance(v, str):
                            v2 = v.strip()
                            if not v2:
                                labels.pop(k, None)
                            else:
                                labels[k] = v2
                else:
                    for k in labels_allowlist:
                        if k == "messages":
                            continue
                        v = rec.get(k)
                        if isinstance(v, (str, int, float, bool)):
                            if isinstance(v, str):
                                v2 = v.strip()
                                if not v2:
                                    continue
                                labels[k] = v2
                            else:
                                labels[k] = v

                if not isinstance(labels, dict) or not labels:
                    print(f"ERROR: labels empty after allowlist at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                tef = {
                    "sample_id": sample_id,
                    "id": rec_id,
                    "target_base": target_base,
                    "messages": msgs,
                    "user_message": msgs[1]["content"],
                    "assistant_response": msgs[2]["content"],
                }

                # Flatten labels into top-level fields
                for k, v in labels.items():
                    if k not in tef:
                        tef[k] = v

                # Required top-level keys must exist
                required_keys = {"sample_id", "id", "target_base", "messages", "user_message", "assistant_response"}
                if not required_keys.issubset(set(tef.keys())):
                    print(f"ERROR: internal TEF key set mismatch at {in_path}:{line_no}", file=sys.stderr)
                    return 2

                fout.write(json.dumps(tef, ensure_ascii=False) + "\n")
                wrote += 1

        if wrote == 0:
            print(f"ERROR: no rows written for split={split_name} (input empty?)", file=sys.stderr)
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            return 2

        tmp_path.replace(out_path)
        print(f"[export:dino-tef-v1] wrote {wrote} rows -> {out_path}")
        return 0
    finally:
        if tmp_path.exists() and not out_path.exists():
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass


def _write_teacher_mode_proof(tef_dir: Path, cfg_path: Path, lane_obj: dict[str, object]) -> Path:
    generation_mode = str(lane_obj.get("generation_mode") or "template_expand").strip() or "template_expand"
    tr = lane_obj.get("teacher_runtime")
    tr = tr if isinstance(tr, dict) else {}
    enabled = bool(tr.get("enabled", False))
    provider = str(tr.get("provider") or "ollama").strip() or "ollama"
    model = str(tr.get("model") or "dino-pro-7b").strip() or "dino-pro-7b"
    policy = str(tr.get("policy") or "structure_only").strip() or "structure_only"
    on_missing = str(tr.get("on_missing_evidence") or "abstain").strip() or "abstain"

    out = tef_dir / "teacher_mode_proof.txt"
    out.write_text(
        "TEACHER_MODE_PROOF v1\n"
        f"config={cfg_path}\n"
        f"generation_mode={generation_mode}\n"
        f"teacher_runtime.enabled={str(enabled).lower()}\n"
        f"teacher_runtime.provider={provider}\n"
        f"teacher_runtime.model={model}\n"
        f"teacher_runtime.policy={policy}\n"
        f"teacher_runtime.on_missing_evidence={on_missing}\n",
        encoding="utf-8",
    )
    return out


def _write_gate_summary(tef_dir: Path, lane_id: str) -> Path:
    # Minimal smoke: first row keys + message role order
    train = tef_dir / "train.jsonl"
    first = None
    with train.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            first = json.loads(line)
            break
    if not isinstance(first, dict):
        raise RuntimeError("GATE_FAIL: train.jsonl missing first record")

    keys = list(first.keys())
    msgs = first.get("messages")
    roles = [m.get("role") for m in msgs] if isinstance(msgs, list) else []

    out = tef_dir / "gate_summary.txt"
    out.write_text(
        "GATE_SUMMARY v1\n"
        f"lane_id={lane_id}\n"
        f"first_row_keys={keys}\n"
        f"first_row_roles={roles}\n",
        encoding="utf-8",
    )
    return out


def _write_tef_labels_compact_proof(tef_dir: Path, labels_allowlist: list[str]) -> Path:
    # Scan first ~50 rows of train.jsonl and prove labels are compact + allowlisted
    train = tef_dir / "train.jsonl"
    bad: list[str] = []
    checked = 0
    with train.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            labels = rec.get("labels")
            if not isinstance(labels, dict) or not labels:
                # Fall back to top-level label fields
                labels = {k: rec.get(k) for k in labels_allowlist if k in rec}
            if not isinstance(labels, dict) or not labels:
                bad.append(f"line {line_no}: labels missing/empty")
            else:
                for k in labels.keys():
                    if k not in labels_allowlist:
                        bad.append(f"line {line_no}: forbidden label key: {k}")
            checked += 1
            if checked >= 50:
                break

    out = tef_dir / "tef_labels_compact_proof.txt"
    if bad:
        out.write_text("FAIL\n" + "\n".join(bad) + "\n", encoding="utf-8")
    else:
        out.write_text("OK\nchecked_rows=50_or_less\n", encoding="utf-8")
    return out


def _write_tef_strict_lint_report(tef_dir: Path) -> Path:
    # Local strict lint: keys + role order for train/val/test
    splits = ["train", "val", "test"]
    lines: list[str] = ["TEF_STRICT_LINT v1"]
    ok = True

    for s in splits:
        path = tef_dir / f"{s}.jsonl"
        if not path.exists():
            ok = False
            lines.append(f"{s}: MISSING")
            continue
        total = 0
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                total += 1
                try:
                    rec = json.loads(line)
                except Exception as e:
                    ok = False
                    lines.append(f"{s}:{line_no}: bad json: {e}")
                    break
                required_keys = {"sample_id", "id", "target_base", "messages", "user_message", "assistant_response"}
                if not required_keys.issubset(set(rec.keys())):
                    ok = False
                    lines.append(f"{s}:{line_no}: bad top-level keys")
                    break
                msgs = rec.get("messages")
                if not isinstance(msgs, list) or len(msgs) < 2:
                    ok = False
                    lines.append(f"{s}:{line_no}: messages invalid")
                    break
                roles = [m.get("role") for m in msgs if isinstance(m, dict)]
                # Must contain exactly one system at most, and must include user then assistant
                if "user" not in roles or "assistant" not in roles:
                    ok = False
                    lines.append(f"{s}:{line_no}: missing user/assistant")
                    break
                # Enforce system -> user -> assistant ordering (system optional)
                def _idx(r: str) -> int:
                    return roles.index(r) if r in roles else -1
                si = _idx("system")
                ui = _idx("user")
                ai = _idx("assistant")
                if ui == -1 or ai == -1 or ui > ai:
                    ok = False
                    lines.append(f"{s}:{line_no}: role order invalid")
                    break
                if si != -1 and si > ui:
                    ok = False
                    lines.append(f"{s}:{line_no}: system must be before user")
                    break

        lines.append(f"{s}: rows={total}")

    out = tef_dir / "lint_tef_strict_report.txt"
    out.write_text(("OK\n" if ok else "FAIL\n") + "\n".join(lines) + "\n", encoding="utf-8")
    return out


def gate_lane(*, config: str, limit: int | None, seed: int) -> int:
    cfg_path = Path(config)
    if not cfg_path.exists():
        print(f"ERROR: config not found: {cfg_path}", file=sys.stderr)
        return ec.CONFIG_INVALID

    # Lane config is lanes/<lane_id>/lane_en.yaml (legacy fallback: lane_en.yaml)
    lane_dir = cfg_path.parent
    lane_id = lane_dir.name

    # Default output root is lanes/<lane_id>/out, but lane config may override via `output_dir`.
    out_root = lane_dir / "out"

    # Validate first (schema)
    print("[1/6] validate lane config (schema)")
    rc = validate_cmd.run(config=str(cfg_path), schema="lane")
    if rc == 0:
        print("[1/6] OK")
    if rc != 0:
        return rc

    # Read lane config for target_base + teacher proof
    try:
        lane_obj = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        if not isinstance(lane_obj, dict):
            print("ERROR: lane config is not a mapping", file=sys.stderr)
            return ec.CONFIG_INVALID
    except Exception as e:
        print(f"ERROR: failed to read lane config: {e}", file=sys.stderr)
        return ec.CONFIG_INVALID

    # Apply output_dir override (lane config knob)
    od = lane_obj.get("output_dir")
    if isinstance(od, str) and od.strip():
        od_path = Path(od.strip())
        out_root = od_path if od_path.is_absolute() else (lane_dir / od_path)

    out_root.mkdir(parents=True, exist_ok=True)

    raw_tb = str(lane_obj.get("target_base") or "").strip()
    tb = _canonicalize_target_base(raw_tb)
    ok, msg = _require_allowed_target_base(tb)
    if not ok:
        print(f"ERROR: {msg}", file=sys.stderr)
        return ec.CONFIG_INVALID

    # Resolve system prompt via registry + system_prompt_id (no hard-coded text)
    registry = pack_cmd._load_system_prompt_registry()
    if not registry:
        print("ERROR: system prompt registry not found or empty", file=sys.stderr)
        return ec.CONFIG_INVALID

    base_row = lane_obj.get("base_row") if isinstance(lane_obj.get("base_row"), dict) else {}
    te = lane_obj.get("template_expand") if isinstance(lane_obj.get("template_expand"), dict) else {}
    te_base = te.get("base_row") if isinstance(te.get("base_row"), dict) else {}

    default_spid = str(
        lane_obj.get("system_prompt_id")
        or te_base.get("system_prompt_id")
        or base_row.get("system_prompt_id")
        or lane_obj.get("system_id")
        or ""
    ).strip()

    # Build
    print("[2/6] build lane -> built_N.jsonl")
    # Name outputs using limit if provided, else use lane count_target (or 'full')
    count_target = None
    te = lane_obj.get("template_expand")
    if isinstance(te, dict):
        te_ct = te.get("count_target")
        if isinstance(te_ct, int) and te_ct > 0:
            count_target = te_ct
    if count_target is None:
        ct = lane_obj.get("count_target")
        if isinstance(ct, int) and ct > 0:
            count_target = ct
    limit_tag = None
    if isinstance(limit, int) and limit > 0:
        limit_tag = str(limit)
    elif isinstance(count_target, int) and count_target > 0:
        limit_tag = str(count_target)
    else:
        limit_tag = "full"

    built_path = out_root / f"built_{limit_tag}.jsonl"
    rc = build_cmd.run_lane(config=str(cfg_path), out=str(built_path), seed=seed, limit=limit)
    if rc != 0:
        return rc

    # Split
    print("[3/6] split built -> train/val/test")
    split_dir = out_root / f"split_{limit_tag}"
    split_dir.mkdir(parents=True, exist_ok=True)
    rc = split_cmd.run(
        in_path=str(built_path),
        outdir=str(split_dir),
        seed=seed,
        train=0.9,
        val=0.05,
        test=0.05,
        min_per_nonzero_split=1,
    )
    if rc != 0:
        return rc

    print("[4/6] export -> dino-tef-v1")
    # Export strict dino-tef-v1
    lang_tag = _lane_language_tag(lane_obj, te_base, base_row)
    run_uuid = _run_uuid()
    tef_dir = out_root / f"dino-tef-{lang_tag}-{limit_tag}-{run_uuid}"
    tef_dir.mkdir(parents=True, exist_ok=True)

    labels_allow = _labels_allowlist_v16()

    for split_name in ("train", "val", "test"):
        rc = _export_qwen_tef_v1(
            indir=split_dir,
            outdir=tef_dir,
            system_prompt_id=default_spid,
            registry=registry,
            split_name=split_name,
            target_base=tb,
            labels_allowlist=labels_allow,
        )
        if rc != 0:
            return rc

    print("[5/6] pack + proofs")
    # Pack manifest (tool-owned)
    manifest_path = tef_dir / "dataset_manifest.v1.json"
    rc = pack_cmd.run(indir=str(tef_dir), out=str(manifest_path))
    if rc != 0:
        return rc

    # Proofs (tool-only)
    tool_sha = _git_sha()
    tool_sha_path = tef_dir / "tool_git_sha.txt"
    tool_sha_path.write_text(tool_sha + "\n", encoding="utf-8")

    proof_teacher = _write_teacher_mode_proof(tef_dir, cfg_path, lane_obj)
    proof_summary = _write_gate_summary(tef_dir, lane_id)
    proof_labels = _write_tef_labels_compact_proof(tef_dir, labels_allow)
    proof_lint = _write_tef_strict_lint_report(tef_dir)

    # Sha256 sidecars
    sidecars: list[Path] = []
    for p in [
        built_path,
        tef_dir / "train.jsonl",
        tef_dir / "val.jsonl",
        tef_dir / "test.jsonl",
        manifest_path,
        tool_sha_path,
        proof_teacher,
        proof_summary,
        proof_labels,
        proof_lint,
    ]:
        sidecars.append(_write_sha256_sidecar(p))

    print("[6/6] zip flat-root gate bundle + sha256")
    # Flat-root gate zip
    zip_tmp = out_root / f"lane_gate_zip_{lane_id}.zip"
    files_to_zip: list[Path] = [
        built_path,
        Path(str(built_path) + ".sha256"),
        tef_dir / "train.jsonl",
        tef_dir / "train.jsonl.sha256",
        tef_dir / "val.jsonl",
        tef_dir / "val.jsonl.sha256",
        tef_dir / "test.jsonl",
        tef_dir / "test.jsonl.sha256",
        manifest_path,
        Path(str(manifest_path) + ".sha256"),
        tool_sha_path,
        Path(str(tool_sha_path) + ".sha256"),
        proof_labels,
        Path(str(proof_labels) + ".sha256"),
        proof_summary,
        Path(str(proof_summary) + ".sha256"),
        proof_teacher,
        Path(str(proof_teacher) + ".sha256"),
        proof_lint,
        Path(str(proof_lint) + ".sha256"),
    ]

    with zipfile.ZipFile(zip_tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in files_to_zip:
            if p.exists():
                z.write(p, arcname=p.name)

    zip_sha = _sha256_file(zip_tmp)
    zip_hash8 = zip_sha[:8]
    zip_final = out_root / f"lane_gate_zip_{zip_hash8}.zip"
    try:
        if zip_final.exists():
            zip_final.unlink()
    except Exception:
        pass
    zip_tmp.replace(zip_final)

    print(f"UPLOAD_THIS: {zip_final}")
    print(f"ZIP_SHA256={zip_sha}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)

    try:
        if args.cmd == "validate":
            return validate_cmd.run(config=args.config, schema=str(args.schema))

        if args.cmd == "lint":
            return lint_cmd.run(qa_jsonl=args.qa_jsonl, pct_jsonl=getattr(args, "pct_jsonl", None))

        if args.cmd == "sources" and args.sources_cmd == "verify":
            return sources_cmd.verify(manifest=args.manifest)

        if args.cmd == "fixtures" and args.fixtures_cmd == "verify":
            return fixtures_cmd.verify(manifest=args.manifest)

        if args.cmd == "build" and args.build_cmd == "lane":
            lim = None
            if args.limit is not None and str(args.limit).strip().lower() not in ("none", ""):
                lim = int(args.limit)
            return build_cmd.run_lane(config=args.config, out=args.out, seed=int(args.seed), limit=lim)

        if args.cmd == "build" and args.build_cmd == "qa":
            return stubs.nyi()

        if args.cmd == "split":
            return split_cmd.run(
                in_path=args.in_path,
                outdir=args.outdir,
                seed=int(args.seed),
                train=float(args.train),
                val=float(args.val),
                test=float(args.test),
                min_per_nonzero_split=int(getattr(args, "min_per_nonzero_split", 0)),
            )

        if args.cmd == "pack":
            return pack_cmd.run(indir=args.indir, out=args.out)

        if args.cmd == "gate" and args.gate_cmd == "lane":
            raw_limit = getattr(args, "limit", None)
            lim = None
            if raw_limit is not None:
                s = str(raw_limit).strip()
                if s:
                    lim = int(s)
            seed = int(str(getattr(args, "seed", "0")).strip() or "0")
            return gate_lane(config=args.config, limit=lim, seed=seed)

        if args.cmd == "export" and args.export_cmd == "qwen":
            indir = Path(args.indir)
            outdir = Path(args.outdir)
            outdir.mkdir(parents=True, exist_ok=True)

            # For TEF export, --system is a registry ID (not free-form text).
            system_prompt_id = str(getattr(args, "system", "") or "").strip()
            system_file = getattr(args, "system_file", None)
            if system_file is not None and str(system_file).strip() not in ("", "none", "None"):
                with open(system_file, "r", encoding="utf-8") as f:
                    system_prompt_id = f.read().strip()

            registry = pack_cmd._load_system_prompt_registry()
            if not registry:
                print("ERROR: system prompt registry not found or empty", file=sys.stderr)
                return ec.CONFIG_INVALID

            # Split name input/output selection
            split_name = str(getattr(args, "target_base", "") or "").strip() or "test"

            # Target base enforcement (trainer-facing)
            tb = str(getattr(args, "target_base", "") or "").strip() or "test"
            tb = _canonicalize_target_base(tb)
            ok, msg = _require_allowed_target_base(tb)
            if not ok:
                print(f"ERROR: {msg}", file=sys.stderr)
                return ec.CONFIG_INVALID

            labels_allow = _labels_allowlist_v16()

            return _export_qwen_tef_v1(
                indir=indir,
                outdir=outdir,
                system_prompt_id=system_prompt_id,
                registry=registry,
                split_name=split_name,
                target_base=tb,
                labels_allowlist=labels_allow,
            )

        if args.cmd == "golden" and args.golden_cmd == "gen":
            return golden_cmd.gen(out=args.out, count=int(args.count), seed=int(args.seed))

        if args.cmd == "golden" and args.golden_cmd == "run":
            return golden_cmd.run(golden=args.golden, engine=args.engine)

        return stubs.nyi()
    except Exception:
        traceback.print_exc()
        return ec.INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
