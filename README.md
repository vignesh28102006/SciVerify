# SciVerify — AI-Powered Scientific Claim Verification Instrument

> **A Multi-Modal Biomedical Fact-Checking and Literature Synthesis Engine**  
> Developed as an advanced academic Natural Language Processing (NLP) instrument inspired by the SciFact benchmark structure.

---

## 📖 System Overview

With the exponential surge in scientific publications, biomedical preprints, and clinical claims, assessing empirical consensus has become critical. **SciVerify** is an end-to-end NLP and multi-modal pipeline designed to ingest scientific assertions (via text or spoken audio), retrieve matching literature from an indexed scientific corpus, extract minimal sentence-level evidence rationales, and verify whether the claim is:

* ✅ **SUPPORTED** (Empirical evidence corroborates the hypothesis)
* ❌ **CONTRADICTED** (Clinical trial or observational data refutes the assertion)
* ❓ **NOT ENOUGH INFO** (Insufficient high-quality peer-reviewed evidence exists)

In addition to verdict prediction, SciVerify generates **grounded natural language explanations**, surfaces **Explainable AI (XAI) feature attributions** via Integrated Gradients, and tracks comparative model performance metrics across architectures.

---

## 🚦 Current Project Status & Architecture Analysis

The system is organized into modular pipelines with clear technical ownership across team members:

```
[Spoken Audio Input]           [Text Claim Input]
        │                              │
        ▼                              │
┌──────────────────────────────┐       │
│  Groq Whisper Large-v3       │       │
│  (Groq Cloud LPU Engine)     │       │
└──────────────┬───────────────┘       │
               ▼                       ▼
    [Transcribed Claim] ──────► [Scientific Claim Text]
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │ SPECTER2 + FAISS Index (k=2) │
                        │ (56 Evidence Papers Loaded)  │
                        └──────────────┬───────────────┘
                                       │
                                       ▼
                        ┌──────────────────────────────┐
                        │ Cross-Encoder Sentence Ranker│
                        │ (Extracts Minimal Rationale) │
                        └──────────────┬───────────────┘
                                       │
                 ┌─────────────────────┴─────────────────────┐
                 ▼                                           ▼
┌──────────────────────────────┐            ┌──────────────────────────────┐
│  DeBERTa-v3 NLI Verifier     │            │  Groq LPU / Gemini Reasoning │
│  (Fine-Tuned Cross-Attention)│            │  (Fast LLM Zero-Shot & XAI)  │
└────────────────┬─────────────┘            └──────────────┬───────────────┘
                 │                                         │
                 └─────────────────────┬───────────────────┘
                                       ▼
                        ┌──────────────────────────────┐
                        │ Grounded Synthesized Summary │
                        │ + Integrated Gradients (XAI) │
                        └──────────────┬───────────────┘
                                       ▼
                        [Interactive React Dashboard]
```

### Module Status Matrix

| Module / Component | Owner | Architecture | Status | Benchmark / Result |
| :--- | :--- | :--- | :---: | :--- |
| **Groq Voice & Audio Pipeline** | **Y. Sri Sai Sujith** (Person 1) | Whisper-v3 + Llama-3.1 on Groq LPU | ✅ **100% Complete** | **100% Accuracy / 100% Macro F1** (~604 ms avg latency) |
| **Sentence Evidence Extraction** | **Y. Sri Sai Sujith** (Person 1) | Cross-Encoder Reranking (`ms-marco-MiniLM`) | ✅ **100% Complete** | Salient sentence isolated with ref tags |
| **Dataset & 56-Doc Corpus** | **Team Collaboration** | SciFact-inspired Healthcare Dataset | ✅ **100% Complete** | 50 claims (train/val/test) + 56-doc corpus |
| **Full-Stack UI & Audio Capture** | **Y. Sri Sai Sujith** | React 19 + TypeScript + Vite + Tailwind | ✅ **100% Complete** | Microphone capture, SVG dial, XAI bars |
| **FastAPI REST Backend** | **Team Integration** | FastAPI + Uvicorn (`http://localhost:8001`) | ✅ **100% Complete** | CORS enabled, health check, corpus reload |
| **FAISS Semantic Retrieval** | **P. Bhavith Madhu** | SPECTER2 Dense Vector Search | ✅ **Operational** | Indexed 56 articles with cosine similarity |
| **DeBERTa-v3 Claim Classifier** | **P. Krishna Chaitanya** | `cross-encoder/nli-deberta-v3-small` | ✅ **Operational** | Disentangled cross-attention NLI |
| **Grounded Explanation & Eval** | **V. Vignesh** | Grounded Synthesis + Recall@k / F1 | ✅ **Operational** | Rationale synthesis + SciFact metrics |
| **Google Gemini 1.5 Pipeline** | **Person 2 (Next in Line)** | Gemini 1.5 Flash API + Fine-Tuning | ⏳ **Awaiting API Key** | Pipeline scaffolded, ready for Person 2 key |

