# Run Comparison

- Baseline: `AI_Policy_refined`
- Candidate: `AI_Policy`

## Summary

- Validation pass rate: `0.731` -> `0.833` (`+0.101`)
- Final benchmark size: `468` -> `681` (`+213`)
- Hard fails: `172` -> `137` (`-35`)

## Quality Deltas

- Multi-chunk ratio delta: `+0.037`
- Avg citations per question delta: `+0.037`
- Avg confidence delta: `+0.043`
- Duplicate hard-fail delta: `-35`
- Low-information soft-fail delta: `-27`

## Preprocessing Deltas

- Filtered chunk delta: `+2`
- Raw chunk delta: `+91`
- Accepted chunk delta: `+89`

## Generation Deltas

- Generated question delta: `+178`
- Duplicate signatures skipped delta: `-8`
- Low-quality topics skipped delta: `-3`
- Unique topic count delta: `+84`

## Evaluation Deltas

- `extractive_baseline` answer support: `0.809` -> `0.792` (`-0.017`)
- `oracle` answer support: `1.000` -> `1.000` (`+0.000`)
- `cautious_refuser` answer support: `0.653` -> `0.602` (`-0.051`)

## Recommendation

Candidate run is an improvement and should be treated as the new benchmark baseline.
