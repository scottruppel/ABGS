# Benchmark Report

## Executive Summary

- Best overall hybrid support: `oracle` at `1.000`
- Best demo-slice hybrid support: `oracle` at `1.000`
- Strongest cautious behavior: `cautious_refuser` at `0.161` appropriate refusal
- The benchmark separates grounded extractive behavior from abstention-heavy behavior and from abstractive answering.

## Model Behavior Profile

### Claude Sonnet 4

**Strengths:**
- Higher citation overlap with source excerpts (quote-style grounding).
- Lower overall refusal rate (answers more often).
- Lower inappropriate-refusal rate.
- Higher answer-alignment vs reference answers (paraphrase match).

**Weaknesses:**
- (none above relative threshold vs peers)

**Behavioral tendency:** Grounded but comparatively willing to answer (moderate refusal).

### Gemini 2.5 Flash

**Strengths:**
- (none above relative threshold vs peers)

**Weaknesses:**
- Lower citation overlap with source excerpts.
- Higher overall refusal rate.
- Higher inappropriate-refusal rate (abstains when benchmark expects an answer).
- Lower answer-alignment vs reference answers.

**Behavioral tendency:** Mixed: lower citation overlap than peers with comparatively higher refusal—review failure examples.

## Use Case Guidance

- **Compliance / policy interpretation (maximize source grounding):** prefer **`Claude Sonnet 4`** (higher citation support on this benchmark).
- **Exploratory Q&A / lower friction:** consider **`Claude Sonnet 4`** (lower refusal rate than `Gemini 2.5 Flash` on this benchmark).
- **Avoid silent abstention on answerable items:** prefer **`Claude Sonnet 4`** (lower inappropriate-refusal rate vs `Gemini 2.5 Flash`).

## Evaluation Protocol (reproducibility)

- **ABGS version:** `0.1.0`
- **Evaluation protocol ID:** `abgs-eval-hybrid-1` (bump when hybrid scoring or refusal taxonomy changes).
- **validated_qa SHA-256:** `6a5ca08ebdbe879cf17a90a7a008b0c9873c4f838d7e6641e97087eb4645a1c4`
- **run_manifest SHA-256:** `7e697f0485cf875fa02149e9655da42bf3d94781c49b6fbde5e65757bf496a1d`
- **Run id:** `709bd80eb54b`
- **Config hash (generation):** `f8e4fb961aae12b89b42a7e38e8012c6601fd2e4e25accb58ceead3928fcebfa`
- **Resolved models (no secrets):**
  - `gemini`: `gemini-2.5-flash`
  - `anthropic`: `claude-sonnet-4-20250514`

## Beyond accuracy: what this benchmark measures

ABGS reports measure **answer policy** and **epistemic stance**, not only scalar accuracy:

- **When models answer vs refuse** — refusal rate, appropriate vs inappropriate refusal given benchmark expectations.
- **How answers relate to sources** — citation-style overlap (quote presence) and hybrid alignment with reference answers.
- **Why refusals happen** — inspect `refusal_type` and example failures; models differ in how often they abstain on answerable items.

Together, this supports **model epistemology** comparisons: conservative grounding vs assertive completion, under the same items and scoring rubric.

## Dataset Overview

- Size: `931`
- Validation pass rate: `0.544`
- Recovered grounding rate: `0.000`
- Multi-chunk ratio: `0.390`
- Difficulty distribution: `{'L2': 253, 'L3': 110, 'L1': 568}`
- Question type distribution: `{'factual': 328, 'procedural': 330, 'analytical': 77, 'edge_case': 196}`

## Model Comparison Table

| Metric | gemini:gemini-2.5-flash | anthropic | oracle | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- | --- |
| Exact Match | 0.001 | 0.001 | 1.000 | 0.610 | 0.567 |
| Answer Support Rate | 0.241 | 0.284 | 1.000 | 0.894 | 0.763 |
| Citation Support Rate | 0.110 | 0.155 | 1.000 | 0.811 | 0.707 |
| Answer Alignment Rate | 0.227 | 0.258 | 1.000 | 0.889 | 0.758 |
| Refusal Rate | 0.643 | 0.609 | 0.000 | 0.000 | 0.161 |
| Appropriate Refusal | 0.145 | 0.150 | 0.000 | 0.000 | 0.161 |

## Breakdown by Difficulty

| Slice | gemini:gemini-2.5-flash | anthropic | oracle | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- | --- |
| L1 | 0.002/0.272 | 0.002/0.343 | 1.000/1.000 | 1.000/1.000 | 0.930/0.930 |
| L2 | 0.000/0.259 | 0.000/0.267 | 1.000/1.000 | 0.000/0.721 | 0.000/0.721 |
| L3 | 0.000/0.040 | 0.000/0.018 | 1.000/1.000 | 0.000/0.746 | 0.000/0.000 |

## Breakdown by Question Type

| Slice | gemini:gemini-2.5-flash | anthropic | oracle | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- | --- |
| factual | 0.003/0.589 | 0.000/0.596 | 1.000/1.000 | 0.619/0.895 | 0.619/0.895 |
| procedural | 0.000/0.063 | 0.003/0.163 | 1.000/1.000 | 0.612/0.890 | 0.612/0.890 |
| analytical | 0.000/0.073 | 0.000/0.070 | 1.000/1.000 | 0.519/0.881 | 0.000/0.000 |
| edge_case | 0.000/0.023 | 0.000/0.050 | 1.000/1.000 | 0.628/0.904 | 0.628/0.628 |

## Multi-Chunk Performance

