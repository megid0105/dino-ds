from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable
import copy
import re

from .. import exit_codes as ec
from ..utils import load_yaml, atomic_write_text
from . import validate_cmd


def _iter_source_paths(src: Any, base: Path) -> list[Path]:
    out: list[Path] = []
    if isinstance(src, str):
        p = (base / src).expanduser().resolve() if not Path(src).is_absolute() else Path(src).expanduser().resolve()
        out.append(p)
    elif isinstance(src, dict) and isinstance(src.get("path"), str):
        p = (base / src["path"]).expanduser().resolve() if not Path(src["path"]).is_absolute() else Path(src["path"]).expanduser().resolve()
        out.append(p)
    return out


def _expand_paths(paths: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.glob("*.jsonl")))
            out.extend(sorted(p.glob("*.json")))
        else:
            out.append(p)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        k = str(p)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _read_json(path: Path) -> list[dict[str, Any]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


def _ensure_sample_id(rows: list[dict[str, Any]], salt: str) -> None:
    seen: set[str] = set()
    for i, r in enumerate(rows):
        sid = r.get("sample_id")
        if not isinstance(sid, str) or not sid.strip():
            sid = f"{salt}_{i:08d}"
            r["sample_id"] = sid
        # collision guard
        base = sid
        j = 1
        while sid in seen:
            sid = f"{base}_{j}"
            j += 1
            r["sample_id"] = sid
        seen.add(sid)


_WS_RE = re.compile(r"\s+")

# Optional similarity ignore list (lane-configurable). Kept small to avoid surprising behavior.
_EN_STOPWORDS: set[str] = {
    "a","an","the","and","or","but","if","then","else","for","to","of","in","on","at","by","with",
    "is","are","was","were","be","been","being","do","does","did","done",
    "i","me","my","mine","you","your","yours","we","our","ours","they","their","theirs",
    "it","its","this","that","these","those","as","not","no","yes","so","very","can","could","will","would",
}

def _build_similarity_ignore(sim: Any) -> set[str]:
    ignore: set[str] = set()
    if isinstance(sim, dict):
        if sim.get("ignore_stopwords") is True:
            ignore |= _EN_STOPWORDS
        extra = sim.get("ignore_tokens")
        if isinstance(extra, list):
            for x in extra:
                if isinstance(x, str) and x.strip():
                    ignore.add(x.strip().lower())
    return ignore

def _build_similarity_ngram(sim: Any) -> int:
    n = 1
    if isinstance(sim, dict):
        v = sim.get("ngram")
        if isinstance(v, int) and 1 <= v <= 3:
            n = v
    return n


def _tokenize(text: str, ignore: set[str] | None = None, ngram: int = 1) -> list[str]:
    t = _WS_RE.sub(" ", text.strip().lower())
    toks = [x for x in t.split(" ") if x]
    if ignore:
        toks = [x for x in toks if x not in ignore]
    if ngram <= 1:
        return toks
    if len(toks) < ngram:
        return []
    out: list[str] = []
    for i in range(0, len(toks) - ngram + 1):
        out.append("__".join(toks[i : i + ngram]))
    return out


def _token_overlap_ratio(a: str, b: str, ignore: set[str] | None = None, ngram: int = 1) -> float:
    ta = set(_tokenize(a, ignore, ngram))
    tb = set(_tokenize(b, ignore, ngram))
    if not ta or not tb:
        return 0.0
    inter = len(ta.intersection(tb))
    denom = len(ta.union(tb))
    return inter / float(denom) if denom > 0 else 0.0


def _row_text_for_similarity(rr: dict[str, Any]) -> str:
    u = rr.get("user_message")
    a = rr.get("assistant_response")
    if isinstance(u, str) and isinstance(a, str):
        return f"{u}\n{a}"
    return json.dumps(rr, ensure_ascii=False)


def _deep_format(obj: Any, ctx: dict[str, Any]) -> Any:
    # Recursively format strings with {slot} placeholders.
    if isinstance(obj, str):
        try:
            return obj.format_map(ctx)
        except Exception:
            # Keep original string if formatting fails; lane authors can debug.
            return obj
    if isinstance(obj, list):
        return [_deep_format(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: _deep_format(v, ctx) for k, v in obj.items()}
    return obj


def _build_shuffle_cap(lane: dict[str, Any], cfg_path: Path, seed: int | None, limit: int | None) -> list[dict[str, Any]]:
    sources = lane.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("sources required for shuffle_cap")

    base_dir = cfg_path.parent
    paths: list[Path] = []
    for s in sources:
        paths.extend(_iter_source_paths(s, base_dir))
    paths = _expand_paths(paths)

    if not paths:
        raise FileNotFoundError("no source paths")

    rows: list[dict[str, Any]] = []
    for p in paths:
        if not p.exists():
            raise FileNotFoundError(str(p))
        if p.suffix.lower() == ".jsonl":
            rows.extend(_read_jsonl(p))
        elif p.suffix.lower() == ".json":
            rows.extend(_read_json(p))

    if not rows:
        raise ValueError("no rows loaded")

    rnd = random.Random(seed if seed is not None else 0)
    rnd.shuffle(rows)

    ct = lane.get("count_target")
    n = None
    if isinstance(ct, int) and ct > 0:
        n = ct
    if isinstance(limit, int) and limit > 0:
        n = min(n, limit) if n is not None else limit
    if n is not None:
        rows = rows[:n]

    return rows


def _build_template_expand(lane: dict[str, Any], cfg_path: Path, seed: int | None, limit: int | None, preexisting_texts: list[str] | None = None) -> list[dict[str, Any]]:
    te = lane.get("template_expand")
    if not isinstance(te, dict):
        raise ValueError("template_expand block required")

    slot_banks = te.get("slot_banks")
    if not isinstance(slot_banks, dict) or not slot_banks:
        raise ValueError("template_expand.slot_banks required")

    row_template = te.get("row_template")
    if not isinstance(row_template, dict) or not row_template:
        raise ValueError("template_expand.row_template required")

    # Optional default fields to apply to every generated row (used to satisfy training schemas).
    # Accept either lane-level `base_row` or template_expand-level `base_row` (template_expand takes precedence).
    base_row = lane.get("base_row")
    if base_row is None:
        base_row = {}
    if not isinstance(base_row, dict):
        raise ValueError("base_row must be object")
    
    # Keep these gates in the human-facing lane.yaml (no hidden defaults).
    if "adult_gate" not in base_row or not isinstance(base_row.get("adult_gate"), bool):
        raise ValueError("base_row.adult_gate (bool) is required in lane.yaml")
    if "profanity_allowed" not in base_row or not isinstance(base_row.get("profanity_allowed"), bool):
        raise ValueError("base_row.profanity_allowed (bool) is required in lane.yaml")

    te_base = te.get("base_row")
    if te_base is None:
        te_base = {}
    if not isinstance(te_base, dict):
        raise ValueError("template_expand.base_row must be object")

    # template_expand overrides lane defaults
    base_row = {**base_row, **te_base}

    # count_target precedence: template_expand.count_target > lane.count_target
    n = te.get("count_target") if isinstance(te.get("count_target"), int) and te.get("count_target") > 0 else lane.get("count_target")
    if not isinstance(n, int) or n <= 0:
        raise ValueError("count_target must be positive")
    if isinstance(limit, int) and limit > 0:
        n = min(n, limit)

    rnd = random.Random(seed if seed is not None else (te.get("seed") if isinstance(te.get("seed"), int) else 0))

    # Similarity gate (optional)
    sim = lane.get("similarity")
    sim_ignore = _build_similarity_ignore(sim)
    sim_ngram = _build_similarity_ngram(sim)
    max_ratio = None
    if isinstance(sim, dict) and isinstance(sim.get("max_token_overlap_ratio"), (int, float)):
        max_ratio = float(sim.get("max_token_overlap_ratio"))

    # Operators are kept lane-agnostic; for now we support simple sampling from slot banks.
    # Future lanes can add operator config without breaking because we ignore unknown operators.
    operators = te.get("operators")
    if operators is None:
        operators = []

    # Keep a sliding window for similarity to avoid O(n^2)
    window_max = 300
    window_texts: list[str] = []
    if preexisting_texts:
        # Seed the sliding window with prior examples (hybrid backfill uses this)
        window_texts = list(preexisting_texts)[-window_max:]

    rows: list[dict[str, Any]] = []
    attempts = 0
    # Similarity gates can be very strict for short templates; allow more attempts.
    # Lane authors may override via template_expand.max_attempts or template_expand.attempts_per_row.
    attempts_per_row = te.get("attempts_per_row")
    if not isinstance(attempts_per_row, int) or attempts_per_row <= 0:
        attempts_per_row = 2000

    max_attempts = te.get("max_attempts")
    if not isinstance(max_attempts, int) or max_attempts <= 0:
        max_attempts = max(50_000, n * attempts_per_row)

    while len(rows) < n and attempts < max_attempts:
        attempts += 1
        ctx: dict[str, Any] = {}
        for k, bank in slot_banks.items():
            if isinstance(bank, list) and bank:
                v = rnd.choice(bank)
                # stringify non-scalars for placeholder substitution
                if isinstance(v, (dict, list)):
                    ctx[k] = json.dumps(v, ensure_ascii=False)
                else:
                    ctx[k] = v

        # Apply very simple operator: allow per-row random overrides via operators named "set"
        if isinstance(operators, list):
            for op in operators:
                if not isinstance(op, dict):
                    continue
                if op.get("name") != "set":
                    continue
                key = op.get("key")
                val = op.get("value")
                if isinstance(key, str):
                    ctx[key] = val

        rr = _deep_format(copy.deepcopy(row_template), ctx)
        if base_row:
            merged = copy.deepcopy(base_row)
            merged.update(rr)
            rr = merged

        # Similarity check on concatenated user/assistant if present
        if max_ratio is not None:
            text = _row_text_for_similarity(rr)
            ok = True
            for prev in window_texts:
                if _token_overlap_ratio(text, prev, sim_ignore, sim_ngram) > max_ratio:
                    ok = False
                    break
            if not ok:
                continue
            window_texts.append(text)
            if len(window_texts) > window_max:
                window_texts.pop(0)

        rows.append(rr)

    if len(rows) < n:
        raise ValueError(
            f"template_expand could not satisfy similarity/constraints: generated {len(rows)}/{n} "
            f"within max_attempts={max_attempts}. Increase slot_banks variety, relax similarity.max_token_overlap_ratio, "
            f"or set template_expand.max_attempts / template_expand.attempts_per_row in the lane config."
        )

    return rows


def _build_teacher_import(lane: dict[str, Any], cfg_path: Path, seed: int | None, limit: int | None) -> list[dict[str, Any]]:
    # No-teacher-resource assumption: this mode IMPORTS only. It does not call any model.
    ti = lane.get("teacher_import")
    if not isinstance(ti, dict):
        raise ValueError("teacher_import block required")

    input_path = ti.get("input_path")
    if not isinstance(input_path, str) or not input_path.strip():
        raise ValueError("teacher_import.input_path required")

    base_dir = cfg_path.parent
    p = (base_dir / input_path).expanduser().resolve() if not Path(input_path).is_absolute() else Path(input_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(str(p))

    rows: list[dict[str, Any]] = []
    if p.suffix.lower() == ".jsonl":
        rows.extend(_read_jsonl(p))
    elif p.suffix.lower() == ".json":
        rows.extend(_read_json(p))
    else:
        raise ValueError("teacher_import.input_path must be .jsonl or .json")

    if not rows:
        raise ValueError("no rows loaded")

    # Deterministic shuffle if requested
    rnd = random.Random(seed if seed is not None else (ti.get("seed") if isinstance(ti.get("seed"), int) else 0))
    rnd.shuffle(rows)

    # Apply lane count_target/limit
    ct = lane.get("count_target")
    n = None
    if isinstance(ct, int) and ct > 0:
        n = ct
    if isinstance(limit, int) and limit > 0:
        n = min(n, limit) if n is not None else limit
    if n is not None:
        rows = rows[:n]

    return rows


def _build_hybrid(lane: dict[str, Any], cfg_path: Path, seed: int | None, limit: int | None) -> list[dict[str, Any]]:
    # Hybrid strategy:
    # - If teacher_import is configured AND its input_path exists, use it as the primary source.
    # - Otherwise fall back to template_expand.
    # - If primary yields fewer than count_target, backfill with template_expand while respecting similarity.
    hy = lane.get("hybrid")
    if hy is None:
        hy = {}
    if not isinstance(hy, dict):
        raise ValueError("hybrid must be object")

    primary = hy.get("primary")
    if not isinstance(primary, str) or not primary:
        primary = "teacher_import"
    backfill = hy.get("backfill")
    if not isinstance(backfill, str) or not backfill:
        backfill = "template_expand"

    # total target
    ct = lane.get("count_target")
    n = ct if isinstance(ct, int) and ct > 0 else None
    if n is None:
        raise ValueError("count_target must be positive")
    if isinstance(limit, int) and limit > 0:
        n = min(n, limit)

    max_primary_ratio = hy.get("max_primary_ratio")
    if isinstance(max_primary_ratio, (int, float)):
        r = float(max_primary_ratio)
        if 0.0 < r < 1.0:
            n_primary_cap = max(1, int(round(n * r)))
        else:
            n_primary_cap = n
    else:
        n_primary_cap = n

    rows: list[dict[str, Any]] = []

    # Determine whether teacher_import is available (file exists)
    teacher_ok = False
    ti = lane.get("teacher_import")
    if isinstance(ti, dict) and isinstance(ti.get("input_path"), str):
        input_path = ti.get("input_path")
        if isinstance(input_path, str) and input_path.strip():
            base_dir = cfg_path.parent
            p = (base_dir / input_path).expanduser().resolve() if not Path(input_path).is_absolute() else Path(input_path).expanduser().resolve()
            teacher_ok = p.exists()

    # Primary
    if primary == "teacher_import" and teacher_ok:
        rows = _build_teacher_import(lane, cfg_path, seed, n_primary_cap)
    elif primary == "template_expand":
        rows = _build_template_expand(lane, cfg_path, seed, n_primary_cap)
    elif primary == "shuffle_cap":
        rows = _build_shuffle_cap(lane, cfg_path, seed, n_primary_cap)
    else:
        # teacher_import requested but not available; fall back
        if teacher_ok:
            rows = _build_teacher_import(lane, cfg_path, seed, n_primary_cap)
        else:
            rows = _build_template_expand(lane, cfg_path, seed, n_primary_cap)

    # Backfill to reach n
    if len(rows) < n:
        need = n - len(rows)
        if backfill != "template_expand":
            # For now we only support backfill via template_expand because it respects similarity controls.
            raise ValueError("hybrid.backfill must be template_expand")
        pre_texts = [_row_text_for_similarity(r) for r in rows if isinstance(r, dict)]
        more = _build_template_expand(lane, cfg_path, seed, need, preexisting_texts=pre_texts)
        rows.extend(more)

    return rows


def run_lane(config: str, out: str, seed: int | None = None, limit: int | None = None) -> int:
    try:
        cfg_path = Path(config).expanduser().resolve()
        out_path = Path(out).expanduser().resolve()

        # Must respect locked lane minimal fields: validate first.
        v = validate_cmd.run(config=str(cfg_path), schema="lane")
        if v != ec.SUCCESS:
            return v

        lane = load_yaml(cfg_path)
        if not isinstance(lane, dict):
            return ec.CONFIG_INVALID

        mode = lane.get("generation_mode")
        if not isinstance(mode, str) or not mode:
            mode = "shuffle_cap"

        if mode == "shuffle_cap":
            rows = _build_shuffle_cap(lane, cfg_path, seed, limit)
        elif mode == "template_expand":
            rows = _build_template_expand(lane, cfg_path, seed, limit)
        elif mode == "teacher_import":
            rows = _build_teacher_import(lane, cfg_path, seed, limit)
        elif mode == "hybrid":
            rows = _build_hybrid(lane, cfg_path, seed, limit)
        else:
            return ec.CONFIG_INVALID

        # Apply lane-level base defaults to every row for ALL modes.
        # This keeps lane.yaml as the single human-facing source of truth for required training fields.
        base_row = lane.get("base_row")
        if base_row is None:
            base_row = {}
        if not isinstance(base_row, dict):
            raise ValueError("base_row must be object")

        if base_row:
            for r in rows:
                if isinstance(r, dict):
                    for k, v in base_row.items():
                        if k not in r:
                            r[k] = v

        # attach lane metadata without clobbering user keys
        meta = {
            "lane_id": lane.get("lane_id"),
            "wave": lane.get("wave"),
            "target_base": lane.get("target_base"),
            "source_type": lane.get("source_type"),
            "generation_mode": mode,
        }
        for r in rows:
            if isinstance(r, dict) and "_lane" not in r:
                r["_lane"] = meta

        _ensure_sample_id(rows, salt=str(lane.get("lane_id") or "lane"))

        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        atomic_write_text(out_path, text)
        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR
