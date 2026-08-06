from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tạo bộ data quality checks cho dataframe.

    Checks:
    1. Row count.
    2. paper_id not null và unique.
    3. title not null.
    4. Độ dài summary >= 100 chars.
    5. Freshness theo age_days <= freshness_threshold_days.
    6. Ghi kết quả vào data/quality/{report_name}.json.
    """
    total_rows = int(len(df))
    if total_rows == 0:
        result = {
            "report_name": report_name,
            "passed": False,
            "total_rows": 0,
            "paper_id_nulls": 0,
            "paper_id_duplicates": 0,
            "title_nulls": 0,
            "short_summaries": 0,
            "stale_rows": 0,
        }
    else:
        paper_id_nulls = int(df["paper_id"].isnull().sum())
        paper_id_duplicates = int(df.duplicated(subset=["paper_id"]).sum())
        title_nulls = int(df["title"].isnull().sum())
        short_summaries = int((df["summary_chars"] < 100).sum()) if "summary_chars" in df.columns else int((df["summary"].str.len() < 100).sum())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0

        passed = (
            paper_id_nulls == 0
            and paper_id_duplicates == 0
            and title_nulls == 0
            and short_summaries == 0
            and stale_rows == 0
        )

        result = {
            "report_name": report_name,
            "passed": passed,
            "total_rows": total_rows,
            "paper_id_nulls": paper_id_nulls,
            "paper_id_duplicates": paper_id_duplicates,
            "title_nulls": title_nulls,
            "short_summaries": short_summaries,
            "stale_rows": stale_rows,
            "freshness_threshold_days": settings.freshness_threshold_days,
        }

    output_path = settings.paths.quality_dir / f"{report_name}.json"
    write_json(output_path, result)
    return result


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Tổng hợp freshness report.

    1. Tìm latest và oldest published date.
    2. Đếm số dòng stale (age_days > freshness_threshold_days).
    3. Tạo payload: latest_published, oldest_published, stale_rows, total_rows, is_fresh.
    4. Ghi JSON report.
    """
    total_rows = int(len(df))
    if total_rows == 0:
        payload = {
            "total_rows": 0,
            "latest_published": "",
            "oldest_published": "",
            "stale_rows": 0,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": False,
        }
    else:
        latest_published = str(df["published"].max())
        oldest_published = str(df["published"].min())
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum()) if "age_days" in df.columns else 0
        is_fresh = (stale_rows == 0)

        payload = {
            "total_rows": total_rows,
            "latest_published": latest_published,
            "oldest_published": oldest_published,
            "stale_rows": stale_rows,
            "freshness_threshold_days": settings.freshness_threshold_days,
            "is_fresh": is_fresh,
        }

    write_json(Path(report_path), payload)
    return payload
