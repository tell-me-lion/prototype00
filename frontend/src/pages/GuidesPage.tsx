import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WeekSummary, ProcessingStatus } from '../types/models'
import { triggerWeekProcess, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProcessingStatus as ProcessingStatusUI } from '../components/ProcessingStatus'
import { useCountUp } from '../hooks/useCountUp'
import { useWeeks } from '../hooks/useWeeks'

// ── 그래디언트 헬퍼 ──

function getGuideGradient(week: number): string {
  const hues = [210, 25, 170, 340]
  const baseHue = hues[(week - 1) % hues.length]
  return `linear-gradient(135deg, hsl(${baseHue}, 55%, 38%), hsl(${baseHue + 35}, 45%, 28%))`
}

// ── StatCard ──

interface StatCardProps {
  label: string
  value: number
  accent: string
  delay: number
}

function StatCard({ label, value, accent, delay }: StatCardProps) {
  const display = useCountUp(value)
  return (
    <div className="tml-guide-stat tml-dashboard-stagger" style={{ animationDelay: `${delay}ms` }}>
      <div className="tml-guide-stat__dot" style={{ background: accent }} />
      <span className="tml-guide-stat__label">{label}</span>
      <span className="tml-guide-stat__value">{display}</span>
    </div>
  )
}

// ── GuideCard ──

interface GuideCardProps {
  weekSummary: WeekSummary
  status: ProcessingStatus
  index: number
  onProcess: (week: number) => void
  onViewResults: (week: number) => void
  onProcessComplete: (week: number) => void
  onProcessError: (week: number) => void
}

function GuideCard({ weekSummary, status, index, onProcess, onViewResults, onProcessComplete, onProcessError }: GuideCardProps) {
  const { week, lecture_count, completed_count, date_range } = weekSummary
  const gradient = getGuideGradient(week)
  const percent = lecture_count > 0 ? Math.round((completed_count / lecture_count) * 100) : 0

  return (
    <div
      className="tml-guide-card tml-dashboard-stagger"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      {/* 그래디언트 헤더 */}
      <div className="tml-guide-card__gradient" style={{ background: gradient }}>
        <span className="tml-guide-card__week-badge">W{week}</span>
        <span className="tml-guide-card__date-badge">{date_range}</span>
      </div>

      {/* 본문 */}
      <div className="tml-guide-card__body">
        <h3 className="tml-guide-card__title">{week}주차 학습 가이드</h3>
        <p className="tml-guide-card__meta">
          {lecture_count}개 강의 · {completed_count}개 분석 완료
        </p>

        {/* 프로그레스 바 */}
        <div className="tml-guide-card__progress">
          <div
            className="tml-guide-card__progress-fill"
            style={{ width: `${percent}%` }}
          />
        </div>

        {/* 액션 */}
        <div className="tml-guide-card__footer">
          {status === 'completed' ? (
            <button className="btn-primary" onClick={() => onViewResults(week)}>
              가이드 보기 →
            </button>
          ) : status === 'processing' ? (
            <ProcessingStatusUI
              week={week}
              onComplete={() => onProcessComplete(week)}
              onError={() => onProcessError(week)}
            />
          ) : (
            <button
              className="btn-primary"
              style={{ background: 'var(--tml-navy)' }}
              onClick={() => onProcess(week)}
            >
              가이드 생성 →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── GuidesPage ──

export function GuidesPage() {
  const { weeks, loading, error } = useWeeks('주차 목록을 불러오지 못했습니다.')
  const [processingWeeks, setProcessingWeeks] = useState<Set<number>>(new Set())
  const [completedWeeks, setCompletedWeeks] = useState<Set<number>>(new Set())
  const navigate = useNavigate()

  const handleProcess = useCallback(async (week: number) => {
    setProcessingWeeks((prev) => new Set(prev).add(week))
    try {
      await triggerWeekProcess(week)
    } catch (err) {
      // 409: 이미 처리 중이거나 완료 → 결과 페이지로 이동
      if (err instanceof ApiError && err.status === 409) {
        setProcessingWeeks((prev) => {
          const next = new Set(prev)
          next.delete(week)
          return next
        })
        navigate(`/weekly/${week}`)
        return
      }
      setProcessingWeeks((prev) => {
        const next = new Set(prev)
        next.delete(week)
        return next
      })
    }
  }, [navigate])

  const handleProcessComplete = useCallback(
    (week: number) => {
      setProcessingWeeks((prev) => {
        const next = new Set(prev)
        next.delete(week)
        return next
      })
      setCompletedWeeks((prev) => new Set(prev).add(week))
      navigate(`/weekly/${week}`)
    },
    [navigate],
  )

  const handleProcessError = useCallback((week: number) => {
    setProcessingWeeks((prev) => {
      const next = new Set(prev)
      next.delete(week)
      return next
    })
  }, [])

  const getEffectiveStatus = (ws: WeekSummary): ProcessingStatus => {
    if (completedWeeks.has(ws.week)) return 'completed'
    if (processingWeeks.has(ws.week)) return 'processing'
    if (ws.status === 'processing') return 'processing'
    return ws.status
  }

  // 통계 산출
  const totalWeeks = weeks.length
  const completedGuides = weeks.filter((w) => getEffectiveStatus(w) === 'completed').length
  const totalAnalyzed = weeks.reduce((sum, w) => sum + w.completed_count, 0)

  return (
    <main className="tml-page-container tml-page-container--hero">
      {/* 페이지 헤더 */}
      <div className="tml-animate">
        <p className="tml-page-eyebrow">Learning Guides · Mode B</p>
        <h1 className="tml-page-title">학습 가이드</h1>
      </div>

      {/* 로딩 */}
      {loading && (
        <div className="tml-guide-grid">
          {[1, 2, 3].map((i) => (
            <div key={i} className="tml-skeleton" style={{ height: 200, borderRadius: 6 }} />
          ))}
        </div>
      )}

      {/* 에러 */}
      {!loading && error && (
        <ErrorCard message={error} title="학습 가이드 로드 실패" />
      )}

      {/* 콘텐츠 */}
      {!loading && !error && (
        weeks.length === 0 ? (
          <div style={{ padding: '48px 24px', textAlign: 'center' }}>
            <p style={{
              fontFamily: 'var(--font-body)', color: 'var(--tml-ink-muted)', margin: 0,
            }}>
              등록된 주차가 없습니다.
            </p>
          </div>
        ) : (
          <>
            {/* 스탯 배너 */}
            <div className="tml-guide-stats">
              <StatCard label="전체 주차" value={totalWeeks} accent="var(--tml-orange)" delay={0} />
              <StatCard label="완료된 가이드" value={completedGuides} accent="var(--tml-navy-mid)" delay={80} />
              <StatCard label="분석 완료 강의" value={totalAnalyzed} accent="var(--tml-quiz)" delay={160} />
            </div>

            {/* 가이드 그리드 */}
            <div className="tml-guide-grid">
              {weeks.map((ws, i) => (
                <GuideCard
                  key={ws.week}
                  weekSummary={ws}
                  status={getEffectiveStatus(ws)}
                  index={i}
                  onProcess={handleProcess}
                  onViewResults={(w) => navigate(`/weekly/${w}`)}
                  onProcessComplete={handleProcessComplete}
                  onProcessError={handleProcessError}
                />
              ))}
            </div>
          </>
        )
      )}
    </main>
  )
}
