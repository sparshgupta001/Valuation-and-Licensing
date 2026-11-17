import type {
  AssessmentCreate,
  AssessmentCreated,
  AssessmentResults,
  AssessmentStatus,
  CommercialInfo,
  ReviewCorrection,
  UploadResult,
} from '../types/api'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body && !(init.body instanceof Blob) && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError(0, 'The Strategos API is unreachable. Check that the backend is running and try again.')
  }

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json() as { detail?: unknown }
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
    } catch {
      // Keep the HTTP status text when the backend returns a non-JSON body.
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  createAssessment: (payload: AssessmentCreate) => request<AssessmentCreated>('/api/v1/assessments', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  uploadDocument: (assessmentId: string, file: File) => {
    const path = `/api/v1/assessments/${encodeURIComponent(assessmentId)}/documents?filename=${encodeURIComponent(file.name)}`
    return request<UploadResult>(path, {
      method: 'POST',
      body: file,
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
    })
  },
  saveCommercialInfo: (assessmentId: string, payload: CommercialInfo) => request<{ assessment_id: string; saved_fields: string[] }>(
    `/api/v1/assessments/${encodeURIComponent(assessmentId)}/commercial-info`,
    { method: 'PUT', body: JSON.stringify(payload) },
  ),
  startAssessment: (assessmentId: string) => request<AssessmentStatus>(
    `/api/v1/assessments/${encodeURIComponent(assessmentId)}/start`, { method: 'POST' },
  ),
  getStatus: (assessmentId: string) => request<AssessmentStatus>(
    `/api/v1/assessments/${encodeURIComponent(assessmentId)}/status`,
  ),
  getResults: (assessmentId: string) => request<AssessmentResults>(
    `/api/v1/assessments/${encodeURIComponent(assessmentId)}/results`,
  ),
  submitReview: (assessmentId: string, payload: ReviewCorrection) => request<AssessmentStatus>(
    `/api/v1/assessments/${encodeURIComponent(assessmentId)}/review`,
    { method: 'POST', body: JSON.stringify(payload) },
  ),
}

export const apiBaseUrl = API_BASE_URL
