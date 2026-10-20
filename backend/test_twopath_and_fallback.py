"""
Comprehensive Test Suite for SciVerify Two-Path Evidence Strategy & Model-Knowledge Fallback
Tests all requirements specified in Prompt 10 Section 7:

1. Claim with directly relevant local supporting evidence (Path A).
2. Claim with directly relevant local contradicting evidence (Path A).
3. Claim with no relevant local evidence (Path B - Local Gate Rejection).
4. Claim for which external literature is available (Path B1 - NCBI PubMed).
5. Claim for which neither local nor external evidence is available (Path B2 - Model-Knowledge Fallback).
6. Groq-only verification mode.
7. Gemini-only verification mode.
8. Compare Both mode (independent side-by-side evaluation).
9. Missing provider credentials handling.
10. Malformed LLM response resilience.
11. Fabricated citation identifiers rejection.
12. Base-model vs fine-tuned-model status reporting (/api/fine-tuning/audit).
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)

from app.main import app, retrieval_engine, groq_verifier, gemini_verifier


class TestTwoPathAndFallback(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        corpus_path = os.path.join(project_root, "data", "corpus.jsonl")
        if os.path.exists(corpus_path):
            retrieval_engine.load_corpus(corpus_path)
            retrieval_engine.build_index()

    # Case 1: Directly relevant local supporting evidence
    def test_01_local_supporting_evidence(self):
        claim = "Urban green space exposure improves self-reported mental health outcomes."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq", "mode": "local_only"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "SUPPORT")
        self.assertEqual(data["provenance"], "LOCAL_CORPUS")
        self.assertFalse(data["isProvisional"])
        self.assertGreater(len(data["evidence"]), 0)
        self.assertEqual(data["evidence"][0]["provenance"], "LOCAL_CORPUS")

    # Case 2: Directly relevant local contradicting evidence
    def test_02_local_contradicting_evidence(self):
        claim = "Handwashing with soap has no measurable effect on reducing diarrheal disease incidence."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq", "mode": "local_only"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "CONTRADICT")
        self.assertEqual(data["provenance"], "LOCAL_CORPUS")
        self.assertFalse(data["isProvisional"])
        self.assertGreater(len(data["evidence"]), 0)

    # Case 3: No relevant local evidence (strict local gating)
    def test_03_no_relevant_local_evidence(self):
        claim = "Regular physical activity lowers the risk of developing type 2 diabetes."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq", "mode": "local_only"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(len(data["evidence"]), 0)
        self.assertEqual(data["provenance"], "LOCAL_CORPUS")
        self.assertIn("does not contain a primary prevention trial directly", data["explanation"])

    # Case 4: External literature available via NCBI PubMed
    def test_04_external_pubmed_literature(self):
        claim = "Vitamin D is good for hair"
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq", "enable_external": True})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["provenance"], "EXTERNAL_PUBMED")
        self.assertFalse(data["isProvisional"])
        self.assertGreater(len(data["evidence"]), 0)
        self.assertTrue(data["evidence"][0]["link"].startswith("https://pubmed.ncbi.nlm.nih.gov/"))
        self.assertEqual(data["evidence"][0]["provenance"], "EXTERNAL_PUBMED")

    # Case 5: Neither local nor external evidence available -> Model Knowledge Fallback
    def test_05_model_knowledge_fallback(self):
        claim = "Quantum entanglement accelerates cellular mitochondria regeneration in telepathic mice"
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq", "fallback_to_knowledge": True})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["provenance"], "MODEL_KNOWLEDGE")
        self.assertTrue(data["isProvisional"])
        self.assertEqual(len(data["evidence"]), 0, "No fake papers allowed in model-knowledge mode")
        self.assertIsNotNone(data.get("scientificReasoning"))

    # Case 6: Groq-only verification mode
    def test_06_groq_only_mode(self):
        claim = "Urban green space exposure improves self-reported mental health outcomes."
        resp = self.client.post("/api/verify/groq", json={"claim": claim})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Groq LPU", data["verifiedBy"])

    # Case 7: Gemini-only verification mode
    def test_07_gemini_only_mode(self):
        claim = "Urban green space exposure improves self-reported mental health outcomes."
        resp = self.client.post("/api/verify/gemini", json={"claim": claim})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Google Gemini", data["verifiedBy"])

    # Case 8: Compare Both mode (independent side-by-side evaluation)
    def test_08_compare_both_mode(self):
        claim = "Urban green space exposure improves self-reported mental health outcomes."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "compare"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNotNone(data.get("comparison"))
        self.assertIn("deberta", data["comparison"])
        self.assertIn("groq", data["comparison"])
        self.assertIn("gemini", data["comparison"])
        self.assertEqual(data["comparison"]["deberta"]["provider"], "Local Hugging Face / PyTorch")
        self.assertNotEqual(data["comparison"]["groq"]["provider"], data["comparison"]["gemini"]["provider"])

    # Case 9: Missing provider credentials handling
    def test_09_missing_credentials_graceful_handling(self):
        from app.pipeline.llm_gemini import GeminiClaimVerifier
        unauthed_verifier = GeminiClaimVerifier(api_key="your_gemini_api_key_here")
        res = unauthed_verifier.assess_model_knowledge("Test assertion")
        self.assertEqual(res["status"], "missing_api_key")
        self.assertEqual(res["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(res["confidence"], 0)
        self.assertTrue(res["is_provisional"])

    # Case 10: Malformed LLM response resilience
    def test_10_malformed_llm_response(self):
        validated = groq_verifier._validate_response({"random_key": "junk"}, supplied_doc_ids=["900011"])
        self.assertEqual(validated["verdict"], "NOT ENOUGH INFO")
        self.assertLessEqual(validated["confidence"], 60)

    # Case 11: Fabricated citation identifiers rejection
    def test_11_fabricated_citation_rejection(self):
        fabricated_output = {
            "verdict": "SUPPORT",
            "confidence": 95,
            "evidence_ids": ["PMID-99999999_fake"],
            "explanation": "Claim is supported based on fake paper."
        }
        validated = groq_verifier._validate_response(fabricated_output, supplied_doc_ids=["900011"])
        self.assertEqual(validated["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(validated["evidence_ids"], [])

    # Case 12: Base-model vs fine-tuned-model status reporting
    def test_12_fine_tuning_audit_reporting(self):
        resp = self.client.get("/api/fine-tuning/audit")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("providers", data)
        groq_info = data["providers"]["groq"]
        gemini_info = data["providers"]["gemini"]
        self.assertEqual(groq_info["status"], "BASE_MODEL_ONLY")
        self.assertFalse(groq_info["training_job_executed"])
        self.assertEqual(gemini_info["status"], "TRAINING_DATA_PREPARED")
        self.assertFalse(gemini_info["training_job_submitted"])

    # Case 13: Unindexed claim with missing credentials returns zero confidence (never 75%)
    def test_13_unindexed_claim_missing_credentials_zero_confidence(self):
        from app.main import groq_verifier
        orig_key = groq_verifier.api_key
        try:
            groq_verifier.api_key = None
            resp = self.client.post("/api/verify", json={
                "claim": "Vitamin C reduces pimples",
                "engine": "groq",
                "mode": "auto",
                "enable_external": False,
                "fallback_to_knowledge": True
            })
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["verdict"], "NOT ENOUGH INFO")
            self.assertEqual(data["confidence"], 0, "Confidence must be 0 when unconfigured credentials prevent LLM evaluation")
            self.assertTrue(data["isProvisional"])
            self.assertEqual(data["evidence"], [])
        finally:
            groq_verifier.api_key = orig_key


if __name__ == "__main__":
    unittest.main()
