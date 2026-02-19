from __future__ import annotations

import json
import os
import random
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
import copy
import re
import sys
import subprocess

from .. import exit_codes as ec
from ..utils import load_yaml, atomic_write_text
from ..validators.row_validator_v16 import validate_row_v16
from ..validators.generation_validator import (
    resolve_rule_profile,
    validate_generated_rows,
)
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


def _normalize_lang_tag(tag: str) -> str:
    # Normalize language tag for IDs (e.g., zh-hk -> zhhk, pt-br -> ptbr)
    out = tag.strip().lower().replace("-", "")
    return out or "en"


def _lane_language_tag(lane_obj: dict[str, Any]) -> str:
    # Prefer explicit language keys; fall back to template_expand.slot_banks.language if it is a single value.
    for v in (lane_obj.get("language"),):
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

# Unresolved template placeholders like {topic} must never leak into outputs.
_PH_RE = re.compile(r"\{[A-Za-z0-9_]+\}")


def _has_unresolved_placeholders(obj: Any) -> bool:
    if isinstance(obj, str):
        return _PH_RE.search(obj) is not None
    if isinstance(obj, list):
        return any(_has_unresolved_placeholders(x) for x in obj)
    if isinstance(obj, dict):
        return any(_has_unresolved_placeholders(v) for v in obj.values())
    return False


