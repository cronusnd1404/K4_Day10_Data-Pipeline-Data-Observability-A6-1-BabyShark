from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.utils import write_text


def generate_phase1_report(
    report_path: Path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Tạo báo cáo markdown cho Phase 1 Baseline Pipeline."""
    hit_rate = metrics.get("retrieval_hit_rate", 0.0) * 100
    token_f1 = metrics.get("mean_token_f1", 0.0) * 100
    judge_acc = metrics.get("judge_accuracy", 0.0) * 100
    judge_score = metrics.get("mean_judge_score", 0.0)

    md_content = f"""# Phase 1: Baseline Pipeline Report

## 1. Source Summary
- **Source API**: {source_summary.get("source_api", "Crossref REST API")}
- **Query**: `{source_summary.get("source_query", "")}`
- **Filter**: `{source_summary.get("source_filter", "")}`
- **Total Raw Records**: {source_summary.get("raw_count", 0)}
- **Cleaned Records**: {source_summary.get("clean_count", 0)}

## 2. Baseline Evaluation Metrics
- **Total Samples**: {metrics.get("samples", 0)}
- **Retrieval Hit Rate**: `{hit_rate:.2f}%`
- **Mean Token F1**: `{token_f1:.2f}%`
- **Judge Accuracy**: `{judge_acc:.2f}%`
- **Mean Judge Score**: `{judge_score:.2f} / 5.0`

## 3. Data Quality & Freshness
- **Quality Checks Passed**: `{'PASSED' if quality.get('passed') else 'FAILED'}`
- **Total Rows**: {quality.get('total_rows', 0)}
- **Null paper_ids**: {quality.get('paper_id_nulls', 0)}
- **Duplicate paper_ids**: {quality.get('paper_id_duplicates', 0)}
- **Short Summaries (<100 chars)**: {quality.get('short_summaries', 0)}
- **Stale Rows (> {freshness.get('freshness_threshold_days', 180)} days)**: {freshness.get('stale_rows', 0)}
- **Latest Published**: {freshness.get('latest_published', 'N/A')}
- **Oldest Published**: {freshness.get('oldest_published', 'N/A')}
- **Is Fresh**: `{'YES' if freshness.get('is_fresh') else 'NO'}`
""".strip() + "\n"

    write_text(Path(report_path), md_content)


def generate_corruption_report(
    report_path: Path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Tạo báo cáo markdown so sánh giữa Baseline, Corrupted và Repaired."""
    def fmt(val: float) -> str:
        return f"{val * 100:.2f}%"

    md_content = f"""# Data Corruption & Repair Comparison Report

## 1. Metrics Comparison

| Metric | Baseline | Corrupted | Repaired |
|---|---|---|---|
| **Retrieval Hit Rate** | {fmt(baseline_metrics.get('retrieval_hit_rate', 0.0))} | {fmt(corrupted_metrics.get('retrieval_hit_rate', 0.0))} | {fmt(repaired_metrics.get('retrieval_hit_rate', 0.0))} |
| **Mean Token F1** | {fmt(baseline_metrics.get('mean_token_f1', 0.0))} | {fmt(corrupted_metrics.get('mean_token_f1', 0.0))} | {fmt(repaired_metrics.get('mean_token_f1', 0.0))} |
| **Judge Accuracy** | {fmt(baseline_metrics.get('judge_accuracy', 0.0))} | {fmt(corrupted_metrics.get('judge_accuracy', 0.0))} | {fmt(repaired_metrics.get('judge_accuracy', 0.0))} |
| **Mean Judge Score** | {baseline_metrics.get('mean_judge_score', 0.0):.2f} | {corrupted_metrics.get('mean_judge_score', 0.0):.2f} | {repaired_metrics.get('mean_judge_score', 0.0):.2f} |

## 2. Data Observability & Quality Impact

| Check | Corrupted | Repaired |
|---|---|---|
| **Quality Status** | {'PASSED' if corrupted_quality.get('passed') else 'FAILED'} | {'PASSED' if repaired_quality.get('passed') else 'FAILED'} |
| **Stale Rows** | {corrupted_quality.get('stale_rows', 0)} | {repaired_quality.get('stale_rows', 0)} |
| **Short Summaries** | {corrupted_quality.get('short_summaries', 0)} | {repaired_quality.get('short_summaries', 0)} |
| **Is Fresh** | {'YES' if corrupted_freshness.get('is_fresh') else 'NO'} | {'YES' if repaired_freshness.get('is_fresh') else 'NO'} |
""".strip() + "\n"

    write_text(Path(report_path), md_content)
