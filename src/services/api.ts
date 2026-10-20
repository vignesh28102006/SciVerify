import type { VerificationResult } from './mockVerification';
import { generateVerification as fallbackVerification } from './mockVerification';

const API_BASE = 'http://localhost:8001';

/**
 * Verifies a claim by querying the SciVerify FastAPI NLP backend.
 * Gracefully falls back to the local client-side verification engine if the backend is offline.
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
        modelMetrics: data.modelMetrics || fallback.modelMetrics,
        xai: data.xai || fallback.xai,
      };
    }
  } catch (err) {
    console.info('SciVerify backend server is not active on localhost:8000. Using client-side simulation engine.');
  }

  return fallbackVerification(claim);
}
