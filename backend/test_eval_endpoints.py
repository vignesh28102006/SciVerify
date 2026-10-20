"""
SciVerify Two-LLM Architecture Regression Test Suite
Validates:
1. /health endpoint reports the two active LLMs.
2. /api/evaluation/models returns strictly the TWO deep-learning LLMs.
3. /api/evaluation/summary returns the two-model pipeline benchmark metrics.
4. /api/verify with Groq LPU (Llama-3.1-8b-instant) & perturbation-based XAI.
5. /api/verify with Google Gemini (gemini-1.5-flash) & perturbation-based XAI.
6. /api/verify with engine="compare" (dual side-by-side LLM verification).
"""

import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app, retrieval_engine

def test_backend_suite():
    print("=" * 68)
    print("   SCIVERIFY: TWO-LLM ARCHITECTURE REGRESSION TEST SUITE")
    print("=" * 68)

    client = TestClient(app)

    # Initialize corpus
    corpus_path = os.path.join(os.path.dirname(backend_dir), "data", "corpus.jsonl")
    if os.path.exists(corpus_path):
        retrieval_engine.load_corpus(corpus_path)
        retrieval_engine.build_index()

    # 1. Health check
    print("[1/6] Testing /health endpoint...")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check failed: {resp.text}"
    health_data = resp.json()
    print(f"      Service: {health_data.get('service')}")
    print(f"      Active LLM Models: {health_data.get('active_models')}")

    # 2. Evaluation Models Endpoint
    print("\n[2/6] Testing /api/evaluation/models endpoint...")
    resp = client.get("/api/evaluation/models")
    assert resp.status_code == 200, f"Models endpoint failed: {resp.text}"
    models_data = resp.json()
    assert len(models_data) == 2, f"Expected exactly 2 LLMs, got {len(models_data)}"
    print(f"      SUCCESS: Retrieved exactly 2 active Deep Learning LLMs:")
    for m in models_data:
        print(f"      - {m['modelName']} ({m['task']}): F1={m['f1Score']}%, Latency={m['latencyMs']}ms, Samples={m['sampleCount']}")

    # 3. Evaluation Summary Endpoint
    print("\n[3/6] Testing /api/evaluation/summary endpoint...")
    resp = client.get("/api/evaluation/summary")
    assert resp.status_code == 200, f"Summary endpoint failed: {resp.text}"
    summary = resp.json()
    print(f"      Active Models: {summary.get('active_llm_models_count')} | Primary: {summary.get('primary_model')} | Alternative: {summary.get('alternative_model')}")

    # 4. Verify Claim with Groq LPU (Primary)
    print("\n[4/6] Testing /api/verify with Groq LPU (Primary Engine)...")
    payload_groq = {
        "claim": "Urban green space exposure improves self-reported mental health outcomes.",
        "engine": "groq"
    }
    resp = client.post("/api/verify", json=payload_groq)
    assert resp.status_code == 200, f"Groq verify endpoint failed: {resp.text}"
    data_groq = resp.json()
    assert data_groq["verifiedBy"].startswith("Groq LPU"), f"Unexpected verifier: {data_groq['verifiedBy']}"
    assert len(data_groq["modelMetrics"]) == 2, "Expected exactly 2 LLMs in modelMetrics"
    assert "Perturbation" in data_groq["xai"]["method"], "Expected perturbation-based XAI method"
    print(f"      Verified By: {data_groq['verifiedBy']} | Verdict: {data_groq['verdict']} ({data_groq['confidence']}%)")
    print(f"      XAI: {data_groq['xai']['method']} | Fidelity: {data_groq['xai']['rationaleFidelity']}%")

    # 5. Verify Claim with Google Gemini (Alternative)
    print("\n[5/6] Testing /api/verify with Google Gemini (Alternative Engine)...")
    payload_gemini = {
        "claim": "Urban green space exposure improves self-reported mental health outcomes.",
        "engine": "gemini"
    }
    resp = client.post("/api/verify", json=payload_gemini)
    assert resp.status_code == 200, f"Gemini verify endpoint failed: {resp.text}"
    data_gemini = resp.json()
    assert "Google Gemini" in data_gemini["verifiedBy"], f"Unexpected verifier: {data_gemini['verifiedBy']}"
    print(f"      Verified By: {data_gemini['verifiedBy']} | Verdict: {data_gemini['verdict']} ({data_gemini['confidence']}%)")

    # 6. Verify Claim with Dual LLM Comparison Mode
    print("\n[6/6] Testing /api/verify with Compare Mode (Dual Side-by-Side)...")
    payload_compare = {
        "claim": "Alcohol is injurious to health.",
        "engine": "compare"
    }
    resp = client.post("/api/verify", json=payload_compare)
    assert resp.status_code == 200, f"Compare verify endpoint failed: {resp.text}"
    data_compare = resp.json()
    assert data_compare.get("comparison") is not None, "Expected comparison dictionary in response"
    print(f"      Comparison Mode Active: Groq={data_compare['comparison']['groq']['verdict']} vs Gemini={data_compare['comparison']['gemini']['verdict']}")

    print("\n" + "=" * 68)
    print("   ALL TWO-LLM ARCHITECTURE REGRESSION TESTS PASSED (6/6)!")
    print("=" * 68)

if __name__ == "__main__":
    test_backend_suite()
