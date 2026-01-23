from __future__ import annotations

import argparse
import sys

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

        if args.cmd == "golden" and args.golden_cmd == "gen":
            return golden_cmd.gen(out=args.out, count=int(args.count), seed=int(args.seed))

        if args.cmd == "golden" and args.golden_cmd == "run":
            return golden_cmd.run(golden=args.golden, engine=args.engine)

        return stubs.nyi()
    except Exception:
        return ec.INTERNAL_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