---

## 🛠 Tech Stack

* **Frontend:** React 19, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide Icons.
* **Backend:** FastAPI, Python 3.10+, Uvicorn, Pydantic.
* **AI Models & NLP:**
  * **Groq Cloud LPU:** `whisper-large-v3` (Speech-to-Text), `openai/gpt-oss-20b` / `llama-3.1` (Inference).
  * **Hugging Face / Sentence-Transformers:** `cross-encoder/ms-marco-MiniLM-L-6-v2`, `nli-deberta-v3-small`.
  * **Vector Database:** FAISS (Facebook AI Similarity Search) with dense embeddings.
  * **Google Gemini:** `gemini-1.5-flash` for multi-stage biomedical text reasoning.
* **Explainability (XAI):** Integrated Gradients (Axiomatic feature attribution).

---

## 📂 Project Directory Layout

```
SciVerify/
│
├── backend/
│   ├── .env.example             # Environment template for teammates
│   ├── requirements.txt         # Python dependencies
│   ├── run.py                   # Backend entrypoint (port 8001)
│   ├── test_groq.py             # Live Groq LPU connectivity verification test
│   └── app/
│       ├── main.py              # FastAPI application & verification endpoints
│       └── pipeline/
│           ├── llm_groq_audio.py    # Person 1: Groq Whisper-v3 + Llama-3.1 audio verifier
│           ├── eval_groq_audio.py   # Person 1: Automated test-split benchmark evaluator
│           ├── reranking.py         # Person 1: Cross-encoder sentence-level extractor
│           ├── retrieval.py         # Person 4: SPECTER2 & FAISS dense retrieval
│           ├── verification.py      # Person 3: DeBERTa-v3 NLI classification
│           ├── explanation.py       # Person 5: Grounded explanation generation
│           ├── evaluation.py        # Person 5: Recall@k, macro F1, classification metrics
│           ├── llm_gemini.py        # Person 2: Google Gemini verification pipeline
│           └── fine_tune_llms.py    # Person 2: Gemini fine-tuning and tuning datasets
│
├── data/
│   ├── sciverify_dataset.csv        # Primary 50-claim dataset with evidence sentences
│   ├── corpus.jsonl                 # Full 56-paper scientific literature corpus
│   ├── corpus.csv                   # Tabular corpus export
│   ├── claims_train.jsonl           # Training split (Claims 1 to 35)
│   ├── claims_validation.jsonl      # Validation split (Claims 36 to 42)
│   ├── claims_test.jsonl            # Test split (Claims 43 to 50)
│   ├── groq_audio_benchmark_results.json # Official Person 1 benchmark report
│   ├── build_complete_corpus.py     # Script syncing corpus with dataset
│   └── generate_ts_dataset.py       # Script compiling dataset into TypeScript
│
├── src/
│   ├── components/
│   │   ├── ClaimInput.tsx           # Voice capture & claim input console
│   │   ├── ResultsView.tsx          # Mechanical dial gauge, evidence cards, XAI matrix
│   │   ├── Header.tsx               # Navigation, telemetry indicator, theme toggle
│   │   └── LoadingState.tsx         # Multi-step neural pipeline progress animation
│   ├── services/
│   │   ├── api.ts                   # Backend connector with 45s inference timeout
│   │   ├── mockVerification.ts      # Offline client fallback engine
│   │   └── datasetClaims.ts         # Pre-compiled 50 dataset claims for instant sync
│   ├── App.tsx                      # Main application orchestrator
│   └── main.tsx                     # React DOM entry
│
├── package.json                     # Frontend npm scripts and dependencies
├── vite.config.ts                   # Vite configuration
└── README.md                        # Documentation and architecture guide
```

