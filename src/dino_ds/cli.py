from __future__ import annotations

import argparse
import sys
import json
import traceback
from pathlib import Path

from . import __version__
from . import exit_codes as ec

from .commands import validate_cmd, lint_cmd, sources_cmd, fixtures_cmd
from .commands import build_cmd, split_cmd, pack_cmd, golden_cmd, stubs


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

        if args.cmd == "export" and args.export_cmd == "qwen":
            indir = Path(args.indir)
            outdir = Path(args.outdir)
            outdir.mkdir(parents=True, exist_ok=True)

            # For TEF export, --system is a registry ID (not free-form text).
            system_id = str(getattr(args, "system", "") or "").strip()
            system_file = getattr(args, "system_file", None)
            if system_file is not None and str(system_file).strip() not in ("", "none", "None"):
                with open(system_file, "r", encoding="utf-8") as f:
                    system_id = f.read().strip()

            # Resolve system prompt text best-effort.
            system_text = ""
            if system_id:
                reg_path = Path(__file__).resolve().parent / "system_prompt_registry.json"
                if reg_path.exists():
                    try:
                        reg = json.loads(reg_path.read_text(encoding="utf-8"))
                        if isinstance(reg, dict) and isinstance(reg.get(system_id), str):
                            system_text = str(reg.get(system_id)).strip()
                        else:
                            # Fall back to using the provided value literally.
                            system_text = system_id
                    except Exception:
                        system_text = system_id
                else:
                    system_text = system_id

            target_base = str(getattr(args, "target_base", "") or "").strip() or "test"
            in_path = indir / f"{target_base}.jsonl"
            if not in_path.exists():
                print(f"ERROR: input split not found: {in_path}", file=sys.stderr)
                return 2

            keep_labels = bool(getattr(args, "keep_labels", False))
            include_id = bool(getattr(args, "include_id", False))

            out_path = outdir / f"{target_base}.jsonl"
            tmp_path = outdir / f".{target_base}.jsonl.tmp"

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

                        # Input CAR fields (support multiple shapes).
                        # Preferred: explicit `messages` list with role/content.
                        msgs = []
                        if system_text:
                            msgs.append({"role": "system", "content": system_text})

                        rec_messages = rec.get("messages")
                        if isinstance(rec_messages, list) and rec_messages:
                            # Copy through only valid role/content pairs.
                            for m in rec_messages:
                                if not isinstance(m, dict):
                                    continue
                                role = m.get("role")
                                content = m.get("content")
                                if isinstance(role, str) and isinstance(content, str) and role and content:
                                    msgs.append({"role": role, "content": content})
                        else:
                            # Legacy/seed CAR: use `user_message` (preferred) or `user_prompt`.
                            user_text = rec.get("user_message")
                            if not (isinstance(user_text, str) and user_text.strip()):
                                user_text = rec.get("user_prompt")
                            assistant_text = rec.get("assistant_response")
                            if not (isinstance(user_text, str) and user_text.strip()):
                                print(f"ERROR: missing user_message/user_prompt at {in_path}:{line_no}", file=sys.stderr)
                                return 2
                            if not (isinstance(assistant_text, str) and assistant_text.strip()):
                                print(f"ERROR: missing assistant_response at {in_path}:{line_no}", file=sys.stderr)
                                return 2
                            msgs.append({"role": "user", "content": user_text.strip()})
                            msgs.append({"role": "assistant", "content": assistant_text.strip()})

                        # Ensure we have at least one user + assistant message in the final TEF.
                        roles = [m.get("role") for m in msgs if isinstance(m, dict)]
                        if "user" not in roles or "assistant" not in roles:
                            print(f"ERROR: messages missing user/assistant roles at {in_path}:{line_no}", file=sys.stderr)
                            return 2

                        if include_id:
                            rec_id = None
                            if isinstance(rec.get("id"), str) and rec.get("id").strip():
                                rec_id = rec.get("id").strip()
                            elif isinstance(rec.get("sample_id"), str) and rec.get("sample_id").strip():
                                rec_id = rec.get("sample_id").strip()
                            if not rec_id:
                                print(f"ERROR: missing id/sample_id at {in_path}:{line_no}", file=sys.stderr)
                                return 2
                            tef = {"messages": msgs, "id": rec_id}
                        else:
                            tef = {"messages": msgs}

                        if keep_labels:
                            labels = rec.get("labels")
                            if isinstance(labels, dict) and labels:
                                tef["labels"] = labels
                            else:
                                # Build compact labels from top-level CAR fields.
                                allow = [
                                    "mode",
                                    "tone",
                                    "language",
                                    "adult_gate",
                                    "profanity_allowed",
                                    "safety_tag",
                                    "intent_family",
                                    "intent_subtype",
                                    "flow_state",
                                    "history_scope",
                                    "continuity_choice",
                                    "representation_choice",
                                    "needs_search",
                                    "needs_history_search",
                                ]
                                compact = {}
                                for k in allow:
                                    v = rec.get(k)
                                    if isinstance(v, (str, int, float, bool)):
                                        # Normalize strings and skip empties.
                                        if isinstance(v, str):
                                            v2 = v.strip()
                                            if not v2:
                                                continue
                                            compact[k] = v2
                                        else:
                                            compact[k] = v
                                tef["labels"] = compact

                        fout.write(json.dumps(tef, ensure_ascii=False) + "\n")
                        wrote += 1

                if wrote == 0:
                    print(f"ERROR: no rows written for {target_base} (input empty?)", file=sys.stderr)
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    return 2

                tmp_path.replace(out_path)
                print(f"[export:qwen] wrote {wrote} rows -> {out_path}")
                return 0
            finally:
                # If we failed early, avoid leaving a temp file behind.
                if tmp_path.exists() and not out_path.exists():
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except Exception:
                        pass

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
