# AAF Benchmark Corpus - Source Manifest

**Purpose**: Document provenance of all source materials for Defense Acquisition System benchmark

**Key Principle**: All sources are official DoD documents, publicly available, and independently verified.

---

## Category 1: Core AAF Policy

### DoDI 5000.02 - Operation of the Adaptive Acquisition Framework
- **Status**: TO BE RETRIEVED
- **Source**: Official DoD Instruction (current version)
- **Authority**: USD(A&S) / OUSD(Acquisition & Sustainment)
- **Purpose**: Master instruction defining six AAF pathways and transition rules
- **Retrieval Method**: acquisition.gov or dod.mil
- **Expected Size**: 50-100 pages
- **Critical Content**:
  - Six pathway definitions
  - Gate/milestone structure for each
  - Entry/exit criteria
  - Decision points and reviews

### AAF 101 Briefing Deck
- **Status**: TO BE RETRIEVED
- **Source**: OUSD(A&S) official briefing
- **Authority**: Office of the Under Secretary of Defense
- **Purpose**: High-level visual summary of AAF pathways
- **Retrieval Method**: osd.mil or DAU site
- **Expected Size**: 30-50 slides
- **Critical Content**:
  - Pathway comparison matrix
  - Timeline comparisons
  - Use case guidance
  - Entry/exit criteria visual

### Modernized Selected Acquisition Report (MSAR) 2026 Guidance
- **Status**: TO BE RETRIEVED
- **Source**: Official DoD reporting guidance (2026 version)
- **Authority**: OUSD(A&S)
- **Purpose**: How DoD reports acquisition under AAF (replaces old SAR)
- **Retrieval Method**: acquisition.gov
- **Expected Size**: 20-40 pages
- **Critical Content**:
  - Reporting structure changes
  - Metrics by pathway
  - Data requirements

---

## Category 2: Non-FAR Acquisition Tools

### DoD Other Transactions (OT) Guide - July 2023
- **Status**: TO BE RETRIEVED
- **Source**: Official DoD Other Transactions Authority guidance
- **Authority**: OUSD(A&S) and Legal Counsel
- **Purpose**: Definitive guide to non-FAR prototyping and production
- **Retrieval Method**: acquisition.gov or DIU site
- **Expected Size**: 80-120 pages
- **Critical Content**:
  - OT legal authority (10 USC 4021, 4022)
  - Prototyping vs. production distinctions
  - Contractor eligibility (traditional + non-traditional)
  - Cost sharing and IP rules
  - Process and timeline
  - "Myth-busting" section

### Commercial Solutions Opening (CSO) Guide - December 2025
- **Status**: TO BE RETRIEVED
- **Source**: GSA/DoD joint guidance (current version)
- **Authority**: GSA and OUSD(A&S)
- **Purpose**: Streamlined acquisition of innovative commercial items
- **Retrieval Method**: acquisition.gov or GSA site
- **Expected Size**: 40-60 pages
- **Critical Content**:
  - CSO legal authority
  - FAR-light procedures
  - Process timeline
  - Contractor outreach
  - Evaluation criteria

### DIU Commercial Solutions Opening Process
- **Status**: TO BE RETRIEVED
- **Source**: Defense Innovation Unit official documentation
- **Authority**: DIU (Pentagon office reporting to USD(A&S))
- **Purpose**: DIU's specific rapid acquisition workflow
- **Retrieval Method**: diu.mil/reports or defense.gov
- **Expected Size**: 20-40 pages
- **Critical Content**:
  - "Solution Brief" to "Pitch" to "Prototype" workflow
  - Timeline (weeks/months, not years)
  - Non-traditional contractor recruitment
  - Success stories/case studies

---

## Category 3: Rapid & Adaptive Pathways

### Middle Tier of Acquisition (MTA) - DoDI 5000.80
- **Status**: TO BE RETRIEVED
- **Source**: Official DoD Instruction
- **Authority**: USD(A&S)
- **Purpose**: Governs Section 804 programs (Rapid Prototyping and Fielding)
- **Retrieval Method**: acquisition.gov or dod.mil
- **Expected Size**: 40-80 pages
- **Critical Content**:
  - Rapid Prototyping pathway (2-3 years)
  - Rapid Innovation Transition pathway
  - JCIDS requirements bypass authority
  - Gate structure (simplified vs. traditional)
  - Examples

