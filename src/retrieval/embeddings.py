from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys

# Tự động thêm 'src' vào sys.path nếu chưa có
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=4)
def _load_model(model_name: str) -> SentenceTransformer:
    return SentenceTransformer(model_name)


class MiniLMEmbeddings(Embeddings):
    def __init__(self, model_name: str):
        self.model = _load_model(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


if __name__ == "__main__":
    print("Testing MiniLMEmbeddings (sentence-transformers/all-MiniLM-L6-v2)...")
    emb = MiniLMEmbeddings("sentence-transformers/all-MiniLM-L6-v2")
    vec = emb.embed_query("Retrieval-Augmented Generation for Large Language Models")
    print(f"Embedding vector dimension: {len(vec)}")
    print(f"Sample vector values (first 5): {vec[:5]}")

