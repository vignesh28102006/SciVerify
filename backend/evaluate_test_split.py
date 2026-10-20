"""
Module: Real-Time Benchmark Evaluation on SciFact-Health Held-Out Test Split
Evaluates the TWO active deep-learning LLMs (Groq LPU Llama-3.1 and Google Gemini)
against ground-truth labels on `data/claims_test.jsonl`.

CRITICAL SCIENTIFIC INTEGRITY RULES:
1. API errors, rate limits (HTTP 429), timeouts, and invalid responses are NEVER counted as NOT ENOUGH INFO predictions.
2. API failures are explicitly counted, categorized, and reported separately from scientific verdicts.
3. Computes 3x3 confusion matrices, per-class Precision/Recall/F1, macro scores, and latency.
"""

import os
import sys
import json
import time
from typing import Dict, Any, List, Optional

backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)

from app.main import retrieval_engine, evidence_extractor, groq_verifier, gemini_verifier

CLASSES = ["SUPPORT", "CONTRADICT", "NOT ENOUGH INFO"]


def compute_comprehensive_metrics(
    y_true: List[str], 
    y_pred: List[str], 
    total_samples: int,
    api_failures: int
) -> Dict[str, Any]:
    """
    Computes rigorous classification metrics on valid evaluations:
    - 3x3 Confusion Matrix
    - Per-class Precision, Recall, F1, and Support
    - Macro-averaged metrics
    - Valid-sample Accuracy vs Effective Accuracy (accounting for API failures)
    """
    # Initialize 3x3 confusion matrix: rows=Ground Truth, cols=Predicted
    matrix = {t: {p: 0 for p in CLASSES} for t in CLASSES}
    valid_count = len(y_true)

    for t, p in zip(y_true, y_pred):
        if t in matrix and p in matrix[t]:
            matrix[t][p] += 1

    per_class = {}
    precisions = []
    recalls = []
    f1s = []

    for c in CLASSES:
        tp = matrix[c][c]
        fp = sum(matrix[other][c] for other in CLASSES if other != c)
        fn = sum(matrix[c][other] for other in CLASSES if other != c)
        support = tp + fn

        prec = (tp / (tp + fp)) if (tp + fp) > 0 else (1.0 if support == 0 else 0.0)
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class[c] = {
            "precision": round(prec * 100, 1),
            "recall": round(rec * 100, 1),
            "f1": round(f1 * 100, 1),
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn
        }
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    total_correct = sum(matrix[c][c] for c in CLASSES)
    valid_accuracy = (total_correct / valid_count * 100) if valid_count > 0 else 0.0
    effective_accuracy = (total_correct / total_samples * 100) if total_samples > 0 else 0.0
    macro_precision = (sum(precisions) / len(CLASSES)) * 100
    macro_recall = (sum(recalls) / len(CLASSES)) * 100
    macro_f1 = (sum(f1s) / len(CLASSES)) * 100

    return {
        "valid_evaluations": valid_count,
        "total_samples": total_samples,
        "api_failures": api_failures,
        "valid_accuracy": round(valid_accuracy, 1),
        "effective_accuracy": round(effective_accuracy, 1),
        "macro_precision": round(macro_precision, 1),
        "macro_recall": round(macro_recall, 1),
        "macro_f1": round(macro_f1, 1),
        "per_class": per_class,
        "confusion_matrix": matrix
    }


