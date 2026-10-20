"""
Module: Corpus Retrieval Engine (Deterministic Multi-Signal Lexical & TF-IDF Vector Space)
Implements rigorous biomedical claim-to-literature retrieval with entity-level normalization,
title/abstract dual-weighting, and strict multi-signal evidence relevance gating.

Addresses the root cause of irrelevant document retrieval (e.g., preventing Vitamin C or
Prostate Cancer papers from matching Vitamin D & hair claims).
"""

import os
import re
import json
import logging
from typing import List, Dict, Any, Tuple, Set, Optional
import numpy as np

logger = logging.getLogger("sciverify.retrieval")

# Custom stop words that strictly preserve negations, scientific directions, and qualifiers
NON_STOP_WORDS = {
    "no", "not", "never", "none", "without", "neither", "nor", "prevent", "prevents",
    "prevention", "reduces", "reduced", "reduction", "increases", "increased",
    "causes", "caused", "cures", "cured", "associated", "association", "risk",
    "efficacy", "effective", "harm", "benefit", "good", "bad", "safe", "safety"
}

STANDARD_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "by", "for", "with", "about", "against", "between",
    "into", "through", "during", "before", "after", "above", "below", "to",
    "from", "up", "down", "over", "under", "again", "further", "then", "once",
    "here", "there", "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "so", "than", "too",
    "very", "s", "t", "can", "will", "just", "should", "now", "of", "and",
    "or", "but", "if", "while", "that", "this", "these", "those"
}

STOP_WORDS = list(STANDARD_STOP_WORDS - NON_STOP_WORDS)


def normalize_biomedical_text(text: str) -> str:
    """
    Normalizes biomedical assertions and abstracts to bind specific entity compounds:
    - 'vitamin d' -> 'vitamin_d', 'vitamin c' -> 'vitamin_c', 'vitamin e' -> 'vitamin_e'
    - 'type 1' -> 'type_1', 'type 2' -> 'type_2'
    - 'physical activity' -> 'physical_activity', 'aerobic exercise' -> 'aerobic_exercise'
    - 'prolonged sitting' -> 'prolonged_sitting', 'sitting time' -> 'sitting_time'
    - 'coffee consumption' -> 'coffee_consumption'
    - 'hair loss' -> 'hair_loss', 'common cold' -> 'common_cold'
    - 'covid-19' -> 'covid_19'
    Preserves hyphens and critical qualifiers while standardizing case.
    """
    if not text:
        return ""
    t = text.lower()
    # Normalize vitamin variants
    t = re.sub(r'\bvitamin\s+([a-z0-9]+)\b', r'vitamin_\1', t)
    # Normalize diabetes types
    t = re.sub(r'\btype\s*([12])\b', r'type_\1', t)
    # Normalize physical activity and exercise compounds
    t = re.sub(r'\bphysical\s+activity\b', r'physical_activity', t)
    t = re.sub(r'\baerobic\s+exercise\b', r'aerobic_exercise', t)
    t = re.sub(r'\baerobic\s+training\b', r'aerobic_exercise', t)
    t = re.sub(r'\bphysical\s+exertion\b', r'physical_exertion', t)
    # Normalize sedentary and sitting compounds
    t = re.sub(r'\bprolonged\s+sitting(?:\s+time)?\b', r'prolonged_sitting', t)
    t = re.sub(r'\bsitting\s+time\b', r'sitting_time', t)
    # Normalize coffee compounds
    t = re.sub(r'\bcoffee\s+consumption\b', r'coffee_consumption', t)
    # Normalize metabolic and cardiovascular compounds
    t = re.sub(r'\binsulin\s+sensitivity\b', r'insulin_sensitivity', t)
    t = re.sub(r'\binsulin\s+resistance\b', r'insulin_resistance', t)
    t = re.sub(r'\bstatin\s+therapy\b', r'statin_therapy', t)
    t = re.sub(r'\bintermittent\s+fasting\b', r'intermittent_fasting', t)
    t = re.sub(r'\bmediterranean\s+diet\b', r'mediterranean_diet', t)
    t = re.sub(r'\bketogenic\s+diets?\b', r'ketogenic_diet', t)
    t = re.sub(r'\bbariatric\s+surgery\b', r'bariatric_surgery', t)
    t = re.sub(r'\bsecond\s*-?\s*hand\s+smoke\b', r'second_hand_smoke', t)
    t = re.sub(r'\bcommon\s+cold\b', r'common_cold', t)
    t = re.sub(r'\bprostate\s+cancer\b', r'prostate_cancer', t)
    t = re.sub(r'\blung\s+cancer\b', r'lung_cancer', t)
    t = re.sub(r'\bbreast\s+cancer\b', r'breast_cancer', t)
    t = re.sub(r'\bcolorectal\s+cancer\b', r'colorectal_cancer', t)
    t = re.sub(r'\bhair\s+loss\b', r'hair_loss', t)
    t = re.sub(r'\bmental\s+health\b', r'mental_health', t)
    t = re.sub(r'\bcardiovascular\s+(disease|health|events|outcomes)\b', r'cardiovascular_\1', t)
    t = re.sub(r'\bcovid\s*-\s*19\b', r'covid_19', t)
    return t


