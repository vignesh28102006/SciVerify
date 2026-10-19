"""
Module: Grounded Explanation Generation
Author: V. Vignesh (CB.SC.U4CSE24265)
Contribution: Recall@k/F1 evaluation, grounded explanation generation, system integration, end-to-end testing, refinement.

This module synthesizes the extracted sentence-level evidence into a coherent,
clinically faithful explanation justifying why a claim was categorized as
SUPPORT, CONTRADICT, or NOT ENOUGH INFO without introducing hallucinated facts.
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger("sciverify.explanation")

class GroundedExplanationGenerator:
    def __init__(self):
        pass

    def generate_explanation(
        self,
        claim: str,
        verdict: str,
        evidence_list: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesizes a grounded explanation summarizing the rationale behind the verdict.
        """
        if not evidence_list:
            return "No conclusive scientific literature was retrieved to evaluate this claim. Additional peer-reviewed randomized controlled trials are required."

        primary_sentence = evidence_list[0].get("sentence_text", "")
        doc_title = evidence_list[0].get("title", "the retrieved peer-reviewed study")

        if verdict == "SUPPORT":
            return (
                f"Peer-reviewed evidence from '{doc_title}' directly supports this claim. "
                f"Specifically, the study reports: \"{primary_sentence}\", corroborating the beneficial or hypothesized effect."
            )
        elif verdict == "CONTRADICT":
            return (
                f"Empirical findings from '{doc_title}' contradict this claim. "
                f"The clinical investigation observes that: \"{primary_sentence}\", directly refuting the asserted outcome."
            )
        else:
            return (
                f"The available scientific literature in '{doc_title}' does not contain sufficient endpoint evidence to substantiate this claim. "
                f"The findings state: \"{primary_sentence}\", which leaves the primary outcome indeterminate or unverified."
            )
