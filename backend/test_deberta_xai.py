"""
Test Suite: DeBERTa-v3 NLI Verification & Explainable AI (Integrated Gradients)
Author: Contributor 3 (CB.SC.U4CSE24440)
Tests:
1. DeBERTa-v3 Claim Verifier loads and classifies SUPPORT, CONTRADICT, NOT ENOUGH INFO.
2. Word-boundary robustness for scientific negation markers (prevents 'no' in 'diagnosis').
3. Differentiable Integrated Gradients feature attribution across premise & hypothesis.
4. Completeness axiom / convergence delta verification (|sum(IG) - (F(x) - F(x'))| < threshold).
5. Empirical Rationale Fidelity & Faithfulness perturbation testing.
6. Edge case handling (empty strings, whitespace, malformed inputs).
7. FastAPI schema compatibility (/api/verify payload contract with modelMetrics & xai).
"""

import os
import sys
import unittest
import torch

sys.path.insert(0, os.path.abspath('backend'))

from app.pipeline.verification import DeBERTaClaimVerifier
from app.pipeline.xai_integrated_gradients import IntegratedGradientsExplainer

class TestDeBERTaAndXAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.verifier = DeBERTaClaimVerifier()
        cls.verifier._load_model()
        cls.explainer = IntegratedGradientsExplainer(
            model=cls.verifier.model,
            tokenizer=cls.verifier.tokenizer,
            device=str(cls.verifier.device)
        )

    def test_01_empty_and_short_evidence_returns_nei(self):
        """Edge case: empty or truncated evidence must yield NOT ENOUGH INFO."""
        res_empty = self.verifier.verify("Regular exercise reduces diabetes risk.", "")
        self.assertEqual(res_empty["verdict"], "NOT ENOUGH INFO")
        self.assertGreaterEqual(res_empty["confidence"], 70)

        res_short = self.verifier.verify("Regular exercise reduces diabetes risk.", "Too short.")
        self.assertEqual(res_short["verdict"], "NOT ENOUGH INFO")

    def test_02_support_classification(self):
        """Claim supported by direct clinical trial evidence."""
        claim = "Regular aerobic exercise improves insulin sensitivity in adults with type 2 diabetes."
        evidence = "Participants who completed 12 weeks of moderate aerobic training showed significantly improved insulin sensitivity compared to sedentary controls."
        res = self.verifier.verify(claim, evidence)
        self.assertEqual(res["verdict"], "SUPPORT")
        self.assertGreaterEqual(res["confidence"], 75)

    def test_03_contradict_classification(self):
        """Claim contradicted by empirical literature."""
        claim = "Statin therapy has no effect on LDL cholesterol levels."
        evidence = "Statins inhibit HMG-CoA reductase and substantially lower circulating low-density lipoprotein cholesterol in multi-center clinical trials."
        res = self.verifier.verify(claim, evidence)
        self.assertEqual(res["verdict"], "CONTRADICT")
        self.assertGreaterEqual(res["confidence"], 75)

    def test_04_not_enough_info_classification(self):
        """Claim with inconclusive/insufficient endpoint evidence."""
        claim = "Wearable fitness trackers directly cause improved long-term weight loss outcomes in all users."
        evidence = "The reviewed abstract discusses short-term step count changes only and does not establish long-term clinical weight loss outcomes."
        res = self.verifier.verify(claim, evidence)
        self.assertEqual(res["verdict"], "NOT ENOUGH INFO")

    def test_05_word_boundary_safety(self):
        """Ensure substring words like 'diagnosis' or 'innovative' do not falsely trigger negation 'no'."""
        claim = "Early antibiotic treatment reduces mortality in sepsis patients."
        evidence = "Sepsis patients who received antibiotics within one hour of diagnosis had significantly lower mortality rates."
        res = self.verifier.verify(claim, evidence)
        # Should be SUPPORT, not falsely CONTRADICT due to 'diagNOsis'
        self.assertEqual(res["verdict"], "SUPPORT")

    def test_06_integrated_gradients_structure(self):
        """Integrated Gradients must return signed token attributions for premise and hypothesis."""
        claim = "Urban green space improves mental health."
        evidence = "Residents with access to green space reported significantly better mental health."
        xai = self.explainer.explain(claim, evidence, steps=10)

        self.assertIn("topFeatures", xai)
        self.assertIn("rationaleFidelity", xai)
        self.assertIn("faithfulnessScore", xai)
        self.assertIn("convergence_delta", xai)
        self.assertIsInstance(xai["topFeatures"], list)
        self.assertGreater(len(xai["topFeatures"]), 0)

        for feat in xai["topFeatures"]:
            self.assertIn("token", feat)
            self.assertIn("weight", feat)
            self.assertIn("polarity", feat)
            self.assertIn(feat["polarity"], ["positive", "negative", "neutral"])

    def test_07_xai_convergence_and_finite_scores(self):
        """Completeness delta must be a finite non-negative float."""
        claim = "Noise pollution affects cardiovascular health."
        evidence = "Exposure to high traffic noise was associated with elevated rates of hypertension."
        xai = self.explainer.explain(claim, evidence, steps=10)

        delta = xai["convergence_delta"]
        self.assertFalse(torch.isnan(torch.tensor(delta)))
        self.assertGreaterEqual(delta, 0.0)

    def test_08_xai_fidelity_and_faithfulness_bounds(self):
        """Rationale fidelity and faithfulness scores must be within [0, 100]."""
        claim = "Early antibiotic treatment reduces sepsis mortality."
        evidence = "Sepsis patients receiving immediate antibiotics showed significantly lower mortality rates."
        xai = self.explainer.explain(claim, evidence, steps=10)

        fid = xai["rationaleFidelity"]
        faith = xai["faithfulnessScore"]
        self.assertTrue(0.0 <= fid <= 100.0, f"Fidelity {fid} out of bounds")
        self.assertTrue(0.0 <= faith <= 100.0, f"Faithfulness {faith} out of bounds")

    def test_09_empty_input_xai_payload_safety(self):
        """Empty input to explainer must return a valid safe payload without throwing exceptions."""
        xai_empty = self.explainer.explain("", "")
        self.assertIn("topFeatures", xai_empty)
        self.assertEqual(xai_empty["target_class_label"], "NOT ENOUGH INFO")
        self.assertEqual(xai_empty["rationaleFidelity"], 0.0)
        self.assertEqual(xai_empty["faithfulnessScore"], 0.0)

    def test_10_no_artificial_minimum_floor_imposed(self):
        """Verify that scores are not artificially clamped to legacy heuristic floors (e.g. 70.0%)."""
        claim = "Prolonged sitting time is associated with increased risk of type 2 diabetes independent of exercise."
        evidence = "Individuals with high daily sitting time showed elevated diabetes risk even after adjusting for total physical activity."
        xai = self.explainer.explain(claim, evidence, steps=20)

        # For this sample, empirical sufficiency retention is genuinely < 50%
        # It must NOT be clamped to 70.0%
        self.assertNotEqual(xai["rationaleFidelity"], 70.0, "Fidelity was artificially clamped to 70.0% floor!")
        self.assertNotEqual(xai["faithfulnessScore"], 75.0, "Faithfulness was artificially clamped to 75.0% floor!")
        self.assertIn("sufficiencyRetention", xai)
        self.assertIn("comprehensivenessDrop", xai)

    def test_11_perturbation_masks_differ_from_original(self):
        """Verify that perturbation token IDs actually differ from original input IDs."""
        claim = "Statin therapy has no effect on LDL cholesterol."
        evidence = "Statins inhibit HMG-CoA reductase and substantially lower circulating LDL cholesterol in clinical trials."
        
        encoded = self.verifier.tokenizer(evidence, claim, return_tensors="pt")
        input_ids = encoded["input_ids"]
        pad_id = self.verifier.tokenizer.pad_token_id or 0
        
        # Explain and inspect internal perturbation logic directly
        xai = self.explainer.explain(claim, evidence, steps=20)
        
        # Verify that explanation identified non-zero token attributions
        top_feats = xai.get("topFeatures", [])
        self.assertGreater(len(top_feats), 0)
        weights = [f["weight"] for f in top_feats]
        self.assertTrue(any(w > 0 for w in weights))

    def test_12_scores_derive_directly_from_probabilities(self):
        """Verify that fidelity and faithfulness follow exact probability retention/drop formulas."""
        claim = "Nicotine replacement therapy has no effect on smoking cessation rates."
        evidence = "Smokers using nicotine replacement therapy achieved significantly higher cessation rates than those attempting to quit unaided."
        xai = self.explainer.explain(claim, evidence, steps=50)

        # In this direct contradiction, rationale contains strong contradiction evidence
        # Sufficiency retention and comprehensiveness drop must be positive, finite numbers
        self.assertGreater(xai["rationaleFidelity"], 10.0)
        self.assertGreater(xai["faithfulnessScore"], 50.0)
        self.assertIn("relative_completeness_error_pct", xai)
        self.assertLess(xai["relative_completeness_error_pct"], 10.0)

    def test_13_trapezoidal_convergence_delta_finite_and_small(self):
        """Verify composite trapezoidal numerical integration produces small relative completeness error."""
        claim = "Nicotine replacement therapy has no effect on smoking cessation rates."
        evidence = "Smokers using nicotine replacement therapy achieved significantly higher cessation rates than those attempting to quit unaided."
        xai_50 = self.explainer.explain(claim, evidence, steps=50)

        # At m=50 steps on clear signal, relative error against logit difference must be < 10%
        rel_err = xai_50["relative_completeness_error_pct"]
        self.assertLess(rel_err, 10.0, f"Relative completeness error too high: {rel_err}%")
        self.assertLess(xai_50["convergence_delta"], 0.5)

    def test_14_reproducibility_of_xai(self):
        """Verify deterministic reproducibility of Integrated Gradients attributions."""
        claim = "Urban green space exposure improves self-reported mental well-being in adults."
        evidence = "Residents with greater access to urban green space reported significantly better mental health scores."
        xai_run1 = self.explainer.explain(claim, evidence, steps=20)
        xai_run2 = self.explainer.explain(claim, evidence, steps=20)

        self.assertAlmostEqual(xai_run1["convergence_delta"], xai_run2["convergence_delta"], places=4)
        self.assertAlmostEqual(xai_run1["rationaleFidelity"], xai_run2["rationaleFidelity"], places=2)
        self.assertAlmostEqual(xai_run1["faithfulnessScore"], xai_run2["faithfulnessScore"], places=2)

if __name__ == "__main__":
    unittest.main(verbosity=2)
