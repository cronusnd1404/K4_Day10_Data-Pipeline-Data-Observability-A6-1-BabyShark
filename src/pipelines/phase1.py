from __future__ import annotations

from datetime import UTC, datetime
import logging
from pathlib import Path
import sys

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe, save_clean_dataset
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logger = logging.getLogger(__name__)


def main() -> None:
    """Xây dựng baseline pipeline end-to-end cho Phase 1."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # 1. Load settings
    logger.info("Step 1: Loading settings...")
    settings = load_settings()

    # 2. Fetch hoặc load raw records
    logger.info("Step 2: Loading/Fetching raw records...")
    raw_records_path = settings.paths.raw_records_json
    if raw_records_path.exists() and not settings.refresh_source:
        logger.info("Loading existing raw records from %s", raw_records_path)
        records = load_raw_records(raw_records_path)
    else:
        logger.info("Fetching fresh raw records from Crossref API...")
        records = fetch_source_records(settings)

    # 3. Clean data & save
    logger.info("Step 3: Cleaning raw records...")
    df_clean = build_clean_dataframe(records, run_date=datetime.now(UTC))
    save_clean_dataset(df_clean, settings.paths.clean_csv, settings.paths.clean_json)

    # 4. Build ChromaDB Vector Index
    logger.info("Step 4: Building ChromaDB vector store index...")
    index = LocalEmbeddingIndex.build(df_clean, settings)

    # 5. Build hoặc load Evaluation Test Set
    logger.info("Step 5: Preparing evaluation test set...")
    testset_path = settings.paths.eval_testset
    if testset_path.exists() and not settings.refresh_test_set:
        logger.info("Loading existing test set from %s", testset_path)
        read_json(testset_path)
    else:
        logger.info("Generating new evaluation test set...")
        build_test_set(df_clean, testset_path)

    # 6. Evaluate Baseline Pipeline
    logger.info("Step 6: Running baseline evaluation...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    logger.info("Baseline Evaluation Summary: %s", bundle.summary)

    # 7. Run Data Quality Checks & Freshness Report
    logger.info("Step 7: Running data observability (quality & freshness)...")
    quality_res = run_data_quality_checks(df_clean, settings, "baseline_quality")
    freshness_res = build_freshness_report(df_clean, settings, settings.paths.freshness_report)

    # 8. Generate Phase 1 Markdown Report
    logger.info("Step 8: Generating Phase 1 Markdown Report...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_count": len(records),
        "clean_count": len(df_clean),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality_res,
        freshness=freshness_res,
    )
    logger.info("Phase 1 Baseline Pipeline completed successfully! Report saved to %s", settings.paths.baseline_report)


if __name__ == "__main__":
    main()
