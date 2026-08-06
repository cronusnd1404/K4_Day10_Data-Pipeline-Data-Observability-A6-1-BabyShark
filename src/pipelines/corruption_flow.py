from __future__ import annotations

import logging
from datetime import datetime, UTC
from pathlib import Path

import pandas as pd

from core.config import load_settings, Settings
from core.utils import read_json, write_csv, write_json
from ingestion import build_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex
from evaluation import evaluate_pipeline

logger = logging.getLogger(__name__)


def _load_corrupted_dataset(settings: Settings) -> pd.DataFrame:
    corrupted_path = settings.paths.corrupted_clean_csv
    if not corrupted_path.exists():
        raise FileNotFoundError(
            f"Corrupted dataset not found: {corrupted_path}. "
            "Please generate or place papers_clean_corrupted.csv before running phase 2."
        )
    logger.info("Loading corrupted clean dataset from %s", corrupted_path)
    return pd.read_csv(corrupted_path)


def _save_repaired_dataset(df: pd.DataFrame, settings: Settings) -> None:
    logger.info("Saving repaired clean dataset to CSV and JSON.")
    write_csv(df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, df.to_dict(orient="records"))


def _build_quality_payload(df: pd.DataFrame, settings: Settings, label: str) -> tuple[dict[str, object], dict[str, object]]:
    quality = run_data_quality_checks(df, settings, report_name=label)
    freshness = build_freshness_report(
        df,
        settings,
        settings.paths.quality_dir / f"{label}_freshness_report.json",
    )
    return quality, freshness


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    settings = load_settings()
    logger.info("Starting corruption flow pipeline.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)

    corrupted_df = _load_corrupted_dataset(settings)
    logger.info("Building corrupted ChromaDB index.")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    logger.info("Evaluating corrupted dataset on frozen test set.")
    evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    logger.info("Repairing corrupted data from raw records.")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    _save_repaired_dataset(repaired_df, settings)

    logger.info("Building repaired ChromaDB index.")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    logger.info("Evaluating repaired dataset on frozen test set.")
    evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    corrupted_quality, corrupted_freshness = _build_quality_payload(corrupted_df, settings, label="corrupted")
    repaired_quality, repaired_freshness = _build_quality_payload(repaired_df, settings, label="repaired")

    logger.info("Generating corruption comparison report.")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=read_json(settings.paths.corrupted_metrics),
        repaired_metrics=read_json(settings.paths.repaired_metrics),
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    logger.info("Corruption flow pipeline completed.")
    logger.info("Artifacts:")
    logger.info("  - corrupted_clean_csv=%s", settings.paths.corrupted_clean_csv)
    logger.info("  - corrupted_embeddings_manifest=%s", settings.paths.corrupted_embeddings_json)
    logger.info("  - corrupted_metrics=%s", settings.paths.corrupted_metrics)
    logger.info("  - corrupted_answers=%s", settings.paths.corrupted_answers)
    logger.info("  - repaired_clean_csv=%s", settings.paths.repaired_clean_csv)
    logger.info("  - repaired_clean_json=%s", settings.paths.repaired_clean_json)
    logger.info("  - repaired_embeddings_manifest=%s", settings.paths.repaired_embeddings_json)
    logger.info("  - repaired_metrics=%s", settings.paths.repaired_metrics)
    logger.info("  - repaired_answers=%s", settings.paths.repaired_answers)
    logger.info("  - comparison_report=%s", settings.paths.comparison_report)


if __name__ == "__main__":
    main()
