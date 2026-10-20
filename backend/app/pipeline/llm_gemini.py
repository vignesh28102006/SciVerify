"""
Module: Gemini Text-Based Claim Verification & Explanation
Alternative LLM Verification Engine powered by Google Gemini 1.5 Flash.
Enforces strict evidence grounding and rejection of fabricated or mismatched citations.
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger("sciverify.gemini")

SYSTEM_INSTRUCTION = """You are SciVerify AI, an expert biomedical scientific claim verification system powered by Google Gemini.
You will evaluate a scientific CLAIM against the supplied EVIDENCE ITEMS from peer-reviewed literature.

MANDATORY SCIENTIFIC VERIFICATION RULES:
1. Verdict Criteria:
   - SUPPORT: ONLY if the supplied evidence explicitly investigates the claim's core entities and confirms the claim.
   - CONTRADICT: ONLY if the supplied evidence explicitly investigates the claim's core entities and refutes the claim.
   - NOT ENOUGH INFO: MANDATORY if:
     a) No evidence is provided, OR
     b) The evidence discusses a DIFFERENT vitamin, drug, disease, intervention, or outcome (e.g. Vitamin C or E cannot prove/disprove Vitamin D claims; cold or cancer trials cannot prove/disprove hair claims), OR
     c) The evidence is inconclusive, missing, or insufficient.
2. Citation Grounding:
   - Return the exact Document IDs from the supplied evidence in "evidence_ids".
   - If verdict is NOT ENOUGH INFO, "evidence_ids" MUST be empty [].
   - NEVER fabricate or invent Document IDs, studies, citations, authors, or statistics.
   - Do NOT use outside training knowledge to guess a verdict when the supplied evidence is missing or unrelated.
3. Confidence:
   - Set between 50 and 99. If evidence is missing or unrelated, confidence must be 50 to 60.