| Slice | gemini:gemini-2.5-flash | anthropic | oracle | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- | --- |
| single_chunk | 0.002/0.272 | 0.002/0.343 | 1.000/1.000 | 1.000/1.000 | 0.930/0.930 |
| multi_chunk | 0.000/0.192 | 0.000/0.191 | 1.000/1.000 | 0.000/0.729 | 0.000/0.503 |

## Demo-Grade Slice

This slice keeps only `L2` and `L3` questions that also require `multi_chunk` synthesis.

| Metric | gemini:gemini-2.5-flash | anthropic | oracle | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- | --- |
| Exact Match | 0.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| Answer Support Rate | 0.192 | 0.191 | 1.000 | 0.729 | 0.503 |
| Citation Support Rate | 0.073 | 0.074 | 1.000 | 0.515 | 0.360 |
| Answer Alignment Rate | 0.191 | 0.188 | 1.000 | 0.714 | 0.489 |
| Refusal Rate | 0.639 | 0.664 | 0.000 | 0.000 | 0.303 |
| Appropriate Refusal | 0.278 | 0.295 | 0.000 | 0.000 | 0.303 |

## Example Failures

### gemini:gemini-2.5-flash

- Question: What does the corpus state about related rules?
- Benchmark answer: related rules. our legacies and outdoor culture should also be a goal we all share and strive towards.
- Model output: The corpus only mentions the phrase "related rules" without providing any further information or statements about them.
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for lake champlain?
- Benchmark answer: Lake Champlain 60 ... opportunities for maintenance workers!
- Model output: The provided source excerpts do not describe any procedure for Lake Champlain.
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for native populations?
- Benchmark answer: have native populations of Arctic charr and is the last true stronghold for wild brook trout. and stocking programs that keep Maine a fishing destination unlike any other in the United States.
- Model output: The provided excerpts do not describe a specific procedure for native populations.
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for warmer-water species?
- Benchmark answer: Cape Cod and the warmer-water species that visit our southern shores create incredible diversity and opportunity. also enlisted the help of hundreds of citizen scientists to collect data on their fishing activities.
- Model output: The provided excerpts do not describe a specific procedure for warmer-water species.
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: How should the reader synthesize the guidance about waterfowl syllabus across the cited material?
- Benchmark answer: and fell asleep at night reading the waterfowl syllabus, dreaming of hermit life dressed in furs. bait.
- Model output: The provided excerpts do not contain sufficient information to synthesize guidance about the waterfowl syllabus. One excerpt mentions someone reading it, but offers no details about its content or how to synthesize guidance from it.
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

### anthropic

- Question: What does the corpus state about related rules?
- Benchmark answer: related rules. our legacies and outdoor culture should also be a goal we all share and strive towards.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for lake champlain?
- Benchmark answer: Lake Champlain 60 ... opportunities for maintenance workers!
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for native populations?
- Benchmark answer: have native populations of Arctic charr and is the last true stronghold for wild brook trout. and stocking programs that keep Maine a fishing destination unlike any other in the United States.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for warmer-water species?
- Benchmark answer: Cape Cod and the warmer-water species that visit our southern shores create incredible diversity and opportunity. also enlisted the help of hundreds of citizen scientists to collect data on their fishing activities.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: How should the reader synthesize the guidance about waterfowl syllabus across the cited material?
- Benchmark answer: and fell asleep at night reading the waterfowl syllabus, dreaming of hermit life dressed in furs. bait.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

### cautious_refuser

- Question: How should the reader synthesize the guidance about waterfowl syllabus across the cited material?
- Benchmark answer: and fell asleep at night reading the waterfowl syllabus, dreaming of hermit life dressed in furs. bait.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: How should the reader synthesize the guidance about fresh-caught dinner across the cited material?
- Benchmark answer: teach kids lifelong lessons — and if you’re lucky, rehash it all over a fresh-caught dinner. available in 1, 3, 7, or 15-day increments, or for the full year ($64 for 2018).
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: How should the reader synthesize the guidance about release survival across the cited material?
- Benchmark answer: has invested lots of resources to address the factors that contribute to catch and release survival. be caught again.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: What edge case or operational risk is associated with tuition reimbursement?
- Benchmark answer: deﬁ ned pension, and training and tuition reimbursement. boat market share.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`

- Question: What edge case or operational risk is associated with nearby water?
- Benchmark answer: you would like to catch, and under it you’ll see a list of nearby water bodies. Grant East Bowerbank Bowdoin College Grant West Bradstreet Brassua Chesuncook Comstock Days Academy Grant Dennistown Plt.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`

### extractive_baseline

- Question: What procedure is described for today?
- Benchmark answer: Today? They are often grouped around structures such as rock piles and boulders and are quite territorial.
- Model output: Today?
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.125`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`

- Question: What does the corpus state about water?
- Benchmark answer: water. slot protects fish and allows them to continue to grow and reach a larger size class.
- Model output: water.
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.125`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`

- Question: What does the corpus state about species?
- Benchmark answer: species. acres Primary Fishery: LLS (S) Access: Trailered boat access on Mayberry Hill Rd.
- Model output: species.
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.163`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`

- Question: What does the corpus state about enosburg falls?
- Benchmark answer: Enosburg Falls. All Applicable Counties 1 Williams River Connecticut River main channel to US Route 5 bridge, Rockingham.
- Model output: Enosburg Falls.
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.221`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`

- Question: What procedure is described for enosburg falls?
- Benchmark answer: Enosburg Falls. All Applicable Counties 1 Williams River Connecticut River main channel to US Route 5 bridge, Rockingham.
- Model output: Enosburg Falls.
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.221`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`
