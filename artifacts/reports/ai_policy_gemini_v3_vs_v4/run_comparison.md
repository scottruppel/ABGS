# Run Comparison

- Baseline: `AI_Policy_gemini_pilot_v3`
- Candidate: `AI_Policy_gemini_pilot_v4`

## Summary

- Validation pass rate: `0.983` -> `0.983` (`+0.000`)
- Final benchmark size: `59` -> `59` (`+0`)
- Hard fails: `1` -> `1` (`+0`)

## Quality Deltas

- Multi-chunk ratio delta: `+0.000`
- Avg citations per question delta: `-0.119`
- Avg confidence delta: `+0.003`
- Recovered grounding rate delta: `+0.033`
- Duplicate hard-fail delta: `+0`
- Low-information soft-fail delta: `-3`

## Preprocessing Deltas

- Filtered chunk delta: `+0`
- Raw chunk delta: `+0`
- Accepted chunk delta: `+0`

## Generation Deltas

- Generated question delta: `+0`
- Duplicate signatures skipped delta: `+0`
- Low-quality topics skipped delta: `+1`
- Unique topic count delta: `+0`

## Evaluation Deltas

- `extractive_baseline` answer support: `0.847` -> `0.931` (`+0.084`)
- `gemini:gemini-2.5-flash` answer support: `0.347` -> `0.751` (`+0.404`)
- `cautious_refuser` answer support: `0.636` -> `0.690` (`+0.054`)

## Recommendation

Candidate run shows mixed results and should be reviewed before replacing the baseline.