Respond STRICTLY in valid JSON format:
{
  "verdict": "SUPPORT" | "CONTRADICT" | "NOT ENOUGH INFO",
  "confidence": <integer between 50 and 99>,
  "evidence_ids": ["<doc_id>"],
  "explanation": "<concise, grounded explanation citing specific findings>",
  "limitations": "<relevant study design or literature limitations>"
}"""


class GeminiClaimVerifier:
    def __init__(self, api_key: str = None, model_name: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.tuned_model_id = os.getenv("GEMINI_TUNED_MODEL_ID")
        self.base_model_name = model_name
        self.model_name = self.tuned_model_id if self.tuned_model_id else model_name
        self.is_tuned = bool(self.tuned_model_id)
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key or "your_" in self.api_key or "AIzaSy..." in self.api_key:
            return

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_INSTRUCTION,
                generation_config={"response_mime_type": "application/json"}
            )
            logger.info(f"Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.info(f"Using direct REST requests for Gemini API: {e}")
            self.client = None

    def _validate_response(self, raw_data: Dict[str, Any], supplied_doc_ids: List[str], model_used: Optional[str] = None) -> Dict[str, Any]:
        """Validates that verdicts are backed by actual supplied evidence IDs."""
        verdict = raw_data.get("verdict", "NOT ENOUGH INFO").upper()
        if verdict not in ("SUPPORT", "CONTRADICT", "NOT ENOUGH INFO"):
            verdict = "NOT ENOUGH INFO"

        returned_ids = raw_data.get("evidence_ids", [])
        if isinstance(returned_ids, str):
            returned_ids = [returned_ids]
        elif not isinstance(returned_ids, list):
            returned_ids = []

        cleaned_ids = [str(i).replace("ev-doc-", "").replace("doc-", "").strip() for i in returned_ids]
        valid_ids = [cid for cid in cleaned_ids if cid in supplied_doc_ids]

        if verdict in ("SUPPORT", "CONTRADICT"):
            if not supplied_doc_ids or not valid_ids:
                logger.warning(
                    f"Gemini response validation: Rejected unsupported {verdict} verdict without valid supplied evidence "
                    f"({cleaned_ids} vs supplied {supplied_doc_ids}). Forcing NOT ENOUGH INFO."
                )
                verdict = "NOT ENOUGH INFO"
                explanation = (
                    "The retrieved literature does not contain sufficient directly relevant evidence to verify this assertion. "
                    "In accordance with evidence gating standards, ungrounded extrapolation is prohibited."
                )
                confidence = min(int(raw_data.get("confidence", 55)), 60)
                valid_ids = []
            else:
                explanation = raw_data.get("explanation", "")
                confidence = int(raw_data.get("confidence", 85))
        else:
            explanation = raw_data.get("explanation", "Insufficient directly relevant evidence in the current corpus.")
            confidence = min(int(raw_data.get("confidence", 55)), 70)
            valid_ids = []

        active_model = model_used or self.model_name
        return {
            "verdict": verdict,
            "confidence": confidence,
            "evidence_ids": valid_ids,
            "explanation": explanation,
            "limitations": raw_data.get("limitations", "Evaluated against indexed biomedical corpus."),
            "model": active_model,
            "status": "success"
        }

    def verify(
        self, 
        claim: str, 
        evidence_text: str = "",
        evidence_items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Verifies a claim using Gemini."""
        supplied_doc_ids = []
        if evidence_items:
            supplied_doc_ids = [str(item.get("doc_id", item.get("id", ""))) for item in evidence_items if item]
            supplied_doc_ids = [i for i in supplied_doc_ids if i]

        if not self.api_key or "your_" in self.api_key or "AIzaSy..." in self.api_key:
            return {
                "verdict": None,
                "confidence": 0,
                "evidence_ids": [],
                "explanation": "Gemini API key is not configured in backend/.env. Please set GEMINI_API_KEY=AIzaSy...",
                "model": self.model_name,
                "status": "missing_api_key",
                "error_type": "MISSING_API_KEY",
                "provenance": "LOCAL_CORPUS"
            }

        # Build evidence block with explicit IDs
        if evidence_items:
            ev_blocks = []
            for item in evidence_items:
                d_id = item.get("doc_id", item.get("id", "UNKNOWN"))
                title = item.get("title", "")
                sent = item.get("sentence", item.get("highlightedSentence", ""))
                ev_blocks.append(f"[DOCUMENT ID: {d_id}]\nTitle: {title}\nEvidence: {sent}")
            formatted_evidence = "\n\n".join(ev_blocks)
        elif evidence_text:
            formatted_evidence = evidence_text
        else:
            formatted_evidence = "NO EVIDENCE FOUND IN CORPUS."

        prompt = f"""SUPPLIED EVIDENCE:
{formatted_evidence}

SCIENTIFIC CLAIM TO VERIFY:
{claim}
"""
        # Try SDK first if initialized
        if self.client:
            try:
                response = self.client.generate_content(prompt)
                data = json.loads(response.text.strip())
                return self._validate_response(data, supplied_doc_ids)
            except Exception as e:
                logger.warning(f"SDK call failed, trying direct REST API: {e}")

        # Direct REST API fallback with multi-model and tuned model capability
        candidate_models = []
        if self.tuned_model_id:
            candidate_models.append(self.tuned_model_id)
        for base in [self.base_model_name, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]:
            if base and base not in candidate_models:
                candidate_models.append(base)

        last_error_code = None
        last_error_text = "No candidate models responded successfully."

        import time

        for m_name in candidate_models:
            for attempt in range(2):
                try:
                    if m_name.startswith("tunedModels/"):
                        url = f"https://generativelanguage.googleapis.com/v1beta/{m_name}:generateContent?key={self.api_key}"
                    else:
                        clean_m = m_name.replace("models/", "")
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_m}:generateContent?key={self.api_key}"
                    headers = {"Content-Type": "application/json"}
                    body = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": f"{SYSTEM_INSTRUCTION}\n\n{prompt}"}]
                            }
                        ],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.05
                        }
                    }
                    resp = requests.post(url, headers=headers, json=body, timeout=12)
                    if resp.status_code == 200:
                        result_json = resp.json()
                        text = result_json["candidates"][0]["content"]["parts"][0]["text"]
                        data = json.loads(text.strip())
                        return self._validate_response(data, supplied_doc_ids, model_used=m_name)
                    elif resp.status_code == 429:
                        last_error_code = 429
                        last_error_text = resp.text
                        logger.warning(f"Gemini model {m_name} rate limit (429), attempting alternative candidate...")
                        break
                    elif resp.status_code == 404:
                        logger.info(f"Model {m_name} returned 404, attempting alternative...")
                        break
                    else:
                        last_error_code = resp.status_code
                        last_error_text = resp.text
                        logger.warning(f"Gemini REST API error {resp.status_code} on {m_name}: {resp.text}")
                        break
                except Exception as e:
                    last_error_text = str(e)
                    logger.error(f"Error calling Gemini REST API on {m_name}: {e}")
                    time.sleep(1)

        error_type = f"HTTP_{last_error_code}" if last_error_code else "NETWORK_ERROR"
        return {
            "verdict": None,
            "raw_verdict": None,
            "confidence": 0,
            "evidence_ids": [],
            "explanation": f"Gemini verification service encountered an API failure ({error_type}): {last_error_text[:200]}",
            "model": self.model_name,
            "status": "error",
            "error_type": error_type,
            "error_details": last_error_text[:300],
            "provenance": "LOCAL_CORPUS"
        }

    def assess_model_knowledge(self, claim: str) -> Dict[str, Any]:
        """
        Path B: LLM Knowledge Assessment Fallback
        Evaluates a claim using pre-trained scientific literature consensus when local indexed evidence is absent.
        Returns a structured, provisional scientific assessment with biological reasoning, caveats, and limitations.
        """
        if not self.api_key or "your_" in self.api_key or "AIzaSy..." in self.api_key:
            return {
                "verdict": "NOT ENOUGH INFO",
                "confidence": 55,
                "is_provisional": True,
                "evidence_ids": [],
                "explanation": "Gemini API key is not configured in backend/.env.",
                "scientific_reasoning": "Unconfigured credentials prevented cloud LLM knowledge evaluation.",
                "qualifications": "Configure GEMINI_API_KEY in backend/.env to activate live knowledge evaluation.",
                "model": self.model_name,
                "status": "missing_api_key",
                "provenance": "MODEL_KNOWLEDGE"
            }

        knowledge_system = (
            "You are SciVerify AI, an expert biomedical reasoning instrument powered by Google Gemini. "
            "The query scientific claim does NOT have an indexed trial in the local literature corpus. "
            "Your task is to provide a PROVISIONAL SCIENTIFIC ASSESSMENT based on established peer-reviewed biomedical literature, "
            "systematic reviews (e.g. Cochrane, PubMed), and physiological mechanisms.\n\n"
            "MANDATORY RULES:\n"
            "1. Verdict:\n"
            "   - SUPPORT: If peer-reviewed biomedical consensus confirms this assertion.\n"
            "   - CONTRADICT: If peer-reviewed biomedical consensus refutes this assertion (e.g. claims of absolute cures, or overgeneralized preventions like 'Vitamin C prevents colds in everyone').\n"
            "   - NOT ENOUGH INFO: If scientific evidence is inconclusive, actively disputed, or missing.\n"
            "2. Provisional: Explicitly note that this is a model-knowledge provisional assessment, NOT verified against local corpus records.\n"
            "3. Scientific Reasoning: Provide the biochemical, physiological, or clinical mechanisms.\n"
            "4. Qualifications & Limitations: Explicitly detail clinical nuances, population constraints, and dosage/delivery factors.\n\n"
            "Respond STRICTLY in valid JSON with keys:\n"
            "{\n"
            '  "verdict": "SUPPORT" | "CONTRADICT" | "NOT ENOUGH INFO",\n'
            '  "confidence": <integer 65-90>,\n'
            '  "explanation": "<concise scientific summary>",\n'
            '  "scientific_reasoning": "<detailed biological and trial mechanism>",\n'
            '  "qualifications": "<clinical caveats, subpopulation distinctions, limitations>",\n'
            '  "is_provisional": true\n'
            "}"
        )

        candidate_models = []
        if self.tuned_model_id:
            candidate_models.append(self.tuned_model_id)
        for base in [self.base_model_name, "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-flash-latest"]:
            if base and base not in candidate_models:
                candidate_models.append(base)

        last_err = "No candidate models responded successfully."
        for m_name in candidate_models:
            for attempt in range(2):
                try:
                    if m_name.startswith("tunedModels/"):
                        url = f"https://generativelanguage.googleapis.com/v1beta/{m_name}:generateContent?key={self.api_key}"
                    else:
                        clean_m = m_name.replace("models/", "")
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_m}:generateContent?key={self.api_key}"
                    headers = {"Content-Type": "application/json"}
                    body = {
                        "contents": [
                            {
                                "role": "user",
                                "parts": [{"text": f"{knowledge_system}\n\nAssess scientific claim: {claim}"}]
                            }
                        ],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 0.1
                        }
                    }
                    resp = requests.post(url, headers=headers, json=body, timeout=12)
                    if resp.status_code == 200:
                        result_json = resp.json()
                        text = result_json["candidates"][0]["content"]["parts"][0]["text"]
                        data = json.loads(text.strip())

                        raw_verdict = str(data.get("verdict", "NOT ENOUGH INFO")).upper()
                        if "TRUE" in raw_verdict or "SUPPORT" in raw_verdict:
                            verdict = "SUPPORT"
                        elif "FALSE" in raw_verdict or "CONTRADICT" in raw_verdict:
                            verdict = "CONTRADICT"
                        else:
                            verdict = "NOT ENOUGH INFO"

                        raw_conf = data.get("confidence", 75)
                        try:
                            conf = int(raw_conf)
                        except (ValueError, TypeError):
                            conf = 80 if "high" in str(raw_conf).lower() else 70

                        return {
                            "verdict": verdict,
                            "confidence": min(90, max(55, conf)),
                            "is_provisional": True,
                            "evidence_ids": [],
                            "explanation": data.get("explanation", "Evaluated based on pre-trained biomedical literature."),
                            "scientific_reasoning": data.get("scientific_reasoning", ""),
                            "qualifications": data.get("qualifications", "Provisional assessment: not verified against indexed local corpus."),
                            "model": f"Google Gemini ({m_name})",
                            "status": "success",
                            "provenance": "MODEL_KNOWLEDGE"
                        }
                    elif resp.status_code == 429:
                        last_err = "HTTP_429: Rate limit exceeded"
                        time.sleep(2)
                        continue
                    elif resp.status_code == 404:
                        break
                    else:
                        last_err = f"HTTP_{resp.status_code}: {resp.text[:100]}"
                        break
                except Exception as e:
                    last_err = str(e)
                    logger.error(f"Error calling Gemini knowledge assessment on {m_name}: {e}")

        # Return explicit API failure if network times out or fails
        return {
            "verdict": None,
            "confidence": 0,
            "is_provisional": True,
            "evidence_ids": [],
            "explanation": f"Gemini knowledge evaluation encountered an API failure: {last_err}",
            "scientific_reasoning": "Could not connect to Gemini service endpoint.",
            "qualifications": "Check internet connectivity and GEMINI_API_KEY in backend/.env.",
            "model": self.model_name,
            "status": "error",
            "error_type": "API_ERROR",
            "error_details": last_err,
            "provenance": "MODEL_KNOWLEDGE"
        }
