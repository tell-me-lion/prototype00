/* ProcessingStatus.tsx — 처리 진행 상태 인디케이터 (퍼센트 + 경과 시간 포함) */

import { useEffect, useRef, useState } from 'react'
import { useProcessingStatus } from '../hooks/useProcessingStatus'
import type { ProcessingStep } from '../types/models'

interface ProcessingStatusProps {
  lectureId?: string
  week?: number
  onComplete: () => void
  onError?: (message: string) => void
}

const DEFAULT_STEPS: ProcessingStep[] = [
  { name: '영상 분석', status: 'pending' },
  { name: '텍스트 추출', status: 'pending' },
  { name: 'AI 분석', status: 'pending' },
]

function calcPercent(steps: ProcessingStep[]): number {
  if (steps.length === 0) return 0
  const unit = Math.floor(100 / steps.length)
  const half = Math.floor(unit / 2)
  const doneCount = steps.filter((s) => s.status === 'done').length
  const isRunning = steps.some((s) => s.status === 'running')
  return Math.min(doneCount * unit + (isRunning ? half : 0), 100)
}

function useElapsed(startedAt: string | null | undefined): string {
  const [elapsed, setElapsed] = useState('')
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!startedAt) { setElapsed(''); return }
    const update = () => {
      const diff = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000)
      if (diff < 60) setElapsed(`${diff}초`)
      else setElapsed(`${Math.floor(diff / 60)}분`)
    }
    update()
    timerRef.current = setInterval(update, 5000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [startedAt])

  return elapsed
}

export function ProcessingStatus({
  lectureId,
  week,
  onComplete,
  onError,
}: ProcessingStatusProps) {
  const { status, error } = useProcessingStatus({
    lectureId,
    week,
    enabled: true,
    onComplete,
    onError,
  })

  const steps = (status?.steps && status.steps.length > 0) ? status.steps : DEFAULT_STEPS
  const percent = calcPercent(steps)
  const elapsed = useElapsed(status?.started_at)

  if (error) {
    return (
      <div className="tml-processing-error">
        <span className="tml-processing-error__msg">{error}</span>
      </div>
    )
  }

  return (
    <div className="tml-processing-status" aria-live="polite" aria-atomic="false" aria-label="처리 진행 상태">
      {/* 전체 진행률 바 */}
      <div className="tml-processing-header">
        <div className="tml-processing-bar-wrap">
          <div className="tml-processing-bar-track">
            <div
              className="tml-processing-bar-fill"
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
        <div className="tml-processing-meta">
          <span className="tml-processing-percent">{percent}%</span>
          {elapsed && (
            <span className="tml-processing-elapsed">{elapsed} 경과</span>
          )}
        </div>
      </div>

      {/* 단계 목록 */}
      <div className="tml-processing-steps">
        {steps.map((step: ProcessingStep, i: number) => (
          <StepRow key={step.name} step={step} index={i} />
        ))}
      </div>
    </div>
  )
}

// ── 개별 단계 행 ──

interface StepRowProps {
  step: ProcessingStep
  index: number
}

function StepRow({ step, index }: StepRowProps) {
  const { name, status } = step

  return (
    <div className={`tml-processing-step tml-processing-step--${status}`}>
      {/* 단계 아이콘 */}
      <div className="tml-processing-step__icon">
        {status === 'done' ? '✓' : index + 1}
      </div>

      {/* 이름 + 진행 바 (running일 때만) */}
      <div className="tml-processing-step__content">
        <span className="tml-processing-step__name">{name}</span>
        {status === 'running' && (
          <div className="tml-processing-step__track">
            <div className="tml-processing-step__fill tml-processing-fill--running" />
          </div>
        )}
      </div>

      {/* 상태 배지 */}
      <span className="tml-processing-step__label">
        {status === 'done' ? '완료' : status === 'running' ? '진행 중' : '대기'}
      </span>
    </div>
  )
}
