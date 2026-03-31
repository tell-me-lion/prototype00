// ===== 처리 상태 =====

export type ProcessingStatus = 'idle' | 'processing' | 'completed' | 'error'

export interface ProcessingStep {
  name: string // "영상 분석", "텍스트 추출", "AI 분석"
  status: 'pending' | 'running' | 'done'
}

// ===== 강의 카탈로그 =====

export interface LectureResultSummary {
  concept_count: number
  learning_point_count: number
  quiz_count: number
}

export interface Lecture {
  lecture_id: string
  date: string // "2026-02-02" (ISO date string)
  day_of_week: string // "월", "화", ...
  week: number
  course_code: string
  course_name: string
  status: ProcessingStatus
  result_summary: LectureResultSummary | null
  meta: Record<string, unknown>
}

export interface WeekSummary {
  week: number
  lecture_count: number
  completed_count: number
  date_range: string
  status: ProcessingStatus
  lectures: Lecture[]
}

// ===== 처리 관련 =====

export interface ProcessTriggerResponse {
  lecture_id?: string
  week?: number
  status: ProcessingStatus
  started_at: string
}

export interface ProcessingStatusResponse {
  lecture_id?: string
  week?: number
  status: ProcessingStatus
  steps: ProcessingStep[]
  started_at: string | null
  completed_at: string | null
  error_message: string | null
}

// ===== 산출물 (파이프라인 출력 스키마 기준) =====

export interface Concept {
  concept_id: string
  concept: string
  definition: string
  related_concepts: string[]
  source_chunk_ids: string[]
  week: number
  lecture_id: string
  importance: number
}

export interface LearningPoint {
  concept_id: string
  concept: string
  definition: string
  related_concepts: string[]
  source_chunk_ids: string[]
  week: number
  lecture_id: string
  importance: number
}

export interface Choice {
  id: number
  text: string
  is_answer: boolean
}

export interface QuizMeta {
  attempt_count: number
  llm_model: string
  used_fact_ids: string[]
}

export interface Quiz {
  quiz_id: string
  blueprint_id: string
  lecture_id: string
  week: number
  question_type: 'mcq_definition' | 'mcq_misconception' | 'fill_blank' | 'ox_quiz' | 'code_execution'
  question_format: string
  difficulty: '상' | '중' | '하'
  question: string
  choices: Choice[] | null
  answers: string | null
  code_template: string | null
  source_text: string
  explanation: string
  meta: QuizMeta
}

export interface LearningGuide {
  week: number
  summary: string
  key_concepts: string[]
  meta: Record<string, unknown>
}

export interface LectureOutputs {
  concepts: Concept[]
  learning_points: LearningPoint[]
  quizzes: Quiz[]
}

export interface WeeklyOutputs {
  guides: LearningGuide[]
}
