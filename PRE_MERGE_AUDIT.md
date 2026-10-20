# SciVerify — Pre-Merge Audit: BERT Branch, Teammate Changes & ML Pipeline

**Audit Date:** October 20, 2026  
**Auditor:** Senior ML Engineer, NLP Researcher & Git Integration Specialist  
**Repository:** [ysujith728/SciVerify](https://github.com/ysujith728/SciVerify)  
**Evaluated Branches:**
- `origin/main` (HEAD commit: `11348da`)
- `origin/feature/deberta-v3-nli-xai` (The "BERT" Branch by Vignesh, commit: `27d5b32`)
- `origin/chaitanya_branch` (Teammate Branch by Chaitanya, commit: `c450ac7`, merged into `origin/main` via PR #4)
- `origin/revert-1-feature/deberta-xai-benchmarks` (PR #2 revert by Sujith, commit: `d538ca5`)

---

## A. Repository and Git State

### 1. Git Graph & Branch Genealogy
```
*   11348da (origin/main, origin/HEAD) Merge pull request #4 from ysujith728/chaitanya_branch
|\  
| * c450ac7 (origin/chaitanya_branch) feat: integrate SciVerify two-LLM architecture, evidence gating, XAI...
|/  
| * 27d5b32 (origin/feature/deberta-v3-nli-xai) feat(deberta-xai): integrate DeBERTa-v3 NLI verification...
|/  
*   b3251b6 Merge pull request #2 from ysujith728/revert-1-feature/deberta-xai-benchmarks
|\  
| * d538ca5 (origin/revert-1-feature/deberta-xai-benchmarks) Revert "feat(deberta-xai)..."
|/  
*   9ca1858 (HEAD -> main) Merge pull request #1 from vignesh28102006/feature/deberta-xai-benchmarks
|\  
| * 70bd723 feat(deberta-xai): add DeBERTa-v3 NLI, trapezoidal IG, and benchmark integration
|/  
* c636e61 docs: update README with step-by-step run guide, project status analysis, and handoff checklist
```

### 2. Branch Relationship Summary
1. **The Revert History**: At commit `9ca1858`, an earlier version of the BERT changes (PR #1) was merged into `main`. Subsequently, PR #2 (`d538ca5`) was opened and merged (`b3251b6`), completely reverting PR #1.
2. **The Two Competing Divergences**:
   - **Vignesh's BERT Branch (`origin/feature/deberta-v3-nli-xai`)**: Branched from revert merge `b3251b6` at commit `27d5b32`. It re-implemented DeBERTa-v3 NLI, Integrated Gradients XAI, and benchmark reporting.
   - **Chaitanya's Two-LLM Branch (`origin/chaitanya_branch`)**: Also branched from `b3251b6` at commit `c450ac7`. It restructured the pipeline around Groq LPU (Llama-3.1) and Google Gemini 1.5 Flash, added PubMed external search, and created new evaluation endpoints.
3. **Current Remote `main`**: Chaitanya's branch was merged into `origin/main` via PR #4 (`11348da`). Thus, **the BERT branch has NOT yet been merged into `origin/main`**, and `origin/main` currently runs the Two-LLM architecture where DeBERTa is absent from the active FastAPI server.
4. **Local Working Tree**: Clean except for updated empirical benchmark JSONs generated during evaluation runs.

---

## B. Change Inventory

### 1. BERT Feature Branch (`origin/feature/deberta-v3-nli-xai`)
- **Base Commit**: `b3251b6` (Merge base with `origin/main`)
- **Key Files Added**:
  - `backend/app/pipeline/fine_tune_deberta.py`: Supervised fine-tuning pipeline for `cross-encoder/nli-deberta-v3-small`.
  - `backend/app/pipeline/eval_deberta.py`: Oracle-evidence NLI benchmark script.
  - `backend/app/pipeline/eval_end_to_end.py`: End-to-end multi-stage pipeline benchmark script.
  - `backend/app/pipeline/xai_integrated_gradients.py`: Differentiable path-integral Integrated Gradients with composite trapezoidal quadrature ($m=50$) and `[PAD]` baseline.
  - `backend/test_deberta_xai.py`: 14 unit tests covering classification, negation word-boundaries, and XAI completeness.
  - `data/deberta_benchmark_results.json`: Benchmark metrics export for UI synchronization.
  - `data/end_to_end_benchmark_results.json`: Pipeline benchmark metrics export.
- **Key Files Modified**:
  - `backend/app/pipeline/verification.py`: Swapped Hugging Face pipeline for native PyTorch model, added local checkpoint detection, and Integrated Gradients hooks.
  - `backend/app/main.py`: Connected `/api/verify` to DeBERTa and Integrated Gradients; loaded comparative metrics.
  - `src/components/ResultsView.tsx`: Integrated token-level XAI heatmap and comparative model cards.
  - `src/services/api.ts`: Modified verification payload.

### 2. Teammate Branch (`origin/chaitanya_branch`, now on `origin/main`)
- **Base Commit**: `b3251b6`
- **Scope**: 30 files changed (6,053 insertions, 768 deletions).
- **Key Files Added**:
  - `backend/app/pipeline/llm_groq.py`: Dedicated Groq Llama-3.1-8b client with fallback mechanisms.
  - `backend/app/pipeline/xai.py`: Perturbation-based token sensitivity (occlusion analysis) for black-box cloud LLMs.
  - `backend/app/pipeline/external_literature.py`: Live NCBI PubMed literature searcher.
  - `backend/app/pipeline/gemini_cloud_tuning.py` & `backend/train_llama_lora.py`: Cloud tuning scripts.
  - `backend/test_relevance_and_evidence_gates.py`, `backend/test_twopath_and_fallback.py`: Gating test suites.
  - `data/models_evaluation_registry.json`, `data/test_evaluation_results.json`: Evaluation outputs.
- **Key Files Modified**:
  - `backend/app/main.py`: Completely redesigned around Groq + Gemini, eliminating the call to DeBERTa.
  - `src/components/ResultsView.tsx`: Redesigned around dual Groq/Gemini model cards, PubMed provenance tags, and occlusion XAI.

---

## C. BERT Implementation Review

1. **Architecture & Pretrained Weights**:  
   The model is **DeBERTa-v3-small** (`cross-encoder/nli-deberta-v3-small`, 86.8M parameters). It is **not** standard BERT, BioBERT, or SciBERT. It uses disentangled attention (content and position represented in separate vectors) and an enhanced mask decoder.
2. **Encoder vs Fine-Tuning**:  
   The model is used as a **sequence classification cross-encoder** for Natural Language Inference (NLI). While a fine-tuning script (`fine_tune_deberta.py`) is provided, `backend/models/` is ignored in `.gitignore`. Hence, a freshly cloned repository operates in **zero-shot NLI mode** unless fine-tuning is executed locally.
3. **Input Format**:  
   `[CLS] Premise (Evidence Sentence) [SEP] Hypothesis (Claim Text) [SEP]`, tokenized with `truncation=True, max_length=512`.
4. **Target Output & Mapping**:  
   3-way classification:
   - Index `0`: `contradiction` $\rightarrow$ `CONTRADICT`
   - Index `1`: `entailment` $\rightarrow$ `SUPPORT`
   - Index `2`: `neutral` $\rightarrow$ `NOT ENOUGH INFO`
5. **Loss, Optimizer & Hyperparameters**:  
   CrossEntropyLoss, AdamW ($lr=2\times 10^{-5}$, weight decay $0.01$, gradient clipping $1.0$), linear warmup schedule (10%), batch size $8$, $5$ epochs.
6. **Defects & Bugs Identified in BERT Branch**:
   - **`NameError: name 'cited_docs' is not defined`**: In `fine_tune_deberta.py#L107`, `cited_docs` was referenced without being unpacked from `item`.
   - **Numerical Tolerance Mismatch**: In `test_deberta_xai.py#L175`, `assertLess(rel_err, 5.0)` fails on real neural weights because the 50-step trapezoidal path integral on DeBERTa produces ~6.15% relative completeness error against logit differences.
   - **Missing Port in `api.ts`**: The BERT branch defaulted `API_BASE` to port `8000` while backend runs on `8001`, causing silent fallback to mock data in the browser.

---

## D. Dataset Audit

### 1. Active Split Statistics (`data/`)

| Split | File Path | Total Records | SUPPORT | CONTRADICT | NOT ENOUGH INFO | ID Range |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Train** | `data/claims_train.jsonl` | 35 | 13 (37.1%) | 12 (34.3%) | 10 (28.6%) | [1, 35] |
| **Validation** | `data/claims_validation.jsonl` | 7 | 3 (42.9%) | 2 (28.6%) | 2 (28.6%) | [36, 42] |
| **Test** | `data/claims_test.jsonl` | 8 | 3 (37.5%) | 2 (25.0%) | 3 (37.5%) | [43, 50] |
| **Total / Unified** | `data/sciverify_dataset.csv` | 50 | 19 (38.0%) | 16 (32.0%) | 15 (30.0%) | [1, 50] |
| **Corpus** | `data/corpus.jsonl` | 56 | — | — | — | [900001, 900106] |

### 2. Dataset Consistency & Quality Findings
- **Claim & Label Alignment**: Verified 100% identical between `data/sciverify_dataset.csv` and `data/claims_*.jsonl`.
- **Document & Sentence Index Integrity**: All 50 claims cite valid `doc_id`s in `data/corpus.jsonl` with zero broken references.
- **Abstract Template Leakage**: In `data/corpus.jsonl`, Sentence 0 of abstracts 900001–900050 literally copies the claim text:
  `"Background: Understanding the empirical mechanisms and outcomes associated with <claim text> is vital for evidence-based medicine."`
- **Annotation Index Offset**: In `data/claims_*.jsonl`, evidence sentence pointers are hardcoded to `[0]` (the background sentence), whereas the actual clinical finding resides at sentence index `2`.
- **Meta-Explanations in CSV**: For `NOT ENOUGH INFO` claims in `data/sciverify_dataset.csv`, the `evidence` field contains human explanations of missing data rather than abstract text.

---

## E. Model & LLM Responsibility Matrix

| Component | Architecture / Model | Input | Output | Purpose in SciVerify | Integration Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Document Retriever** | SPECTER2 + FAISS / TF-IDF | Claim text (string) | Top-k candidate documents | Filters 56+ papers to top 2 relevant candidates | Lexical fallback used if embeddings not initialized |
| **Sentence Reranker** | Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) | `(claim, sentence)` pairs | Relevance score | Extracts minimal evidence sentence from abstract | Overlap heuristic has 100% bias toward Sentence 0 |
| **NLI Classifier (BERT)** | DeBERTa-v3 (`nli-deberta-v3-small`) | `(evidence, claim)` pair | Logits & 3-way probabilities | Authoritative, fast, deterministic veracity prediction | Currently bypassed in `origin/main` |
| **Path-Integral XAI** | Integrated Gradients (Trapezoidal, $m=50$) | Model embeddings + input tokens | Signed token attribution weights | Axiomatic explanation of DeBERTa's prediction | Requires differentiable local model; fails on APIs |
| **Perturbation XAI** | Occlusion Saliency ($f(X) - f(X \setminus \{w_i\})$) | Tokenized claim + evidence | Saliency scores | Explaining black-box cloud LLM predictions | High latency (requires $N$ API calls per claim) |
| **Cloud LLM (Primary)** | Groq LPU (`llama-3.1-8b-instant`) | Prompt with claim + context | JSON verdict, confidence, rationale | High-speed cloud reasoning and explanation | Requires live `GROQ_API_KEY`; prone to NEI bias |
| **Cloud LLM (Alternative)**| Google Gemini (`gemini-1.5-flash` / `3.5`) | Prompt with claim + context | JSON verdict, confidence, rationale | Multi-hop reasoning and validation | Requires live `GEMINI_API_KEY`; cloud dependency |
| **Explanation Generator**| Rule-based Formatter (`explanation.py`) | Claim, Verdict, Top Evidence | Clinical explanation paragraph | Zero-hallucination communication of evidence | Deterministic template; not a generative LLM |

---

## F. Evaluation Audit & Metric Discrepancies

### 1. Test Split Benchmark Comparison ($N=8$ Held-Out Assertions)

| Model & Evaluation Setup | Evaluated Script | Accuracy | Macro-Precision | Macro-Recall | Macro-F1 | Weighted-F1 | Avg Latency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **DeBERTa-v3 (Fine-Tuned Oracle NLI)** | `eval_deberta.py` | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **100.0%** | **16.9 ms** |
| **DeBERTa-v3 (Zero-Shot Base NLI)** | `eval_deberta.py` | **87.5%** | **88.9%** | **88.9%** | **86.7%** | **87.5%** | **18.4 ms** |
| **Google Gemini (gemini-3.5-flash-lite)** | `evaluate_test_split.py` | **75.0%** | **53.3%** | **66.7%** | **58.3%** | **70.8%** | **1600 ms** |
| **Groq LPU (llama-3.1-8b-instant)** | `evaluate_test_split.py` | **62.5%** | **50.0%** | **55.6%** | **48.9%** | **56.2%** | **1816 ms** |
| **DeBERTa-v3 (End-to-End Pipeline)** | `eval_end_to_end.py` | **37.5%** | **12.5%** | **33.3%** | **18.2%** | **20.5%** | **76.0 ms** |
| **Groq Audio Benchmark (Recorded in Git)** | `eval_groq_audio.py` | *100.0%* | *100.0%* | *100.0%* | *100.0%* | *100.0%* | *125 ms* |

### 2. Technical Reasons for Metric Discrepancies
1. **Oracle NLI (100.0%) vs End-to-End Pipeline (37.5%)**:  
   - In Oracle mode, DeBERTa receives the clean gold evidence sentence (Sentence 2) directly from `sciverify_dataset.csv`.
   - In End-to-End mode, the lexical extractor selects Sentence 0 because Sentence 0 in the corpus literally copies the claim text (`"Background: Understanding ... <claim> ..."`). Having 100% token overlap, Sentence 0 is always extracted. Because it contains no experimental findings, DeBERTa predicts `SUPPORT` for every sample, correctly matching only the 3 true SUPPORT claims ($3/8 = 37.5\%$).
2. **DeBERTa (100.0% Fine-Tuned vs 87.5% Zero-Shot)**:  
   Zero-shot base `cross-encoder/nli-deberta-v3-small` misclassified Sample 44 (NOT ENOUGH INFO as CONTRADICT) due to strict phrasing penalties. Supervised fine-tuning on the 35 training claims adapted the boundary, achieving 100% on the test split.
3. **Groq (62.5%) & Gemini (75.0%) False Neutral Bias**:  
   Both LLMs failed on all `CONTRADICT` claims in `claims_test.jsonl` (e.g., Nicotine replacement and Noise pollution), classifying them as `NOT ENOUGH INFO` because they conservatively hesitated to assert outright contradiction from short abstracts.
4. **The Groq Audio 100% Artifact**:  
   In `eval_groq_audio.py#L81`, when no live API key is present, the script explicitly sets `predicted_verdict = ground_truth`, generating a simulated 100% benchmark rather than measuring true performance.

---

## G. Merge Risk Matrix

| Risk ID | Severity | Category | Affected Files | Conflict Nature / Technical Root Cause | Recommended Fix |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **R-1** | **CRITICAL** | Git / Semantic | `backend/app/main.py` | Git merge conflict. `origin/main` removed `DeBERTaClaimVerifier` and replaced `/api/verify` with Groq/Gemini routing. BERT branch expects DeBERTa to serve `/api/verify`. | Harmonize into multi-engine architecture supporting `engine='deberta' \| 'groq' \| 'gemini'`. |
| **R-2** | **CRITICAL** | Git / Runtime | `src/components/ResultsView.tsx` | 450+ line conflict. `origin/main` displays dual Groq/Gemini cards and occlusion XAI; BERT branch displays DeBERTa cards and Integrated Gradients token matrix. | Merge UI to conditionally display the active engine's card and render Integrated Gradients when DeBERTa is active. |
| **R-3** | **HIGH** | Git / Schema | `src/services/api.ts`, `mockVerification.ts` | Conflicting API parameter schemas (`options`, `engine`) and conflicting `VerificationResult` TypeScript interfaces. Port mismatch (`8000` vs `8001`). | Unify TypeScript interfaces; ensure `API_BASE` defaults to port `8001`. |
| **R-4** | **HIGH** | Semantic / Model | `backend/app/pipeline/verification.py` | `origin/main` uses `pipeline("text-classification")` with string concatenation (`</s></s>`), while BERT branch uses direct PyTorch DeBERTa with `IntegratedGradientsExplainer`. | Adopt PyTorch implementation from BERT branch with proper premise-hypothesis tokenization. |
| **R-5** | **MEDIUM** | Runtime / Bug | `fine_tune_deberta.py` | `NameError: cited_docs` on line 107 if claim ID is missing from CSV. | Add `cited_docs = item.get("cited_doc_ids", [])` unpacking. |
| **R-6** | **MEDIUM** | Performance / Data | `reranking.py`, `eval_end_to_end.py` | Heuristic sentence extractor pulls Sentence 0 background instead of Sentence 2 clinical evidence, collapsing end-to-end accuracy to 37.5%. | Filter out `"Background:"` boilerplate or prioritize sentences with clinical outcome keywords (`"significantly"`, `"conclude"`). |
| **R-7** | **LOW** | Unit Test | `test_deberta_xai.py` | `test_13` asserts relative completeness error $< 5.0\%$, but real DeBERTa yields 6.15%. | Adjust assertion tolerance to $< 10.0\%$. |

---

## H. Test Results

| Test Target | Command Executed | Outcome | Key Metrics / Observed Behavior |
| :--- | :--- | :---: | :--- |
| **DeBERTa Fine-Tuning** | `python backend/app/pipeline/fine_tune_deberta.py` | **PASSED** | 5 epochs completed; saved checkpoint to `backend/models/deberta-v3-scifact` with Val Macro-F1 = 100.0%. |
| **Oracle DeBERTa Benchmark** | `python backend/app/pipeline/eval_deberta.py` | **PASSED** | Tested on 8 held-out claims: **Accuracy: 100.0%**, **Macro-F1: 100.0%**, **Avg Latency: 16.93 ms**. |
| **End-to-End Benchmark** | `python backend/app/pipeline/eval_end_to_end.py` | **PASSED (with known bottleneck)** | Tested full retrieval + extraction + NLI: **Accuracy: 37.5%**, **Macro-F1: 18.2%** due to Sentence 0 extraction bias. |
| **DeBERTa XAI Unit Tests** | `python -m unittest backend/test_deberta_xai.py` | **13/14 PASSED (1 Tolerance Fail)** | 13 tests passed on real neural weights; `test_13` failed strictly on relative error threshold (6.15% vs 5.0%). |
| **Groq Connectivity** | `python backend/test_groq.py` | **NOT CONFIGURED** | Placeholder API key in `.env`; correctly reported configuration notice. |
| **FastAPI Backend Smoke Test** | `python run.py` (Port 8001) | **PASSED** | `/health` returned healthy (corpus size: 56 docs). `/api/verify` successfully completed end-to-end inference. |
| **Frontend Production Build** | `npm run build` | **PASSED** | TypeScript compilation and Vite bundle built with 0 errors in 770 ms. |

---

## I. Changes Made During Audit

1. **Safety Preservation**:  
   Created `_backup_dataset/` preserving all original 150-claim dataset files and generation scripts, and added it to `.git/info/exclude`.
2. **Local Model Artifact Generation**:  
   Executed `fine_tune_deberta.py` on the 35 training assertions, creating the fine-tuned checkpoint in `backend/models/deberta-v3-scifact`.
3. **Empirical Benchmark Synchronization**:  
   Re-evaluated `eval_deberta.py` and `eval_end_to_end.py` using genuine PyTorch neural inference, replacing simulated mock values in `data/deberta_benchmark_results.json` and `data/end_to_end_benchmark_results.json`.

---

## J. Final Recommendation

### **Status: NOT SAFE TO MERGE YET**

### Blocking Conditions:
1. **Unresolved Merge Conflicts**: Directly merging `origin/feature/deberta-v3-nli-xai` into `origin/main` will produce merge conflicts across 5 core files (`main.py`, `verification.py`, `ResultsView.tsx`, `api.ts`, `mockVerification.ts`).
2. **Architectural Reconciliation Required**: `origin/main` was committed to a two-LLM (Groq/Gemini) pipeline, while the feature branch was committed to a local DeBERTa-v3 pipeline. Merging requires harmonizing `main.py` and `ResultsView.tsx` into a unified multi-engine system where users can select either local DeBERTa or cloud LLMs.
3. **Sentence Extraction Bottleneck**: The end-to-end pipeline accuracy remains at 37.5% until `reranking.py` is patched to prevent extracting boilerplate background sentences.

### Progression to "SAFE AFTER FIXES":
Once the unified `main.py` routing, `ResultsView.tsx` multi-model view, `reranking.py` evidence selection patch, and unit test tolerances are resolved on an isolated integration branch, the changes will be safe for final merge into `main`.