# Collect all unique {slot} placeholders referenced in a template object.
def _collect_placeholders(obj: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(obj, str):
        for m in _PH_RE.finditer(obj):
            tok = m.group(0)
            # tok looks like {name}
            if len(tok) >= 3 and tok.startswith("{") and tok.endswith("}"):
                name = tok[1:-1]
                if name:
                    out.add(name)
        return out
    if isinstance(obj, list):
        for x in obj:
            out |= _collect_placeholders(x)
        return out
    if isinstance(obj, dict):
        for v in obj.values():
            out |= _collect_placeholders(v)
        return out
    return out


# Summarize top validator rejection reasons for error messages.
def _format_validator_rejects(rejects: Counter[str]) -> str:
    if not rejects:
        return "no validator failures recorded"
    parts = [f"{reason}={count}" for reason, count in rejects.most_common(10)]
    return ", ".join(parts)


_BOOL_FIELDS = {
    "adult_gate",
    "profanity_allowed",
    "needs_search",
    "needs_history_search",
    "connector_needed",
    "deeplink_needed",
}


def _coerce_bool_fields(row: dict[str, Any]) -> None:
    for field in _BOOL_FIELDS:
        if field not in row:
            continue
        val = row.get(field)
        if isinstance(val, bool):
            continue
        if isinstance(val, str):
            low = val.strip().lower()
            if low == "true":
                row[field] = True
            elif low == "false":
                row[field] = False


# -----------------------------
# Teacher runtime (Ollama)
# -----------------------------


def _teacher_runtime_cfg(lane: dict[str, Any]) -> dict[str, Any]:
    tr = lane.get("teacher_runtime")
    return tr if isinstance(tr, dict) else {}


def _teacher_runtime_enabled(lane: dict[str, Any]) -> bool:
    tr = _teacher_runtime_cfg(lane)
    if tr.get("enabled") is True:
        return True
    mode = lane.get("generation_mode")
    return isinstance(mode, str) and mode.strip() == "teacher_runtime"


def _ollama_rewrite(
    *, model: str, prompt: str, timeout_s: int = 120, keepalive: str | None = None, env: dict[str, str] | None = None
) -> str:
    # Use the Ollama CLI for portability. stderr is suppressed unless the call fails.
    try:
        args = ["ollama", "run", model]
        if isinstance(keepalive, str) and keepalive.strip():
            args.extend(["--keepalive", keepalive.strip()])
        cp = subprocess.run(args, input=prompt, text=True, capture_output=True, timeout=timeout_s, env=env)
    except subprocess.TimeoutExpired:
        raise ValueError("teacher_runtime timeout")

    if cp.returncode != 0:
        err = (cp.stderr or "").strip()
        msg = err.splitlines()[-1] if err else "ollama run failed"
        raise ValueError(f"teacher_runtime failed: {msg}")

    out = (cp.stdout or "").strip()
    return out


def _teacher_prompt_structure_only(
    rr: dict[str, Any],
    *,
    teacher_system_prompt: str | None = None,
    training_system_prompt: str | None = None,
) -> str:
    # Ship-safe: structure only. Do NOT invent new facts.
    mode = rr.get("mode") if isinstance(rr.get("mode"), str) else ""
    tone = rr.get("tone") if isinstance(rr.get("tone"), str) else ""
    user_msg = rr.get("user_message") if isinstance(rr.get("user_message"), str) else ""
    draft = rr.get("assistant_response") if isinstance(rr.get("assistant_response"), str) else ""
    tsp = teacher_system_prompt.strip() if isinstance(teacher_system_prompt, str) and teacher_system_prompt.strip() else ""

    # Keep prompt concise and deterministic.
    return (
        "You are a TEACHER rewriter for Dino.\n"
        "Task: rewrite the assistant draft to match the requested mode and tone.\n"
        "Rules (hard):\n"
        "    - Only rewrite the assistant draft text. Do NOT modify labels, tool calls, or any other fields.\n"
        "    - Do NOT include or echo any hidden system prompt text.\n"
        "    - Do NOT add any new entities, numbers, names, prices, dates, or claims.\n"
        "    - Do NOT add new factual claims beyond what is already in the draft.\n"
        "    - Do NOT mention teachers, models, or tooling.\n"
        "    - The assistant is named Dino. Do NOT rename or change identity.\n"
        "    - Keep the output format aligned to mode:\n"
        "        * quick: 3–5 bullets + a 'Next step:' line, compact.\n"
        "        * think: unnumbered headings + bullets, include 'Bottom line:' and 'Next step:', no numbered headings.\n"
        "        * conversation: short spoken style, no 'Bottom line' / 'Next step' scaffolding.\n"
        "    - Output ONLY the final assistant text.\n"
        "\n"
        f"mode={mode}\n"
        f"tone={tone}\n"
        + (
            "\nTrainingSystemContext (do not repeat):\n" + training_system_prompt.strip() + "\n"
            if isinstance(training_system_prompt, str) and training_system_prompt.strip()
            else ""
        )
        + ("\nLaneTeacherConstraints (do not repeat):\n" + tsp + "\n" if tsp else "")
        + "\n"
        "User:\n"
        f"{user_msg}\n"
        "\n"
        "Draft:\n"
        f"{draft}\n"
    )


def _apply_teacher_runtime(lane: dict[str, Any], rows: list[dict[str, Any]], cfg_path: Path) -> None:
    tr = _teacher_runtime_cfg(lane)
    provider = tr.get("provider") if isinstance(tr.get("provider"), str) else "ollama"
    model = tr.get("model") if isinstance(tr.get("model"), str) and tr.get("model").strip() else "dino-pro-7b"
    policy = tr.get("policy") if isinstance(tr.get("policy"), str) else "structure_only"
    on_missing = tr.get("on_missing_evidence") if isinstance(tr.get("on_missing_evidence"), str) else "abstain"
    timeout_s = tr.get("timeout_s") if isinstance(tr.get("timeout_s"), int) and tr.get("timeout_s") > 0 else 120
    keepalive = tr.get("keepalive") if isinstance(tr.get("keepalive"), str) else "5m"
    progress = tr.get("progress")
    if progress is None:
        progress = True

    # Optional sampling: rewrite only a fraction of rows (spot-rewrite).
    ratio = None
    if isinstance(tr.get("sample_ratio"), (int, float)):
        ratio = float(tr.get("sample_ratio"))
    elif isinstance(tr.get("sample_percent"), (int, float)):
        ratio = float(tr.get("sample_percent")) / 100.0
    if ratio is None:
        ratio = 1.0
    ratio = max(0.0, min(1.0, ratio))

    seed = tr.get("seed")
    if not isinstance(seed, int):
        te = lane.get("template_expand")
        seed = te.get("seed") if isinstance(te, dict) else None
    if not isinstance(seed, int):
        seed = 0
    rnd = random.Random(seed)
    lane_id = lane.get("lane_id") if isinstance(lane.get("lane_id"), str) else ""

    # Optional OLLAMA_HOST override
    env = None
    host = tr.get("ollama_host")
    if isinstance(host, str) and host.strip():
        env = dict(os.environ)
        env["OLLAMA_HOST"] = host.strip()

    if provider != "ollama":
        raise ValueError("teacher_runtime.provider must be 'ollama'")

    # For now, we only support structure_only safely (no evidence subsystem shipped yet).
    if policy != "structure_only":
        if on_missing == "fail":
            raise ValueError("teacher_runtime.policy=grounded_requires_evidence is not supported without evidence")
        # abstain: keep outputs as-is (deterministic) rather than hallucinating.
        return

    # Resolve teacher system prompt text (optional)
    def _read_prompt(path_str: str | None) -> str:
        if not isinstance(path_str, str) or not path_str.strip():
            return ""
        raw = path_str.strip()
        p = Path(raw).expanduser()
        candidates: list[Path] = []
        if p.is_absolute():
            candidates.append(p)
        else:
            # Prefer CWD, then lane dir, then repo root
            candidates.append(Path.cwd() / p)
            candidates.append(cfg_path.parent / p)
            if len(cfg_path.parents) >= 3:
                candidates.append(cfg_path.parents[2] / p)
        for c in candidates:
            if c.is_file():
                return c.read_text(encoding="utf-8").strip()
        return ""

    teacher_system_prompt = _read_prompt(tr.get("system_prompt_path"))
    if not teacher_system_prompt and isinstance(tr.get("system_prompt"), str):
        teacher_system_prompt = tr.get("system_prompt", "").strip()

    training_system_prompt = _read_prompt(lane.get("system_prompt_path"))

    # Only enforce post-rewrite mode checks when the lane asks for it
    validators = lane.get("validators")
    has_mode_richness = False
    if isinstance(validators, list):
        for v in validators:
            if isinstance(v, dict) and v.get("name") == "mode_richness":
                has_mode_richness = True
                break

    total = len(rows)
    for i, rr in enumerate(rows, start=1):
        if not isinstance(rr, dict):
            continue
        if not (isinstance(rr.get("assistant_response"), str) and rr.get("assistant_response").strip()):
            continue
        if ratio < 1.0 and rnd.random() > ratio:
            continue
        original = rr.get("assistant_response")
        prompt = _teacher_prompt_structure_only(
            rr,
            teacher_system_prompt=teacher_system_prompt,
            training_system_prompt=training_system_prompt,
        )
        if progress:
            print(f"[teacher_runtime] rewriting {i}/{total}", file=sys.stderr, flush=True)
        try:
            rr["assistant_response"] = _ollama_rewrite(
                model=model,
                prompt=prompt,
                timeout_s=timeout_s,
                keepalive=keepalive,
                env=env,
            )
        except ValueError as e:
            msg = str(e)
            if "timeout" in msg:
                print(
                    f"[teacher_runtime] timeout after {timeout_s}s at row {i}/{total}; "
                    "skipping remaining rewrites and exporting mixed rows.",
                    file=sys.stderr,
                    flush=True,
                )
                break
            raise

        ok, reason = validate_row_v16(rr, lane_id)
        if not ok:
            rr["assistant_response"] = original
            ok2, reason2 = validate_row_v16(rr, lane_id)
            if not ok2:
                raise ValueError(f"v16_row_validator_failed_after_rewrite:{reason2}")
            if progress:
                print(
                    f"[teacher_runtime] v16 validator failed at row {i}/{total}; "
                    "reverting to pre-rewrite draft.",
                    file=sys.stderr,
                    flush=True,
                )

        # Post-rewrite validation: if format drifts, fall back to original
        if has_mode_richness and not _mode_richness_ok(rr, lane):
            rr["assistant_response"] = original
            if progress:
                print(
                    f"[teacher_runtime] mode_richness failed at row {i}/{total}; "
                    "reverting to pre-rewrite draft.",
                    file=sys.stderr,
                    flush=True,
                )

# -----------------------------
# Preset rendering (no-teacher)
# -----------------------------

def _as_nonempty_str(x: Any) -> str | None:
    if isinstance(x, str):
        s = x.strip()
        return s if s else None
    return None



def _as_list_of_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, str):
        s = x.strip()
        return [s] if s else []
    if isinstance(x, list):
        out: list[str] = []
        for v in x:
            s = _as_nonempty_str(v)
            if s is not None:
                out.append(s)
        return out
    return []


