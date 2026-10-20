import json
import statistics
from typing import Dict, Any, List

import os

def audit():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_path = os.path.join(base_dir, "data", "claims_test.jsonl")
    eval_path = os.path.join(base_dir, "data", "test_evaluation_results.json")
    registry_path = os.path.join(base_dir, "data", "models_evaluation_registry.json")

    with open(test_path, "r", encoding="utf-8") as f:
        ground_truth_claims = [json.loads(line) for line in f if line.strip()]

    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)

    with open(registry_path, "r", encoding="utf-8") as f:
        registry_data = json.load(f)

    print("=" * 95)
    print("                    SCIVERIFY SECTION 05 AUDIT & RE-CALCULATION")
    print("=" * 95)
    print(f"Dataset Split File  : data/claims_test.jsonl")
    print(f"Total Test Claims   : {len(ground_truth_claims)}")
    print(f"Evaluation Timestamp: {eval_data.get('timestamp')}")
    print()

    groq_details = {d['id']: d for d in eval_data['evaluations']['groq']['details']}
    gemini_details = {d['id']: d for d in eval_data['evaluations']['gemini']['details']}

    print(f"{'ID':<4} | {'Claim Excerpt':<42} | {'Ground Truth':<16} | {'Groq (Llama 3.1)':<18} | {'Gemini (3.5 Lite)':<18}")
    print("-" * 95)
    for c in ground_truth_claims:
        cid = c['id']
        claim_short = (c['claim'][:39] + "...") if len(c['claim']) > 42 else c['claim']
        gt = c['label']
        g_pred = groq_details[cid]['predicted']
        m_pred = gemini_details[cid]['predicted']
        g_match = "[OK]" if g_pred == gt else "[MIS]"
        m_match = "[OK]" if m_pred == gt else "[MIS]"
        print(f"{cid:<4} | {claim_short:<42} | {gt:<16} | {g_pred:<10} {g_match:<7} | {m_pred:<10} {m_match:<7}")
    print("-" * 95)

    CLASSES = ["SUPPORT", "CONTRADICT", "NOT ENOUGH INFO"]
    # User synonym mapping test: SUPPORTED, CONTRADICTED, NOT ENOUGH INFO
    SYNONYM_MAP = {
        "SUPPORT": "SUPPORTED",
        "SUPPORTED": "SUPPORTED",
        "CONTRADICT": "CONTRADICTED",
        "CONTRADICTED": "CONTRADICTED",
        "NOT ENOUGH INFO": "NOT ENOUGH INFO"
    }

    for model_key in ["groq", "gemini"]:
        model_name = eval_data['evaluations'][model_key]['model']
        provider = eval_data['evaluations'][model_key]['provider']
        details = eval_data['evaluations'][model_key]['details']

        y_true = [d['ground_truth'] for d in details]
        y_pred = [d['predicted'] for d in details]
        latencies = [d['latency_ms'] for d in details]

        # 3x3 Confusion Matrix
        cm = {t: {p: 0 for p in CLASSES} for t in CLASSES}
        for t, p in zip(y_true, y_pred):
            cm[t][p] += 1

        print(f"\n=======================================================")
        print(f" MODEL AUDIT: {provider} ({model_name})")
        print(f"=======================================================")
        print("3x3 CONFUSION MATRIX (Rows: True, Cols: Pred):")
        print(f"{'True \\ Pred':<18} | {'SUPPORT':<10} | {'CONTRADICT':<12} | {'NOT ENOUGH INFO':<16} | {'Total'}")
        print("-" * 72)
        for t in CLASSES:
            sup = cm[t]["SUPPORT"]
            con = cm[t]["CONTRADICT"]
            nei = cm[t]["NOT ENOUGH INFO"]
            tot = sup + con + nei
            print(f"{t:<18} | {sup:<10} | {con:<12} | {nei:<16} | {tot}")

        # Per-class metrics
        per_class = {}
        prec_list = []
        rec_list = []
        f1_list = []
        supports = []

        for c in CLASSES:
            tp = cm[c][c]
            fp = sum(cm[other][c] for other in CLASSES if other != c)
            fn = sum(cm[c][other] for other in CLASSES if other != c)
            sup = tp + fn
            supports.append(sup)

            prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            rec = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            per_class[c] = {
                "tp": tp, "fp": fp, "fn": fn, "support": sup,
                "precision": prec, "recall": rec, "f1": f1
            }
            prec_list.append(prec)
            rec_list.append(rec)
            f1_list.append(f1)

        total_correct = sum(cm[c][c] for c in CLASSES)
        n = len(y_true)
        accuracy = total_correct / n

        # Macro (unweighted average across the 3 classes)
        macro_prec = sum(prec_list) / len(CLASSES)
        macro_rec = sum(rec_list) / len(CLASSES)
        macro_f1 = sum(f1_list) / len(CLASSES)

        # Weighted average (weighted by support of each class)
        weighted_prec = sum(p * s for p, s in zip(prec_list, supports)) / n
        weighted_rec = sum(r * s for r, s in zip(rec_list, supports)) / n
        weighted_f1 = sum(f * s for f, s in zip(f1_list, supports)) / n

        print("\nPER-CLASS CLASSIFICATION REPORT:")
        print(f"{'Class':<18} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support'}")
        print("-" * 65)
        for c in CLASSES:
            s = per_class[c]
            print(f"{c:<18} | {s['precision']*100:>8.1f}% | {s['recall']*100:>8.1f}% | {s['f1']*100:>8.1f}% | {s['support']:>7}")
        print("-" * 65)
        print(f"{'Macro Average':<18} | {macro_prec*100:>8.1f}% | {macro_rec*100:>8.1f}% | {macro_f1*100:>8.1f}% | {n:>7}")
        print(f"{'Weighted Average':<18} | {weighted_prec*100:>8.1f}% | {weighted_rec*100:>8.1f}% | {weighted_f1*100:>8.1f}% | {n:>7}")
        print(f"{'Accuracy':<18} | {accuracy*100:>8.1f}% ({total_correct}/{n})")

        # Latency
        mean_lat = statistics.mean(latencies)
        median_lat = statistics.median(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        stdev_lat = statistics.stdev(latencies)
        p90_lat = sorted(latencies)[int(len(latencies)*0.9)]

        print(f"\nLATENCY METRICS (Measured End-to-End per query):")
        print(f" - Sample Count : {len(latencies)}")
        print(f" - Raw ms values: {latencies}")
        print(f" - Mean Latency : {mean_lat:.2f} ms (Reported in UI: {round(mean_lat)} ms)")
        print(f" - Median Latency: {median_lat:.2f} ms")
        print(f" - 90th Pct Lat : {p90_lat} ms")
        print(f" - Min / Max    : {min_lat} ms / {max_lat} ms (StdDev: {stdev_lat:.2f} ms)")

if __name__ == "__main__":
    audit()
