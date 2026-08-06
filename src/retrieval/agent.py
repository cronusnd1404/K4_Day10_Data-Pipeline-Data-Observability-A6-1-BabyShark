from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from langchain.agents import create_agent
from langchain.tools import tool

from core.config import Settings
from retrieval.index import LocalEmbeddingIndex
from retrieval.llm import build_llm


def build_agent(settings: Settings, index: LocalEmbeddingIndex):
    @tool
    def semantic_search_papers(query: str, top_k: int = 4) -> str:
        """Search the local paper corpus with embeddings and return the most relevant papers."""
        results = index.search(query, top_k=top_k)
        lines = []
        for result in results:
            lines.append(
                f"paper_id: {result.paper_id}\n"
                f"title: {result.title}\n"
                f"score: {result.score:.4f}\n"
                f"{result.content}"
            )
        return "\n\n".join(lines)

    @tool
    def lookup_paper(paper_id_or_title: str) -> str:
        """Look up a paper by exact paper_id or exact title from the local corpus."""
        record = index.lookup(paper_id_or_title)
        if not record:
            return "No exact paper match found."
        return (
            f"paper_id: {record['paper_id']}\n"
            f"title: {record['title']}\n"
            f"{record['content']}"
        )

    llm = build_llm(settings=settings, temperature=0.0)
    return create_agent(
        model=llm,
        tools=[semantic_search_papers, lookup_paper],
        system_prompt=(
            "You answer questions about the indexed scholarly paper corpus sourced from Crossref. "
            "Use tools before answering factual questions. "
            "If the indexed corpus does not support the answer, say so clearly."
        ),
        name="paper_corpus_agent",
    )


def run_agent_question(agent: Any, question: str) -> str:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    if not messages:
        return ""
    final_message = messages[-1]
    return getattr(final_message, "content", str(final_message))


if __name__ == "__main__":
    import pandas as pd
    from core.config import load_settings

    settings = load_settings()
    clean_json_path = settings.paths.clean_json

    if not clean_json_path.exists():
        print(f"File {clean_json_path} chưa tồn tại. Hãy chạy cleaning.py trước!")
    else:
        df = pd.read_json(clean_json_path)
        print("Loading ChromaDB index...")
        index = LocalEmbeddingIndex.build(df, settings)
        print(f"Index built with {len(index.documents)} documents.")

        print(f"Initializing RAG Agent with LLM provider '{settings.llm_provider}' ({settings.model_name})...")
        agent = build_agent(settings, index)

        q = "What is the SafeRAG paper about?"
        print(f"\nUser Question: {q}")
        ans = run_agent_question(agent, q)
        print(f"Agent Answer :\n{ans}")

