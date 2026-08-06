from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Any

import pandas as pd

# Tự động thêm 'src' vào sys.path nếu chưa có để cho phép chạy script trực tiếp
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.utils import compact_join, first_sentence, normalize_whitespace, write_json

MIN_DOCUMENTS = 3
MAX_SAMPLE_PAPERS = 6
MIN_QUESTIONS = 8
MIN_SUMMARY_CHARS = 120
MIN_TOPIC_CHARS = 25

# Schema yeu cau question_type = "factual". Doi thanh None neu muon ghi
# nhan chi tiet (summary/authors/date/categories/topic) de report breakdown theo loai.
QUESTION_TYPE = "factual"

# Thu tu nhanh cua retrieval.qa._extract_answer (qa.py:20-29). Cau hoi phai
# roi dung nhanh minh nham toi, neu khong harness se tra ve field khac.
BRANCH_TRIGGERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("authors", ("who authored", "list the authors")),
    ("date", ("when was", "publication date", "published on")),
    ("categories", ("what categories",)),
)


def _harness_branch(question: str) -> str:
    lowered = question.lower()
    for branch, triggers in BRANCH_TRIGGERS:
        if any(trigger in lowered for trigger in triggers):
            return branch
    return "summary"


def _field(row: dict[str, Any], *keys: str) -> str:
    """Doc text tu cot dau tien khong rong; tra "" cho NaN/None/cot thieu."""
    for key in keys:
        value = row.get(key)
        if isinstance(value, (list, tuple)):
            value = compact_join(str(item) for item in value)
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass
        cleaned = normalize_whitespace(str(value))
        if cleaned:
            return cleaned
    return ""


def _is_usable(row: dict[str, Any]) -> bool:
    """Loai row khong the tao ground truth kiem chung duoc."""
    title = _field(row, "title")
    summary = _field(row, "summary")
    if not _field(row, "paper_id") or not title or not summary:
        return False
    if len(summary) < MIN_SUMMARY_CHARS:
        return False
    # qa.answer_question tach title bang re.search(r"'([^']+)'"), nen title
    # chua dau nhay don se lam exact lookup bat sai doan text.
    return "'" not in title


def _topic(title: str) -> str:
    """Rut chu de tu title de dat cau hoi tu nhien, khong doc nguyen title.

    Cau hoi dang nay khong boc title trong dau nhay don nen bo qua exact
    lookup, buoc harness phai dua vao semantic retrieval that.
    """
    _, _, tail = title.partition(":")
    topic = tail.strip() if len(tail.strip()) >= MIN_TOPIC_CHARS else title.strip()
    # Bo mao tu dau cau nhung giu nguyen casing con lai: title thuong chua
    # danh tu rieng va tu ghep viet hoa (vi du "Large-Language-Model-Based").
    return re.sub(r"^(a|an|the)\s+", "", topic, flags=re.IGNORECASE).strip(" .")


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

    rows = df.to_dict(orient="records")
    usable = [row for row in rows if _is_usable(row)]
    sample = usable[:MAX_SAMPLE_PAPERS]

    test_set: list[dict[str, Any]] = []
    next_id = 1

    def _add(kind: str, branch: str, question: str, ground_truth: str, paper_id: str) -> None:
        """Chi ghi sample khi ground truth co that va harness se di dung nhanh."""
        nonlocal next_id
        if not ground_truth or _harness_branch(question) != branch:
            return
        test_set.append(
            {
                "id": f"q{next_id}",
                "question_type": QUESTION_TYPE or kind,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )
        next_id += 1

    for row in sample:
        title = _field(row, "title")
        paper_id = _field(row, "paper_id")
        lead_sentence = first_sentence(_field(row, "summary"))
        topic = _topic(title)

        _add(
            "summary",
            "summary",
            f"What is the paper '{title}' about?",
            lead_sentence,
            paper_id,
        )
        _add(
            "authors",
            "authors",
            f"Who authored the paper '{title}'?",
            _field(row, "authors_joined", "authors"),
            paper_id,
        )
        _add(
            "date",
            "date",
            f"When was the paper '{title}' published?",
            _field(row, "published"),
            paper_id,
        )
        _add(
            "categories",
            "categories",
            f"What categories does the paper '{title}' belong to?",
            _field(row, "categories_joined", "categories", "primary_category"),
            paper_id,
        )
        if topic:
            _add(
                "topic",
                "summary",
                f"Which indexed paper studies {topic}, and what does it report?",
                lead_sentence,
                paper_id,
            )

    if len(test_set) < MIN_QUESTIONS:
        raise ValueError(
            f"Built only {len(test_set)} samples from {len(usable)} usable rows (of {len(rows)} total); "
            f"need >= {MIN_QUESTIONS}. Kiem tra cleaning output: title/summary rong hay summary qua ngan."
        )

    known_ids = {_field(row, "paper_id") for row in rows}
    unknown = sorted(
        {doc_id for item in test_set for doc_id in item["ground_truth_doc_ids"]} - known_ids
    )
    if unknown:
        raise ValueError(f"Test set references paper_id khong co trong clean data: {unknown}.")

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