### Software Acquisition Pathway Quick Start Primer
- **Status**: TO BE RETRIEVED
- **Source**: Official DoD guidance
- **Authority**: OUSD(A&S)
- **Purpose**: Pathway designed for Agile/DevSecOps development
- **Retrieval Method**: acquisition.gov or dau.mil
- **Expected Size**: 15-30 pages
- **Critical Content**:
  - MVCR (Minimum Viable Capability Release) concept
  - Continuous iteration vs. "Big Bang"
  - Testing and evaluation for software
  - DevSecOps integration
  - Examples

### DoD Software Pathway 101 Presentation
- **Status**: TO BE RETRIEVED
- **Source**: Practitioner's guide
- **Authority**: OUSD(A&S) / DAU
- **Purpose**: How Software Pathway differs from hardware acquisition
- **Retrieval Method**: dau.mil or acquisition.gov
- **Expected Size**: 20-40 slides
- **Critical Content**:
  - Agile methodology integration
  - Continuous deployment concepts
  - Risk management for software
  - Team structure differences

---

## Category 4: Interactive Resources

### DAU Interactive AAF Site
- **Status**: REFERENCE (not directly downloadable)
- **URL**: dau.mil (DAU Academy)
- **Purpose**: Current source for custom job support tools
- **Access**: Can generate pathway-specific PDFs
- **Value**: Real-time updates, community discussions

---

## Data Collection Workflow

### Phase 1: Retrieval
1. Scott identifies which documents are most accessible
2. Documents retrieved from official sources
3. Store as PDFs in this directory
4. Document URL, retrieval date, version

### Phase 2: Validation
1. Verify official DoD/GSA seals
2. Check publication dates (prefer 2023-2026)
3. Confirm no modifications to original
4. Validate against known versions

### Phase 3: Organization
Each source stored as:
```
[CATEGORY]_[DOCUMENT_NAME]_[VERSION].pdf
Example: 01_DoDI_5000.02_AAF_2024.pdf
```

Metadata for each:
```json
{
  "filename": "document.pdf",
  "source_url": "official_url",
  "retrieved_date": "2026-03-31",
  "version": "latest",
  "authority": "OUSD(A&S)",
  "pages": 75,
  "verified": true
}
```

### Phase 4: ABGS Processing
1. ABGS ingests raw PDFs
2. Generates QA pairs purely from content
3. No agent synthesis or interpretation
4. Questions traceable to source documents

---

## Expected Benchmark Outcome

**Target**: 80-150 QA pairs covering:
- AAF pathway selection and decision-making
- OT/CSO vs. FAR-based trade-offs
- Rapid acquisition process and timelines
- Software pathway specifics
- Non-traditional contractor integration
- Risk management in rapid pathways

**Difficulty Distribution** (target):
- L1 (Retrieval): 60% - Facts about pathways, authorities, timelines
- L2 (Synthesis): 30% - When to use which pathway, trade-off analysis
- L3 (Expert): 10% - Complex scenario reasoning, policy interpretation

**Live Evaluation**:
- Claude Sonnet 4 vs. Gemini 3.0 Flash
- Questions derived from official sources only
- Test domain understanding, not memorization

---

## Success Criteria

✅ All sources officially published by DoD/GSA
✅ Retrievable from government sites (publicly available)
✅ Current versions (2023 or later, preferably 2025-2026)
✅ Verified unmodified from original
✅ Covers 6+ distinct AAF topics
✅ Mix of policy, guidance, and practical examples
✅ 8-12 core source documents minimum
✅ Total 300+ pages of source material
✅ Full provenance documentation
✅ No agent-generated synthesis

---

## Next Steps

1. **Scott retrieves documents** from official sources
2. **Documents stored** in this directory with metadata
3. **ABGS processes** raw materials only
4. **QA pairs generated** purely from ingested documents
5. **Live evaluation** tests Claude and Gemini on real policy understanding

---

**Document Created**: March 31, 2026
**Status**: Awaiting source retrieval and validation
