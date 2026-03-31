# Benchmark Development Log

## Project: Agentic Benchmark Generation System for Defense & Strategy Domains

**Status**: Phase 1 - Data Collection Planning  
**Date**: March 31, 2026

---

## Executive Summary

Building a non-gameable benchmark system to evaluate LLM capability on complex, specialized domains. Focus: Defense Acquisition and Strategic Decision-Making.

**Key Principle**: Agent role is **data collection orchestration**, NOT content generation. All corpus materials must come from independent, authoritative sources.

---

## Completed Work

### 1. MTG Draft Benchmark ✅
**Status**: 48 QA pairs generated and evaluated

**Corpus**:
- `01_draft_fundamentals.txt` - Draft mechanics, strategy, evaluation
- `02_limited_theory.txt` - Format theory, card evaluation, metagame
- Total: ~3,500 words

**Results**:
- 48 validated QA pairs
- L1/L2/L3 distribution: 67%/17%/17%
- Difficulty gradient: Oracle 100%, Extractive 66.7%
- Multi-chunk synthesis: 33.3%

**Live Evaluation**:
- Claude Sonnet 4: 31.1% support rate, 54.2% attempt rate
- Gemini 3.0 Flash: 20.4% support rate, 35.4% attempt rate
- **Verdict**: Claude significantly better at strategic reasoning

**Assessment**: ✅ **Benchmark is valid**
- Prevents memorization (0% exact match)
- Clear difficulty gradient
- Measures real reasoning (procedural questions separate models)

---

### 2. Defense Acquisition Benchmark ⚠️
**Status**: 57 QA pairs generated BUT corpus is compromised

**Corpus** (INVALID - Agent-Generated):
- `01_das_overview.txt` - Written from my training knowledge
- `02_far_dfars_fundamentals.txt` - Synthesized from my understanding
- `03_adaptive_acquisition_framework.txt` - My knowledge, not independent sources
- Total: ~42 KB

**Results**:
- 57 validated QA pairs
- L1/L2/L3 distribution: 68%/19%/12%
- Difficulty gradient: Oracle 100%, Extractive 68.4%

**Critical Issue**: ⚠️ **CORPUS VALIDITY COMPROMISED**
- I generated content based on my training data
- This makes evaluation circular: Claude tested against content I synthesized
- Defeats entire purpose of independent benchmark
- Scott correctly identified this as unacceptable

---

## Next Phase: Proper Data Collection for AAF Benchmark

### Focus Area
**Adaptive Acquisition Framework & Non-FAR Acquisition**

Why this domain:
- Fast-moving policy area
- Where real innovation happens
- Tests understanding of modern acquisition strategy
- High stakes for DoD acquisition professionals

### Source Categories to Collect

**Official Policy** (High Priority):
- DoD Instruction 5000.02 (latest) - AAF official policy
- OSD Policy Memos - Deputy Secretary memos on acquisition reform
- Defense Acquisition Guidebook (DAG) - Implementation guidance
- Middle-Tier Acquisition (MTA) Guidance - Specific pathway details

**Alternative Acquisition Authorities**:
- Other Transaction (OT) Authority Guidance (10 USC 4021, 4022)
- Commercial Solutions Opening (CSO) guidance
- Software Acquisition Pathway documentation
- Services Acquisition Reform Act (SARA) guidance

**Real-World Analysis & Case Studies**:
- Defense Innovation Unit (DIU) reports on rapid acquisition
- RAND Corporation studies on acquisition reform
- GAO reports on acquisition effectiveness
- Public case studies (Space Force, missile programs, etc.)

**Think Tank & Expert Analysis**:
- CSIS acquisition analysis
- Hudson Institute defense technology reports
- Brookings Institution on defense transformation
- War College publications on acquisition strategy

### Data Collection Workflow

1. **Source Identification** (Agent coordinates):
   - Identify authoritative document sources
   - Verify they are official/unmodified
   - Create list of specific documents to retrieve

2. **Source Retrieval** (Using independent tools):
   - Gemini Deep Research (systematic document gathering)
   - Web fetch from official sources (acquisition.gov, dod.gov)
   - Direct access to government databases (if available)
   - University/think tank repositories

3. **Source Validation** (Human oversight):
   - You verify documents are legitimate
   - Check publication dates, authorship
   - Ensure no agent bias in selection
   - Confirm independent sourcing

4. **Raw Storage**:
   - Store validated sources in `/home/scott/ABGS/data/aaf_sources_raw/`
   - Document provenance of each source
   - Keep originals unmodified

5. **ABGS Pipeline** (Automated):
   - Ingest raw sources
   - Generate QA pairs purely from source material
   - Apply validation filters
   - Create benchmark dataset

6. **Live Evaluation**:
   - Test Claude & Gemini on questions derived from sources
   - Neither model has seen these specific Q&A pairs
   - Evaluate on domain understanding, not training data overlap

