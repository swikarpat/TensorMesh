import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Optional
from tensormesh.config.settings import settings
from tensormesh.storage import CF_SECURE_STATE, RocksDBStore

class SemanticCache:
    def __init__(self, similarity_threshold: float = 0.95):
        # Downloads a tiny, ultra-fast embedding model locally on first run
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.threshold = similarity_threshold
        self.store = RocksDBStore(settings.ROCKSDB_PATH)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        dot_product = np.dot(vec1, vec2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return float(dot_product / norm) if norm != 0 else 0.0

    def check_cache(self, query: str) -> Optional[str]:
        """Checks if a semantically identical query was recently processed."""
        query_embedding = self.encoder.encode(query)
        
        for _, entry in self.store.scan_json(CF_SECURE_STATE, "semantic_cache:"):
            entry["embedding"] = np.array(entry["embedding"])
            sim = self._cosine_similarity(query_embedding, entry["embedding"])
            if sim >= self.threshold:
                return entry["response"]
                
        return None

    def add_to_cache(self, query: str, response: str):
        """Saves a new query and its response to the vector cache."""
        embedding = self.encoder.encode(query)
        cache_key = f"semantic_cache:{hash(query)}"
        self.store.put_json(CF_SECURE_STATE, cache_key, {
            "query": query,
            "embedding": embedding.tolist(),
            "response": response,
        })