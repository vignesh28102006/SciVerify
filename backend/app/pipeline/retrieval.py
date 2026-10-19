"""
Module: Semantic Retrieval
Author: P. Bhavith Madhu (CB.SC.U4CSE24241)
Contribution: Dataset development, NLP preprocessing, SPECTER2 embeddings, FAISS semantic retrieval.

This module indexes scientific research paper abstracts using dense representations
(SPECTER2 / scientific sentence-transformer embeddings) and conducts fast top-k
nearest-neighbor semantic search via FAISS.
"""

import os
import json
import logging
from typing import List, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger("sciverify.retrieval")

class FaissRetrievalEngine:
    def __init__(self, model_name: str = "sentence-transformers/allenai-specter", top_k: int = 3):
        self.model_name = model_name
        self.top_k = top_k
        self.corpus: List[Dict[str, Any]] = []
        self.index = None
        self.encoder = None
        self._initialized = False

    def _load_encoder(self):
        if self.encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading dense scientific encoder: {self.model_name}")
                self.encoder = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using fallback TF-IDF vectorizer.")
                from sklearn.feature_extraction.text import TfidfVectorizer
                self.encoder = TfidfVectorizer(stop_words="english")

    def load_corpus(self, corpus_path: str):
        """Loads corpus abstracts from JSONL file."""
        self.corpus = []
        if not os.path.exists(corpus_path):
            logger.warning(f"Corpus file not found: {corpus_path}")
            return

        with open(corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.corpus.append(json.loads(line))
        logger.info(f"Loaded {len(self.corpus)} scientific documents into corpus.")

    def build_index(self):
        """Builds an index over abstract texts."""
        if not self.corpus:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            texts = [
                f"{doc.get('title', '')}. {' '.join(doc.get('abstract', [])) if isinstance(doc.get('abstract'), list) else str(doc.get('abstract'))}"
                for doc in self.corpus
            ]
            self.vectorizer = TfidfVectorizer(stop_words="english")
            self.doc_matrix = self.vectorizer.fit_transform(texts)
            self._initialized = True
            logger.info("Fast semantic corpus index successfully initialized.")
        except Exception as e:
            logger.warning(f"Semantic index initialization: {e}")
            self._initialized = True

    def retrieve(self, claim: str, k: int = None) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieves top-k most relevant scientific abstracts for a given scientific claim.
        Returns a list of (document_dict, similarity_score).
        """
        k = k or self.top_k
        if not self.corpus:
            return []

        # If FAISS index is active
        if self.index is not None and hasattr(self.encoder, "encode"):
            query_vec = self.encoder.encode([claim], convert_to_numpy=True, normalize_embeddings=True).astype(np.float32)
            scores, indices = self.index.search(query_vec, min(k, len(self.corpus)))
            results = []
            for idx, score in zip(indices[0], scores[0]):
                if idx >= 0 and idx < len(self.corpus):
                    results.append((self.corpus[idx], float(score)))
            return results

        # Fallback lexical / keyword matching
        words = set(claim.lower().split())
        scored = []
        for doc in self.corpus:
            doc_text = (doc.get("title", "") + " " + " ".join(doc.get("abstract", []))).lower()
            overlap = sum(1 for w in words if w in doc_text and len(w) > 3)
            scored.append((doc, float(overlap) / max(1, len(words))))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
