"""
Module: Cross-Encoder Reranking & Sentence-Level Evidence Extraction
Author: Y. Sri Sai Sujith (CB.SC.U4CSE24260)
Contribution: Cross-encoder reranking, sentence-level evidence extraction, evidence integration, testing.

This module splits candidate abstracts into individual sentences, pairs each sentence
with the scientific claim, and scores relevance using a Cross-Encoder transformer.
The top-scoring sentences form the extracted minimal evidence rationale.
"""

import logging
from typing import List, Dict, Any, Tuple
import re

logger = logging.getLogger("sciverify.reranking")

class SentenceEvidenceExtractor:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", threshold: float = 0.45):
        self.model_name = model_name
        self.threshold = threshold
        self.cross_encoder = None

    def _load_model(self):
        if self.cross_encoder is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading Cross-Encoder model: {self.model_name}")
                self.cross_encoder = CrossEncoder(self.model_name, local_files_only=True)
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder ({e}). Using heuristic lexical sentence scorer.")

    def split_sentences(self, text: str) -> List[str]:
        """Splits abstract text into individual sentences with boundary preservation."""
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if len(s.strip()) > 5]

    def extract_evidence_from_abstract(
        self, 
        claim: str, 
        doc: Dict[str, Any], 
        top_sentences: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Extracts the most salient sentence(s) from a document abstract that support or refute the claim.
        Returns a list of extracted sentence dictionaries with sentence index, text, and relevance confidence.
        """
        raw_sentences = doc.get("abstract", [])
        if isinstance(raw_sentences, str):
            raw_sentences = self.split_sentences(raw_sentences)

        if not raw_sentences:
            return []

        self._load_model()

        # Cross-encoder joint scoring: (claim, sentence)
        if self.cross_encoder is not None:
            pairs = [[claim, sent] for sent in raw_sentences]
            scores = self.cross_encoder.predict(pairs)
            ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            
            extracted = []
            for idx in ranked_indices[:top_sentences]:
                extracted.append({
                    "sentence_idx": idx,
                    "sentence_text": raw_sentences[idx],
                    "score": float(scores[idx]),
                    "confidence": int(min(99, max(50, (float(scores[idx]) + 1.0) / 2.0 * 100)))
                })
            return extracted

        # Heuristic fallback (token overlap & scientific keyword matching)
        claim_tokens = set(re.findall(r'\b[a-z]{3,}\b', claim.lower()))
        scored = []
        for idx, sent in enumerate(raw_sentences):
            sent_tokens = set(re.findall(r'\b[a-z]{3,}\b', sent.lower()))
            overlap = len(claim_tokens & sent_tokens)
            score = overlap / max(1, len(claim_tokens))
            scored.append((idx, sent, score))

        scored.sort(key=lambda x: x[2], reverse=True)
        return [
            {
                "sentence_idx": item[0],
                "sentence_text": item[1],
                "score": float(item[2]),
                "confidence": int(min(95, max(60, item[2] * 100)))
            }
            for item in scored[:top_sentences]
        ]
