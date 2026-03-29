# Benchmark Report

## Executive Summary

- Best overall hybrid support: `extractive_baseline` at `0.931`
- Best demo-slice hybrid support: `extractive_baseline` at `0.906`
- Strongest cautious behavior: `cautious_refuser` at `0.288` appropriate refusal
- The benchmark separates grounded extractive behavior from abstention-heavy behavior and from abstractive answering.

## Model Behavior Profile

### Claude Sonnet 4

**Strengths:**
- Higher hybrid answer support on multi-chunk synthesis (vs other live models).
- Lower overall refusal rate (answers more often).

**Weaknesses:**
- Lower citation overlap with source excerpts.

**Behavioral tendency:** More assertive: lower refusal; source-quote overlap is not the strongest signal on this slice.

### Gemini 2.5 Flash

**Strengths:**
- Higher citation overlap with source excerpts (quote-style grounding).

**Weaknesses:**
- Lower hybrid answer support on multi-chunk synthesis (vs other live models).
- Higher overall refusal rate.

**Behavioral tendency:** Conservative: stays close to source overlap and declines more often.

## Use Case Guidance

- **Compliance / policy interpretation (maximize source grounding):** prefer **`Gemini 2.5 Flash`** (higher citation support on this benchmark).
- **Multi-document synthesis:** prefer **`Claude Sonnet 4`** (higher hybrid support on multi-chunk items).
- **Exploratory Q&A / lower friction:** consider **`Claude Sonnet 4`** (lower refusal rate than `Gemini 2.5 Flash` on this benchmark).

## Evaluation Protocol (reproducibility)

- **ABGS version:** `0.1.0`
- **Evaluation protocol ID:** `abgs-eval-hybrid-1` (bump when hybrid scoring or refusal taxonomy changes).
- **validated_qa SHA-256:** `02d922681bc4e38d5502778048a163905f23eee29997bcfdf6adacca4284edac`
- **run_manifest SHA-256:** `f479e84a20f710faaa0fd61b93b862063c1ed3c3c81a4d5ac696b1aae37cc895`
- **Run id:** `805d62b03b4a`
- **Config hash (generation):** `5745477fc9fc327dbe5860859ac231934d8a42a807d7157ed0afd990721e6167`
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

- Size: `59`
- Validation pass rate: `0.983`
- Recovered grounding rate: `0.883`
- Multi-chunk ratio: `0.356`
- Difficulty distribution: `{'L2': 18, 'L3': 9, 'L1': 32}`
- Question type distribution: `{'factual': 17, 'procedural': 15, 'analytical': 13, 'edge_case': 14}`

## Model Comparison Table

| Metric | gemini:gemini-2.5-flash | anthropic | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- |
| Exact Match | 0.085 | 0.034 | 0.017 | 0.017 |
| Answer Support Rate | 0.751 | 0.741 | 0.931 | 0.690 |
| Citation Support Rate | 0.390 | 0.314 | 0.907 | 0.678 |
| Answer Alignment Rate | 0.715 | 0.709 | 0.685 | 0.492 |
| Refusal Rate | 0.102 | 0.068 | 0.000 | 0.288 |
| Appropriate Refusal | 0.051 | 0.000 | 0.000 | 0.288 |

## Breakdown by Difficulty

| Slice | gemini:gemini-2.5-flash | anthropic | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- |
| L1 | 0.125/0.828 | 0.031/0.795 | 0.000/1.000 | 0.000/0.875 |
| L2 | 0.056/0.705 | 0.056/0.674 | 0.056/0.841 | 0.056/0.707 |
| L3 | 0.000/0.572 | 0.000/0.685 | 0.000/0.863 | 0.000/0.000 |

## Breakdown by Question Type

| Slice | gemini:gemini-2.5-flash | anthropic | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- |
| factual | 0.176/0.891 | 0.059/0.855 | 0.000/0.956 | 0.000/0.956 |
| procedural | 0.067/0.728 | 0.067/0.624 | 0.067/0.964 | 0.067/0.964 |
| analytical | 0.077/0.712 | 0.000/0.763 | 0.000/0.817 | 0.000/0.000 |
| edge_case | 0.000/0.644 | 0.000/0.709 | 0.000/0.968 | 0.000/0.714 |

## Multi-Chunk Performance

| Slice | gemini:gemini-2.5-flash | anthropic | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- |
| single_chunk | 0.105/0.799 | 0.026/0.763 | 0.000/0.944 | 0.000/0.775 |
| multi_chunk | 0.048/0.665 | 0.048/0.701 | 0.048/0.906 | 0.048/0.536 |

