"""
Module: Pipeline Evaluation Metrics
Author: V. Vignesh (CB.SC.U4CSE24265) & Team
Contribution: Recall@k/F1 evaluation, end-to-end testing, refinement.

Computes standard SciFact benchmark evaluation metrics:
1. Retrieval Recall@k: Proportion of ground-truth evidence documents retrieved in top-k.
2. Sentence-level Evidence F1 (Precision, Recall, F1).
3. Label Classification Macro-F1 (SUPPORT, CONTRADICT, NOT ENOUGH INFO).
"""

import json
from typing import List, Dict, Any

class SciVerifyEvaluator:
    def __init__(self):
        pass

    @staticmethod
    def compute_retrieval_recall_at_k(predictions: List[Dict[str, Any]], ground_truth: List[Dict[str, Any]], k: int = 3) -> float:
        """Computes proportion of cited doc IDs retrieved in top-k."""
        hits = 0
        total = 0

        for pred, gt in zip(predictions, ground_truth):
            true_docs = set(gt.get("cited_doc_ids", []))
            if not true_docs:
                continue
            retrieved_docs = set(pred.get("retrieved_doc_ids", [])[:k])
            if true_docs & retrieved_docs:
                hits += 1
            total += 1

        return float(hits) / max(1, total)

    @staticmethod
    def compute_classification_metrics(predictions: List[str], ground_truth: List[str]) -> Dict[str, float]:
        """Calculates Macro Precision, Recall, and F1 across 3 classes."""
        labels = ["SUPPORT", "CONTRADICT", "NOT ENOUGH INFO"]
        metrics = {}

        total_correct = sum(1 for p, g in zip(predictions, ground_truth) if p == g)
        accuracy = float(total_correct) / max(1, len(ground_truth))

        f1_scores = []
        for label in labels:
            tp = sum(1 for p, g in zip(predictions, ground_truth) if p == label and g == label)
            fp = sum(1 for p, g in zip(predictions, ground_truth) if p == label and g != label)
            fn = sum(1 for p, g in zip(predictions, ground_truth) if p != label and g == label)

            prec = float(tp) / max(1, tp + fp)
            rec = float(tp) / max(1, tp + fn)
            f1 = (2 * prec * rec) / max(1e-6, prec + rec)
            f1_scores.append(f1)
            metrics[f"{label}_f1"] = round(f1, 4)

        metrics["accuracy"] = round(accuracy, 4)
        metrics["macro_f1"] = round(sum(f1_scores) / len(f1_scores), 4)
        return metrics
