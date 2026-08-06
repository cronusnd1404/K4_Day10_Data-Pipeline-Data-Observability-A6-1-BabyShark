from __future__ import annotations

import logging
from datetime import datetime, UTC
from pathlib import Path

from core.config import load_settings, Settings
from core.utils import write_csv, write_json
from ingestion import PaperRecord, build_clean_dataframe, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex
from evaluation import build_test_set, evaluate_pipeline

logger = logging.getLogger(__name__)


def _load_raw_records(settings: Settings) -> list[PaperRecord]:
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings)

    logger.info(
        "Raw records snapshot exists at %s and refresh disabled, loading from disk.",
        settings.paths.raw_records_json,
    )
    return load_raw_records(settings.paths.raw_records_json)


def _save_clean_dataset(df, settings: Settings) -> None:
    logger.info("Saving cleaned dataset to CSV and JSON.")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))


def _build_source_summary(records: list[PaperRecord], settings: Settings) -> dict[str, object]:
    return {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "max_results": settings.max_results,
        "refresh_source": settings.refresh_source,
        "raw_api_response": str(settings.paths.raw_api_response),
        "raw_records_json": str(settings.paths.raw_records_json),
        "raw_record_count": len(records),
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    settings = load_settings()
    logger.info("Starting phase1 baseline pipeline.")

    records = _load_raw_records(settings)
    source_summary = _build_source_summary(records, settings)

    run_date = datetime.now(UTC)
    logger.info("Building cleaned dataframe from raw records.")
    clean_df = build_clean_dataframe(records, run_date)
    _save_clean_dataset(clean_df, settings)

    logger.info("Building ChromaDB index from cleaned data.")
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        logger.info("Generating evaluation test set.")
        build_test_set(clean_df, settings.paths.eval_testset)
    else:
        logger.info(
            "Evaluation test set already exists at %s and refresh disabled.",
            settings.paths.eval_testset,
        )

    logger.info("Evaluating baseline pipeline on test set.")
    evaluation_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    logger.info("Running data quality and freshness checks.")
    quality_report = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness_report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    logger.info("Generating phase1 markdown report.")
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )

    logger.info("Baseline pipeline completed.")
    logger.info("Artifacts:")
    logger.info("  - clean_csv=%s", settings.paths.clean_csv)
    logger.info("  - clean_json=%s", settings.paths.clean_json)
    logger.info("  - embeddings_manifest=%s", settings.paths.embeddings_json)
    logger.info("  - eval_testset=%s", settings.paths.eval_testset)
    logger.info("  - baseline_metrics=%s", settings.paths.baseline_metrics)
    logger.info("  - baseline_answers=%s", settings.paths.baseline_answers)
    logger.info("  - freshness_report=%s", settings.paths.freshness_report)
    logger.info("  - baseline_report=%s", settings.paths.baseline_report)


if __name__ == "__main__":
    main()
