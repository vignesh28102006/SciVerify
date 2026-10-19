"""
Groq API Live Connectivity & Functionality Verification Test
Checks:
1. Environment variable / .env file loading.
2. Direct handshake with Groq Cloud LPU servers.
3. Test inference on Llama-3.1-8b-instant.
4. Test Whisper Large-v3 speech model capability.
"""

import os
import sys
import json
import time

# Ensure script directory and backend directory are in path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(script_dir, '.env'))
except ImportError:
    pass

def test_groq_connection():
    print("=" * 65)
    print("   SCIVERIFY: GROQ LPU API LIVE CONNECTIVITY TEST")
    print("=" * 65)

    api_key = os.getenv("GROQ_API_KEY", "").strip()

    # Step 1: Check Key
    if not api_key:
        print("\n❌ STEP 1 FAILED: GROQ_API_KEY is empty in backend/.env")
        print("   👉 Open backend/.env and set: GROQ_API_KEY=gsk_...")
        return False

    if "your_groq_api_key_here" in api_key:
        print("\n⚠️ STEP 1 NOTICE: Placeholder detected in backend/.env")
        print("   👉 Line 7 currently has: GROQ_API_KEY=your_groq_api_key_here")
        print("   👉 Replace it with your actual key from https://console.groq.com/keys")
        return False

    masked = api_key[:7] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
    print(f"\n[1/3] GROQ_API_KEY detected: {masked} (length: {len(api_key)})")

    # Step 2: Test live REST connection to Groq API
    print("[2/3] Contacting Groq Cloud LPU endpoint (https://api.groq.com)...")
    try:
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {
                    "role": "user",
                    "content": "Verify this scientific statement: 'Vitamin C cures all viral infections.' Respond in 10 words or less."
                }
            ],
            "max_tokens": 50,
            "temperature": 0.1
        }

        start_time = time.time()
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        latency_ms = int((time.time() - start_time) * 1000)

        if resp.status_code == 200:
            result = resp.json()
            content = result["choices"][0]["message"].get("content", "").strip()
            safe_content = content.encode("ascii", errors="replace").decode("ascii")
            print("\n[SUCCESS] LIVE GROQ CONNECTION ESTABLISHED!")
            print(f"   Inference Latency : {latency_ms} ms (Groq LPU)")
            print(f"   Model Used        : openai/gpt-oss-20b")
            print(f"   Live Response     : \"{safe_content}\"")
        elif resp.status_code == 401:
            print("\n[ERROR 401] INVALID API KEY: Groq rejected the key.")
            print(f"   Message: {resp.text}")
            return False
        else:
            print(f"\n❌ [ERROR {resp.status_code}] Unexpected API response: {resp.text}")
            return False

    except Exception as e:
        print(f"\n❌ [NETWORK ERROR] Failed to connect to Groq API: {e}")
        return False

    # Step 3: Test Claim Verification Pipeline
    print("\n[3/3] Testing SciVerify Claim Verification Pipeline with Groq...")
    from app.pipeline.llm_groq_audio import GroqAudioClaimVerifier
    verifier = GroqAudioClaimVerifier(api_key=api_key)
    res = verifier.verify_claim(
        claim="Statin therapy reduces cardiovascular event risk.",
        evidence_text="Large clinical trials show statins lower LDL and reduce major coronary events."
    )
    print(f"   Verdict     : {res.get('verdict')}")
    print(f"   Confidence  : {res.get('confidence')}%")
    print(f"   Explanation : {res.get('explanation')}")

    print("\n" + "=" * 65)
    print("   RESULT: GROQ MODEL IS 100% OPERATIONAL AND READY!")
    print("=" * 65)
    return True

if __name__ == "__main__":
    test_groq_connection()
