from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw PaperRecord list thanh dataframe san sang de embed.

    1. Normalize title, summary, authors, categories.
    2. Parse published date, bo record thieu/sai ngay xuat ban.
    3. Tinh age_days so voi run_date.
    4. Tao cot helper: authors_joined, categories_joined, summary_chars,
       text_for_embedding.
    5. Drop duplicate paper_id, sort theo published (moi nhat truoc).
    """
    run_date_only = run_date.date() if isinstance(run_date, datetime) else run_date

    rows: list[dict] = []
    for record in records:
        title = normalize_whitespace(record.title)
        summary = normalize_whitespace(record.summary)
        if not record.paper_id or not title or not summary:
            continue

        published_date = _parse_date(record.published)
        if published_date is None:
            continue

        authors = [normalize_whitespace(a) for a in record.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in record.categories if normalize_whitespace(c)]
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)
        primary_category = normalize_whitespace(record.primary_category) or (categories[0] if categories else "")

        age_days = (run_date_only - published_date).days

        text_for_embedding = normalize_whitespace(
            f"Title: {title}. Categories: {categories_joined}. Abstract: {summary}"
        )

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
                "published": published_date.isoformat(),
                "updated": record.updated,
                "abs_url": record.abs_url,
                "pdf_url": record.pdf_url,
                "comment": record.comment,
                "age_days": age_days,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values("published", ascending=False).reset_index(drop=True)
    return df
