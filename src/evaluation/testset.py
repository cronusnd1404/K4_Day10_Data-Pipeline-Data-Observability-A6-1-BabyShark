from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd

# Tự động thêm 'src' vào sys.path nếu chưa có để cho phép chạy script trực tiếp
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.utils import first_sentence, write_json

MIN_DOCUMENTS = 3
MAX_SAMPLE_PAPERS = 6


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Tao bo evaluation set tu cleaned dataframe.

    Voi moi paper dai dien, sinh cau hoi factual (summary/authors/date/
    categories) voi cau hoi chua title trong dau nhay don, khop voi cach
    `retrieval.qa.answer_question` tra loi (exact title lookup + pattern
    matching), de metrics phan anh dung chat luong RAG.
    """
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(
            f"Not enough clean documents to build a test set (need >= {MIN_DOCUMENTS}, got {len(df)})."
        )

    sample = df.head(min(MAX_SAMPLE_PAPERS, len(df)))

    test_set: list[dict[str, Any]] = []
    next_id = 1

    def _add(question_type: str, question: str, ground_truth: str, paper_id: str) -> None:
        nonlocal next_id
        test_set.append(
            {
                "id": f"q{next_id}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        next_id += 1

    for _, row in sample.iterrows():
        title = row["title"]
        paper_id = row["paper_id"]

        _add(
            "summary",
            f"What is the paper '{title}' about?",
            first_sentence(row["summary"]),
            paper_id,
        )

        if row["authors_joined"]:
            _add(
                "authors",
                f"Who authored the paper '{title}'?",
                row["authors_joined"],
                paper_id,
            )

        if row["published"]:
            _add(
                "date",
                f"When was the paper '{title}' published?",
                row["published"],
                paper_id,
            )

        if row["categories_joined"]:
            _add(
                "categories",
                f"What categories does the paper '{title}' belong to?",
                row["categories_joined"],
                paper_id,
            )

    write_json(Path(output_path), test_set)
    return test_set


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from core.config import load_settings

    settings = load_settings()
    clean_json_path = settings.paths.clean_json
    eval_testset_path = settings.paths.eval_testset

    if not clean_json_path.exists():
        print(f"File {clean_json_path} chưa tồn tại. Hãy chạy cleaning.py trước!")
    else:
        df = pd.read_json(clean_json_path)
        test_set = build_test_set(df, eval_testset_path)
        print(f"\nSuccessfully built test set with {len(test_set)} questions → {eval_testset_path}")
        if test_set:
            print("\nSample Question 1:")
            print("  ID          :", test_set[0]["id"])
            print("  Type        :", test_set[0]["question_type"])
            print("  Question    :", test_set[0]["question"])
            print("  Ground Truth:", test_set[0]["ground_truth"])
            print("  Doc IDs     :", test_set[0]["ground_truth_doc_ids"])