# Deterministic, sentence-aware truncation.
def _safe_truncate(text: str, max_chars: int) -> str:
    """Deterministic, sentence-aware truncation.

    Preference order:
      1) sentence boundary within limit (., !, ?, 。, ！, ？, newline)
      2) last whitespace within limit
      3) hard cut
    """
    if not isinstance(text, str):
        return ""
    s = text.strip()
    if max_chars <= 0 or len(s) <= max_chars:
        return s

    cut = s[:max_chars]

    # Prefer sentence boundaries.
    boundaries = ["\n", ".", "!", "?", "。", "！", "？"]
    best = -1
    for b in boundaries:
        i = cut.rfind(b)
        if i > best:
            best = i

    if best >= 0:
        out = cut[: best + 1].rstrip()
        # If boundary is newline, don't keep trailing newline.
        out = out.rstrip("\n").rstrip()
        return out.rstrip(":;,-")

    # Fall back to whitespace.
    ws = cut.rfind(" ")
    if ws >= 0:
        return cut[:ws].rstrip().rstrip(":;,-")

    return cut.rstrip().rstrip(":;,-")


def _render_steps_v1(question: str | None, steps: Any, mode: str | None = None, continuity_choice: str | None = None) -> str:
    # steps: list[{step: str, details: list[{action:str, description:str}]}]
    if not isinstance(steps, list):
        return ""

    m = (mode or "").strip().lower()
    if m not in ("conversation", "quick", "think"):
        m = "think"

    cc = (continuity_choice or "").strip().lower()

    # Per-mode caps (no-teacher; deterministic)
    if m == "conversation":
        include_leadin = False
        max_steps = 3
        max_details_per_step = 1
        blank_line_between_steps = False
        max_desc_chars = 140
        max_total_chars = 520
    elif m == "quick":
        include_leadin = False
        max_steps = 5
        max_details_per_step = 2
        blank_line_between_steps = False
        max_desc_chars = 220
        max_total_chars = 900
    else:  # think
        include_leadin = True
        max_steps = 50
        max_details_per_step = 50
        blank_line_between_steps = True
        max_desc_chars = 99999
        max_total_chars = 999999

    lines: list[str] = []

    # Light continuity is optional; keep it truly light (one line) and only for quick/conversation.
    if cc == "light_continuity" and m in ("conversation", "quick"):
        lines.append("Building on that:")

    # Optional 1-line lead-in (neutral; safe for training)
    if include_leadin and question and question.strip():
        lines.append("Here’s a structured way to approach it:")
        lines.append("")

    n = 0
    for st in steps:
        if not isinstance(st, dict):
            continue
        title = _as_nonempty_str(st.get("step"))
        if title is None:
            continue
        n += 1
        if n > max_steps:
            break

        # Numbered step headline
        lines.append(f"{n}. {title}")

        details = st.get("details")
        dcount = 0
        if isinstance(details, list) and details:
            for d in details:
                if not isinstance(d, dict):
                    continue
                if dcount >= max_details_per_step:
                    break
                action = _as_nonempty_str(d.get("action"))
                desc = _as_nonempty_str(d.get("description"))
                if isinstance(desc, str) and max_desc_chars and len(desc) > max_desc_chars:
                    desc = _safe_truncate(desc, int(max_desc_chars))

                if action and desc:
                    lines.append(f"{action}: {desc}")
                    dcount += 1
                elif desc:
                    lines.append(desc)
                    dcount += 1

        if blank_line_between_steps:
            lines.append("")

    # Trim trailing blank lines
    while lines and lines[-1] == "":
        lines.pop()

    out = "\n".join(lines).strip()
    if max_total_chars and len(out) > max_total_chars:
        out = _safe_truncate(out, int(max_total_chars))
    return out


