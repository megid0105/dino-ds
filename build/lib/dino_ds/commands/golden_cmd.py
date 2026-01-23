from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .. import exit_codes as ec
from ..utils import atomic_write_text

# Must-pass categories per addendum: recency trigger, politics/history, closed-book evidence linkage.  [oai_citation:2‡PCT_CT_ADDENDUM_DTA_AccuracyQA_Sources_RealAnswer_Guardrails_2026-01-16.md](sediment://file_000000002cdc71f8ba39f72854901adf)
MUST_TAGS = {"recency_trigger", "politics_sensitive", "closed_book_sourcepack"}


def gen(out: str, count: int = 400, seed: int = 0) -> int:
    try:
        if count < 300 or count > 800:
            return ec.CONFIG_INVALID  # golden size contract 300–800  [oai_citation:3‡DTA_CTv3_WorkOrder_DinoReboot_dino-ds_Golden_Wave0_2026-01-16.md](sediment://file_000000009e4471fda4fec4954bebe284)

        rnd = random.Random(seed)
        out_path = Path(out).expanduser().resolve()

        cases: list[dict[str, Any]] = []

        # seed mandatory must-pass buckets first
        cases.append({"case_id": "must_recency_001", "user": "What is the latest price of Bitcoin?", "tags": ["recency_trigger"], "must_pass": True})
        cases.append({"case_id": "must_politics_001", "user": "Who is the current president of the United States?", "tags": ["politics_sensitive", "recency_trigger"], "must_pass": True})
        cases.append({"case_id": "must_closedbook_001", "user": "What is the capital of France?", "tags": ["closed_book_sourcepack"], "must_pass": True})

        # fill remainder with lightweight, engine-agnostic prompts
        pool = [
            ("math_basic", "Compute 17*23."),
            ("reasoning_short", "Explain why the sky appears blue in one paragraph."),
            ("recency_weather", "What's the weather today in Tokyo?"),
            ("history_sensitive", "Summarize the UN Charter's purpose in one paragraph."),
            ("qa_style", "Give a concise definition of photosynthesis."),
        ]

        while len(cases) < count:
            tag, prompt = rnd.choice(pool)
            tags = []
            if "recency" in tag:
                tags.append("recency_trigger")
            if "history" in tag:
                tags.append("politics_sensitive")
            if not tags:
                tags.append("closed_book_sourcepack")
            cases.append(
                {
                    "case_id": f"case_{len(cases)+1:04d}",
                    "user": prompt,
                    "tags": tags,
                    "must_pass": False,
                }
            )

        header = {
            "golden_eval_version": "dino.golden_eval.v1",
            "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "count": count,
        }

        # JSONL: first line header, then cases
        text = json.dumps({"_header": header}, ensure_ascii=False) + "\n"
        text += "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cases)

        atomic_write_text(out_path, text)
        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR


def run(golden: str, engine: str = "none") -> int:
    try:
        gpath = Path(golden).expanduser().resolve()
        if not gpath.exists():
            return ec.IO_ERROR

        lines = [ln.strip() for ln in gpath.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if not lines:
            return ec.GOLDEN_FAILED

        # allow optional header on line 1
        start = 0
        try:
            obj0 = json.loads(lines[0])
            if isinstance(obj0, dict) and "_header" in obj0:
                start = 1
        except Exception:
            pass

        cases = []
        for ln in lines[start:]:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                cases.append(obj)

        if engine != "none":
            # structure-only is required to run everywhere; engines are allowed later on GPU.  [oai_citation:4‡DTA_CTv3_WorkOrder_DinoReboot_dino-ds_Golden_Wave0_2026-01-16.md](sediment://file_000000009e4471fda4fec4954bebe284)
            return ec.INTERNAL_ERROR

        # structure-only checks:
        n = len(cases)
        if n < 300 or n > 800:
            return ec.GOLDEN_FAILED

        seen_tags: set[str] = set()
        for c in cases:
            cid = c.get("case_id")
            user = c.get("user")
            tags = c.get("tags")
            if not isinstance(cid, str) or not cid.strip():
                return ec.GOLDEN_FAILED
            if not isinstance(user, str) or not user.strip():
                return ec.GOLDEN_FAILED
            if isinstance(tags, list):
                for t in tags:
                    if isinstance(t, str):
                        seen_tags.add(t)

        # Must-pass category presence
        if not MUST_TAGS.issubset(seen_tags):
            return ec.GOLDEN_FAILED

        return ec.SUCCESS
    except FileNotFoundError:
        return ec.IO_ERROR
    except ValueError:
        return ec.CONFIG_INVALID
    except Exception:
        return ec.INTERNAL_ERROR
