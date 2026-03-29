# Run Comparison Guide

## Purpose

Use the run comparison workflow to measure how one benchmark iteration differs from another. This is the fastest way to track whether preprocessing, generation, validation, or evaluation changes are improving the benchmark.

## Command

Compare two run directories with:

```bash
abgs-compare compare --baseline artifacts/runs/AI_Policy_refined --candidate artifacts/runs/AI_Policy --output artifacts/reports/ai_policy_delta
```

This writes:

- `run_comparison.json`
- `run_comparison.md`

to the output directory and also prints the markdown summary to the terminal.

## Recommended Comparison Metrics

Review these first:

- validation pass rate delta
- accepted, soft-fail, and hard-fail deltas
- final benchmark size delta
- duplicate hard-fail delta
- low-information soft-fail delta
- multi-chunk ratio delta
- answer support rate delta by model
- filtered chunk count delta
- duplicate signatures skipped delta

## Suggested Trend Tracking Fields

When comparing runs over time, keep a simple record of:

- run name
- corpus name
- config hash
- validation pass rate
- total retained questions
- duplicate hard fails
- low-information soft fails
- multi-chunk ratio
- filtered chunk count
- unique topic count
- answer support rate by model

## Interpreting Results

- If validation pass rate increases and hard fails decrease, the candidate run is usually an improvement.
- If retained question count increases but quality drops, the candidate run may be too permissive.
- If filtered chunk count increases modestly and validation quality rises, preprocessing is likely working.
- If duplicate signatures skipped increases and duplicate hard fails still remain high, generation is improving but validation still needs to catch residual duplication.
- If answer support rate falls while dataset size rises, benchmark breadth may be improving at the expense of answer grounding.

## Good Practice

- Always compare runs created from the same corpus when evaluating pipeline changes.
- Use the same reference config when possible.
- Treat the comparison markdown as the human-readable summary and the comparison JSON as the system record.
- For conference reporting, keep each major refinement step paired with one comparison artifact.
