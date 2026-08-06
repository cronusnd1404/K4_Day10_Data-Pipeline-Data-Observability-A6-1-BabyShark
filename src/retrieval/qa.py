from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.config import Settings
from core.utils import first_sentence
from retrieval.index import LocalEmbeddingIndex, SearchResult


@dataclass(frozen=True)
class AnswerResult:
    question: str
    answer: str
    retrieved_doc_ids: list[str]
    retrieved_contexts: list[str]
    retrieved_titles: list[str]


def _extract_answer(question: str, top_result: SearchResult) -> str:
    lowered = question.lower()
    metadata = top_result.metadata
    if "who authored" in lowered or "list the authors" in lowered:
        return metadata["authors_joined"]
    if "when was" in lowered or "publication date" in lowered or "published on" in lowered:
        return metadata["published"]
    if "what categories" in lowered:
        return metadata["categories_joined"]
    return first_sentence(metadata["summary"])


def answer_question(question: str, settings: Settings, index: LocalEmbeddingIndex, top_k: int | None = None) -> AnswerResult:
    title_match = re.search(r"'([^']+)'", question)
    exact = index.lookup(title_match.group(1)) if title_match else None
    retrieved = index.search(question, top_k=top_k)
    if exact:
        exact_result = SearchResult(
            paper_id=exact["paper_id"],
            title=exact["title"],
            score=1.0,
            content=exact["content"],
            metadata=exact["metadata"],
        )
        deduped = [exact_result] + [item for item in retrieved if item.paper_id != exact_result.paper_id]
        retrieved = deduped[: (top_k or settings.top_k)]
    if not retrieved:
        answer = "I don't know from the indexed corpus."
    else:
        answer = _extract_answer(question, retrieved[0])
    return AnswerResult(
        question=question,
        answer=answer,
        retrieved_doc_ids=[item.paper_id for item in retrieved],
        retrieved_contexts=[item.content for item in retrieved],
        retrieved_titles=[item.title for item in retrieved],
    )


if __name__ == "__main__":
    import pandas as pd
    from core.config import load_settings

    settings = load_settings()
    clean_json_path = settings.paths.clean_json

    if not clean_json_path.exists():
        print(f"File {clean_json_path} chưa tồn tại. Hãy chạy cleaning.py trước!")
    else:
        df = pd.read_json(clean_json_path)
        print("Building ChromaDB vector index...")
        index = LocalEmbeddingIndex.build(df, settings)
        print(f"Index built with {len(index.documents)} documents.")

        question = "What is the paper 'SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation' about?"
        result = answer_question(question, settings, index)
        print(f"\nQuestion: {question}")
        print(f"Answer  : {result.answer}")
        print(f"Retrieved Doc IDs: {result.retrieved_doc_ids}")

