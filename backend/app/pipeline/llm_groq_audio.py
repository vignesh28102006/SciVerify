"""
Module: Groq Audio Scientific Claim Verification Pipeline
Processes spoken audio / speech inputs using:
1. Groq's high-speed Whisper Large v3 (whisper-large-v3) speech-to-text API.
2. Groq's Llama-3-70b-versatile / Llama-3.1-8b-instant for fast scientific claim verification & rationale.
"""

import os
import json
import logging
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))
except ImportError:
    pass

logger = logging.getLogger("sciverify.groq")

class GroqAudioClaimVerifier:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.whisper_model = "whisper-large-v3"
        self.llm_model = "openai/gpt-oss-20b"
        self.client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key or "your_" in self.api_key:
            return
        try:
            import httpx
            from groq import Groq
            http_client = httpx.Client(timeout=30.0)
            self.client = Groq(api_key=self.api_key, http_client=http_client)
            logger.info("Groq client successfully initialized.")
        except Exception as e:
            logger.info(f"Using direct REST requests for Groq API: {e}")
            self.client = None

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> str:
        """
        Transcribes speech audio using Groq Whisper Large v3.
        """
        if not self.api_key:
            return ""

        try:
            if self.client:
                transcription = self.client.audio.transcriptions.create(
                    file=(filename, audio_bytes),
                    model=self.whisper_model,
                    language="en",
                    response_format="text"
                )
                return str(transcription).strip()

            import requests
            headers = {"Authorization": f"Bearer {self.api_key}"}
            files = {"file": (filename, audio_bytes, "audio/wav")}
            data = {"model": self.whisper_model, "response_format": "text"}
            resp = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
                timeout=20
            )
            if resp.status_code == 200:
                return resp.text.strip()
        except Exception as e:
            logger.error(f"Error in Groq Whisper transcription: {e}")
        return ""

    def verify_claim(self, claim: str, evidence_text: str = "") -> Dict[str, Any]:
        """
        Verifies the transcribed claim using Groq's high-speed Llama 3.1 inference.
        """
        if not self.api_key:
            return {
                "verdict": "NOT ENOUGH INFO",
                "confidence": 70,
                "explanation": "GROQ_API_KEY is not configured in backend/.env.",
                "model": f"Groq ({self.whisper_model} + {self.llm_model})",
                "status": "missing_api_key"
            }

        system_prompt = (
            "You are SciVerify AI, an expert biomedical claim verification system powered by Groq LPUs. "
            "Given a scientific CLAIM and EVIDENCE from scientific research: "
            "1. Output verdict as exactly one of: SUPPORT, CONTRADICT, or NOT ENOUGH INFO. "
            "2. Provide calibrated confidence (50-99). "
            "3. Provide a concise explanation grounded strictly in the evidence. "
            "Return JSON only: {\"verdict\": \"...\", \"confidence\": 85, \"explanation\": \"...\"}"
        )

        user_content = f"EVIDENCE:\n{evidence_text if evidence_text else 'No specific evidence provided.'}\n\nCLAIM:\n{claim}"

        try:
            if self.client:
                completion = self.client.chat.completions.create(
                    model=self.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1
                )
                res_text = completion.choices[0].message.content
                data = json.loads(res_text)
                return {
                    "verdict": data.get("verdict", "NOT ENOUGH INFO").upper(),
                    "confidence": int(data.get("confidence", 80)),
                    "explanation": data.get("explanation", ""),
                    "model": f"Groq ({self.whisper_model} + {self.llm_model})",
                    "status": "success"
                }

            import requests
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.llm_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                return {
                    "verdict": data.get("verdict", "NOT ENOUGH INFO").upper(),
                    "confidence": int(data.get("confidence", 80)),
                    "explanation": data.get("explanation", ""),
                    "model": f"Groq ({self.whisper_model} + {self.llm_model})",
                    "status": "success"
                }
        except Exception as e:
            logger.error(f"Error in Groq claim verification: {e}")

        return {
            "verdict": "NOT ENOUGH INFO",
            "confidence": 60,
            "explanation": "Could not complete claim verification with Groq API.",
            "model": f"Groq ({self.whisper_model} + {self.llm_model})",
            "status": "error"
        }

    def transcribe_and_verify(self, audio_bytes: bytes, audio_filename: str = "audio.wav", evidence_text: str = "") -> Dict[str, Any]:
        """Full pipeline: Audio input -> Whisper Large-v3 -> Llama 3.1 Claim Verification"""
        transcription = self.transcribe_audio(audio_bytes, audio_filename)
        if not transcription:
            transcription = "[Audio input captured for verification]"

        res = self.verify_claim(transcription, evidence_text)
        res["transcription"] = transcription
        return res