def _apply_answer_preset(preset: str, rr: dict[str, Any]) -> None:
    # Mutates rr in-place.

    q = rr.get("user_message")
    question = q if isinstance(q, str) else None

    preset = (preset or "").strip()
    if not preset:
        return

    if preset == "steps_v1":
        # Only render when answer_steps exists; this prevents overriding lanes that don't use steps.
        if not isinstance(rr.get("answer_steps"), list):
            return

        text = _render_steps_v1(
            question,
            rr.get("answer_steps"),
            mode=rr.get("mode") if isinstance(rr.get("mode"), str) else None,
            continuity_choice=rr.get("continuity_choice") if isinstance(rr.get("continuity_choice"), str) else None,
        )
        if text:
            # Always override assistant_response for steps_v1 so mode caps are enforced.
            rr["assistant_response"] = text
        return

    # Unknown preset: do nothing (forward compatible)
    return

# Optional similarity ignore list (lane-configurable). Kept small to avoid surprising behavior.
_EN_STOPWORDS: set[str] = {
    "a","an","the","and","or","but","if","then","else","for","to","of","in","on","at","by","with",
    "is","are","was","were","be","been","being","do","does","did","done",
    "i","me","my","mine","you","your","yours","we","our","ours","they","their","theirs",
    "it","its","this","that","these","those","as","not","no","yes","so","very","can","could","will","would",
}
_LATIN_RUN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
_CJK_CHAR_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\u31F0-\u31FF\uAC00-\uD7AF]")
_THAI_CHAR_RE = re.compile(r"[\u0E00-\u0E7F]")
_CJK_LANGS = {"zh-hk", "zh_hk", "zh-hant", "zh_hant", "zh-hans", "zh_hans", "ja", "ko"}
_THAI_LANGS = {"th"}

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