def evaluate_model_on_test_split(
    verifier, 
    provider_name: str, 
    test_samples: List[Dict[str, Any]],
    inter_query_delay: float = 1.0
) -> Dict[str, Any]:
    print(f"\nEvaluating: {provider_name} ({verifier.model_name}) ...")
    y_true_valid = []
    y_pred_valid = []
    latencies = []
    results_detail = []
    api_failures = 0
    failure_breakdown = {}

    for idx, sample in enumerate(test_samples):
        claim_id = sample.get("id")
        claim = sample.get("claim", "")
        ground_truth = sample.get("label", "NOT ENOUGH INFO")

        t0 = time.time()
        retrieved = retrieval_engine.retrieve(claim, k=2)
        ev_items = []
        top_sent = ""

        if retrieved:
            doc = retrieved[0][0]
            ext = evidence_extractor.extract_evidence_from_abstract(claim, doc, top_sentences=1)
            top_sent = ext[0]["sentence_text"] if ext else " ".join(doc.get("abstract", [])[:2])
            ev_items.append({
                "doc_id": str(doc.get("doc_id")),
                "title": doc.get("title", ""),
                "sentence": top_sent
            })

        res = verifier.verify(claim, evidence_items=ev_items, evidence_text=top_sent)
        latency = round((time.time() - t0) * 1000)
        latencies.append(latency)

        status = res.get("status", "unknown")
        pred = res.get("verdict")
        error_type = res.get("error_type")

        # CRITICAL INTEGRITY CHECK: Distinguish API failures from scientific verdicts
        is_api_failure = (status != "success" or pred is None or pred not in CLASSES)

        if is_api_failure:
            api_failures += 1
            err_label = error_type or status or "API_FAILURE"
            failure_breakdown[err_label] = failure_breakdown.get(err_label, 0) + 1
            results_detail.append({
                "id": claim_id,
                "claim": claim,
                "ground_truth": ground_truth,
                "predicted": None,
                "is_api_failure": True,
                "error_type": err_label,
                "error_explanation": res.get("explanation", "API call failed"),
                "match": False,
                "latency_ms": latency
            })
            print(f"  [{idx+1}/{len(test_samples)}] Claim {claim_id}: [API ERROR] ({err_label}) Truth={ground_truth:15} | Call Failed ({latency}ms)")
        else:
            y_true_valid.append(ground_truth)
            y_pred_valid.append(pred)
            match = (ground_truth == pred)
            results_detail.append({
                "id": claim_id,
                "claim": claim,
                "ground_truth": ground_truth,
                "predicted": pred,
                "is_api_failure": False,
                "error_type": None,
                "match": match,
                "latency_ms": latency
            })
            status_sym = "[MATCH]" if match else "[MISMATCH]"
            print(f"  [{idx+1}/{len(test_samples)}] Claim {claim_id}: {status_sym} Truth={ground_truth:15} | Pred={pred:15} ({latency}ms)")

        if inter_query_delay > 0 and idx < len(test_samples) - 1:
            time.sleep(inter_query_delay)

    metrics = compute_comprehensive_metrics(
        y_true_valid, 
        y_pred_valid, 
        len(test_samples), 
        api_failures
    )
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0

    return {
        "provider": provider_name,
        "model": verifier.model_name,
        "sample_count": len(test_samples),
        "valid_evaluations": metrics["valid_evaluations"],
        "api_failures": api_failures,
        "api_failure_breakdown": failure_breakdown,
        "accuracy": metrics["valid_accuracy"],
        "effective_accuracy": metrics["effective_accuracy"],
        "precision": metrics["macro_precision"],
        "recall": metrics["macro_recall"],
        "f1": metrics["macro_f1"],
        "per_class": metrics["per_class"],
        "confusion_matrix": metrics["confusion_matrix"],
        "avg_latency_ms": avg_latency,
        "details": results_detail
    }


def print_confusion_matrix(provider: str, matrix: Dict[str, Dict[str, int]]):
    print(f"\n--- Confusion Matrix for {provider} ---")
    print(f"{'Truth / Pred':<16} | {'SUPPORT':<8} | {'CONTRADICT':<10} | {'NOT ENOUGH INFO':<15} | {'Total'}")
    print("-" * 65)
    for t in CLASSES:
        sup = matrix[t]["SUPPORT"]
        con = matrix[t]["CONTRADICT"]
        nei = matrix[t]["NOT ENOUGH INFO"]
        tot = sup + con + nei
        print(f"{t:<16} | {sup:<8} | {con:<10} | {nei:<15} | {tot}")


