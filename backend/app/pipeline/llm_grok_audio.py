"""
Module: Grok Audio/Multimodal Scientific Claim Verification
Processes audio input (scientific claims spoken via audio file or speech),
transcribes/interprets via Grok / Whisper multimodal audio pipeline,
and performs scientific claim verification.
"""

import os
import json
import base64
import logging
from typing import Dict, Any

logger = logging.getLogger("sciverify.grok")

class GrokAudioClaimVerifier:
    def __init__(self, api_key: str = None, model_name: str = "grok-2-latest", base_url: str = "https://api.x.ai/v1"):
        self.api_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        self.model_name = model_name
        self.base_url = base_url

    def transcribe_and_verify(self, audio_bytes: bytes, audio_filename: str = "audio.wav", evidence_text: str = "") -> Dict[str, Any]:
        """
        Receives raw audio bytes, extracts the spoken scientific claim,
        and verifies it using Grok's multimodal API.
        """
        if not self.api_key:
            logger.warning("GROK_API_KEY or XAI_API_KEY not set.")
            return {
                "transcription": "[Audio transcription unavailable: API key not configured]",
                "verdict": "NOT ENOUGH INFO",
                "confidence": 70,
                "explanation": "Grok API key is not configured. Please set XAI_API_KEY or GROK_API_KEY.",
                "model": self.model_name,
                "status": "missing_api_key"
            }

        try:
            import requests

            # Convert audio bytes to base64 data URI
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            mime_type = "audio/wav"
            if audio_filename.endswith(".mp3"):
                mime_type = "audio/mp3"
            elif audio_filename.endswith(".m4a"):
                mime_type = "audio/m4a"

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            system_prompt = (
                "You are Grok, an advanced multimodal scientific research assistant. "
                "Analyze the provided audio input containing a spoken scientific or health claim. "
                "1. Transcribe the spoken claim accurately. "
                "2. Evaluate it against scientific literature / provided evidence. "
                "3. Classify into: SUPPORT, CONTRADICT, or NOT ENOUGH INFO. "
                "4. Provide confidence (50-99) and a concise rationale. "
                "Return response ONLY in JSON format: "
                '{"transcription": "...", "verdict": "SUPPORT"|"CONTRADICT"|"NOT ENOUGH INFO", "confidence": 85, "explanation": "..."}'
            )

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": f"Context/Evidence: {evidence_text}\nAnalyze the spoken claim in this audio:"},
                            {"type": "input_audio", "input_audio": {"data": audio_b64, "format": mime_type.split('/')[-1]}}
                        ]
                    }
                ],
                "temperature": 0.2
            }

            resp = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                result_json = resp.json()
                content = result_json["choices"][0]["message"]["content"]
                # Parse JSON out of markdown code fence if present
                clean_content = content.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_content)
                return {
                    "transcription": parsed.get("transcription", ""),
                    "verdict": parsed.get("verdict", "NOT ENOUGH INFO").upper(),
                    "confidence": int(parsed.get("confidence", 80)),
                    "explanation": parsed.get("explanation", ""),
                    "model": self.model_name,
                    "status": "success"
                }
            else:
                return {
                    "transcription": "[Error querying Grok API]",
                    "verdict": "NOT ENOUGH INFO",
                    "confidence": 60,
                    "explanation": f"Grok API returned status code {resp.status_code}: {resp.text[:200]}",
                    "model": self.model_name,
                    "status": "api_error"
                }
        except Exception as e:
            logger.error(f"Error in Grok audio processing: {e}")
            return {
                "transcription": "[Audio processing error]",
                "verdict": "NOT ENOUGH INFO",
                "confidence": 60,
                "explanation": f"Failed to process audio with Grok: {str(e)}",
                "model": self.model_name,
                "status": "error"
            }
