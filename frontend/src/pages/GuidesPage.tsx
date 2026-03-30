import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { WeekSummary, ProcessingStatus } from '../types/models'
import { fetchWeeks, triggerWeekProcess, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProcessingStatus as ProcessingStatusUI } from '../components/ProcessingStatus'

// ── GuideCard ──

interface GuideCardProps {
  weekSummary: WeekSummary
  status: ProcessingStatus
  onProcess: (week: number) => void
  onViewResults: (week: number) => void
  onProcessComplete: (week: number) => void
  onProcessError: (week: number) => void
}

function GuideCard({ weekSummary, status, onProcess, onViewResults, onProcessComplete, onProcessError }: GuideCardProps) {
  const { week, lecture_count, completed_count, date_range } = weekSummary

  return (
    <div className="tml-card tml-animate" style={{ padding: '24px 28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8, flexWrap: 'wrap' }}>
            <span className="badge-orange">{week}주차</span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--tml-ink-muted)',
            }}>
              {date_range}
            </span>
          </div>
          <h3 style={{
            fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: '1.125rem',
            color: 'var(--tml-ink)', margin: '0 0 6px',
          }}>
            {week}주차 학습 가이드
          </h3>
          <p style={{
            fontFamily: 'var(--font-body)', fontSize: '0.8125rem', color: 'var(--tml-ink-muted)',
            margin: 0,
          }}>
            {lecture_count}개 강의 · {completed_count}개 분석 완료
          </p>
        </div>

        <div style={{ flexShrink: 0 }}>
          {status === 'completed' ? (
            <button
              className="btn-primary"
              onClick={() => onViewResults(week)}
            >
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
    // 백엔드 버그 보정: 일부 idle + 일부 completed 시 processing으로 오는 문제
    if (ws.status === 'processing' && !processingWeeks.has(ws.week)) return 'idle'
    return ws.status
  }

  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '40px 40px 80px' }}>
      {/* 페이지 헤더 */}
      <div className="tml-animate">
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '0.6875rem',
          fontWeight: 600,
          color: 'var(--tml-navy-mid)',
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
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[1, 2].map((i) => (
            <div key={i} className="tml-skeleton" style={{ height: 100, borderRadius: 6 }} />
          ))}
        </div>
      )}

      {/* 에러 */}
      {!loading && error && (
        <ErrorCard message={error} title="학습 가이드 로드 실패" />
      )}

      {/* 가이드 목록 */}
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {weeks.map((ws) => (
              <GuideCard
                key={ws.week}
                weekSummary={ws}
                status={getEffectiveStatus(ws)}
                onProcess={handleProcess}
                onViewResults={(w) => navigate(`/weekly/${w}`)}
                onProcessComplete={handleProcessComplete}
                onProcessError={handleProcessError}
              />
            ))}
          </div>
        )
      )}
    </main>
  )
}