def _norm_lang_for_overlap(lang: Any) -> str:
    if not isinstance(lang, str):
        return ""
    return lang.strip().lower()


def _char_ngrams(chars: list[str], n: int) -> list[str]:
    if n <= 1:
        return chars
    if len(chars) < n:
        return []
    out: list[str] = []
    for i in range(0, len(chars) - n + 1):
        out.append("".join(chars[i : i + n]))
    return out


def _tokenize(text: str, ignore: set[str] | None = None, ngram: int = 1, lang: str | None = None) -> list[str]:
    ltag = _norm_lang_for_overlap(lang)

    # Equator v4.1 script-aware overlap view:
    # - CJK: char bigram/trigram + Latin runs
    # - Thai: fallback char bigram/trigram when dictionary segmenter is unavailable
    if ltag in _CJK_LANGS or ltag in _THAI_LANGS:
        n_char = 2 if ngram <= 2 else 3
        chars: list[str] = []
        if ltag in _CJK_LANGS:
            chars = _CJK_CHAR_RE.findall(text or "")
        else:
            chars = _THAI_CHAR_RE.findall(text or "")
        toks = _char_ngrams(chars, n_char)
        latin = _LATIN_RUN_RE.findall((text or "").lower())
        if ignore:
            latin = [t for t in latin if t not in ignore]
        return toks + latin

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


def _token_overlap_ratio(
    a: str,
    b: str,
    ignore: set[str] | None = None,
    ngram: int = 1,
    lang: str | None = None,
) -> float:
    ta = set(_tokenize(a, ignore, ngram, lang=lang))
    tb = set(_tokenize(b, ignore, ngram, lang=lang))
    if not ta or not tb:
        return 0.0
    inter = len(ta.intersection(tb))
    denom = len(ta.union(tb))
    return inter / float(denom) if denom > 0 else 0.0


def _row_text_for_similarity(rr: dict[str, Any], scope: str | None = None) -> str:
    u = rr.get("user_message")
    a = rr.get("assistant_response")
    if isinstance(scope, str):
        key = scope.strip().lower()
        if key in ("assistant", "assistant_response", "assistant-only", "assistant_only"):
            return a if isinstance(a, str) else ""
        if key in ("user", "user_message", "user-only", "user_only"):
            return u if isinstance(u, str) else ""
    if isinstance(u, str) and isinstance(a, str):
        return f"{u}\n{a}"
    return json.dumps(rr, ensure_ascii=False)


# ---- Mode richness validator ----
def _mode_richness_ok(rr: dict[str, Any], lane: dict[str, Any]) -> bool:
    """Return True if assistant_response richness matches rr['mode'].

    This is a no-teacher guardrail to prevent mode/verbosity mismatch.
    Defaults are conservative and can be overridden by lane['mode_richness'].
    """
    mode = rr.get("mode")
    text = rr.get("assistant_response")
    if not isinstance(mode, str) or not isinstance(text, str):
        return True

    m = mode.strip().lower()
    if m not in ("conversation", "quick", "think"):
        return True

    cfg = lane.get("mode_richness")
    cfg = cfg if isinstance(cfg, dict) else {}

    # Heuristics: char-count + number of numbered steps.
    chars = len(text.strip())
    step_lines = 0
    for ln in text.splitlines():
        ln = ln.strip()
        if len(ln) >= 3 and ln[0].isdigit() and ln[1] == ".":
            step_lines += 1

    if m == "conversation":
        max_chars = int(cfg.get("conversation_max_chars", 520))
        max_steps = int(cfg.get("conversation_max_steps", 3))
        return chars <= max_chars and step_lines <= max_steps

    if m == "quick":
        min_chars = int(cfg.get("quick_min_chars", 180))
        max_chars = int(cfg.get("quick_max_chars", 900))
        max_steps = int(cfg.get("quick_max_steps", 5))
        return (min_chars <= chars <= max_chars) and (1 <= step_lines <= max_steps)

    # think
    min_chars = int(cfg.get("think_min_chars", 650))
    min_steps = int(cfg.get("think_min_steps", 2))
    return chars >= min_chars and step_lines >= min_steps



