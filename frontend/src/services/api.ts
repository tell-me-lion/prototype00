import type {
  Lecture,
  WeekSummary,
  ProcessTriggerResponse,
  ProcessingStatusResponse,
  LectureOutputs,
  WeeklyOutputs,
} from '../types/models'

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

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

const DEFAULT_TIMEOUT = 15_000

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT)

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...options,
    })
    clearTimeout(timeout)

    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new ApiError(res.status, body.detail ?? `오류 (${res.status})`)
    }
    return (await res.json()) as T
  } catch (err) {
    clearTimeout(timeout)
    if (err instanceof ApiError) throw err
    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiError(408, '요청 시간이 초과되었습니다')
    }
    throw new ApiError(0, '서버에 연결할 수 없습니다')
  }
}

// ===== 강의 카탈로그 =====

export async function fetchLectures(): Promise<Lecture[]> {
  return request('/api/lectures')
}

export async function fetchLecture(lectureId: string): Promise<Lecture> {
  return request(`/api/lectures/${lectureId}`)
}

export async function fetchWeeks(): Promise<WeekSummary[]> {
  return request('/api/weeks')
}

export async function fetchWeek(week: number): Promise<WeekSummary> {
  return request(`/api/weeks/${week}`)
}

// ===== 처리 트리거 =====

export async function triggerLectureProcess(
  lectureId: string,
  force?: boolean,
): Promise<ProcessTriggerResponse> {
  const query = force ? '?force=true' : ''
  console.log(`[API] 강의 처리 트리거: ${lectureId}${query}`)
  const result = await request<ProcessTriggerResponse>(`/api/lectures/${lectureId}/process${query}`, {
    method: 'POST',
  })
  console.log(`[API] 트리거 응답:`, result)
  return result
}

export async function triggerWeekProcess(
  week: number,
  force?: boolean,
): Promise<ProcessTriggerResponse> {
  const query = force ? '?force=true' : ''
  return request(`/api/weeks/${week}/process${query}`, { method: 'POST' })
}

// ===== 처리 상태 =====

export async function fetchLectureStatus(lectureId: string): Promise<ProcessingStatusResponse> {
  return request(`/api/lectures/${lectureId}/status`)
}

export async function fetchWeekStatus(week: number): Promise<ProcessingStatusResponse> {
  return request(`/api/weeks/${week}/status`)
}

// ===== 결과 =====

export async function fetchLectureResults(lectureId: string): Promise<LectureOutputs> {
  const data = await request<LectureOutputs & { status?: string }>(`/api/lectures/${lectureId}/results`)
  if (data.status === 'processing') {
    throw new ApiError(202, '아직 처리가 완료되지 않았습니다.')
  }
  return data
}

export async function fetchWeekResults(week: number): Promise<WeeklyOutputs> {
  const data = await request<WeeklyOutputs & { status?: string }>(`/api/weeks/${week}/results`)
  if (data.status === 'processing') {
    throw new ApiError(202, '아직 처리가 완료되지 않았습니다.')
  }
  return data
}
