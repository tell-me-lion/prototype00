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

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: '알 수 없는 오류' }))
    throw new ApiError(res.status, body.detail ?? `오류 (${res.status})`)
  }
  return res.json()
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
  return request(`/api/lectures/${lectureId}/process`, {
    method: 'POST',
    body: JSON.stringify({ force: force ?? false }),
  })
}

export async function triggerWeekProcess(week: number): Promise<ProcessTriggerResponse> {
  return request(`/api/weeks/${week}/process`, { method: 'POST' })
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
  return request(`/api/lectures/${lectureId}/results`)
}

export async function fetchWeekResults(week: number): Promise<WeeklyOutputs> {
  return request(`/api/weeks/${week}/results`)
}
