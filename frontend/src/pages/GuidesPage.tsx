import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WeekSummary, ProcessingStatus } from '../types/models'
import { fetchWeeks, triggerWeekProcess, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProcessingStatus as ProcessingStatusUI } from '../components/ProcessingStatus'

// ── useCountUp (Dashboard 패턴 재사용) ──

function useCountUp(target: number, duration = 600) {
  const [value, setValue] = useState(0)
  const rafRef = useRef(0)

  useEffect(() => {
    if (target === 0) { setValue(0); return }
    const start = performance.now()
    const animate = (now: number) => {
      const elapsed = now - start
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(Math.round(eased * target))
      if (progress < 1) rafRef.current = requestAnimationFrame(animate)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration])

  return value
}

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
  const [weeks, setWeeks] = useState<WeekSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processingWeeks, setProcessingWeeks] = useState<Set<number>>(new Set())
  const navigate = useNavigate()

  useEffect(() => {
    fetchWeeks()
      .then(setWeeks)
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : '주차 목록을 불러오지 못했습니다.')
      })
      .finally(() => setLoading(false))
  }, [])

  const handleProcess = useCallback(async (week: number) => {
    setProcessingWeeks((prev) => new Set(prev).add(week))
    try {
      await triggerWeekProcess(week)
    } catch {
      setProcessingWeeks((prev) => {
        const next = new Set(prev)
        next.delete(week)
        return next
      })
    }
  }, [])

  const handleProcessComplete = useCallback(
    (week: number) => {
      setProcessingWeeks((prev) => {
        const next = new Set(prev)
        next.delete(week)
        return next
      })
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
    if (processingWeeks.has(ws.week)) return 'processing'
    if (ws.status === 'processing' && !processingWeeks.has(ws.week)) return 'idle'
    return ws.status
  }

  // 통계 산출
  const totalWeeks = weeks.length
  const completedGuides = weeks.filter((w) => getEffectiveStatus(w) === 'completed').length
  const totalAnalyzed = weeks.reduce((sum, w) => sum + w.completed_count, 0)

  return (
    <main style={{ maxWidth: 1280, margin: '0 auto', padding: '40px 40px 80px' }}>
      {/* 페이지 헤더 */}
      <div className="tml-animate">
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '0.75rem',
          fontWeight: 600,
          color: 'var(--tml-orange)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          margin: '0 0 8px',
        }}>
          Learning Guides · Mode B
        </p>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          fontSize: '1.75rem',
          letterSpacing: '-0.02em',
          color: 'var(--tml-ink)',
          margin: '0 0 28px',
        }}>
          학습 가이드
        </h1>
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