def print_per_class_scores(provider: str, per_class: Dict[str, Dict[str, Any]]):
    print(f"\n--- Per-Class Metrics for {provider} ---")
    print(f"{'Class':<18} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support'}")
    print("-" * 62)
    for c, scores in per_class.items():
        print(f"{c:<18} | {scores['precision']:>8.1f}% | {scores['recall']:>8.1f}% | {scores['f1']:>8.1f}% | {scores['support']:>7}")


def main():
    print("=" * 75)
    print("      SCIVERIFY REAL-TIME BENCHMARK EVALUATION (HELD-OUT TEST SPLIT)     ")
    print("=" * 75)

    corpus_path = os.path.join(project_root, "data", "corpus.jsonl")
    test_path = os.path.join(project_root, "data", "claims_test.jsonl")

    if not os.path.exists(corpus_path) or not os.path.exists(test_path):
        print("Error: Dataset files not found.")
        return

    retrieval_engine.load_corpus(corpus_path)
    retrieval_engine.build_index()

    with open(test_path, "r", encoding="utf-8") as f:
        test_samples = [json.loads(line) for line in f if line.strip()]

    print(f"Loaded {len(test_samples)} held-out test samples from: {test_path}")

    # Evaluate Groq LPU (Primary)
    groq_eval = evaluate_model_on_test_split(groq_verifier, "Groq Cloud LPU", test_samples, inter_query_delay=0.3)

    # Evaluate Google Gemini (Alternative)
    gemini_eval = evaluate_model_on_test_split(gemini_verifier, "Google Gemini", test_samples, inter_query_delay=1.0)

    # Detailed Matrices & Per-Class Reports
    for ev in [groq_eval, gemini_eval]:
        print_confusion_matrix(f"{ev['provider']} ({ev['model']})", ev["confusion_matrix"])
        print_per_class_scores(f"{ev['provider']} ({ev['model']})", ev["per_class"])

    # Summary Benchmark Table
    print("\n" + "=" * 78)
    print("                      EVALUATION BENCHMARK SUMMARY                    ")
    print("=" * 78)
    print(f"{'Provider & Model':<35} | {'ValAcc':<6} | {'EffAcc':<6} | {'Prec':<6} | {'Rec':<6} | {'F1':<6} | {'Failures'}")
    print("-" * 78)
    for res in [groq_eval, gemini_eval]:
        name_str = f"{res['provider']} ({res['model']})"
        fail_str = f"{res['api_failures']}/{res['sample_count']}"
        print(f"{name_str:<35} | {res['accuracy']:>5.1f}% | {res['effective_accuracy']:>5.1f}% | {res['precision']:>5.1f}% | {res['recall']:>5.1f}% | {res['f1']:>5.1f}% | {fail_str}")
    print("=" * 78)

    # Save to JSON
    output_path = os.path.join(project_root, "data", "test_evaluation_results.json")
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "dataset_split": "data/claims_test.jsonl",
            "samples": len(test_samples),
            "evaluations": {
                "groq": groq_eval,
                "gemini": gemini_eval
            }
        }, out, indent=2)

    # Also sync data/models_evaluation_registry.json
    registry_path = os.path.join(project_root, "data", "models_evaluation_registry.json")
    groq_status = "DEPLOYED" if os.getenv("GROQ_TUNED_MODEL_ID") else "BASE_MODEL_EVALUATED"
    gemini_status = "DEPLOYED" if (os.getenv("GEMINI_TUNED_MODEL_ID") and os.getenv("GEMINI_TUNED_MODEL_ID").startswith("tunedModels/")) else "BASE_MODEL_EVALUATED"

    registry_data = {
        "evaluation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "benchmark_dataset": "SciFact-Health Held-Out Test Benchmark (Unseen Claims)",
        "sample_count": len(test_samples),
        "models": {
            "groq_llama_3_1": {
                "model_key": "groq_llama_3_1",
                "model_name": f"Groq LPU ({groq_verifier.model_name})",
                "provider": "Groq Cloud / LPU Tensor Architecture",
                "architecture": "Dense Autoregressive LLM (8B Parameters)",
                "task": "Primary Scientific Claim Verification & Evidence Grounding",
                "role": "Primary Verification Engine",
                "status": groq_status,
                "accuracy": groq_eval["accuracy"],
                "effective_accuracy": groq_eval["effective_accuracy"],
                "precision": groq_eval["precision"],
                "recall": groq_eval["recall"],
                "f1_score": groq_eval["f1"],
                "macro_f1": groq_eval["f1"],
                "latency_ms": groq_eval["avg_latency_ms"],
                "dataset_split": "SciFact Test Split (claims_test.jsonl)",
                "samples": len(test_samples),
                "valid_evaluations": groq_eval["valid_evaluations"],
                "api_failures": groq_eval["api_failures"],
                "api_failure_breakdown": groq_eval["api_failure_breakdown"],
                "per_class": groq_eval["per_class"],
                "confusion_matrix_3x3": groq_eval["confusion_matrix"],
                "explanation": "Evaluated against held-out test split (claims_test.jsonl). API failures are strictly tracked and isolated from valid verdicts."
            },
            "gemini_1_5_flash": {
                "model_key": "gemini_1_5_flash",
                "model_name": f"Google Gemini ({gemini_verifier.model_name})",
                "provider": "Google DeepMind / Generative AI",
                "architecture": "Multimodal Transformer (Decoder-only)",
                "task": "Alternative Scientific Verification & Rationale Cross-Examination",
                "role": "Alternative Reasoning Engine",
                "status": gemini_status,
                "accuracy": gemini_eval["accuracy"],
                "effective_accuracy": gemini_eval["effective_accuracy"],
                "precision": gemini_eval["precision"],
                "recall": gemini_eval["recall"],
                "f1_score": gemini_eval["f1"],
                "macro_f1": gemini_eval["f1"],
                "latency_ms": gemini_eval["avg_latency_ms"],
                "dataset_split": "SciFact Test Split (claims_test.jsonl)",
                "samples": len(test_samples),
                "valid_evaluations": gemini_eval["valid_evaluations"],
                "api_failures": gemini_eval["api_failures"],
                "api_failure_breakdown": gemini_eval["api_failure_breakdown"],
                "per_class": gemini_eval["per_class"],
                "confusion_matrix_3x3": gemini_eval["confusion_matrix"],
                "explanation": "Evaluated against held-out test split (claims_test.jsonl). Rate limits or timeouts are recorded as API failures, never conflated with NOT ENOUGH INFO."
            }
        },
        "pipeline_summary": {
            "active_llm_models_count": 2,
            "primary_model": f"Groq LPU ({groq_verifier.model_name})",
            "alternative_model": f"Google Gemini ({gemini_verifier.model_name})",
            "macro_f1_groq": groq_eval["f1"],
            "macro_f1_gemini": gemini_eval["f1"],
            "benchmark_split": f"SciFact Unseen Test Set ({len(test_samples)} Claims)",
            "retrieval_method": "Deterministic Multi-Signal TF-IDF Vector Space",
            "evaluation_mode": "REAL_MEASURED_PREDICTIONS",
            "groq_api_failures": groq_eval["api_failures"],
            "gemini_api_failures": gemini_eval["api_failures"]
        }
    }

    with open(registry_path, "w", encoding="utf-8") as rf:
        json.dump(registry_data, rf, indent=2)

    print(f"\n[SUCCESS] Saved genuine held-out evaluation results to:")
    print(f" - {output_path}")
    print(f" - {registry_path}")


if __name__ == "__main__":
    main()
