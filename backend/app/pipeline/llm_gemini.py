"""
Module: Gemini Text-Based Claim Verification & Explanation
Implements zero-shot/few-shot claim verification and structured explanation
using Google Gemini API.
"""

import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("sciverify.gemini")

SYSTEM_INSTRUCTION = """You are SciVerify AI, an expert biomedical claim verification system.
Given a scientific CLAIM and extracted EVIDENCE from peer-reviewed scientific abstracts:
1. Determine the verdict strictly as one of:
   - SUPPORT (if evidence confirms the claim)
   - CONTRADICT (if evidence refutes or disproves the claim)
   - NOT ENOUGH INFO (if evidence is insufficient, inconclusive, or missing)
2. Provide a calibrated confidence score between 50 and 99.
3. Provide a concise, grounded explanation explaining why, citing the evidence without hallucinating facts.

Respond STRICTLY in valid JSON format:
{
  "verdict": "SUPPORT" | "CONTRADICT" | "NOT ENOUGH INFO",
  "confidence": <integer between 50 and 99>,
  "explanation": "<grounded explanation>"
}
"""

class GeminiClaimVerifier:
    def __init__(self, api_key: str = None, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Set environment variable GEMINI_API_KEY to use Gemini.")
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
            logger.warning(f"Failed to initialize google-generativeai client: {e}")

    def verify(self, claim: str, evidence_text: str = "") -> Dict[str, Any]:
        """Verifies a claim using Gemini."""
        if not self.client:
            return {
                "verdict": "NOT ENOUGH INFO",
                "confidence": 70,
                "explanation": "Gemini API client not initialized. Please configure GEMINI_API_KEY.",
                "model": self.model_name,
                "status": "missing_api_key"
            }

        prompt = f"""EVIDENCE:
{evidence_text if evidence_text else "No specific evidence provided; evaluate general biomedical consensus."}

CLAIM:
{claim}
"""
        try:
            response = self.client.generate_content(prompt)
            data = json.loads(response.text.strip())
            return {
                "verdict": data.get("verdict", "NOT ENOUGH INFO").upper(),
                "confidence": int(data.get("confidence", 75)),
                "explanation": data.get("explanation", ""),
                "model": self.model_name,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error during Gemini verification: {e}")
            return {
                "verdict": "NOT ENOUGH INFO",
                "confidence": 60,
                "explanation": f"Error querying Gemini: {str(e)}",
                "model": self.model_name,
                "status": "error"
            }
