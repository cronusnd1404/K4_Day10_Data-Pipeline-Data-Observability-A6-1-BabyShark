from __future__ import annotations

import random
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import now_utc, write_json

RANDOM_SEED = 42

DROP_LATEST_FRACTION = 0.15
BLANK_SUMMARY_FRACTION = 0.15
NOISE_FRACTION = 0.15
TRUNCATE_TITLE_FRACTION = 0.15
STALE_DATE_FRACTION = 0.15
DUPLICATE_FRACTION = 0.10

STALE_DATE_DAYS = 3650
TITLE_MAX_CHARS = 12

NOISE_SNIPPETS = [
    "#@$%!! corrupted_bytes",
    "<<<CORRUPTED>>>",
    "lorem gibberish qzxjk",
    "!!!ERROR_INJECTED!!!",
    "�� broken_encoding",
]


def _sample_indices(rng: random.Random, index: pd.Index, fraction: float) -> list:
    available = list(index)
    if not available:
        return []
    count = max(1, round(len(available) * fraction))
    count = min(count, len(available))
    return rng.sample(available, count)


def _drop_latest_records(df: pd.DataFrame, rng: random.Random, log: list[dict[str, Any]]) -> pd.DataFrame:
    if df.empty:
        return df
    sort_key = pd.to_datetime(df["published"], errors="coerce")
    ordered = df.assign(_sort_key=sort_key).sort_values(
        "_sort_key", ascending=False, na_position="last"
    )
    count = max(1, round(len(df) * DROP_LATEST_FRACTION))
    count = min(count, len(df))
    dropped = ordered.iloc[:count]
    remaining = ordered.iloc[count:].drop(columns="_sort_key")
    for paper_id in dropped["paper_id"].tolist():
        log.append(
            {
                "type": "drop_latest_record",
                "paper_id": paper_id,
                "detail": "Dropped as part of latest-record simulated ingestion gap.",
            }
        )
    return remaining


def _blank_summaries(df: pd.DataFrame, rng: random.Random, log: list[dict[str, Any]]) -> pd.DataFrame:
    targets = _sample_indices(rng, df.index, BLANK_SUMMARY_FRACTION)
    for idx in targets:
        before = df.at[idx, "summary"]
        df.at[idx, "summary"] = ""
        if "summary_chars" in df.columns:
            df.at[idx, "summary_chars"] = 0
        log.append(
            {
                "type": "blank_summary",
                "paper_id": df.at[idx, "paper_id"],
                "before_chars": len(before) if isinstance(before, str) else None,
                "after_chars": 0,
            }
        )
    return df


def _inject_noise(df: pd.DataFrame, rng: random.Random, log: list[dict[str, Any]]) -> pd.DataFrame:
    targets = _sample_indices(rng, df.index, NOISE_FRACTION)
    for idx in targets:
        before = df.at[idx, "summary"]
        snippet = rng.choice(NOISE_SNIPPETS)
        after = f"{before} {snippet}".strip()
        df.at[idx, "summary"] = after
        if "summary_chars" in df.columns:
            df.at[idx, "summary_chars"] = len(after)
        log.append(
            {
                "type": "inject_noise",
                "paper_id": df.at[idx, "paper_id"],
                "snippet": snippet,
            }
        )
    return df


def _truncate_titles(df: pd.DataFrame, rng: random.Random, log: list[dict[str, Any]]) -> pd.DataFrame:
    targets = _sample_indices(rng, df.index, TRUNCATE_TITLE_FRACTION)
    for idx in targets:
        before = df.at[idx, "title"]
        if not isinstance(before, str) or len(before) <= TITLE_MAX_CHARS:
            continue
        after = before[:TITLE_MAX_CHARS].rstrip() + "..."
        df.at[idx, "title"] = after
        log.append(
            {
                "type": "truncate_title",
                "paper_id": df.at[idx, "paper_id"],
                "before": before,
                "after": after,
            }
        )
    return df


def _stale_dates(df: pd.DataFrame, rng: random.Random, log: list[dict[str, Any]]) -> pd.DataFrame:
    targets = _sample_indices(rng, df.index, STALE_DATE_FRACTION)
    reference = now_utc()
    stale_date = (reference - timedelta(days=STALE_DATE_DAYS)).date().isoformat()
    for idx in targets:
        before = df.at[idx, "published"]
        df.at[idx, "published"] = stale_date
        if "age_days" in df.columns:
            df.at[idx, "age_days"] = STALE_DATE_DAYS
        log.append(
            {
                "type": "stale_date",
                "paper_id": df.at[idx, "paper_id"],
                "before_published": before,
                "after_published": stale_date,
            }
        )
    return df


def _add_duplicate_rows(df: pd.DataFrame, rng: random.Random, log: list[dict[str, Any]]) -> pd.DataFrame:
    targets = _sample_indices(rng, df.index, DUPLICATE_FRACTION)
    if not targets:
        return df
    duplicates = df.loc[targets].copy()
    for paper_id in duplicates["paper_id"].tolist():
        log.append(
            {
                "type": "duplicate_row",
                "paper_id": paper_id,
                "detail": "Duplicated existing row with identical paper_id.",
            }
        )
    return pd.concat([df, duplicates], ignore_index=True)


def _build_text_for_embedding(row: pd.Series) -> str:
    parts = [
        str(row.get("title", "") or ""),
        str(row.get("authors_joined", "") or ""),
        str(row.get("categories_joined", "") or ""),
        str(row.get("summary", "") or ""),
    ]
    return ". ".join(part for part in parts if part).strip()


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: Path,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    rng = random.Random(seed)
    working = df.reset_index(drop=True).copy()
    log_entries: list[dict[str, Any]] = []
    original_row_count = len(working)

    working = _drop_latest_records(working, rng, log_entries)
    working = working.reset_index(drop=True)
    working = _blank_summaries(working, rng, log_entries)
    working = _inject_noise(working, rng, log_entries)
    working = _truncate_titles(working, rng, log_entries)
    working = _stale_dates(working, rng, log_entries)
    working = _add_duplicate_rows(working, rng, log_entries)
    working = working.reset_index(drop=True)

    if not working.empty:
        working["text_for_embedding"] = working.apply(_build_text_for_embedding, axis=1)

    write_json(
        Path(output_log_path),
        {
            "seed": seed,
            "original_row_count": original_row_count,
            "corrupted_row_count": len(working),
            "corruption_counts": pd.Series(
                [entry["type"] for entry in log_entries]
            ).value_counts().to_dict()
            if log_entries
            else {},
            "entries": log_entries,
        },
    )
    return working
