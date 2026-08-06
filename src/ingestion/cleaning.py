from __future__ import annotations

from datetime import UTC, date, datetime
import json
import logging
import re
import sys
from pathlib import Path

import pandas as pd

# Tự động thêm 'src' vào sys.path nếu chưa có để cho phép chạy script trực tiếp
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.utils import compact_join, ensure_parent, normalize_whitespace, write_csv, write_json
from ingestion.crossref import PaperRecord, load_raw_records

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Loại bỏ các thẻ HTML/XML (ví dụ: <jats:p>, <b>) và chuẩn hóa khoảng trắng."""
    if not text:
        return ""
    # Strip XML/HTML tags
    text_no_html = re.sub(r"<[^>]+>", " ", text)
    return normalize_whitespace(text_no_html)


def _parse_date(value: str) -> date | None:
    """Chuyển đổi chuỗi ngày xuất bản thành object date chuẩn YYYY-MM-DD."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError):
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime | None = None) -> pd.DataFrame:
    """Clean raw PaperRecord list thành pandas DataFrame chuẩn cho embedding và RAG.

    Quy tắc làm sạch:
    1. Loại bỏ bản ghi rác: Drop hàng không có tiêu đề hoặc summary < 100 ký tự.
    2. Chuẩn hóa text: Strip thẻ XML/HTML khỏi title, summary, authors, categories.
    3. Xử lý tác giả & category: Gộp thành authors_joined, categories_joined (cách nhau dấu phẩy).
    4. Tính Freshness: Chuẩn hóa published YYYY-MM-DD và tính age_days so với run_date.
    5. Cột ngữ nghĩa text_for_embedding: "Title: [title] | Authors: [authors_joined] | Summary: [summary]".
    6. Deduplicate: Drop duplicate paper_id và sắp xếp mới nhất trước.
    """
    if run_date is None:
        run_date = datetime.now(UTC)
    run_date_only = run_date.date() if isinstance(run_date, datetime) else run_date

    rows: list[dict] = []
    skipped_short_summary = 0
    skipped_no_title = 0

    for record in records:
        title = clean_text(record.title)
        summary = clean_text(record.summary)

        # 1. Loại bỏ bản ghi rác: thiếu title hoặc summary < 100 ký tự
        if not title:
            skipped_no_title += 1
            continue
        if len(summary) < 100:
            skipped_short_summary += 1
            logger.debug("Bỏ qua record summary quá ngắn (< 100 chars): %s", title[:50])
            continue

        # 2. Xử lý tác giả & categories
        authors = [clean_text(a) for a in record.authors if clean_text(a)]
        categories = [clean_text(c) for c in record.categories if clean_text(c)]
        authors_joined = compact_join(authors, sep=", ")
        categories_joined = compact_join(categories, sep=", ")
        primary_category = clean_text(record.primary_category) or (categories[0] if categories else "")

        # 3. Date & Freshness (age_days)
        published_date = _parse_date(record.published)
        published_str = published_date.isoformat() if published_date else record.published
        age_days = (run_date_only - published_date).days if published_date else 0

        # 4. Cột biểu diễn ngữ nghĩa text_for_embedding
        text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"

        rows.append(
            {
                "paper_id": record.paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "authors_joined": authors_joined,
                "categories": categories,
                "categories_joined": categories_joined,
                "primary_category": primary_category,
                "published": published_str,
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    logger.info(
        "Filtered raw records: %d kept, %d skipped (<100 chars summary), %d skipped (no title).",
        len(rows),
        skipped_short_summary,
        skipped_no_title,
    )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # Deduplicate & Sort
    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    return df


def save_clean_dataset(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Lưu kết quả làm sạch vào data/clean/papers_clean.csv và data/clean/papers_clean.json."""
    ensure_parent(csv_path)
    ensure_parent(json_path)

    # 1. Lưu CSV
    write_csv(df, csv_path)
    logger.info("Đã lưu clean CSV (%d hàng) → %s", len(df), csv_path)

    # 2. Lưu JSON (giữ nguyên kiểu dữ liệu list cho authors và categories)
    records_dict = df.to_dict(orient="records")
    write_json(json_path, records_dict)
    logger.info("Đã lưu clean JSON (%d hàng) → %s", len(df), json_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from core.config import load_settings

    settings = load_settings()
    raw_records_path = settings.paths.raw_records_json
    clean_csv_path = settings.paths.clean_csv
    clean_json_path = settings.paths.clean_json

    if not raw_records_path.exists():
        print(f"File {raw_records_path} chưa tồn tại. Hãy chạy crossref.py trước!")
    else:
        records = load_raw_records(raw_records_path)
        df_clean = build_clean_dataframe(records)
        save_clean_dataset(df_clean, clean_csv_path, clean_json_path)
        print(f"\nSuccessfully cleaned {len(records)} records into {len(df_clean)} clean rows.")
        if not df_clean.empty:
            print("Columns:", list(df_clean.columns))
            print("\nSample clean record 0:")
            print("  Paper ID :", df_clean.iloc[0]["paper_id"])
            print("  Title    :", df_clean.iloc[0]["title"])
            print("  Authors  :", df_clean.iloc[0]["authors_joined"])
            print("  Published:", df_clean.iloc[0]["published"])
            print("  Age Days :", df_clean.iloc[0]["age_days"])
            print("  Embedding Text:", df_clean.iloc[0]["text_for_embedding"][:150] + "...")
