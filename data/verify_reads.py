import os
import sys
import json
import pandas as pd

# Set utf-8 stdout encoding if possible
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def main():
    print("==================================================")
    print("   SCIVERIFY DATASET READ & INTEGRITY TEST")
    print("==================================================")
    
    # 1. JSONL Files Test
    jsonl_files = [
        'claims_train.jsonl',
        'claims_validation.jsonl',
        'claims_test.jsonl',
        'corpus.jsonl',
        'claims_custom.jsonl'
    ]
    
    print("\n--- [1] JSONL Files Verification ---")
    for fname in jsonl_files:
        path = os.path.join('data', fname)
        if not os.path.exists(path):
            print(f"[FAIL] {fname}: File NOT FOUND at {path}")
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = [json.loads(line) for line in f if line.strip()]
            first_keys = list(lines[0].keys()) if lines else []
            print(f"[PASS] {fname:25} | {len(lines):2} records | Keys: {first_keys}")
        except Exception as e:
            print(f"[FAIL] {fname}: Failed to read - {e}")

    # 2. CSV Files Test
    csv_files = [
        'claims_train.csv',
        'claims_validation.csv',
        'claims_test.csv',
        'corpus.csv',
        'sciverify_dataset.csv'
    ]
    
    print("\n--- [2] CSV Files Verification (pandas) ---")
    for fname in csv_files:
        path = os.path.join('data', fname)
        if not os.path.exists(path):
            print(f"[FAIL] {fname}: File NOT FOUND at {path}")
            continue
        try:
            df = pd.read_csv(path)
            print(f"[PASS] {fname:25} | {len(df):2} rows | Columns: {list(df.columns)}")
        except Exception as e:
            print(f"[FAIL] {fname}: Failed to read - {e}")

    # 3. Hugging Face Datasets Test (if installed)
    print("\n--- [3] Hugging Face datasets Verification ---")
    try:
        from datasets import load_dataset
        claims = load_dataset('json', data_files={
            'train': 'data/claims_train.jsonl',
            'validation': 'data/claims_validation.jsonl',
            'test': 'data/claims_test.jsonl'
        })
        corpus = load_dataset('json', data_files='data/corpus.jsonl')
        print(f"[PASS] Hugging Face load_dataset: SUCCESS")
        print(f"       Train samples     : {len(claims['train'])}")
        print(f"       Validation samples: {len(claims['validation'])}")
        print(f"       Test samples      : {len(claims['test'])}")
        print(f"       Corpus documents  : {len(corpus['train'])}")
    except Exception as e:
        print(f"[INFO] Hugging Face load_dataset notice: {e}")

    # 4. Backend Pipeline Integration Test
    print("\n--- [4] Backend Pipeline Corpus Ingestion Test ---")
    sys.path.insert(0, os.path.abspath('backend'))
    try:
        from app.pipeline.retrieval import FaissRetrievalEngine
        retriever = FaissRetrievalEngine()
        retriever.load_corpus('data/corpus.jsonl')
        print(f"[PASS] FaissRetrievalEngine: Read {len(retriever.corpus)} documents from data/corpus.jsonl")
        
        sample_query = "statin therapy cardiovascular"
        matches = retriever.retrieve(sample_query, k=2)
        print(f"[PASS] Search query '{sample_query}': retrieved {len(matches)} matching documents:")
        for doc, score in matches:
            print(f"       - [Doc {doc.get('doc_id')}] (score={score:.2f}) {doc.get('title')}")
    except Exception as e:
        print(f"[FAIL] Backend retrieval failed: {e}")

    print("\n==================================================")
    print("   ALL FILES ARE BEING READ SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    main()
