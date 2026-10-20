"""
Comprehensive Regression Test Suite: Scientific Evidence Relevance & Multi-Signal Gating
Tests all 12 required failure and edge cases specified in the Critical Bug Fix specification:

1. 'Vitamin D is good for hair.'
2. A claim about vitamin C and the common cold.
3. A claim about vitamin E and prostate cancer.
4. A claim with explicit negation.
5. A claim for which the corpus contains no relevant evidence.
6. A claim with relevant supporting evidence.
7. A claim with relevant contradicting evidence.
8. Two claims sharing generic terms but discussing different outcomes.
9. Groq returning an unsupported verdict.
10. Gemini returning fabricated evidence IDs.
11. Compare Both mode with one provider unavailable.
12. Empty corpus or retrieval failure.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(backend_dir)
sys.path.insert(0, backend_dir)

from app.main import app, retrieval_engine
from app.pipeline.retrieval import CorpusRetrievalEngine
from app.pipeline.reranking import SentenceEvidenceExtractor
from app.pipeline.llm_groq import GroqClaimVerifier
from app.pipeline.llm_gemini import GeminiClaimVerifier


class TestEvidenceRelevanceAndGating(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        corpus_path = os.path.join(project_root, "data", "corpus.jsonl")
        retrieval_engine.load_corpus(corpus_path)
        retrieval_engine.build_index()

    # Case 1: 'Vitamin D is good for hair.'
    def test_01_vitamin_d_hair_gating(self):
        """Case 1: Vitamin D and hair claim must be rejected by relevance gates."""
        claim = "Vitamin D is good for hair"
        retrieved = retrieval_engine.retrieve(claim, k=3)
        # Must return empty list: No Vitamin C or Prostate Cancer papers allowed!
        self.assertEqual(len(retrieved), 0, f"Expected 0 papers for unindexed Vitamin D & hair claim, got {len(retrieved)}")

        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(len(data["evidence"]), 0, "Expected empty evidence list without fabricated cards")
        self.assertLessEqual(data["confidence"], 60, "Confidence should reflect epistemic uncertainty")
        self.assertIn("does not contain sufficient directly relevant", data["explanation"])

    # Case 2: Claim about Vitamin C and the common cold
    def test_02_vitamin_c_common_cold(self):
        """Case 2: Vitamin C & common cold must retrieve Doc 900011 and NOT Vitamin E papers."""
        claim = "High-dose vitamin C supplementation prevents the common cold in the general population"
        retrieved = retrieval_engine.retrieve(claim, k=2)
        self.assertGreater(len(retrieved), 0, "Expected at least 1 relevant paper for Vitamin C & cold")
        top_doc_id = str(retrieved[0][0]["doc_id"])
        self.assertEqual(top_doc_id, "900011")
        # Ensure Doc 900104 (Vitamin E) is NOT in retrieved docs
        retrieved_ids = [str(d["doc_id"]) for d, _ in retrieved]
        self.assertNotIn("900104", retrieved_ids, "Vitamin E paper must not appear in Vitamin C retrieval")

    # Case 3: Claim about Vitamin E and prostate cancer
    def test_03_vitamin_e_prostate_cancer(self):
        """Case 3: Vitamin E & prostate cancer must retrieve Doc 900104 and NOT Vitamin C papers."""
        claim = "Vitamin E supplementation reduces the risk of prostate cancer"
        retrieved = retrieval_engine.retrieve(claim, k=2)
        self.assertGreater(len(retrieved), 0, "Expected at least 1 relevant paper for Vitamin E & cancer")
        top_doc_id = str(retrieved[0][0]["doc_id"])
        self.assertEqual(top_doc_id, "900104")
        retrieved_ids = [str(d["doc_id"]) for d, _ in retrieved]
        self.assertNotIn("900011", retrieved_ids, "Vitamin C paper must not appear in Vitamin E retrieval")

    # Case 4: Claim with explicit negation
    def test_04_explicit_negation_preservation(self):
        """Case 4: Negations must be preserved, retrieving Doc 900005 for Statin claim."""
        claim = "Statin therapy has no effect on LDL cholesterol levels."
        retrieved = retrieval_engine.retrieve(claim, k=2)
        self.assertGreater(len(retrieved), 0)
        retrieved_ids = [str(d["doc_id"]) for d, _ in retrieved]
        self.assertIn("900005", retrieved_ids)
        # Nicotine replacement therapy (900045) should NOT match despite sharing 'has no effect on'
        self.assertNotIn("900045", retrieved_ids)

    # Case 5: Claim for which corpus contains no relevant evidence
    def test_05_zero_evidence_corpus(self):
        """Case 5: Unrelated biomedical assertion returns NOT ENOUGH INFO with 0 evidence cards."""
        claim = "Quantum entanglement accelerates cellular regeneration."
        retrieved = retrieval_engine.retrieve(claim, k=2)
        self.assertEqual(len(retrieved), 0)

        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(len(data["evidence"]), 0)

    # Case 6: Claim with relevant supporting evidence
    def test_06_relevant_supporting_evidence(self):
        """Case 6: Supported claim retrieves Doc 900043 and confirms SUPPORT."""
        claim = "Urban green space exposure improves self-reported mental health outcomes."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "SUPPORT")
        self.assertGreater(len(data["evidence"]), 0)
        self.assertIn("900043", data["evidence"][0]["id"])

    # Case 7: Claim with relevant contradicting evidence
    def test_07_relevant_contradicting_evidence(self):
        """Case 7: Contradicted claim retrieves Doc 900002 and confirms CONTRADICT."""
        claim = "Handwashing with soap has no measurable effect on reducing diarrheal disease incidence."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "groq"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["verdict"], "CONTRADICT")
        self.assertGreater(len(data["evidence"]), 0)
        self.assertIn("900002", data["evidence"][0]["id"])

    # Case 8: Two claims sharing generic terms but discussing different outcomes
    def test_08_shared_generic_terms_disambiguation(self):
        """Case 8: Claims sharing generic words (e.g. 'supplementation') must not cross-contaminate."""
        claim_a = "High-dose vitamin C supplementation prevents the common cold in the general population"
        claim_b = "Vitamin E supplementation reduces the risk of prostate cancer"

        res_a = [str(d["doc_id"]) for d, _ in retrieval_engine.retrieve(claim_a, k=2)]
        res_b = [str(d["doc_id"]) for d, _ in retrieval_engine.retrieve(claim_b, k=2)]

        self.assertIn("900011", res_a)
        self.assertNotIn("900104", res_a)

        self.assertIn("900104", res_b)
        self.assertNotIn("900011", res_b)

    # Case 9: Groq returning an unsupported verdict
    def test_09_groq_unsupported_verdict_rejection(self):
        """Case 9: Model response validation overrides unsupported SUPPORT to NOT ENOUGH INFO."""
        verifier = GroqClaimVerifier()
        # Simulated raw LLM output that claims SUPPORT without valid supplied evidence IDs
        raw_output = {
            "verdict": "SUPPORT",
            "confidence": 95,
            "evidence_ids": [],
            "explanation": "I believe this is supported based on outside general knowledge."
        }
        validated = verifier._validate_response(raw_output, supplied_doc_ids=[])
        self.assertEqual(validated["verdict"], "NOT ENOUGH INFO", "Must override to NOT ENOUGH INFO when no evidence IDs supplied")
        self.assertLessEqual(validated["confidence"], 60)

    # Case 10: Gemini returning fabricated evidence IDs
    def test_10_gemini_fabricated_citation_rejection(self):
        """Case 10: Hallucinated evidence IDs not in supplied list must be rejected."""
        verifier = GeminiClaimVerifier()
        raw_output = {
            "verdict": "SUPPORT",
            "confidence": 92,
            "evidence_ids": ["fabricated_doc_999999"],
            "explanation": "Supported by fabricated_doc_999999."
        }
        # Supplied doc ID is 900011, but model returned 999999
        validated = verifier._validate_response(raw_output, supplied_doc_ids=["900011"])
        self.assertEqual(validated["verdict"], "NOT ENOUGH INFO", "Must reject verdict citing unsupplied/fabricated IDs")
        self.assertEqual(validated["evidence_ids"], [])

    # Case 11: Compare Both mode with one provider unavailable
    def test_11_compare_both_graceful_handling(self):
        """Case 11: Compare Both mode operates cleanly and reports separate model statuses."""
        claim = "Regular aerobic exercise improves insulin sensitivity in adults with type 2 diabetes."
        resp = self.client.post("/api/verify", json={"claim": claim, "engine": "compare"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNotNone(data.get("comparison"))
        self.assertIn("groq", data["comparison"])
        self.assertIn("gemini", data["comparison"])
        self.assertEqual(data["comparison"]["groq"]["model"], "Llama-3.1-8b-instant")
        self.assertEqual(data["comparison"]["gemini"]["model"], "Gemini 1.5 Flash")

    # Case 12: Empty corpus or retrieval failure
    def test_12_empty_corpus_handling(self):
        """Case 12: An empty or missing corpus must fail gracefully without throwing exceptions."""
        empty_engine = CorpusRetrievalEngine()
        # Not calling load_corpus or build_index
        res = empty_engine.retrieve("Any scientific assertion", k=2)
        self.assertEqual(res, [], "Empty corpus must return [] safely")

    # Case 13: Physical activity and diabetes claim - Covariate exclusion & direct evidence check
    def test_13_physical_activity_diabetes_covariate_exclusion(self):
        """Case 13: Physical activity & diabetes claim must NOT retrieve sitting (900046) or coffee (900103) studies."""
        claim = "Regular physical activity lowers the risk of developing type 2 diabetes."
        retrieved = retrieval_engine.retrieve(claim, k=3)
        retrieved_ids = [str(d["doc_id"]) for d, _ in retrieved]
        self.assertNotIn("900046", retrieved_ids, "Sitting study 900046 must be excluded as physical activity is merely an adjusted covariate")
        self.assertNotIn("900103", retrieved_ids, "Coffee study 900103 must be excluded as physical activity is merely an adjusted covariate")
        self.assertEqual(len(retrieved), 0, "Expected 0 papers because local corpus lacks direct primary prevention trial")

        # Test Groq engine mode
        resp_groq = self.client.post("/api/verify", json={"claim": claim, "engine": "groq"})
        self.assertEqual(resp_groq.status_code, 200)
        data_groq = resp_groq.json()
        self.assertEqual(data_groq["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(len(data_groq["evidence"]), 0, "No irrelevant or covariate evidence cards displayed")
        self.assertLessEqual(data_groq["confidence"], 60, "Confidence reflects epistemic uncertainty of indexed corpus")
        self.assertIn("does not contain a primary prevention trial directly evaluating regular physical activity", data_groq["explanation"])
        self.assertIn("Diabetes Prevention Program", data_groq["explanation"], "Must note broader literature exists outside local corpus")

        # Test Gemini engine mode
        resp_gem = self.client.post("/api/verify", json={"claim": claim, "engine": "gemini"})
        self.assertEqual(resp_gem.status_code, 200)
        data_gem = resp_gem.json()
        self.assertEqual(data_gem["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(len(data_gem["evidence"]), 0)

        # Test Compare engine mode
        resp_cmp = self.client.post("/api/verify", json={"claim": claim, "engine": "compare"})
        self.assertEqual(resp_cmp.status_code, 200)
        data_cmp = resp_cmp.json()
        self.assertEqual(data_cmp["verdict"], "NOT ENOUGH INFO")
        self.assertEqual(len(data_cmp["evidence"]), 0)

    # Case 14: Coffee, Sitting, Insulin Sensitivity, and Parkinson claims disambiguation
    def test_14_exposure_and_outcome_disambiguation(self):
        """Case 14: Distinct exposures and outcomes must retrieve only their true target documents."""
        # 1. Coffee and diabetes
        claim_coffee = "Long-term coffee consumption is associated with a reduced risk of type 2 diabetes."
        res_coffee = [str(d["doc_id"]) for d, _ in retrieval_engine.retrieve(claim_coffee, k=2)]
        self.assertIn("900103", res_coffee, "Doc 900103 must be retrieved for coffee & diabetes")
        self.assertNotIn("900046", res_coffee, "Doc 900046 must not appear in coffee retrieval")

        # 2. Prolonged sitting and diabetes
        claim_sitting = "Prolonged sitting time is associated with increased risk of type 2 diabetes independent of exercise."
        res_sitting = [str(d["doc_id"]) for d, _ in retrieval_engine.retrieve(claim_sitting, k=2)]
        self.assertIn("900046", res_sitting, "Doc 900046 must be retrieved for prolonged sitting")
        self.assertNotIn("900103", res_sitting, "Doc 900103 must not appear in sitting retrieval")

        # 3. Aerobic exercise and insulin sensitivity
        claim_exercise = "Regular aerobic exercise improves insulin sensitivity in adults with type 2 diabetes."
        res_exercise = [str(d["doc_id"]) for d, _ in retrieval_engine.retrieve(claim_exercise, k=2)]
        self.assertIn("900001", res_exercise, "Doc 900001 must be retrieved for exercise & insulin sensitivity")
        self.assertNotIn("900046", res_exercise)
        self.assertNotIn("900103", res_exercise)

        # 4. Coffee and Parkinson's disease
        claim_parkinson = "Coffee consumption has no association with reduced risk of Parkinson's disease"
        res_parkinson = [str(d["doc_id"]) for d, _ in retrieval_engine.retrieve(claim_parkinson, k=2)]
        self.assertIn("900015", res_parkinson, "Doc 900015 must be retrieved for coffee & Parkinson")
        self.assertNotIn("900103", res_parkinson, "Diabetes coffee paper must not match Parkinson query")


if __name__ == "__main__":
    unittest.main()