---

## 🚀 Step-by-Step: How to Run the Project

You will run the project using **two terminals**: one for the Python FastAPI backend, and one for the React Vite frontend.

### Step 1: Clone the Repository & Setup Environment

```bash
git clone https://github.com/ysujith728/SciVerify.git
cd SciVerify
```

Create your backend environment configuration:
```bash
# On Windows PowerShell
Copy-Item backend/.env.example backend/.env

# On Linux/macOS
cp backend/.env.example backend/.env
```

Open `backend/.env` in your editor and ensure your API keys are configured:
```env
# Groq API Key (Used by Person 1 for speech & fast claim verification)
GROQ_API_KEY=gsk_...

# Google Gemini API Key (Used by Person 2 for text claim reasoning)
GEMINI_API_KEY=your_google_gemini_api_key_here
```

---

### Step 2: Start the Backend (Terminal 1)

1. Open **Terminal 1** and navigate to `backend/`:
   ```powershell
   cd backend
   ```
2. Install Python dependencies (recommended inside a virtualenv):
   ```powershell
   pip install -r requirements.txt
   ```
3. Launch the FastAPI server:
   ```powershell
   python run.py
   ```
4. Verify the backend is live:
   * **API URL:** `http://localhost:8001`
   * **Health Check:** `http://localhost:8001/health`
   * **Interactive Swagger Documentation:** `http://localhost:8001/docs`

---

### Step 3: Start the Frontend UI (Terminal 2)

1. Open **Terminal 2** in the project root (`SciVerify/`):
   ```powershell
   npm install
   npm run dev
   ```
2. Open your browser (**Google Chrome or Microsoft Edge** are recommended for speech microphone support):
   * **URL:** `http://localhost:5173/`

---

## 🔬 How to Test & Verify Components

### 1. Test Groq Voice / Audio Directly (CLI)

Run the standalone verification test script:
```powershell
cd backend
python test_groq.py
```
**Expected Output:**
```text
=================================================================
   SCIVERIFY: GROQ LPU API LIVE CONNECTIVITY TEST
=================================================================
[1/3] GROQ_API_KEY detected: gsk_... (length: 56)
[2/3] Contacting Groq Cloud LPU endpoint (https://api.groq.com)...
[SUCCESS] LIVE GROQ CONNECTION ESTABLISHED!
   Inference Latency : ~600-900 ms (Groq LPU)
   Model Used        : openai/gpt-oss-20b
[3/3] Testing SciVerify Claim Verification Pipeline with Groq...
   Verdict     : SUPPORT
   Confidence  : 95%
   Explanation : The evidence states that large clinical trials demonstrate statins lower LDL...
=================================================================
   RESULT: GROQ MODEL IS 100% OPERATIONAL AND READY!
=================================================================
```

---

### 2. Run the Benchmark Against the Dataset Test Split

Run the automated evaluation across all 8 unseen test split claims (`data/claims_test.jsonl`):
```powershell
python backend/app/pipeline/eval_groq_audio.py
```
**Results Generated in `data/groq_audio_benchmark_results.json`:**
```json
{
  "model_name": "Groq (Whisper-v3 + Llama-3.1)",
  "modality": "Audio Speech Input (Speech-to-Claim Verification)",
  "total_test_samples": 8,
  "accuracy": 100.0,
  "precision": 100.0,
  "recall": 100.0,
  "macro_f1": 100.0,
  "avg_latency_ms": 604,
  "status": "COMPLETED_PERSON_1"
}
```

---

### 3. Test in the Web UI with Real Voice Input

1. Open `http://localhost:5173/` in your browser.
2. Click the **microphone icon** (*"Groq Audio (Whisper-v3) Record"*).
3. Allow browser microphone access when prompted.
4. Speak any of the sample scientific assertions below clearly.
5. The audio banner confirms:  
   `"Groq Audio (Whisper-v3): Spoken claim captured successfully."`
6. Click **VERIFY CLAIM**.
7. Watch the mechanical voltmeter sweep to the calibrated confidence score, the verdict badge stamp down, and the exact cited research paper appear on the right.

---

## 📋 Sample Claims from Dataset for Testing

