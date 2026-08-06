from __future__ import annotations

import json
import logging
import random
import sys
from datetime import datetime, UTC, date
from pathlib import Path
from typing import Any

import pandas as pd

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.config import load_settings, Settings
from core.utils import write_csv, write_json, read_json, ensure_parent

logger = logging.getLogger(__name__)

RANDOM_SEED = 42

BLANK_SUMMARY_FRACTION = 0.20
NOISE_FRACTION = 0.20
STALE_DATE_FRACTION = 0.20
DUPLICATE_FRACTION = 0.15

STALE_DATE_STR = "2000-01-01"
STALE_AGE_DAYS = 9500

NOISE_SNIPPETS = [
    "#@$%!! corrupted_text",
    "<<<DATA_CORRUPTED_ERROR>>>",
    "lorem gibberish qzxjk random noise text",
    "!!!INVALID_ABSTRACT_INJECTED!!!",
    " broken_encoding_data",
]


def _build_text_for_embedding(row: pd.Series) -> str:
    title = str(row.get("title", "") or "")
    authors = str(row.get("authors_joined", "") or "")
    summary = str(row.get("summary", "") or "")
    return f"Title: {title} | Authors: {authors} | Summary: {summary}"


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_csv_path: Path,
    output_json_path: Path,
    output_log_path: Path,
    test_set_path: Path | None = None,
    seed: int = RANDOM_SEED,
) -> pd.DataFrame:
    """Tự động làm hỏng dữ liệu sạch một cách có kiểm soát.

    Các kịch bản làm hỏng:
    1. Blank Summary: Xóa summary của 20% bản ghi.
    2. Stale Date: Đổi ngày xuất bản thành 2000-01-01 (stale) cho 20% bản ghi.
    3. Add Noise: Chèn ký tự gây nhiễu vào summary cho 20% bản ghi.
    4. Duplicates: Trùng lặp 15% bản ghi giữ nguyên paper_id.

    Bắt buộc: Ưu tiên tác động lên các paper_id nằm trong frozen test set để đo đạc được sự sụt giảm chỉ số RAG.
    """
    rng = random.Random(seed)
    working = df.reset_index(drop=True).copy()
    log_entries: list[dict[str, Any]] = []
    original_row_count = len(working)

    # 1. Tìm danh sách paper_id trong frozen test set (để tạo overlap bắt buộc)
    target_test_doc_ids: set[str] = set()
    if test_set_path and test_set_path.exists():
        try:
            test_data = read_json(test_set_path)
            for item in test_data:
                target_test_doc_ids.update(item.get("ground_truth_doc_ids", []))
            logger.info("Identified %d target paper_ids from frozen test set for targeted corruption.", len(target_test_doc_ids))
        except Exception as e:
            logger.warning("Could not read test_set_path for target corruption: %s", e)

    # Phân loại chỉ số hàng
    all_indices = list(working.index)
    test_target_indices = [idx for idx in all_indices if working.at[idx, "paper_id"] in target_test_doc_ids]
    non_test_indices = [idx for idx in all_indices if idx not in test_target_indices]

    # Đảm bảo các chỉ số bị hỏng có sự tham gia của test_target_indices
    rng.shuffle(test_target_indices)
    rng.shuffle(non_test_indices)

    # --- 1. Blank Summary ---
    blank_count = max(1, round(len(all_indices) * BLANK_SUMMARY_FRACTION))
    blank_targets = test_target_indices[:2] + non_test_indices[: max(0, blank_count - 2)]
    for idx in blank_targets:
        if idx in working.index:
            paper_id = working.at[idx, "paper_id"]
            before_len = len(str(working.at[idx, "summary"]))
            working.at[idx, "summary"] = ""
            if "summary_chars" in working.columns:
                working.at[idx, "summary_chars"] = 0
            log_entries.append({
                "type": "blank_summary",
                "paper_id": paper_id,
                "before_chars": before_len,
                "after_chars": 0,
            })

    # --- 2. Stale Date ---
    stale_count = max(1, round(len(all_indices) * STALE_DATE_FRACTION))
    stale_targets = test_target_indices[2:4] + non_test_indices[blank_count: blank_count + max(0, stale_count - 2)]
    for idx in stale_targets:
        if idx in working.index:
            paper_id = working.at[idx, "paper_id"]
            before_pub = working.at[idx, "published"]
            working.at[idx, "published"] = STALE_DATE_STR
            if "age_days" in working.columns:
                working.at[idx, "age_days"] = STALE_AGE_DAYS
            log_entries.append({
                "type": "stale_date",
                "paper_id": paper_id,
                "before_published": before_pub,
                "after_published": STALE_DATE_STR,
            })

    # --- 3. Add Noise ---
    noise_count = max(1, round(len(all_indices) * NOISE_FRACTION))
    noise_targets = test_target_indices[4:6] + non_test_indices[blank_count + stale_count: blank_count + stale_count + max(0, noise_count - 2)]
    for idx in noise_targets:
        if idx in working.index:
            paper_id = working.at[idx, "paper_id"]
            before_summary = str(working.at[idx, "summary"])
            noise_snippet = rng.choice(NOISE_SNIPPETS)
            after_summary = f"{noise_snippet} {before_summary}".strip()
            working.at[idx, "summary"] = after_summary
            if "summary_chars" in working.columns:
                working.at[idx, "summary_chars"] = len(after_summary)
            log_entries.append({
                "type": "inject_noise",
                "paper_id": paper_id,
                "snippet": noise_snippet,
            })

    # --- 4. Duplicates ---
    dup_count = max(1, round(len(all_indices) * DUPLICATE_FRACTION))
    dup_indices = rng.sample(all_indices, min(dup_count, len(all_indices)))
    duplicates = working.loc[dup_indices].copy()
    for paper_id in duplicates["paper_id"].tolist():
        log_entries.append({
            "type": "duplicate_row",
            "paper_id": paper_id,
            "detail": "Duplicated row with identical paper_id.",
        })
    working = pd.concat([working, duplicates], ignore_index=True)

    # Cập nhật lại cột text_for_embedding sau khi corrupt
    working["text_for_embedding"] = working.apply(_build_text_for_embedding, axis=1)

    # --- Lưu trữ CSV, JSON và Log ---
    ensure_parent(output_csv_path)
    ensure_parent(output_json_path)
    ensure_parent(output_log_path)

    write_csv(working, output_csv_path)
    write_json(output_json_path, working.to_dict(orient="records"))

    log_payload = {
        "seed": seed,
        "original_row_count": original_row_count,
        "corrupted_row_count": len(working),
        "target_test_doc_ids_count": len(target_test_doc_ids),
        "corruption_counts": pd.Series([e["type"] for e in log_entries]).value_counts().to_dict() if log_entries else {},
        "entries": log_entries,
    }
    write_json(output_log_path, log_payload)

    logger.info("Corrupted dataset saved → CSV: %s | JSON: %s | Log: %s", output_csv_path, output_json_path, output_log_path)
    return working


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    settings = load_settings()
    clean_csv_path = settings.paths.clean_csv
    if not clean_csv_path.exists():
        print(f"File {clean_csv_path} chưa tồn tại. Hãy chạy phase1.py trước!")
    else:
        df_clean = pd.read_csv(clean_csv_path)
        df_corrupted = corrupt_clean_dataframe(
            df_clean,
            output_csv_path=settings.paths.corrupted_clean_csv,
            output_json_path=settings.paths.corrupted_clean_json,
            output_log_path=settings.paths.corruption_log,
            test_set_path=settings.paths.eval_testset,
        )
        print(f"\nCorrupted {len(df_clean)} rows → {len(df_corrupted)} corrupted rows.")
