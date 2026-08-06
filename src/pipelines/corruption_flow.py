from __future__ import annotations

from datetime import UTC, datetime
import logging
from pathlib import Path
import sys

import pandas as pd

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.config import Settings, load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe, save_clean_dataset
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def _ensure_corrupted_dataset(settings: Settings) -> pd.DataFrame:
    corrupted_path = settings.paths.corrupted_clean_csv
    if not corrupted_path.exists():
        logger.info("Corrupted dataset not found at %s. Generating controlled corrupted dataset...", corrupted_path)
        clean_csv_path = settings.paths.clean_csv
        if not clean_csv_path.exists():
            raise FileNotFoundError(f"Clean dataset not found at {clean_csv_path}. Please run Phase 1 baseline pipeline first!")
        df_clean = pd.read_csv(clean_csv_path)
        corrupt_clean_dataframe(
            df_clean,
            output_csv_path=settings.paths.corrupted_clean_csv,
            output_json_path=settings.paths.corrupted_clean_json,
            output_log_path=settings.paths.corruption_log,
            test_set_path=settings.paths.eval_testset,
        )
    logger.info("Loading corrupted clean dataset from %s", corrupted_path)
    return pd.read_csv(corrupted_path).fillna("")


def _save_repaired_dataset(df: pd.DataFrame, settings: Settings) -> None:
    logger.info("Saving repaired clean dataset to CSV and JSON.")
    save_clean_dataset(df, settings.paths.repaired_clean_csv, settings.paths.repaired_clean_json)


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
    logger.info("Starting Phase 2: Corruption Flow Pipeline.")

    # 1. Load Baseline Metrics
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # 2. Corrupted Phase
    logger.info("Step 1: Loading/Generating corrupted dataset...")
    corrupted_df = _ensure_corrupted_dataset(settings)

    logger.info("Step 2: Building corrupted ChromaDB index...")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    logger.info("Step 3: Evaluating corrupted dataset on frozen test set...")
    evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    corrupted_metrics = read_json(settings.paths.corrupted_metrics)
    logger.info("Corrupted Evaluation Metrics: %s", corrupted_metrics)

    # 3. Repair Phase
    logger.info("Step 4: Repairing corrupted data from raw records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, datetime.now(UTC))
    _save_repaired_dataset(repaired_df, settings)

    logger.info("Step 5: Building repaired ChromaDB index...")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    logger.info("Step 6: Evaluating repaired dataset on frozen test set...")
    evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_metrics = read_json(settings.paths.repaired_metrics)
    logger.info("Repaired Evaluation Metrics: %s", repaired_metrics)

    # 4. Observability & Report
    logger.info("Step 7: Running data observability for corrupted and repaired states...")
    corrupted_quality, corrupted_freshness = _build_quality_payload(corrupted_df, settings, label="corrupted")
    repaired_quality, repaired_freshness = _build_quality_payload(repaired_df, settings, label="repaired")

    logger.info("Step 8: Generating corruption comparison report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_metrics,
        repaired_metrics=repaired_metrics,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    logger.info("Phase 2 Corruption Flow Pipeline completed successfully!")
    logger.info("Artifacts created:")
    logger.info("  - corrupted_clean_csv        : %s", settings.paths.corrupted_clean_csv)
    logger.info("  - corrupted_clean_json       : %s", settings.paths.corrupted_clean_json)
    logger.info("  - corruption_log             : %s", settings.paths.corruption_log)
    logger.info("  - corrupted_metrics          : %s", settings.paths.corrupted_metrics)
    logger.info("  - repaired_clean_csv         : %s", settings.paths.repaired_clean_csv)
    logger.info("  - repaired_metrics           : %s", settings.paths.repaired_metrics)
    logger.info("  - comparison_report (md)     : %s", settings.paths.comparison_report)


if __name__ == "__main__":
    main()
