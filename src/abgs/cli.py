from __future__ import annotations

import argparse
from pathlib import Path

from abgs.config import load_config
from abgs.env_utils import load_local_env
from abgs.logging_utils import configure_logging
from abgs.pipeline import run_pipeline
from abgs.reporting.comparison import compare_runs, render_comparison_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="ABGS command line tools.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the ABGS pipeline.")
    run_parser.add_argument("--config", required=True, help="Path to a YAML config file.")
    run_parser.add_argument("--input", required=True, help="Path to the input corpus directory.")
    run_parser.add_argument("--output", required=True, help="Path to the output artifact directory.")
    run_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    compare_parser = subparsers.add_parser("compare", help="Compare two ABGS run directories.")
    compare_parser.add_argument("--baseline", required=True, help="Path to the baseline run directory.")
    compare_parser.add_argument("--candidate", required=True, help="Path to the candidate run directory.")
    compare_parser.add_argument(
        "--output",
        required=False,
        help="Optional directory to write run_comparison.json and run_comparison.md.",
    )
    compare_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    live_parser = subparsers.add_parser(
        "live-eval",
        help="Live Gemini + Anthropic evaluation, merge baselines, write benchmark report.",
    )
    live_parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Completed pipeline run (validated_qa.jsonl, evaluation_records.jsonl).",
    )
    live_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for evaluation_records.jsonl, benchmark_report, evaluation_protocol, live_eval_meta.json.",
    )
    live_parser.add_argument(
        "--repo-root",
        nargs="?",
        const=Path("."),
        default=None,
        type=Path,
        help="Repo root for .env loading. Omit entirely or pass --repo-root alone to use the current directory; "
        "otherwise pass an explicit path (e.g. . or the repo root).",
    )
    live_parser.add_argument(
        "--strategy",
        choices=["full", "anthropic_only"],
        default="full",
        help="full: run Gemini + Anthropic live; anthropic_only: reuse Gemini from baseline eval on disk (v4 workflow).",
    )
    live_parser.add_argument(
        "--v4-paths",
        action="store_true",
        help="Use AI_Policy_gemini_pilot_v4 run and ai_policy_v4_with_claude report paths under --repo-root.",
    )
    live_parser.add_argument("--probe", action="store_true", help="Only test APIs on the first benchmark item.")
    live_parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry rows with live-eval transport failures in existing output-dir.",
    )
    live_parser.add_argument("--skip-probe", action="store_true", help="Skip API probe (not recommended).")
    live_parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    cmp_reports = subparsers.add_parser(
        "compare-reports",
        help="Compare evaluation_summary.json from two report directories (cross-corpus).",
    )
    cmp_reports.add_argument("--baseline", type=Path, required=True, help="First report directory.")
    cmp_reports.add_argument("--candidate", type=Path, required=True, help="Second report directory.")
    cmp_reports.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write markdown here (default: stdout only).",
    )
    cmp_reports.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    args = parser.parse_args()
    configure_logging(getattr(args, "verbose", False))
    load_local_env()

    if args.command == "run":
        config = load_config(args.config)
        run_pipeline(args.input, args.output, config)
        return

    if args.command == "compare":
        comparison = compare_runs(args.baseline, args.candidate, args.output)
        print(render_comparison_markdown(comparison))
        return

    if args.command == "compare-reports":
        from abgs.reporting.cross_corpus import compare_report_summaries, render_cross_corpus_markdown

        text = render_cross_corpus_markdown(
            compare_report_summaries(args.baseline, args.candidate),
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text, encoding="utf-8")
            print(f"Wrote {args.output}")
        else:
            print(text)
        return

    if args.command == "live-eval":
        from abgs.evaluate import live_report

        repo_root = (args.repo_root or Path.cwd()).resolve()
        if args.v4_paths:
            run_dir = repo_root / "artifacts" / "runs" / "AI_Policy_gemini_pilot_v4"
            output_dir = repo_root / "artifacts" / "reports" / "ai_policy_v4_with_claude"
        else:
            if not args.run_dir or not args.output_dir:
                live_parser.error("--run-dir and --output-dir are required unless --v4-paths is set")
            run_dir = args.run_dir.resolve()
            output_dir = args.output_dir.resolve()

        if args.probe:
            validated = run_dir / "validated_qa.jsonl"
            if args.strategy == "full":
                ok = live_report.probe_apis(validated, repo_root)
            else:
                ok = live_report.probe_anthropic_only(validated, repo_root)
            raise SystemExit(0 if ok else 1)

        if args.retry_failed:
            live_report.retry_failed_live_eval(
                run_dir,
                output_dir,
                repo_root=repo_root,
                strategy=args.strategy,
            )
            return

        live_report.run_live_eval_and_report(
            run_dir,
            output_dir,
            args.strategy,
            repo_root=repo_root,
            skip_probe=args.skip_probe,
        )
        return


if __name__ == "__main__":
    main()
