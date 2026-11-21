import type {
  ApiErrorResponseV1,
  BeneficiaryListResponseV1,
  CreateSessionRequestV1,
  CreateSessionResponseV1,
  DangerSignCheckRequestV1,
  DangerSignCheckResponseV1,
  HealthResponseV1,
  PersistenceAckRequestV1,
  PersistenceAckResponseV1,
  SessionVisitResponseV1,
} from '@/lib/contracts/v1';

export class FastApiError extends Error {
  status: number;
  code: string;
  retryable: boolean;
  detail?: string | null;

  constructor(status: number, code: string, message: string, retryable = false, detail?: string | null) {
    super(message);
    this.name = 'FastApiError';
    this.status = status;
    this.code = code;
    this.retryable = retryable;
    this.detail = detail;
  }
}

export function getVoiceApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_VOICE_API_BASE_URL;
  if (configured && configured.trim().length > 0) {
    return configured.replace(/\/+$/, '');
  }
  return 'http://localhost:8000';
}

export function getVoiceWsBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_VOICE_WS_URL;
  if (configured && configured.trim().length > 0) {
    // Strip trailing /ws/voice if user passed legacy URL
    return configured.replace(/\/ws\/voice\/?$/, '').replace(/\/+$/, '');
  }
  const httpBase = getVoiceApiBaseUrl();
  return httpBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const baseUrl = getVoiceApiBaseUrl();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);

  try {
    const res = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
      signal: init?.signal || controller.signal,
    });

    const text = await res.text();
    const json = text ? JSON.parse(text) : {};

    if (!res.ok) {
      const errBody = json as Partial<ApiErrorResponseV1>;
      throw new FastApiError(
        res.status,
        errBody.code || 'HTTP_ERROR',
        errBody.message || `Backend request failed (${res.status})`,
        errBody.retryable ?? res.status >= 500,
        errBody.detail
      );
    }

    return json as T;
  } catch (err) {
    if (err instanceof FastApiError) throw err;
    const msg = err instanceof Error ? err.message : 'Network error reaching voice backend';
    throw new FastApiError(0, 'NETWORK_UNREACHABLE', msg, true);
  } finally {
    clearTimeout(timeout);
  }
}

export const fastApiClient = {
  getHealth(): Promise<HealthResponseV1> {
    return requestJson<HealthResponseV1>('/health', { method: 'GET' });
  },

  createSession(req: CreateSessionRequestV1): Promise<CreateSessionResponseV1> {
    return requestJson<CreateSessionResponseV1>('/api/v1/sessions', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  listBeneficiaries(query?: string): Promise<BeneficiaryListResponseV1> {
    const qs = query ? `?q=${encodeURIComponent(query)}` : '';
    return requestJson<BeneficiaryListResponseV1>(`/api/v1/beneficiaries${qs}`, {
      method: 'GET',
    });
  },

  createBeneficiary(payload: {
    full_name: string;
    category: string;
    village: string;
    preferred_language: string;
    age_years: number;
    household_head?: string;
    phone_number?: string;
    edd_date?: string;
    high_risk_status?: boolean;
  }): Promise<{
    schema_version: 'v1';
    synthetic_data_only: boolean;
    beneficiary: {
      beneficiary_id: string;
      full_name: string;
      category: string;
      village: string;
      preferred_language: string;
      age_years?: number;
      household_head?: string | null;
      phone_number?: string | null;
      edd_date?: string | null;
      high_risk_status?: boolean;
    };
  }> {
    return requestJson('/api/v1/beneficiaries', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getSessionVisit(sessionId: string): Promise<SessionVisitResponseV1> {
    return requestJson<SessionVisitResponseV1>(
      `/api/v1/sessions/${encodeURIComponent(sessionId)}/visit`,
      { method: 'GET' }
    );
  },

  acknowledgePersistence(
    sessionId: string,
    payload: PersistenceAckRequestV1
  ): Promise<PersistenceAckResponseV1> {
    return requestJson<PersistenceAckResponseV1>(
      `/api/v1/sessions/${encodeURIComponent(sessionId)}/persistence-ack`,
      {
        method: 'POST',
        body: JSON.stringify(payload),
      }
    );
  },

  checkDangerSigns(payload: DangerSignCheckRequestV1): Promise<DangerSignCheckResponseV1> {
    return requestJson<DangerSignCheckResponseV1>('/api/v1/danger-signs/check', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};

