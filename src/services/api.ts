import type { VerificationResult } from './mockVerification';
import { generateVerification as fallbackVerification } from './mockVerification';

// Base URL defaults to port 8001 (matching FastAPI backend), configurable via VITE_API_URL
const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8001';

/**
 * Verifies a claim by querying the SciVerify FastAPI NLP backend.
 * Supports multi-engine routing: 'deberta' (local NLI), 'groq' (LPU Llama-3.1), or 'gemini' (Gemini 1.5/3.5).
 * Gracefully falls back to the local client-side verification engine if the backend is offline.
 * Clearly differentiates live neural backend predictions from client simulation fallbacks.
 */
export async function verifyClaimOnline(
  claim: string,
  engine: string = 'deberta',
  options?: { mode?: string; enable_external?: boolean; fallback_to_knowledge?: boolean }
): Promise<VerificationResult> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000); // 45s timeout for deep neural inference

    const payload = {
      claim,
      engine,
      mode: options?.mode || 'auto',
      enable_external: options?.enable_external ?? true,
      fallback_to_knowledge: options?.fallback_to_knowledge ?? true,
    };

    const res = await fetch(`${API_BASE}/api/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      const fallback = fallbackVerification(claim, engine);
      return {
        ...fallback,
        ...data,
        verifiedBy: data.verifiedBy || fallback.verifiedBy,
        provenance: data.provenance || 'LOCAL_CORPUS',
        isProvisional: !!data.isProvisional,
        scientificReasoning: data.scientificReasoning || '',
        qualifications: data.qualifications || '',
        isSimulated: false,
        dataSource: 'live_neural_backend',
        modelMetrics: data.modelMetrics || fallback.modelMetrics,
        xai: data.xai || fallback.xai,
        comparison: data.comparison || fallback.comparison,
      };
    } else {
      console.warn(`[SciVerify API] Server responded with status ${res.status}: ${res.statusText}. Using simulation fallback.`);
    }
  } catch (err) {
    console.warn(`[SciVerify Network Notice] Failed to reach backend at ${API_BASE}. Falling back to client-side simulation. Real evaluation metrics and live XAI require an active backend server on ${API_BASE}.`, err);
  }

  const fallback = fallbackVerification(claim, engine);
  return {
    ...fallback,
    isSimulated: true,
    dataSource: 'client_simulation_fallback'
  };
}

/**
 * Fetches the honest fine-tuning audit report from the backend API.
 */
export async function fetchFineTuningAudit(): Promise<any> {
  try {
    const res = await fetch(`${API_BASE}/api/fine-tuning/audit`);
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.info('Could not reach fine-tuning audit endpoint.');
  }
  return null;
}
