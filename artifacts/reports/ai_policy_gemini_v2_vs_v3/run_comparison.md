# Run Comparison

- Baseline: `AI_Policy_gemini_pilot_v2`
- Candidate: `AI_Policy_gemini_pilot_v3`

## Summary

- Validation pass rate: `0.883` -> `0.983` (`+0.100`)
- Final benchmark size: `53` -> `59` (`+6`)
- Hard fails: `7` -> `1` (`-6`)

## Quality Deltas

- Multi-chunk ratio delta: `-0.021`
- Avg citations per question delta: `+0.116`
- Avg confidence delta: `+0.070`
- Recovered grounding rate delta: `+0.850`
- Duplicate hard-fail delta: `+0`
- Low-information soft-fail delta: `+0`

## Preprocessing Deltas

- Filtered chunk delta: `+0`
- Raw chunk delta: `+0`
- Accepted chunk delta: `+0`

## Generation Deltas

- Generated question delta: `+0`
- Duplicate signatures skipped delta: `+0`
- Low-quality topics skipped delta: `-2`
- Unique topic count delta: `+0`

## Evaluation Deltas

- `cautious_refuser` answer support: `0.708` -> `0.636` (`-0.072`)
- `gemini:gemini-2.5-flash` answer support: `0.000` -> `0.347` (`+0.347`)
- `extractive_baseline` answer support: `0.915` -> `0.847` (`-0.068`)
- `oracle` answer support: `0.000` -> `0.000` (`+0.000`)

## Recommendation

Candidate run is an improvement and should be treated as the new benchmark baseline.
