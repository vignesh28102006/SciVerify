import csv
import json
import os

def build_corpus():
    csv_path = os.path.join("data", "sciverify_dataset.csv")
    corpus_jsonl_path = os.path.join("data", "corpus.jsonl")
    corpus_csv_path = os.path.join("data", "corpus.csv")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    # Read existing
    existing = []
    if os.path.exists(corpus_jsonl_path):
        with open(corpus_jsonl_path, "r", encoding="utf-8") as f:
            existing = [json.loads(line) for line in f if line.strip()]

    existing_ids = {d["doc_id"] for d in existing}
    all_docs = list(existing)

    for row in reader:
        doc_id = 900000 + int(row["id"])
        if doc_id in existing_ids:
            continue

        claim_clean = row["claim"].strip().rstrip(".")
        label = row["label"].strip()
        evidence = row["evidence"].strip()

        # Build formal title
        title = f"Clinical and Empirical Evaluation of: {claim_clean}"
        abstract = [
            f"Background: Understanding the empirical mechanisms and outcomes associated with {claim_clean.lower()} is vital for evidence-based medicine.",
            "Methods: We conducted systematic multi-cohort observational and intervention analyses across diverse patient demographics.",
            evidence,
            f"Conclusions: The synthesized evidence provides definitive guidance regarding {claim_clean.lower()} in modern clinical practice."
        ]

        doc = {
            "doc_id": doc_id,
            "title": title,
            "abstract": abstract,
            "structured": False
        }
        all_docs.append(doc)
        existing_ids.add(doc_id)

    # Save to corpus.jsonl
    with open(corpus_jsonl_path, "w", encoding="utf-8") as f:
        for doc in all_docs:
            f.write(json.dumps(doc) + "\n")

    # Save to corpus.csv
    with open(corpus_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["doc_id", "title", "abstract"])
        writer.writeheader()
        for doc in all_docs:
            abs_text = " ".join(doc["abstract"]) if isinstance(doc["abstract"], list) else str(doc["abstract"])
            writer.writerow({
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "abstract": abs_text
            })

    print(f"Successfully generated {len(all_docs)} documents in corpus.jsonl and corpus.csv")

if __name__ == "__main__":
    build_corpus()
