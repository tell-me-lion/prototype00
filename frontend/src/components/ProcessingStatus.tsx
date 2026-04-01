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
  { name: 'Step 1: 텍스트 정제', status: 'pending' },
  { name: 'Step 2: 문장 분리', status: 'pending' },
  { name: 'Step 3: 의미 단위 청킹', status: 'pending' },
  { name: 'Step 4: 명제 추출', status: 'pending' },
  { name: 'Step 5: 팩트 포맷팅', status: 'pending' },
  { name: '개념 분석 (EP)', status: 'pending' },
  { name: '문제 설계', status: 'pending' },
  { name: '퀴즈 생성', status: 'pending' },
]

const DEFAULT_WEEK_STEPS: ProcessingStep[] = [
  { name: '학습 가이드 생성', status: 'pending' },
]

interface MainStep {
  name: string
  status: 'pending' | 'running' | 'done'
  subSteps?: ProcessingStep[]
}

function calcPercent(steps: ProcessingStep[]): number {
  if (steps.length === 0) return 0
  const unit = 100 / steps.length
  const doneCount = steps.filter((s) => s.status === 'done').length
  const isRunning = steps.some((s) => s.status === 'running')
  return Math.min(Math.floor(doneCount * unit + (isRunning ? unit / 2 : 0)), 100)
}

function groupSteps(steps: ProcessingStep[]): MainStep[] {
  // 강의(Mode A) 여부 확인: Step 1이 있으면 4단계 UI로 그룹핑
  const preprocessSteps = steps.filter(s => s.name.startsWith('Step '))
  if (preprocessSteps.length > 0) {
    const grouped: MainStep[] = []
    
    // 1. 전처리 (Phase 1~5 묶음)
    const isDone = preprocessSteps.every(s => s.status === 'done')
    const isRunning = preprocessSteps.some(s => s.status === 'running' || s.status === 'done') && !isDone
    grouped.push({
      name: '전처리',
      status: isDone ? 'done' : isRunning ? 'running' : 'pending',
      subSteps: preprocessSteps,
    })

    // 2. 개념 & 3. 퀴즈 등 나머지 스텝 매핑
    const stepNames = ['개념 분석', '문제 설계', '퀴즈 생성']
    const displayNames = ['개념 추출', '문제 설계', '퀴즈 생성']
    
    stepNames.forEach((target, idx) => {
      const step = steps.find(s => s.name.includes(target))
      if (step) {
        grouped.push({
          name: displayNames[idx],
          status: step.status as 'pending' | 'running' | 'done',
        })
      } else {
        grouped.push({ name: displayNames[idx], status: 'pending' })
      }
    })
    
    return grouped
  }

  // 주차 등 기타(통짜) 배치는 그대로 반환
  return steps.map(s => ({
    name: s.name,
    status: s.status as 'pending' | 'running' | 'done',
  }))
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

  const defaultSteps = week !== undefined ? DEFAULT_WEEK_STEPS : DEFAULT_STEPS
  const steps = (status?.steps && status.steps.length > 0) ? status.steps : defaultSteps
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
        {groupSteps(steps).map((step: MainStep, i: number) => (
          <StepRow key={step.name} step={step} index={i} />
        ))}
      </div>
    </div>
  )
}

// ── 개별 단계 행 ──

interface StepRowProps {
  step: MainStep
  index: number
}

function StepRow({ step, index }: StepRowProps) {
  const { name, status, subSteps } = step

  return (
    <div className={`tml-processing-step tml-processing-step--${status}`}>
      {/* 단계 아이콘 */}
      <div className="tml-processing-step__icon">
        {status === 'done' ? '✓' : index + 1}
      </div>

      {/* 이름 + 플로우 + 진행 바 */}
      <div className="tml-processing-step__content">
        <span className="tml-processing-step__name">{name}</span>
        
        {/* 서브 스텝(전처리 상세) - 부모가 pending이 아닐 때 노출 */}
        {subSteps && subSteps.length > 0 && status !== 'pending' && (
          <div className="tml-processing-step__substeps">
            {subSteps.map((sub) => {
              const subName = sub.name.replace(/Step \d+:\s*/, '')
              return (
                <div key={sub.name} className={`tml-processing-substep tml-processing-substep--${sub.status}`}>
                  <span className="tml-processing-substep__icon">
                    {sub.status === 'done' ? '✓' : sub.status === 'running' ? '•' : '○'}
                  </span>
                  {subName}
                </div>
              )
            })}
          </div>
        )}

        {status === 'running' && subSteps === undefined && (
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