## Demo-Grade Slice

This slice keeps only `L2` and `L3` questions that also require `multi_chunk` synthesis.

| Metric | gemini:gemini-2.5-flash | anthropic | extractive_baseline | cautious_refuser |
| --- | --- | --- | --- | --- |
| Exact Match | 0.048 | 0.048 | 0.048 | 0.048 |
| Answer Support Rate | 0.665 | 0.701 | 0.906 | 0.536 |
| Citation Support Rate | 0.310 | 0.262 | 0.881 | 0.524 |
| Answer Alignment Rate | 0.638 | 0.680 | 0.668 | 0.380 |
| Refusal Rate | 0.143 | 0.048 | 0.000 | 0.429 |
| Appropriate Refusal | 0.095 | 0.000 | 0.000 | 0.429 |

## Example Failures

### gemini:gemini-2.5-flash

- Question: What type of guidance has the DoD Chief Information Office (CIO) published to ensure AI systems are secure and resilient?
- Benchmark answer: The DoD Chief Information Office (CIO) has published guidance integrating cybersecurity risk management, cyber test and evaluation (T&E), and acquisitions processes for the Software Acquisition Pathway.
- Model output: The provided source excerpts do not specify the type of guidance published by the DoD Chief Information Office (CIO) to ensure AI systems are secure and resilient. It mentions guidance related to cybersecurity risk management, cyber test and evaluation, and acquisitions processes for the Software Acquisition Pathway.
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: What measures are required to protect advanced AI technologies from misuse or theft?
- Benchmark answer: Advanced AI technologies must be prevented from being misused or stolen by malicious actors, and emerging and unforeseen risks from AI need to be monitored with constant vigilance.
- Model output: The provided source excerpts state that preventing advanced technologies from being misused or stolen will require constant vigilance, but they do not detail specific measures required to achieve this.
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: What specific instruction does DoDI 8500.01 mandate for DoD organizations regarding their systems, especially in the context of evolving vulnerabilities?
- Benchmark answer: DoDI 8500.01 requires DoD organizations to categorize all their systems in accordance with Committee on National Security Systems Instruction (CNSSI) 1253.
- Model output: The provided source excerpt states that DoDI 8500.01 mandates DoD organizations to categorize all DoD systems in accordance with Committee on National Security Systems Instruction (CNSSI) 1253. It does not provide specific instructions regarding evolving vulnerabilities.
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`

- Question: How does U.S. government policy aim to protect freedom of speech and ensure truthfulness in the era of AI, according to the provided text?
- Benchmark answer: U.S. government policy aims to ensure free speech flourishes and that AI procured by the Federal government objectively reflects truth rather than social engineering agendas, and also plans to revise the NIST AI Risk Management Framework to eliminate references to misinformation, Diversity, Equity, and Inclusion, and climate change.
- Model output: REFUSE: live evaluation failed
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `['multi_hop_required']`

- Question: What specific component of President Trump's AI Action Plan is the Department of War's AI integration strategy designed to be consistent with?
- Benchmark answer: The strategy is consistent with the directive to "Lead in International AI Diplomacy and Security."
- Model output: The provided source excerpts do not mention the Department of War's AI integration strategy or what specific component of President Trump's AI Action Plan it is designed to be consistent with.
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L1`, `['ambiguous_question']`

### anthropic

- Question: What measures are required to protect advanced AI technologies from misuse or theft?
- Benchmark answer: Advanced AI technologies must be prevented from being misused or stolen by malicious actors, and emerging and unforeseen risks from AI need to be monitored with constant vigilance.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `[]`

- Question: How does America plan to make large-scale computing power more accessible for startups and academics?
- Benchmark answer: By improving the financial market for compute.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L2`, `['low_information_value', 'overly_trivial']`

- Question: What security priorities should data scientists, data engineers, and cybersecurity teams consider when implementing cybersecurity for an AI system?
- Benchmark answer: They should consider the security priorities outlined in the following sections of the document.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L1`, `[]`

- Question: How should the effectiveness of the DOD and IC's AI adoption initiatives be evaluated?
- Benchmark answer: The effectiveness should be evaluated based on AI net assessments.
- Model output: REFUSE: insufficient source excerpts
- Support/refusal: support `0.000`, refused `True`, refusal_type `inappropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L1`, `[]`

