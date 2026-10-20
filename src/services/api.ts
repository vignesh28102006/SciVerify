import type { VerificationResult } from './mockVerification';
import { generateVerification as fallbackVerification } from './mockVerification';

const API_BASE = 'http://localhost:8001';

/**
 * Verifies a claim by querying the SciVerify FastAPI NLP backend.
 * Gracefully falls back to the local client-side verification engine if the backend is offline.
 */
export async function verifyClaimOnline(
  claim: string,
  engine: string = 'groq',
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
        modelMetrics: data.modelMetrics || fallback.modelMetrics,
        xai: data.xai || fallback.xai,
        comparison: data.comparison || fallback.comparison,
      };
    }
  } catch (err) {
    console.info('SciVerify backend server is not active on localhost:8001. Using client-side simulation engine.');
  }

  return fallbackVerification(claim, engine);
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
