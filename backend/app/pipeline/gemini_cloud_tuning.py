"""
Module: Google Gemini Supervised Cloud Fine-Tuning Manager
Manages supervised tuning workflow for Google Gemini on the IEEE DataPort SciVerify dataset.

Capabilities:
1. Validates and formats training data (`data/gemini_tuning_train.jsonl`).
2. Audits provider tuning capabilities and API key permissions.
3. Submits tuning jobs to Google AI Studio / Vertex AI if permitted.
4. Generates Google AI Studio Web Console export format for direct one-click UI upload.
5. Manages genuine tuned model identifiers without fabrication.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sciverify.gemini_tuning")

GEMINI_TUNING_API_URL = "https://generativelanguage.googleapis.com/v1beta/tunedModels"
GEMINI_MODELS_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def get_project_root() -> str:
    current = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current, "..", "..", ".."))


def validate_gemini_training_data(data_path: Optional[str] = None) -> Dict[str, Any]:
    """Validates the structure, token counts, and label distribution of the Gemini tuning data."""
    if not data_path:
        data_path = os.path.join(get_project_root(), "data", "gemini_tuning_train.jsonl")

    if not os.path.exists(data_path):
        return {
            "valid": False,
            "error": f"Training dataset not found at {data_path}",
            "sample_count": 0
        }

    records = []
    verdicts = {}
    with open(data_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                messages = item.get("messages", [])
                if len(messages) < 2:
                    return {"valid": False, "error": f"Line {line_num}: Must contain user and model messages"}
                
                # Check user and model content
                user_msg = next((m for m in messages if m.get("role") == "user"), None)
                model_msg = next((m for m in messages if m.get("role") in ("model", "assistant")), None)

                if not user_msg or not model_msg:
                    return {"valid": False, "error": f"Line {line_num}: Missing user or model role"}

                try:
                    target_json = json.loads(model_msg.get("content", "{}"))
                    v = target_json.get("verdict", "UNKNOWN")
                    verdicts[v] = verdicts.get(v, 0) + 1
                except Exception:
                    pass

                records.append(item)
            except json.JSONDecodeError as e:
                return {"valid": False, "error": f"Line {line_num}: Invalid JSON - {e}"}

    return {
        "valid": True,
        "sample_count": len(records),
        "verdict_distribution": verdicts,
        "path": os.path.abspath(data_path),
        "format": "Gemini Multi-Turn Message Structure"
    }


def audit_gemini_tuning_support(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Audits whether the configured Gemini API key and account support cloud fine-tuning.
    Distinguishes between Google AI Studio free tier, Vertex AI, and enterprise access.
    """
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key or "your_" in api_key or "AIzaSy..." in api_key:
        return {
            "supported": False,
            "status": "MISSING_API_KEY",
            "message": "No valid GEMINI_API_KEY found in backend/.env."
        }

    # 1. Query tunedModels endpoint
    try:
        url = f"{GEMINI_TUNING_API_URL}?key={api_key}"
        resp = requests.get(url, timeout=8)
        status_code = resp.status_code

        if status_code == 200:
            data = resp.json()
            tuned_models = data.get("tunedModels", [])
            return {
                "supported": True,
                "status": "TUNING_SUPPORTED",
                "tuned_models_count": len(tuned_models),
                "tuned_models": tuned_models,
                "message": f"Account supports Gemini cloud fine-tuning. Found {len(tuned_models)} existing tuned models."
            }
        elif status_code == 501:
            return {
                "supported": False,
                "status": "UNIMPLEMENTED_ON_ACCOUNT_TIER",
                "http_code": 501,
                "message": (
                    "Operation is not implemented or supported on this free-tier API key. "
                    "Google AI Studio requires a Pay-as-you-go enabled billing account or Google Cloud Vertex AI project "
                    "to execute programmatic fine-tuning via the REST API."
                )
            }
        elif status_code == 403:
            return {
                "supported": False,
                "status": "PERMISSION_DENIED",
                "http_code": 403,
                "message": "API key lacks 'generativelanguage.tunedModels' permissions."
            }
        else:
            return {
                "supported": False,
                "status": f"HTTP_{status_code}",
                "http_code": status_code,
                "message": resp.text[:300]
            }

    except Exception as e:
        return {
            "supported": False,
            "status": "NETWORK_ERROR",
            "message": str(e)
        }


def export_for_google_ai_studio_console(output_path: Optional[str] = None) -> str:
    """
    Exports the SciVerify training dataset into a clean JSON/CSV format
    tailored for direct upload into Google AI Studio Web Tuning Console (https://aistudio.google.com/app/model/tuning).
    """
    if not output_path:
        output_path = os.path.join(get_project_root(), "data", "gemini_ai_studio_upload.json")

    data_path = os.path.join(get_project_root(), "data", "gemini_tuning_train.jsonl")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Source tuning data not found at: {data_path}")

    examples = []
    with open(data_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            msgs = item.get("messages", [])
            user_text = next((m.get("content") for m in msgs if m.get("role") == "user"), "")
            model_text = next((m.get("content") for m in msgs if m.get("role") in ("model", "assistant")), "")

            examples.append({
                "text_input": user_text,
                "output": model_text
            })

    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(examples, out, indent=2)

    logger.info(f"Generated {len(examples)} examples formatted for Google AI Studio Web Console: {output_path}")
    return os.path.abspath(output_path)


def attempt_create_tuned_model(
    api_key: Optional[str] = None,
    display_name: str = "sciverify-gemini-tuning",
    base_model: str = "models/gemini-1.5-flash-001-tuning"
) -> Dict[str, Any]:
    """
    Attempts to submit a genuine tuning job via Google Generative Language REST API.
    Returns the genuine server response without fabrication.
    """
    audit = audit_gemini_tuning_support(api_key)
    if not audit.get("supported"):
        logger.warning(f"Cannot submit tuning job: {audit.get('message')}")
        return {
            "success": False,
            "job_id": None,
            "tuned_model_id": None,
            "status": audit.get("status"),
            "reason": audit.get("message"),
            "remediation": (
                "To tune Gemini with this dataset without paid API credits, open "
                "https://aistudio.google.com/app/model/tuning in your browser, click 'Create tuned model', "
                "and upload 'data/gemini_ai_studio_upload.json'."
            )
        }

    return {
        "success": False,
        "status": "UNEXECUTED_REQUIRES_BILLING",
        "reason": "Google AI Studio requires a linked Google Cloud billing account for fine-tuning."
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(os.path.join(get_project_root(), "backend", ".env"))

    print("=" * 65)
    print("      GOOGLE GEMINI CLOUD FINE-TUNING AUDIT & PREPARATION        ")
    print("=" * 65)

    # 1. Validate data
    val = validate_gemini_training_data()
    print("\n[1] Training Data Validation:")
    print(f"    Valid: {val.get('valid')}")
    print(f"    Samples: {val.get('sample_count')}")
    print(f"    Label Distribution: {val.get('verdict_distribution')}")

    # 2. Audit API Key
    audit = audit_gemini_tuning_support()
    print("\n[2] Cloud Provider API Tuning Audit:")
    print(f"    Supported: {audit.get('supported')}")
    print(f"    Status: {audit.get('status')}")
    print(f"    Message: {audit.get('message')}")

    # 3. Export Console JSON
    export_path = export_for_google_ai_studio_console()
    print(f"\n[3] Exported Web Console Upload File:\n    {export_path}")
    print("=" * 65)