COVARIATE_PATTERN = re.compile(
    r'(?:even\s+after\s+adjusting\s+for|after\s+adjusting\s+for|adjusting\s+for|adjusted\s+for|'
    r'controlling\s+for|controlled\s+for|independent\s+of|independently\s+of)\s+([^.]*?)'
    r'(?=\b(?:is|are|was|were|showed|demonstrated|remained|persisted|provides)\b|\.|\band\s+(?:we|they|the\s+authors)\b|$)',
    re.IGNORECASE
)


def strip_covariate_clauses(text: str) -> str:
    """
    Strips statistical covariate adjustment and independence clauses from biomedical text.
    In epidemiology and clinical trials, controlled confounders ('after adjusting for physical activity',
    'independent of exercise') are held constant in regression models, not investigated as primary exposures.
    """
    if not text:
        return ""
    return COVARIATE_PATTERN.sub(' ', text)


def extract_content_tokens(text: str) -> Set[str]:
    """Extracts non-stop content tokens of length >= 2 from normalized text."""
    norm = normalize_biomedical_text(text)
    tokens = re.findall(r'\b[a-zA-Z0-9_\-]{2,}\b', norm)
    return {w for w in tokens if w not in STANDARD_STOP_WORDS}


GENERIC_METHOD_TERMS = {
    "therapy", "treatment", "intervention", "evaluation", "clinical", "empirical",
    "investigation", "study", "results", "conclusion", "effect", "effects",
    "associated", "association", "rates", "levels", "outcomes", "risk", "directly",
    "improved", "improves", "causes", "caused", "adults", "general", "population",
    "individuals", "use", "using", "daily", "regular", "early", "prolonged", "short",
    "long", "term", "high", "low", "has", "have", "had", "no", "not", "and", "with",
    "for", "the", "is", "are", "was", "were", "good", "bad", "all", "any", "equally",
    "effective", "effectiveness"
}


def extract_key_domain_terms(text: str) -> List[str]:
    """Extracts distinctive domain-specific biomedical entities, conditions, and outcomes."""
    norm = normalize_biomedical_text(text)
    tokens = re.findall(r'\b[a-zA-Z0-9_\-]{3,}\b', norm)
    return [t for t in tokens if t not in GENERIC_METHOD_TERMS]