def _deep_format(obj: Any, ctx: dict[str, Any]) -> Any:
    # Recursively format strings with {slot} placeholders.
    if isinstance(obj, str):
        # Preserve non-string slot values when the template is a single placeholder.
        if obj.startswith("{") and obj.endswith("}") and obj.count("{") == 1 and obj.count("}") == 1:
            key = obj[1:-1]
            if key in ctx and not isinstance(ctx.get(key), str):
                return ctx.get(key)
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


# --- NEW: Helper to resolve placeholders inside ctx string values ---
def _resolve_ctx_placeholders(ctx: dict[str, Any], max_passes: int = 3) -> dict[str, Any]:
    """Resolve {slot} placeholders inside ctx string values using ctx itself.

    Example: style_line may contain "... {topic} ..." while topic is also in ctx.
    We do a few passes to allow simple dependencies without risking infinite loops.
    """
    ctx = dict(ctx)
    for _ in range(max_passes):
        changed = False
        for k, v in list(ctx.items()):
            if isinstance(v, str) and _PH_RE.search(v):
                try:
                    nv = v.format_map(ctx)
                except Exception:
                    nv = v
                if nv != v:
                    ctx[k] = nv
                    changed = True
        if not changed:
            break
    return ctx


# Weighted/Uniform/Constant slot bank sampling helper.
def _sample_from_bank(bank: Any, rnd: random.Random) -> Any:
    """Sample a value from a slot bank.

    Supported forms:
      - list: uniform choice
      - dict: weighted choice where keys are values and values are numeric weights
      - scalar (str/int/float/bool): constant
    """
    if bank is None:
        return None
    if isinstance(bank, (str, int, float, bool)):
        return bank
    if isinstance(bank, list):
        if not bank:
            return None
        return rnd.choice(bank)
    if isinstance(bank, dict):
        items: list[tuple[Any, float]] = []
        for k, w in bank.items():
            if isinstance(w, (int, float)) and float(w) > 0:
                items.append((k, float(w)))
        if not items:
            return None
        total = sum(w for _, w in items)
        r = rnd.random() * total
        acc = 0.0
        for val, w in items:
            acc += w
            if r <= acc:
                return val
        return items[-1][0]
    return None


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
    
    # Keep these gates in the human-facing lane config (no hidden defaults).
    if "adult_gate" not in base_row or not isinstance(base_row.get("adult_gate"), bool):
        raise ValueError("base_row.adult_gate (bool) is required in lane config")
    if "profanity_allowed" not in base_row or not isinstance(base_row.get("profanity_allowed"), bool):
        raise ValueError("base_row.profanity_allowed (bool) is required in lane config")

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

    # Operators are kept lane-agnostic; for now we support simple sampling from slot banks.
    # Future lanes can add operator config without breaking because we ignore unknown operators.
    operators = te.get("operators")
    if operators is None:
        operators = []

    # Normalize preset once (avoid repeated lookups / whitespace issues)
    answer_preset = te.get("answer_preset")
    if isinstance(answer_preset, str):
        answer_preset = answer_preset.strip()
    else:
        answer_preset = ""

    # Preflight: ensure all {slot} placeholders referenced by row_template are defined.
    expand_dict_slots = te.get("expand_dict_slots")
    if not isinstance(expand_dict_slots, list):
        expand_dict_slots = []
    expand_dict_slots = [s for s in expand_dict_slots if isinstance(s, str) and s.strip()]

    required_slots = _collect_placeholders(row_template)
    provided_slots: set[str] = set(slot_banks.keys())

    # If expand_dict_slots are used, treat keys from those dict items as provided slots.
    for bank_key in expand_dict_slots:
        bank = slot_banks.get(bank_key)
        if isinstance(bank, list):
            for item in bank:
                if isinstance(item, dict):
                    provided_slots.update(item.keys())
    # Operators of type set can also provide slots.
    if isinstance(operators, list):
        for op in operators:
            if not isinstance(op, dict):
                continue
            if op.get("name") != "set":
                continue
            key = op.get("key")
            if isinstance(key, str) and key:
                provided_slots.add(key)

    missing = sorted([s for s in required_slots if s not in provided_slots])
    if missing:
        raise ValueError(
            "template_expand.row_template references missing slot(s): "
            + ", ".join(missing)
            + ". Define them in template_expand.slot_banks or operators (name: set)."
        )

    del preexisting_texts

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

    # Optional progress preview (stderr). Defaults ON for interactive usability.
    progress = te.get("progress")
    if progress is None:
        progress = True
    progress_every_rows = te.get("progress_every_rows", 25)
    progress_every_attempts = te.get("progress_every_attempts", 5000)
    try:
        progress_every_rows = int(progress_every_rows)
    except Exception:
        progress_every_rows = 25
    try:
        progress_every_attempts = int(progress_every_attempts)
    except Exception:
        progress_every_attempts = 5000
    if progress_every_rows < 1:
        progress_every_rows = 1
    if progress_every_attempts < 1:
        progress_every_attempts = 1
    last_print_attempts = 0

    fail_if_underfilled = te.get("fail_if_underfilled")
    if fail_if_underfilled is None:
        fail_if_underfilled = True
    else:
        fail_if_underfilled = bool(fail_if_underfilled)

    while len(rows) < n and attempts < max_attempts:
        attempts += 1
        # Heartbeat progress so users can tell generation is still running during retries.
        if progress and (attempts - last_print_attempts) >= progress_every_attempts:
            print(
                f"[template_expand] generated {len(rows)}/{n} (attempt {attempts}/{max_attempts})",
                file=sys.stderr,
                flush=True,
            )
            last_print_attempts = attempts
        ctx: dict[str, Any] = {}
        for k, bank in slot_banks.items():
            v = _sample_from_bank(bank, rnd)
            if v is None:
                continue
            # Allow dict expansion for coupled slots (e.g., case dicts)
            if isinstance(v, dict) and k in expand_dict_slots:
                for dk, dv in v.items():
                    ctx[dk] = dv
                continue
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

        # Resolve placeholders inside sampled slot strings (e.g., style_line may reference {topic}).
        ctx = _resolve_ctx_placeholders(ctx)
        # Also allow placeholders inside operator-provided values to resolve.
        ctx = _resolve_ctx_placeholders(ctx)

        rr = _deep_format(copy.deepcopy(row_template), ctx)
        # Some slot values can themselves contain placeholders (e.g., style_line: "... {topic} ...").
        # Run a few additional passes to fully resolve nested placeholders.
        for _ in range(3):
            rr2 = _deep_format(copy.deepcopy(rr), ctx)
            if rr2 == rr:
                break
            rr = rr2
        if base_row:
            merged = copy.deepcopy(base_row)
            merged.update(rr)
            rr = merged

        # Optional preset renderer: lets lane authors provide structured fields (e.g., answer_steps)
        # and have the tool produce a stable assistant_response. Empty-safe.
        if answer_preset:
            _apply_answer_preset(answer_preset, rr)
            # Fail-fast: if a preset is requested but produced no assistant_response, stop.
            if not (isinstance(rr.get("assistant_response"), str) and rr["assistant_response"].strip()):
                raise ValueError(
                    f"answer_preset={answer_preset} produced no assistant_response. "
                    "For steps_v1, provide template_expand.row_template.answer_steps as a list of steps."
                )

        _coerce_bool_fields(rr)

        # Hard gate: do not allow unresolved {slot} placeholders to leak into outputs.
        # If a lane references a slot (e.g., {topic}) it must be provided via slot_banks/operators.
        if _has_unresolved_placeholders(rr) or _has_unresolved_placeholders(rr.get("assistant_response")):
            continue

        # Optional validator: mode richness must match the shuffled mode label.
        validators = lane.get("validators")
        if isinstance(validators, list):
            for v in validators:
                if not isinstance(v, dict):
                    continue
                if v.get("name") == "mode_richness":
                    if not _mode_richness_ok(rr, lane):
                        # reject and retry
                        rr = {}
                        break
            if rr == {}:
                continue

        rows.append(rr)

        # Row-based progress preview
        if progress and (len(rows) == 1 or len(rows) % progress_every_rows == 0 or len(rows) == n):
            print(
                f"[template_expand] generated {len(rows)}/{n} (attempt {attempts}/{max_attempts})",
                file=sys.stderr,
                flush=True,
            )
            last_print_attempts = attempts

    if len(rows) < n:
        msg = (
            f"template_expand underfilled: generated {len(rows)}/{n} within max_attempts={max_attempts}. "
            f"attempts={attempts}. Increase slot_banks variety or adjust "
            "template_expand.max_attempts / template_expand.attempts_per_row."
        )
        if fail_if_underfilled:
            raise ValueError(msg)
        print(msg, file=sys.stderr)
        return rows

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
        pre_texts = [_row_text_for_similarity(r, sim_scope) for r in rows if isinstance(r, dict)]
        more = _build_template_expand(lane, cfg_path, seed, need, preexisting_texts=pre_texts)
        rows.extend(more)

    return rows


