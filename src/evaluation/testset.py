from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

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