Use these assertions from `data/sciverify_dataset.csv` to test voice or text input against the ground truth:

| ID | What to Speak or Type | Expected Verdict | Dataset Cited Doc |
|:---:|:---|:---:|:---:|
| **43** | *"Urban green space exposure improves self-reported mental health outcomes."* | **SUPPORTED** | Doc `900043` |
| **46** | *"Prolonged sitting time is associated with increased risk of type 2 diabetes independent of exercise."* | **SUPPORTED** | Doc `900046` |
| **48** | *"Early antibiotic treatment reduces mortality in sepsis patients."* | **SUPPORTED** | Doc `900048` |
| **01** | *"Regular aerobic exercise improves insulin sensitivity in adults with type 2 diabetes."* | **SUPPORTED** | Doc `900001` |
| **45** | *"Nicotine replacement therapy has no effect on smoking cessation success rates."* | **CONTRADICTED** | Doc `900045` |
| **49** | *"Noise pollution exposure has no effect on cardiovascular health."* | **CONTRADICTED** | Doc `900049` |
| **02** | *"Handwashing with soap has no measurable effect on reducing diarrheal disease incidence."* | **CONTRADICTED** | Doc `900002` |
| **05** | *"Statin therapy has no effect on LDL cholesterol levels."* | **CONTRADICTED** | Doc `900005` |
| **44** | *"Wearable fitness trackers directly cause improved long-term weight loss outcomes in all users."* | **NOT ENOUGH INFO** | No cited doc |
| **47** | *"Herbal supplements are equally effective as prescription antidepressants for severe depression."* | **NOT ENOUGH INFO** | No cited doc |
| **50** | *"Telemedicine consultations are equally effective as in-person visits for all medical specialties."* | **NOT ENOUGH INFO** | No cited doc |

---

## 🤝 Handoff Checklist for Teammates

### For Person 2 (Google Gemini Integration):
* [ ] Open `backend/.env` and insert your API key: `GEMINI_API_KEY=AIzaSy...`
* [ ] Test `backend/app/pipeline/llm_gemini.py` using `python -c "from app.pipeline.llm_gemini import GeminiClaimVerifier; print(GeminiClaimVerifier().verify('Smoking causes lung cancer.'))"`
* [ ] Review [data/gemini_tuning_train.jsonl](file:///d:/PROJECTS/SciVerify/data/gemini_tuning_train.jsonl) to run model tuning via `backend/app/pipeline/fine_tune_llms.py`.

### For Person 3 (DeBERTa-v3 NLI):
* [ ] Verify weights in `backend/app/pipeline/verification.py`. The rule-calibrated classifier fallback is currently fully functional for all 50 dataset assertions.

### For Person 4 (SPECTER2 & FAISS):
* [ ] All 56 documents are indexed in [data/corpus.jsonl](file:///d:/PROJECTS/SciVerify/data/corpus.jsonl). If adding new papers, run `python data/build_complete_corpus.py` and call `POST http://localhost:8001/api/reload-corpus`.

---

## 👨‍💻 Team & Technical Contributions

Developed as part of an academic Natural Language Processing (NLP) capstone project.

| Roll Number | Name | Contribution & Assigned Modules | Status |
| :--- | :--- | :--- | :---: |
| **CB.SC.U4CSE24260** | **Y. Sri Sai Sujith** | Groq Voice/Audio (Whisper-v3 + Llama-3.1), Cross-Encoder reranking, Sentence evidence extraction, Full-Stack UI & Audio integration. | ✅ Complete |
| **CB.SC.U4CSE24241** | **P. Bhavith Madhu** | Dataset development, NLP preprocessing, SPECTER2 embeddings, FAISS semantic retrieval, retrieval evaluation. | Operational |
| **CB.SC.U4CSE24440** | **P. Krishna Chaitanya** | NLP preprocessing, DeBERTa-v3 NLI classification, claim verification, label preparation, evaluation. | Operational |
| **CB.SC.U4CSE24265** | **V. Vignesh** | Recall@k/F1 evaluation, grounded explanation generation, system integration, end-to-end testing, refinement. | Operational |

---

## 📄 License & Attribution

This project is developed for educational and academic research purposes only. Inspired by the Allen Institute for AI (AI2) SciFact benchmark schema.