def run_lane(
    config: str,
    out: str,
    seed: int | None = None,
    limit: int | None = None,
    rule_profile: str | None = None,
    teacher_force: bool = False,
) -> int:
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
        rp = resolve_rule_profile(rule_profile)

        mode = lane.get("generation_mode")
        if not isinstance(mode, str) or not mode:
            mode = "shuffle_cap"
        apply_teacher_runtime = False
        if mode == "teacher_runtime":
            apply_teacher_runtime = True
        if teacher_force:
            apply_teacher_runtime = True
            tr = lane.get("teacher_runtime")
            if not isinstance(tr, dict):
                tr = {}
                lane["teacher_runtime"] = tr
            tr["enabled"] = True
            # Explicit CLI override should actually engage rewriting even when
            # lane YAML keeps teacher sampling at 0 during generation-only phases.
            sr = tr.get("sample_ratio")
            sp = tr.get("sample_percent")
            if isinstance(sr, (int, float)):
                if float(sr) <= 0.0:
                    tr["sample_ratio"] = 1.0
            elif isinstance(sp, (int, float)):
                if float(sp) <= 0.0:
                    tr["sample_percent"] = 100
            else:
                tr["sample_percent"] = 100

        if mode == "shuffle_cap":
            rows = _build_shuffle_cap(lane, cfg_path, seed, limit)
        elif mode == "template_expand":
            rows = _build_template_expand(lane, cfg_path, seed, limit)
        elif mode == "teacher_import":
            rows = _build_teacher_import(lane, cfg_path, seed, limit)
        elif mode == "teacher_runtime":
            # Generate first (template_expand), then rewrite via teacher runtime.
            rows = _build_template_expand(lane, cfg_path, seed, limit)
        elif mode == "hybrid":
            rows = _build_hybrid(lane, cfg_path, seed, limit)
        else:
            return ec.CONFIG_INVALID
        if apply_teacher_runtime:
            _apply_teacher_runtime(lane, rows, cfg_path)

        # Apply lane-level base defaults to every row for ALL modes.
        # This keeps the lane config as the single human-facing source of truth for required training fields.
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

        for r in rows:
            if isinstance(r, dict):
                _coerce_bool_fields(r)

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

        lane_id = str(lane.get("lane_id") or "lane")
        lang_tag = _normalize_lang_tag(_lane_language_tag(lane))
        _ensure_sample_id(rows, salt=f"{lane_id}_{lang_tag}")

        # QC report output should follow operator working directory by default
        # (works consistently for repo runs and wrapped-package runs).
        repo_root = str(Path.cwd())
        run_id = str(os.environ.get("DINO_DS_RUN_UUID", "")).strip() or None
        ok_rules, report = validate_generated_rows(
            rows=rows,
            lane_id=lane_id,
            lane=lane,
            rule_profile=rp,
            repo_root=repo_root,
            run_id=run_id,
        )
        if not ok_rules:
            raise ValueError(report)

        text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        atomic_write_text(out_path, text)
        print(f"[build] validation pass ({len(rows)} rows): {report}", file=sys.stderr)
        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR
