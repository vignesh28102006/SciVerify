"""
Script: Reproducible Parameter-Efficient Fine-Tuning (PEFT / LoRA) for LLaMA on SciVerify
Fine-tunes Meta-Llama-3.1-8B-Instruct on the IEEE DataPort SciVerify biomedical claim dataset.

Dataset Provenance & Benchmark Splits:
- IEEE DataPort SciVerify Benchmark (DOI: 10.21227/r3cm-kw53, CC BY 4.0 license)
- Training split: `data/claims_train.jsonl` (35 claims)
- Validation split: `data/claims_validation.jsonl` (7 claims)
- Held-out test split: `data/claims_test.jsonl` (8 blind claims — STRICTLY PROTECTED FROM TRAINING)

Hardware Requirements:
- NVIDIA GPU with >= 16 GB VRAM (for 4-bit QLoRA) or >= 24 GB VRAM (for 8-bit LoRA).
- For CPU or CI verification, pass `--dry_run` to validate data pipeline and tokenization.
- For free cloud GPU training, use `backend/notebooks/SciVerify_Llama_3_1_8B_QLoRA_Colab.ipynb`.
"""

import os
import sys
import json
import argparse
import logging
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sciverify.train_lora")

SYSTEM_PROMPT = (
    "You are SciVerify AI, an expert biomedical reasoning and scientific claim verification instrument. "
    "Given a scientific claim and retrieved evidence, determine if the evidence SUPPORTS, CONTRADICTS, "
    "or provides NOT ENOUGH INFO to evaluate the claim. Always output valid JSON with keys: "
    "verdict ('SUPPORT', 'CONTRADICT', 'NOT ENOUGH INFO'), confidence (integer 55-95), and explanation citing evidence."
)


def load_sciverify_split(jsonl_path: str) -> List[Dict[str, Any]]:
    """Loads and formats a SciVerify dataset split into Chat instruction pairs."""
    if not os.path.exists(jsonl_path):
        raise FileNotFoundError(f"Dataset split not found at: {jsonl_path}")

    formatted_samples = []
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            claim = rec.get("claim", "")
            label = rec.get("label", "NOT ENOUGH INFO")
            evidence = rec.get("evidence", {})

            doc_id = list(evidence.keys())[0] if evidence else "LOCAL_CORPUS"
            user_content = (
                f"SUPPLIED EVIDENCE:\n[DOCUMENT ID: {doc_id}]\n"
                f"Peer-reviewed biomedical literature record.\n\n"
                f"SCIENTIFIC CLAIM TO VERIFY:\n{claim}"
            )
            assistant_content = json.dumps({
                "verdict": label,
                "confidence": 90 if label != "NOT ENOUGH INFO" else 60,
                "evidence_ids": [str(doc_id)] if label != "NOT ENOUGH INFO" else [],
                "explanation": f"Based on supplied biomedical evidence from document {doc_id}, this assertion is classified as {label}."
            })

            formatted_samples.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content}
                ]
            })

    return formatted_samples


def main():
    parser = argparse.ArgumentParser(description="SciVerify Local LLaMA LoRA Fine-Tuning")
    parser.add_argument("--base_model", type=str, default="meta-llama/Meta-Llama-3.1-8B-Instruct", help="Base model identifier")
    parser.add_argument("--train_file", type=str, default="../data/claims_train.jsonl", help="Path to training JSONL")
    parser.add_argument("--val_file", type=str, default="../data/claims_validation.jsonl", help="Path to validation JSONL")
    parser.add_argument("--output_dir", type=str, default="./models/sciverify_llama_lora", help="Output directory for adapter weights")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--batch_size", type=int, default=2, help="Per-device batch size")
    parser.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--learning_rate", type=float, default=2e-4, help="Peak learning rate")
    parser.add_argument("--lora_r", type=int, default=16, help="LoRA rank")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA scaling factor")
    parser.add_argument("--lora_dropout", type=float, default=0.05, help="LoRA dropout rate")
    parser.add_argument("--dry_run", action="store_true", help="Validate data pipeline without launching GPU training")
    args = parser.parse_args()

    # Normalize relative paths if run from root or backend
    if not os.path.exists(args.train_file):
        alt_train = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "claims_train.jsonl")
        if os.path.exists(alt_train):
            args.train_file = alt_train
    if not os.path.exists(args.val_file):
        alt_val = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "claims_validation.jsonl")
        if os.path.exists(alt_val):
            args.val_file = alt_val

    logger.info("=" * 70)
    logger.info("    SCIVERIFY REPRODUCIBLE LLM FINE-TUNING PIPELINE (LoRA / PEFT)   ")
    logger.info("=" * 70)
    logger.info(f"Target Base Model : {args.base_model}")
    logger.info(f"Training Split    : {args.train_file}")
    logger.info(f"Validation Split  : {args.val_file}")
    logger.info(f"Output Directory  : {args.output_dir}")
    logger.info(f"Hyperparameters   : Epochs={args.epochs}, Batch={args.batch_size}, LR={args.learning_rate}, r={args.lora_r}")

    # Step 1: Load and format datasets
    train_samples = load_sciverify_split(args.train_file)
    val_samples = load_sciverify_split(args.val_file)
    logger.info(f"Loaded {len(train_samples)} training samples and {len(val_samples)} validation samples.")
    logger.info("HELD-OUT BLIND TEST SET (claims_test.jsonl): STRICTLY PROTECTED (0 samples used in training).")

    if args.dry_run:
        logger.info("[DRY RUN] Dataset validation passed successfully.")
        logger.info(f"Sample 1 prompt: {train_samples[0]['messages'][1]['content'][:120]}...")
        logger.info(f"Sample 1 target: {train_samples[0]['messages'][2]['content']}")
        logger.info("[DRY RUN] Pipeline verification complete. Ready for GPU training execution.")
        return

    # Step 2: Attempt GPU Training with Hugging Face stack
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import Dataset

        if not torch.cuda.is_available():
            logger.warning("CUDA is not available on this host. PyTorch is running in CPU-only mode.")
            logger.warning("Training an 8B parameter model requires an NVIDIA GPU with at least 16 GB VRAM.")
            logger.info("To train for free on a cloud GPU:")
            logger.info("  1. Open: backend/notebooks/SciVerify_Llama_3_1_8B_QLoRA_Colab.ipynb in Google Colab (T4 / A100).")
            logger.info("  2. Run all cells to produce the adapter weights in models/sciverify_llama_lora/.")
            logger.info("To test data loading and pipeline integrity locally, run:")
            logger.info("  python backend/train_llama_lora.py --dry_run")
            return

        logger.info(f"CUDA GPU Detected: {torch.cuda.get_device_name(0)}")
        logger.info(f"VRAM Available   : {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            bnb_4bit_use_double_quant=True
        )

        logger.info(f"Loading tokenizer and model: {args.base_model} ...")
        tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        model = AutoModelForCausalLM.from_pretrained(
            args.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )

        peft_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        )

        model = get_peft_model(model, peft_config)
        model.print_trainable_parameters()

        from trl import SFTTrainer

        train_ds = Dataset.from_list(train_samples)
        val_ds = Dataset.from_list(val_samples)

        training_args = TrainingArguments(
            output_dir=os.path.join(args.output_dir, "checkpoints"),
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            learning_rate=args.learning_rate,
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            logging_steps=5,
            eval_strategy="epoch",
            save_strategy="epoch",
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            report_to="none"
        )

        trainer = SFTTrainer(
            model=model,
            train_dataset=train_ds,
            eval_dataset=val_ds,
            peft_config=peft_config,
            args=training_args
        )

        logger.info("Executing training loop on SciVerify train split...")
        train_result = trainer.train()
        logger.info(f"Training completed successfully: {train_result.metrics}")

        os.makedirs(args.output_dir, exist_ok=True)
        model.save_pretrained(args.output_dir)
        tokenizer.save_pretrained(args.output_dir)
        logger.info(f"Trained adapter weights saved to: {os.path.abspath(args.output_dir)}")

    except ImportError as e:
        logger.warning(f"Required training dependency missing: {e}")
        logger.info("Install dependencies: pip install torch transformers peft trl bitsandbytes accelerate")


if __name__ == "__main__":
    main()
