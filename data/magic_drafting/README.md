# Magic: The Gathering Draft Corpus

This corpus contains comprehensive resources for evaluating Large Language Model (LLM) understanding of Magic: The Gathering draft theory, card evaluation, strategic decision-making, and meta-game knowledge.

## Corpus Contents

### 1. Foundational Theory
- **01_draft_fundamentals.md**: Core draft mechanics, the pick-and-pass process, deck construction rules, basic strategy principles, and fundamental evaluation concepts.
- **02_limited_theory.md**: Advanced limited format theory, card evaluation frameworks, mana management, mechanics, and format-level analysis.

## Domain Description

Magic: The Gathering Draft is a complex strategic domain requiring:

1. **Mechanical Knowledge**
   - Game rules and format specifics
   - Card interactions and stack mechanics
   - Mana system and resource management

2. **Strategic Thinking**
   - Signal reading (inferring opponent's colors from passed cards)
   - Archetype synergies and format meta-game
   - Deck curve and composition ratios
   - Risk assessment and trade-offs

3. **Card Evaluation**
   - Assessing card power level in context
   - Understanding efficiency and mana value
   - Recognizing situational vs. universally good cards
   - Synergy evaluation

4. **Metagame Analysis**
   - Identifying open lanes (undercontested strategies)
   - Adapting to format composition
   - Understanding which archetypes are viable

## Why This Corpus?

Magic draft is an **excellent test domain** for LLM evaluation because:

### 1. **Domain Specificity**
Magic has a well-defined rules set and established strategic theory. There are objectively correct and incorrect answers to most draft questions.

### 2. **Prevents Benchmark Gaming**
Unlike general knowledge benchmarks that might be in training data, specific draft questions about card interactions and strategic choices require genuine understanding, not memorization.

### 3. **Gradient of Difficulty**
- **Easy**: "What is a bomb in limited?" (factual retrieval)
- **Medium**: "When should you splash a third color?" (procedural reasoning)
- **Hard**: "Why is card A better than card B in this archetype?" (expert reasoning)

### 4. **Objective Evaluation**
Draft questions have objectively correct answers rooted in game theory and competitive analysis. Models can't "guess" their way through—they must understand the reasoning.

### 5. **Multiple Answer Formats**
- Factual (direct answers)
- Strategic (reasoning and justification)
- Comparative (evaluating options)
- Procedural (step-by-step decisions)

## Question Generation Strategy

The ABGS system will generate questions across multiple dimensions:

### By Content Type
- **Mechanics**: How the game works (20%)
- **Strategy**: Decision-making (30%)
- **Evaluation**: Card assessment (25%)
- **Meta**: Format-level analysis (25%)

### By Difficulty
- **L1 Retrieval** (30%): "What is X?"
- **L2 Synthesis** (40%): "Why/how should you X?"
- **L3 Expert** (30%): Complex multi-factor reasoning

### By Format
- **Factual**: Direct knowledge
- **Procedural**: Process understanding
- **Analytical**: Strategic reasoning
- **Adversarial**: Edge cases and trick questions

## Expected Benchmark Characteristics

- **~150-200 QA pairs** from this corpus
- **Coverage across all archetypes** (Aggressive, Midrange, Control, Ramp)
- **Multiple difficulty levels** to distinguish novice from expert LLMs
- **Grounded answers** with citations to specific corpus sections
- **Difficulty ratings** to contextualize performance

## Future Expansion

This corpus can be extended with:

1. **Set-Specific Analysis**: Current rotation draft guides
2. **Card Databases**: Specific card mechanics and interactions
3. **Competitive Records**: Pro player analyses and pick decisions
4. **Format Evolution**: How draft has changed over time
5. **Complex Synergies**: Multi-card interaction patterns

## Corpus Philosophy

Unlike generic knowledge datasets, this corpus is **strategically dense**. Every document is selected to provide actionable strategic knowledge. Filler and generic "facts" are minimized. The goal is to create a benchmark that truly evaluates LLM understanding of strategy, not just recall.

---

**Corpus Created**: March 31, 2026
**Intended for**: ABGS Benchmark Generation System
**Evaluation Models**: Claude Sonnet 4, Gemini 3.0 Pro
**Domain Difficulty**: High (requires strategic reasoning, not just factual recall)
