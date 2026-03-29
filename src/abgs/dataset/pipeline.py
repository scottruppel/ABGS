from __future__ import annotations

from collections import Counter

from abgs.contracts import BenchmarkRecord, CoverageLedgerEntry, DatasetProfile


def build_dataset_profile(
    records: list[BenchmarkRecord],
    coverage: list[CoverageLedgerEntry],
) -> DatasetProfile:
    difficulty_distribution = Counter(record.difficulty.value for record in records)
    question_type_distribution = Counter(
        record.metadata["generation_trace"]["question_type"] for record in records
    )
    citations = [len(record.metadata["citations"]) for record in records]
    multi_chunk_count = sum(
        1 for record in records if record.metadata["quality_signals"].get("multi_chunk_required", False)
    )

    return DatasetProfile(
        total_questions=len(records),
        difficulty_distribution=dict(difficulty_distribution),
        question_type_distribution=dict(question_type_distribution),
        multi_chunk_ratio=round(multi_chunk_count / max(1, len(records)), 3),
        avg_citations_per_question=round(sum(citations) / max(1, len(citations)), 3),
        coverage_summary={
            item.document_id: {
                "chunks_total": item.chunks_total,
                "chunks_covered": item.chunks_covered,
                "questions_generated": item.questions_generated,
                "multi_chunk_questions": item.multi_chunk_questions,
                "question_types": item.question_types,
            }
            for item in coverage
        },
    )