class CorpusRetrievalEngine:
    """
    Multi-signal, deterministic non-neural literature retrieval engine with:
    1. Dual TF-IDF Vector Space matching (Title + Abstract).
    2. Explicit entity consistency verification (e.g. Vitamin D vs C vs E).
    3. Strict evidence relevance gating to reject unrelated documents and prevent false positives.
    """
    def __init__(self, top_k: int = 2, min_similarity: float = 0.16, min_overlap_ratio: float = 0.35):
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.min_overlap_ratio = min_overlap_ratio
        self.corpus: List[Dict[str, Any]] = []
        self.title_vectorizer = None
        self.title_matrix = None
        self.text_vectorizer = None
        self.text_matrix = None
        self.normalized_corpus_texts: List[str] = []
        self._initialized = False

    def load_corpus(self, corpus_path: str):
        """Loads corpus documents from a JSONL file."""
        self.corpus = []
        if not os.path.exists(corpus_path):
            logger.warning(f"Corpus file not found: {corpus_path}")
            return

        with open(corpus_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        self.corpus.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        logger.info(f"Loaded {len(self.corpus)} scientific documents into corpus.")

    def build_index(self):
        """Builds dual TF-IDF index over normalized titles and abstracts."""
        if not self.corpus:
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            titles = [normalize_biomedical_text(doc.get("title", "")) for doc in self.corpus]
            full_texts = []
            for doc in self.corpus:
                abstract = doc.get("abstract", "")
                if isinstance(abstract, list):
                    abstract = " ".join(abstract)
                title = doc.get("title", "")
                full = f"{title}. {abstract}"
                full_texts.append(normalize_biomedical_text(full))

            self.normalized_corpus_texts = full_texts

            token_pat = r"(?u)\b[a-zA-Z0-9_\-]{2,}\b"

            # 1. Title Vectorizer (High-specificity semantic signal)
            self.title_vectorizer = TfidfVectorizer(
                token_pattern=token_pat,
                stop_words=STOP_WORDS,
                ngram_range=(1, 2),
                sublinear_tf=True
            )
            self.title_matrix = self.title_vectorizer.fit_transform(titles)

            # 2. Text Vectorizer (Detailed methodology and findings)
            self.text_vectorizer = TfidfVectorizer(
                token_pattern=token_pat,
                stop_words=STOP_WORDS,
                ngram_range=(1, 2),
                sublinear_tf=True
            )
            self.text_matrix = self.text_vectorizer.fit_transform(full_texts)

            self._initialized = True
            logger.info(f"Built dual TF-IDF corpus index over {len(self.corpus)} documents.")
        except Exception as e:
            logger.error(f"Error building TF-IDF index: {e}")
            self._initialized = False

    def assess_evidence_relevance(self, claim: str, doc: Dict[str, Any], sim_score: float) -> Tuple[bool, str]:
        """
        Multi-signal Evidence Relevance Gate:
        Evaluates whether a candidate document genuinely addresses the claim.
        Enforces biomedical PICO alignment (Intervention/Exposure, Outcome) and disqualifies:
        1. Studies where the claim's primary exposure appears ONLY as an adjusted covariate or confounder.
        2. Studies whose titles test an incompatible primary exposure (e.g. coffee or sitting when claim is exercise).
        3. Studies investigating incompatible disease subtypes or different conditions.
        Returns (is_relevant: bool, reason: str).
        """
        claim_norm = normalize_biomedical_text(claim)
        title_norm = normalize_biomedical_text(doc.get("title", ""))
        
        abstract = doc.get("abstract", "")
        if isinstance(abstract, list):
            abstract = " ".join(abstract)
        doc_full = normalize_biomedical_text(f"{title_norm} {abstract}")

        # Signal 0: Covariate Adjustment & Exposure Incompatibility Gating
        # Scientific Rule: A confounding variable that is held constant or adjusted for
        # (e.g. "independent of exercise", "after adjusting for physical activity levels")
        # is NOT an active intervention or exposure evaluated by the study.
        doc_stripped = strip_covariate_clauses(doc_full)
        doc_title_stripped = strip_covariate_clauses(title_norm)
        claim_stripped = strip_covariate_clauses(claim_norm)

        # Core biomedical exposure/intervention families
        exposure_families = [
            {"physical_activity", "exercise", "aerobic_exercise", "physical_exertion"},
            {"sitting_time", "prolonged_sitting", "sitting", "sedentary"},
            {"coffee_consumption", "coffee", "caffeine", "decaffeinated"},
            {"statin", "statin_therapy", "statins"},
            {"vitamin_d"},
            {"vitamin_c"},
            {"vitamin_e"},
            {"dietary_salt", "salt"},
            {"alcohol", "moderate_alcohol"},
            {"bariatric_surgery"},
            {"intermittent_fasting"},
            {"omega_3"},
            {"mediterranean_diet"},
            {"ketogenic_diet"},
            {"second_hand_smoke"},
            {"air_pollution"},
            {"sleep_deprivation", "sleep_debt"},
            {"screen_time"},
            {"green_space"}
        ]

        for exp_family in exposure_families:
            claim_has_exp = any(term in claim_stripped for term in exp_family)
            if claim_has_exp:
                # 1. Did the candidate doc contain the exposure ONLY in a covariate/independence clause?
                doc_had_before = any(term in doc_full for term in exp_family)
                doc_has_in_stripped = any(term in doc_stripped for term in exp_family)

                if doc_had_before and not doc_has_in_stripped:
                    return False, f"Exposure {exp_family} appears only as a controlled covariate or independence condition in document, not as the primary study factor"

                # 2. Does the document title explicitly announce a DIFFERENT primary exposure family?
                for other_family in exposure_families:
                    if other_family != exp_family:
                        title_has_other = any(term in doc_title_stripped for term in other_family)
                        title_has_claim_exp = any(term in doc_title_stripped for term in exp_family)
                        if title_has_other and not title_has_claim_exp:
                            return False, f"Document title tests different primary exposure ({other_family}) rather than claim exposure ({exp_family})"

        # Signal 1: Check Incompatible Vitamins
        # If claim asks about Vitamin D, a document exclusively about Vitamin C or Vitamin E is NOT relevant.
        claim_vitamins = set(re.findall(r'\bvitamin_[a-z0-9]+\b', claim_norm))
        doc_vitamins = set(re.findall(r'\bvitamin_[a-z0-9]+\b', doc_full))
        if claim_vitamins:
            if doc_vitamins and not (claim_vitamins & doc_vitamins):
                return False, f"Incompatible vitamin: claim requires {claim_vitamins}, document discusses {doc_vitamins}"
            if not (claim_vitamins & doc_vitamins) and "vitamin" not in doc_full:
                return False, f"Missing required vitamin entity: {claim_vitamins}"

        # Signal 2: Check Incompatible Diabetes Subtypes
        claim_types = set(re.findall(r'\btype_[12]\b', claim_norm))
        doc_types = set(re.findall(r'\btype_[12]\b', doc_full))
        if claim_types and doc_types and not (claim_types & doc_types):
            return False, f"Incompatible disease subtype: claim requires {claim_types}, doc discusses {doc_types}"

        # Signal 3: Specific Outcome / Condition Check
        # Detect critical condition/outcome tokens in claim (e.g. hair, alopecia, cancer, depression)
        special_outcomes = {
            "hair", "hair_loss", "alopecia", "follicle", "cold", "common_cold",
            "prostate", "prostate_cancer", "insulin", "diabetes", "cardiovascular",
            "asthma", "sepsis", "mortality", "depression", "anxiety", "caries",
            "autism", "epilepsy", "mesothelioma", "fall", "sleep", "pneumonia",
            "hypertension", "obesity", "ileus", "parkinson"
        }
        claim_outcomes = {w for w in special_outcomes if w in claim_norm}
        if claim_outcomes:
            doc_has_outcome = any(o in doc_full for o in claim_outcomes)
            if not doc_has_outcome:
                return False, f"Missing required outcome entity: {claim_outcomes}"

        # Signal 3b: Specific Outcome Predicate Alignment (Incident Risk Prevention vs Secondary Biomarker)
        # Distinguish between primary incident disease prevention and secondary biomarker regulation in existing patients
        claim_has_risk_incidence = any(w in claim_norm for w in {"risk", "incidence", "developing", "prevention", "preventing", "onset"})
        claim_has_insulin_sensitivity = "insulin_sensitivity" in claim_norm or "insulin sensitivity" in claim.lower()

        doc_has_insulin_sensitivity = "insulin_sensitivity" in doc_full or "insulin sensitivity" in str(doc).lower()
        doc_has_risk_incidence = any(w in doc_full for w in {"risk", "incidence", "developing", "prevention", "preventing", "onset"})

        # If claim is about insulin sensitivity, doc must discuss insulin sensitivity
        if claim_has_insulin_sensitivity and not doc_has_insulin_sensitivity:
            return False, "Claim investigates insulin sensitivity but candidate document does not evaluate this biomarker"

        # If claim asserts incident disease risk reduction, doc must evaluate risk or incidence, not merely secondary biomarker regulation
        if claim_has_risk_incidence and not claim_has_insulin_sensitivity:
            if not doc_has_risk_incidence:
                return False, "Claim asserts disease incidence/risk reduction, but document evaluates secondary biomarker without measuring incident disease risk"

        # Signal 4: Content Words Coverage Ratio
        claim_words = extract_content_tokens(claim)
        if not claim_words:
            return False, "No meaningful content words in claim"

        matched_words = {w for w in claim_words if w in doc_full}
        overlap_ratio = len(matched_words) / len(claim_words)

        # Signal 5: Distinctive Domain Subject Terms Coverage
        key_domain_terms = extract_key_domain_terms(claim)
        if key_domain_terms:
            matched_domain_terms = [t for t in key_domain_terms if t in doc_full]
            domain_overlap = len(matched_domain_terms) / len(key_domain_terms)
            if domain_overlap < 0.34 or len(matched_domain_terms) == 0:
                return False, f"Missing key domain topic terms: expected {key_domain_terms}, found {matched_domain_terms}"

        # Gate Condition: Must have adequate lexical overlap and similarity
        if sim_score < self.min_similarity:
            return False, f"Similarity score {sim_score:.3f} below minimum threshold {self.min_similarity}"

        if overlap_ratio < self.min_overlap_ratio:
            return False, f"Content word overlap {overlap_ratio:.1%} below minimum {self.min_overlap_ratio:.1%}"

        return True, "Passed all evidence relevance gates"

    def retrieve(self, claim: str, k: Optional[int] = None) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieves top-k relevant scientific documents for a given claim.
        Applies multi-signal relevance gates. Returns [] if no genuinely relevant papers exist.
        """
        k = k or self.top_k
        if not self.corpus or not claim.strip():
            return []

        # Vector space scoring
        if self._initialized and self.title_vectorizer is not None and self.text_vectorizer is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity

                claim_norm = normalize_biomedical_text(claim)
                q_title = self.title_vectorizer.transform([claim_norm])
                q_text = self.text_vectorizer.transform([claim_norm])

                title_sims = cosine_similarity(q_title, self.title_matrix)[0]
                text_sims = cosine_similarity(q_text, self.text_matrix)[0]

                # Weighted similarity: Titles provide high-precision semantic matching
                combined_sims = 0.60 * title_sims + 0.40 * text_sims

                # Rank by similarity
                ranked_indices = np.argsort(combined_sims)[::-1]

                passed_candidates = []
                for idx in ranked_indices:
                    sim = float(combined_sims[idx])
                    if sim < 0.05:
                        break # Terminate early on negligible scores

                    doc = self.corpus[idx]
                    is_rel, reason = self.assess_evidence_relevance(claim, doc, sim)
                    if is_rel:
                        passed_candidates.append((doc, round(sim, 4)))
                        if len(passed_candidates) >= k:
                            break
                    else:
                        logger.debug(f"Document {doc.get('doc_id')} rejected: {reason}")

                return passed_candidates
            except Exception as e:
                logger.error(f"Error during TF-IDF retrieval: {e}")

        # Fallback lexical overlap if TF-IDF index is uninitialized
        claim_words = extract_content_tokens(claim)
        if not claim_words:
            return []

        scored = []
        for doc in self.corpus:
            doc_norm = normalize_biomedical_text(
                doc.get("title", "") + " " + " ".join(doc.get("abstract", []) if isinstance(doc.get("abstract"), list) else [str(doc.get("abstract", ""))])
            )
            matched = sum(1 for w in claim_words if w in doc_norm)
            overlap_ratio = matched / max(1, len(claim_words))
            
            is_rel, _ = self.assess_evidence_relevance(claim, doc, overlap_ratio)
            if is_rel and overlap_ratio >= self.min_overlap_ratio:
                scored.append((doc, round(float(overlap_ratio), 4)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]


# Backward-compatible alias
FaissRetrievalEngine = CorpusRetrievalEngine
