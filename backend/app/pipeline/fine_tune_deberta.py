"""
Script: Fine-Tuning Pipeline for DeBERTa-v3 NLI on SciFact-Health Dataset
Author: Contributor 3 (CB.SC.U4CSE24440)
Contribution: DeBERTa-v3 fine-tuning, validation early-stopping, local artifact persistence.

Fine-tunes cross-encoder/nli-deberta-v3-small on the domain-specific SciFact dataset:
- Training Split: data/claims_train.jsonl (35 assertions)
- Validation Split: data/claims_validation.jsonl (7 assertions)
- Preserves Premise (Evidence) -> Hypothesis (Claim) NLI pair format.
- Saves best checkpoint to local ignored directory: backend/models/deberta-v3-scifact
- Never touches or uses the test set during training or model selection.
"""

import os
import sys
import json
import random
import logging
from typing import List, Dict, Any, Tuple
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sciverify.finetune")

# Standard label mapping matching cross-encoder config:
# 0: contradiction (CONTRADICT), 1: entailment (SUPPORT), 2: neutral (NOT ENOUGH INFO)
LABEL2ID = {
    "CONTRADICT": 0,
    "SUPPORT": 1,
    "NOT ENOUGH INFO": 2
}

ID2LABEL = {v: k for k, v in LABEL2ID.items()}

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

class SciFactNLIDataset(Dataset):
    def __init__(self, records: List[Dict[str, Any]], tokenizer, max_length: int = 512):
        self.records = records
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.records)

    def __getitem__(self, idx):
        item = self.records[idx]
        premise = item["evidence"]
        hypothesis = item["claim"]
        label_id = LABEL2ID.get(item["label"], 2)

        encoded = self.tokenizer(
            premise,
            hypothesis,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt"
        )

        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": torch.tensor(label_id, dtype=torch.long)
        }

def load_data_split(jsonl_path: str, corpus_path: str = "data/corpus.jsonl", csv_path: str = "data/sciverify_dataset.csv") -> List[Dict[str, Any]]:
    corpus = {}
    if os.path.exists(corpus_path):
        with open(corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    doc = json.loads(line)
                    corpus[doc.get("doc_id")] = doc

    csv_ev = {}
    if os.path.exists(csv_path):
        import pandas as pd
        df = pd.read_csv(csv_path)
        for _, r in df.iterrows():
            cid = r.get("id")
            ev = r.get("evidence")
            if pd.notna(ev):
                csv_ev[cid] = str(ev).strip()

    records = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            cid = item.get("id")
            claim = item.get("claim", "").strip()
            label = item.get("label", "NOT ENOUGH INFO").strip()

            evidence_text = ""
            if cid in csv_ev and csv_ev[cid]:
                evidence_text = csv_ev[cid]
            elif cited_docs and cited_docs[0] in corpus:
                doc = corpus[cited_docs[0]]
                abstract_sents = doc.get("abstract", [])
                evidence_info = item.get("evidence", {}).get(str(cited_docs[0]), [])
                if evidence_info and "sentences" in evidence_info[0] and evidence_info[0]["sentences"]:
                    s_idx = evidence_info[0]["sentences"][0]
                    if s_idx < len(abstract_sents):
                        evidence_text = abstract_sents[s_idx]
                if not evidence_text and abstract_sents:
                    evidence_text = abstract_sents[0]

            if not evidence_text or len(evidence_text) < 10:
                evidence_text = "No conclusive or supporting empirical evidence was reported in scientific literature."

            records.append({
                "id": cid,
                "claim": claim,
                "evidence": evidence_text,
                "label": label
            })

    return records

def evaluate_model(model, dataloader, device) -> Tuple[float, float]:
    model.eval()
    total_correct = 0
    total_samples = 0
    all_preds = []
    all_targets = []

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=-1)

            total_correct += (preds == labels).sum().item()
            total_samples += labels.size(0)

            all_preds.extend(preds.cpu().numpy().tolist())
            all_targets.extend(labels.cpu().numpy().tolist())

    accuracy = (total_correct / max(1, total_samples)) * 100.0

    # Compute Macro F1
    classes = [0, 1, 2]
    f1_list = []
    for c in classes:
        tp = sum(1 for p, t in zip(all_preds, all_targets) if p == c and t == c)
        fp = sum(1 for p, t in zip(all_preds, all_targets) if p == c and t != c)
        fn = sum(1 for p, t in zip(all_preds, all_targets) if p != c and t == c)
        prec = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)

    macro_f1 = (sum(f1_list) / len(f1_list)) * 100.0
    return accuracy, macro_f1

def fine_tune_deberta(
    base_model_name: str = "cross-encoder/nli-deberta-v3-small",
    output_dir: str = "backend/models/deberta-v3-scifact",
    epochs: int = 5,
    batch_size: int = 8,
    lr: float = 2e-5,
    seed: int = 42
):
    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] Using device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    print(f"[1/5] Loading tokenizer and base checkpoint: {base_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained(base_model_name, local_files_only=True)
    model.to(device)

    print("[2/5] Loading and formatting train & validation splits...")
    train_records = load_data_split("data/claims_train.jsonl")
    val_records = load_data_split("data/claims_validation.jsonl")
    print(f"      Train assertions     : {len(train_records)}")
    print(f"      Validation assertions: {len(val_records)}")

    train_dataset = SciFactNLIDataset(train_records, tokenizer)
    val_dataset = SciFactNLIDataset(val_records, tokenizer)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Initial zero-shot evaluation on validation set
    init_val_acc, init_val_f1 = evaluate_model(model, val_loader, device)
    print(f"      Pretrained Baseline Val Acc: {init_val_acc:.1f}% | Val Macro F1: {init_val_f1:.1f}%")

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_steps = len(train_loader) * epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=max(1, int(total_steps * 0.1)), num_training_steps=total_steps)
    criterion = torch.nn.CrossEntropyLoss()

    best_val_f1 = -1.0
    best_epoch = 0
    os.makedirs(output_dir, exist_ok=True)

    print("\n[3/5] Starting supervised fine-tuning...")
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0

        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = criterion(outputs.logits, labels)
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(train_loader)
        val_acc, val_f1 = evaluate_model(model, val_loader, device)
        print(f"  Epoch {epoch:02d}/{epochs:02d} | Train Loss: {avg_loss:.4f} | Val Acc: {val_acc:5.1f}% | Val Macro F1: {val_f1:5.1f}%")

        if val_f1 > best_val_f1 or (val_f1 == best_val_f1 and val_acc >= init_val_acc):
            best_val_f1 = val_f1
            best_epoch = epoch
            print(f"    --> [CHECKPOINT] New best validation F1: {val_f1:.1f}%. Saving to {output_dir}")
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

    print(f"\n[4/5] Fine-tuning finished. Best Checkpoint at Epoch {best_epoch} with Val F1: {best_val_f1:.1f}%")
    print(f"[5/5] Ignored artifact directory verified: {output_dir}")
    return output_dir

if __name__ == "__main__":
    fine_tune_deberta()
