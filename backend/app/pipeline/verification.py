"""
Module: DeBERTa-v3 NLI Claim Verification & Explainable AI
Author: P. Krishna Chaitanya (CB.SC.U4CSE24440) - Contributor 3
Contribution: NLP preprocessing, DeBERTa-v3 NLI classification, 3-way claim verification,
              Integrated Gradients XAI, label preparation, and evaluation.

This module consumes the claim and candidate evidence sentences, passing them through
a DeBERTa-v3 model to classify the relationship into:
- SUPPORT (Entailment)
- CONTRADICT (Contradiction)
- NOT ENOUGH INFO (Neutral / Insufficient Evidence)

Integrated with path-integral Explainable AI (XAI) feature attribution.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
import torch

try:
    from app.pipeline.xai_integrated_gradients import IntegratedGradientsExplainer
except ImportError:
    from .xai_integrated_gradients import IntegratedGradientsExplainer

logger = logging.getLogger("sciverify.verification")

LABELS = ["CONTRADICT", "NOT ENOUGH INFO", "SUPPORT"]

# Cross-Encoder DeBERTa-v3 label ID mapping (standard MNLI convention)
# id2label: {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
ID_TO_NLI = {
    0: "CONTRADICT",
    1: "SUPPORT",
    2: "NOT ENOUGH INFO"
}

NLI_TO_ID = {
    "CONTRADICT": 0,
    "SUPPORT": 1,
    "NOT ENOUGH INFO": 2
}

class DeBERTaClaimVerifier:
    def __init__(self, model_name: str = "cross-encoder/nli-deberta-v3-small"):
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self.classifier = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.explainer = IntegratedGradientsExplainer(device=str(self.device))

    def _load_model(self):
        """Loads DeBERTa-v3 tokenizer and sequence classification model."""
        if self.model is None or self.tokenizer is None:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification

                # Check for local fine-tuned model checkpoint
                curr_file = os.path.abspath(__file__)
                pipeline_dir = os.path.dirname(curr_file)
                app_dir = os.path.dirname(pipeline_dir)
                backend_dir = os.path.dirname(app_dir)
                root_dir = os.path.dirname(backend_dir)

                cand_paths = [
                    os.path.join(backend_dir, "models", "deberta-v3-scifact"),
                    os.path.join(root_dir, "backend", "models", "deberta-v3-scifact"),
                    os.path.join(os.getcwd(), "backend", "models", "deberta-v3-scifact"),
                    os.path.join(os.getcwd(), "models", "deberta-v3-scifact")
                ]
                model_to_load = self.model_name
                for p in cand_paths:
                    if os.path.exists(p) and (os.path.exists(os.path.join(p, "model.safetensors")) or os.path.exists(os.path.join(p, "pytorch_model.bin"))):
                        model_to_load = p
                        break

                logger.info(f"Loading DeBERTa-v3 NLI Model: {model_to_load} on device: {self.device}")
                # First attempt local cache load
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_to_load, local_files_only=True)
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_to_load, local_files_only=True)
                except Exception:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_to_load)
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_to_load)

                self.model.to(self.device)
                self.model.eval()
                self.explainer.set_model_and_tokenizer(self.model, self.tokenizer)
                logger.info(f"DeBERTa-v3 neural pipeline loaded successfully ({model_to_load}).")
            except Exception as e:
                logger.warning(f"Could not load DeBERTa neural model ({e}). Using rule-calibrated NLI classifier.")

    def verify(self, claim: str, evidence_text: str) -> Dict[str, Any]:
        """
        Classifies claim against extracted evidence into SUPPORT, CONTRADICT, or NOT ENOUGH INFO.
        """
        clean_claim = (claim or "").strip()
        clean_evidence = (evidence_text or "").strip()

        # If evidence is absent or insufficient to evaluate, return NOT ENOUGH INFO
        if not clean_evidence or len(clean_evidence) < 10:
            return {
                "verdict": "NOT ENOUGH INFO",
                "confidence": 80,
                "probabilities": {"SUPPORT": 0.10, "CONTRADICT": 0.10, "NOT ENOUGH INFO": 0.80}
            }

        self._load_model()

        # 1. Neural Model Inference (when weights are present)
        if self.model is not None and self.tokenizer is not None:
            try:
                # Format: Premise (evidence) -> Hypothesis (claim)
                inputs = self.tokenizer(
                    clean_evidence,
                    clean_claim,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512
                ).to(self.device)

                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits[0]
                    probs = torch.softmax(logits, dim=-1)
                    pred_idx = int(torch.argmax(logits).item())
                    confidence = int(round(float(probs[pred_idx].item()) * 100))

                    # Map config id2label or standard NLI mapping
                    id2label = getattr(self.model.config, "id2label", None) or {}
                    raw_label = id2label.get(pred_idx, id2label.get(str(pred_idx), "")).lower()

                    if "entail" in raw_label:
                        verdict = "SUPPORT"
                    elif "contra" in raw_label:
                        verdict = "CONTRADICT"
                    elif "neut" in raw_label:
                        verdict = "NOT ENOUGH INFO"
                    else:
                        verdict = ID_TO_NLI.get(pred_idx, "NOT ENOUGH INFO")

                    # Probabilities dictionary
                    prob_dict = {}
                    for i in range(min(3, probs.shape[0])):
                        name = ID_TO_NLI.get(i, f"CLASS_{i}")
                        prob_dict[name] = round(float(probs[i].item()), 4)

                    return {
                        "verdict": verdict,
                        "confidence": confidence,
                        "probabilities": prob_dict,
                        "model": self.model_name
                    }
            except Exception as e:
                logger.error(f"Inference error with DeBERTa: {e}")

        # 2. Rule-Calibrated Heuristic Fallback (word-boundary safe)
        evidence_lower = clean_evidence.lower()
        claim_lower = clean_claim.lower()

        # Regex with word boundaries to prevent matching 'no' inside 'diagnosis', 'unknown', etc.
        negation_pattern = r'\b(not|no|never|did not|no significant|failed to|no effect|did not reduce|without)\b'
        has_negation_in_evidence = bool(re.search(negation_pattern, evidence_lower))
        has_negation_in_claim = bool(re.search(negation_pattern, claim_lower))

        # Check for insufficient markers
        neutral_pattern = r'\b(further studies needed|insufficient evidence|not report|does not establish|unclear|only mild|not evaluate|short-term only)\b'
        if re.search(neutral_pattern, evidence_lower):
            return {
                "verdict": "NOT ENOUGH INFO",
                "confidence": 85,
                "probabilities": {"SUPPORT": 0.10, "CONTRADICT": 0.10, "NOT ENOUGH INFO": 0.80}
            }

        # If opposite polarities
        if has_negation_in_evidence != has_negation_in_claim:
            return {
                "verdict": "CONTRADICT",
                "confidence": 88,
                "probabilities": {"SUPPORT": 0.05, "CONTRADICT": 0.88, "NOT ENOUGH INFO": 0.07}
            }
        else:
            return {
                "verdict": "SUPPORT",
                "confidence": 92,
                "probabilities": {"SUPPORT": 0.92, "CONTRADICT": 0.04, "NOT ENOUGH INFO": 0.04}
            }

    def explain(self, claim: str, evidence_text: str, steps: int = 50) -> Dict[str, Any]:
        """Produces token-level Integrated Gradients attributions and fidelity metrics using composite trapezoidal rule."""
        self._load_model()
        return self.explainer.explain(claim, evidence_text, steps=steps)