- Question: What specific governmental action is emphasized as necessary to allow the private sector to lead AI innovation and maintain global leadership?
- Benchmark answer: The government must remove red tape and onerous regulations to enable private-sector-led innovation.
- Model output: Removing red tape and dismantling unnecessary regulatory barriers that hinder private sector innovation is emphasized as the necessary governmental action to allow the private sector to lead AI innovation and maintain global leadership.
- Support/refusal: support `0.381`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.000`, alignment `0.381`, mode `hybrid_alignment`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`

### cautious_refuser

- Question: What type of guidance has the DoD Chief Information Office (CIO) published to ensure AI systems are secure and resilient?
- Benchmark answer: The DoD Chief Information Office (CIO) has published guidance integrating cybersecurity risk management, cyber test and evaluation (T&E), and acquisitions processes for the Software Acquisition Pathway.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: What are the three foundational pillars of America's AI Action Plan?
- Benchmark answer: The three pillars of America’s AI Action Plan are innovation, infrastructure, and international diplomacy and security.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: To what extent do individual DoD organizations have the authority to set their own risk tolerance for the use of AI systems, despite overarching cybersecurity implementation guidance?
- Benchmark answer: Each DoD organization retains the autonomy to determine its own risk tolerance for AI system use, provided it aligns with established DoD strategies, policies, and specific cybersecurity program parameters.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`

- Question: What specific governmental action is emphasized as necessary to allow the private sector to lead AI innovation and maintain global leadership?
- Benchmark answer: The government must remove red tape and onerous regulations to enable private-sector-led innovation.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`

- Question: Why is tailoring of general DoD cybersecurity risk management methods necessary for AI systems?
- Benchmark answer: Tailoring is required because AI systems possess essential priorities and unique security considerations.
- Model output: REFUSE: insufficient certainty
- Support/refusal: support `0.000`, refused `True`, refusal_type `appropriate_refusal`
- Scoring trace: citation `0.000`, alignment `0.000`, mode `empty_response`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

### extractive_baseline

- Question: What strategic actions are being pursued to foster AI development and adoption in America?
- Benchmark answer: Strategic actions include identifying, revising, or repealing regulations that unnecessarily hinder AI development or deployment, and ensuring America has leading open-source and open-weight AI models founded on American values.
- Model output: work 
with all F ederal agencies to identify, revise, or repeal regulations, rules, memoranda, 
administrative orders, guidance documents, policy statements, and interagency 
agreements that unnecessarily hinder AI development or deployment.
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.321`, mode `hybrid_alignment`
- Difficulty/failure modes: `L3`, `['multi_hop_required']`

- Question: What is the dual impact of AI on the American workforce, and what is the necessary response to this transformation?
- Benchmark answer: AI can create new pathways to economic opportunity for American workers, but it will also transform how work is done across all industries, demanding a serious workforce response to help workers navigate this transition.
- Model output: can help America build an economy that delivers more pathways to economic opportunity for American workers.
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.375`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `['multi_hop_required']`

- Question: What is the process for system owners to handle deviations when tailoring the RMF process?
- Benchmark answer: System owners must document deviations within the system’s Security Plan. If these deviations create unmitigated cybersecurity risks, they must be tracked and closed via the system’s Plan of Action and Milestones (POA&M).
- Model output: tailoring allows system owners to document deviations within the system’s Security Plan
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.462`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`

- Question: How does the Department plan to achieve Military AI Dominance and become an "AI-first" warfighting force?
- Benchmark answer: The Department aims to achieve Military AI Dominance by unleashing experimentation with leading AI models, eliminating bureaucratic barriers, focusing investment on America's core asymmetric advantages in AI, and executing "Pace-Setting Projects."
- Model output: The Department will achieve this objective by: 
• Unleashing experimentation with America's leading AI models Department­
wide, and rewarding AI-first re-conceptions of legacy approaches;
- Support/refusal: support `0.500`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.473`, mode `hybrid_alignment`
- Difficulty/failure modes: `L2`, `[]`

- Question: What specific governmental action is emphasized as necessary to allow the private sector to lead AI innovation and maintain global leadership?
- Benchmark answer: The government must remove red tape and onerous regulations to enable private-sector-led innovation.
- Model output: dismantle unnecessary regulatory barriers that hinder the 
private sector in doing so.
- Support/refusal: support `0.556`, refused `False`, refusal_type `None`
- Scoring trace: citation `0.500`, alignment `0.556`, mode `hybrid_alignment`
- Difficulty/failure modes: `L3`, `['ambiguous_question']`