---

## Key Learnings

### ✅ What Went Right
1. **MTG benchmark validated the approach**
   - Non-gameable domain (game strategy, not general knowledge)
   - Clear difficulty gradient
   - Effective model differentiation
   - Real reasoning tests (not memorization)

2. **Architecture is sound**
   - ABGS pipeline works well
   - Config-based approach enables flexibility
   - Evaluation metrics are meaningful
   - Baseline vs live evaluation comparison works

3. **Agent's role clarified**
   - Orchestration, not generation
   - Data collection coordination
   - Validation and quality gates
   - Reproducibility tracking

### ⚠️ What Went Wrong
1. **Self-dealing in DAS benchmark**
   - Agent generated corpus from own knowledge
   - Defeated purpose of independent benchmark
   - Scott correctly called this out
   - Lesson: Never synthesize corpus content

2. **Bias risk**
   - Agent selecting/generating sources introduces bias
   - Real sources must come from human review
   - Independent tools (Deep Research) should supplement, not replace, human judgment

### 📚 Acquired Knowledge
1. **Benchmark design principles**
   - Non-gameable = domain-specific, not in training data
   - Difficulty gradient essential for discrimination
   - Multi-chunk synthesis forces reasoning
   - Baseline performance should show clear cliff at L2+

2. **Defense Acquisition complexity**
   - Enormous domain with interconnected concepts
   - Policy constantly evolving
   - Multiple pathways appropriate for different scenarios
   - Real practitioners spend years learning this

3. **Agent limitations**
   - Cannot be trusted to generate "neutral" content
   - Own training data biases what I consider important
   - Data collection must be independent and verifiable
   - Agent's role is coordination, not creation

---

## Next Steps

### Immediate (This Week)
1. Define specific AAF sources to collect
2. Identify which sources you can access
3. Set up raw source directory structure
4. Create collection plan with source targets

### Short-term (Next Week)
1. Use Gemini Deep Research to systematically gather documents
2. You validate each source
3. Store raw materials with provenance tracking
4. Begin ABGS ingestion on validated sources

### Medium-term (2-3 Weeks)
1. Generate QA pairs from independent sources
2. Run live evaluation against Claude & Gemini
3. Analyze results on real policy understanding
4. Document findings on model acquisition policy reasoning

### Long-term Vision
Agentic framework that:
- ✅ Orchestrates data collection from multiple sources
- ✅ Validates source independence and authority
- ✅ Manages ABGS pipeline execution
- ✅ Coordinates live evaluations
- ✅ Reports results with full provenance tracking
- ✅ Commits findings to GitHub automatically

---

## Files & Locations

### Source Materials
```
/home/scott/ABGS/data/
├── magic_drafting/           # ✅ Validated MTG corpus
│   ├── 01_draft_fundamentals.txt
│   ├── 02_limited_theory.txt
│   └── README.md
├── aaf_sources_raw/          # 🚧 To be populated with real sources
│   └── (sources collected here)
└── reference_configs/
    ├── magic_drafting.yaml   # ✅ Config
    └── defense_acquisition.yaml  # ⚠️ Config only (no valid corpus yet)
```

### Generated Benchmarks
```
/home/scott/ABGS/artifacts/
├── runs/
│   ├── magic_drafting_v1/        # ✅ 48 validated pairs
│   └── defense_acquisition_v1/   # ⚠️ 57 pairs (compromised corpus)
└── reports/
    ├── magic_drafting_v1/        # ✅ Evaluation complete
    └── defense_acquisition_v1/   # 🚧 Waiting for source validation
```

### Memory & Documentation
```
/home/scott/.openclaw/workspace/memory/
├── ABGS-agent-integration.md
├── ABGS-mtg-progress.md
├── ABGS-eval-results.md
├── gemini-vs-sonnet-results.md
└── das-benchmark-complete.md (⚠️ References compromised corpus)
```

---

## Commit History

- `135b18d` - Add Magic: The Gathering draft corpus and benchmark config
- `e545c71` - Add benchmark configs for MTG draft and defense acquisition (data collection phase)

---

## Success Criteria for AAF Benchmark

✅ Sources are independent (you validate)
✅ Documents are authoritative (official DoD/government)
✅ No agent-generated synthesis
✅ Provenance of each source documented
✅ 50+ QA pairs across AAF domain
✅ Clear difficulty gradient (L1/L2/L3)
✅ Multi-chunk synthesis present
✅ Live evaluation completes on both Claude & Gemini
✅ Results show meaningful model differentiation

---

## Conclusion

The MTG benchmark proved the approach works. The DAS corpus mistake (agent generation) was a valuable lesson in maintaining benchmark integrity. 

**Next phase**: Proper data collection on AAF/non-traditional acquisition using independent sources, orchestrated by the agent but validated by you. This will create a legitimate, non-gameable benchmark for evaluating LLM understanding of modern defense acquisition strategy.
