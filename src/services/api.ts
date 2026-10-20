import type { VerificationResult } from './mockVerification';
import { generateVerification as fallbackVerification } from './mockVerification';

// Base URL defaults to standard port 8000, configurable via VITE_API_URL
const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

/**
 * Verifies a claim by querying the SciVerify FastAPI NLP backend.
 * Gracefully falls back to the local client-side verification engine if the backend is offline.
 * Clearly differentiates live neural backend predictions from client simulation fallbacks.
 */
export async function verifyClaimOnline(claim: string): Promise<VerificationResult> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000); // 45s timeout for deep neural inference

    const res = await fetch(`${API_BASE}/api/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ claim }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data = await res.json();
      const fallback = fallbackVerification(claim);
      return {
        ...fallback,
        ...data,
        isSimulated: false,
        dataSource: 'live_neural_backend',
        modelMetrics: data.modelMetrics || fallback.modelMetrics,
        xai: data.xai || fallback.xai,
      };
    } else {
      console.warn(`[SciVerify API] Server responded with status ${res.status}: ${res.statusText}. Using simulation fallback.`);
    }
  } catch (err) {
    console.warn(`[SciVerify Network Notice] Failed to reach backend at ${API_BASE}. Falling back to client-side simulation. Real evaluation metrics and live XAI require an active backend server on ${API_BASE}.`, err);
  }

  const fallback = fallbackVerification(claim);
  return {
    ...fallback,
    isSimulated: true,
    dataSource: 'client_simulation_fallback'
  };
}
