/* ProcessingStatus.tsx — 3단계 처리 진행 상태 인디케이터 */

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

  if (error) {
    return (
      <div className="tml-processing-error">
        <span className="tml-processing-error__msg">{error}</span>
      </div>
    )
  }

  return (
    <div className="tml-processing-status" aria-live="polite" aria-atomic="false" aria-label="처리 진행 상태">
      {steps.map((step: ProcessingStep, i: number) => (
        <StepRow key={step.name} step={step} index={i} />
      ))}
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

      {/* 이름 + 바 */}
      <div className="tml-processing-step__content">
        <span className="tml-processing-step__name">{name}</span>
        <div className="tml-processing-step__track">
          <div className={`tml-processing-step__fill tml-processing-fill--${status}`} />
        </div>
      </div>

      {/* 상태 텍스트 */}
      <span className="tml-processing-step__label">
        {status === 'done' ? '완료' : status === 'running' ? '진행 중' : '대기'}
      </span>
    </div>
  )
}
