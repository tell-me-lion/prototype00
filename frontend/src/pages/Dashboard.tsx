import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import type { WeekSummary, Lecture, ProcessingStatus } from '../types/models'
import { fetchWeeks, triggerLectureProcess, triggerWeekProcess, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProcessingStatus as ProcessingStatusUI } from '../components/ProcessingStatus'

// ── 썸네일 그래디언트 헬퍼 ──

function getLectureThumbnailGradient(date: string, week: number): string {
  const hues = [210, 25, 170, 340]
  const baseHue = hues[(week - 1) % hues.length]
  const dayOffset = new Date(date).getDay() * 8
  return `linear-gradient(135deg, hsl(${baseHue + dayOffset}, 60%, 35%), hsl(${baseHue + dayOffset + 30}, 50%, 25%))`
}

// ── DashboardStats ──

interface DashboardStatsProps {
  totalLectures: number
  completedLectures: number
  totalQuizzes: number
}

function DashboardStats({ totalLectures, completedLectures, totalQuizzes }: DashboardStatsProps) {
  const stats = [
    { label: '전체 강의', value: totalLectures },
    { label: '분석 완료', value: completedLectures },
    { label: '생성 퀴즈', value: totalQuizzes },
  ]

  return (
    <div className="tml-dashboard-stats tml-animate">
      {stats.map(({ label, value }) => (
        <div key={label} className="tml-stat-card tml-card">
          <span className="tml-stat-card__value">{value}</span>
          <span className="tml-stat-card__label">{label}</span>
        </div>
      ))}
    </div>
  )
}

// ── WeekFilter ──

interface WeekFilterProps {
  weeks: number[]
  activeWeek: number | null
  onSelect: (week: number | null) => void
}

function WeekFilter({ weeks, activeWeek, onSelect }: WeekFilterProps) {
  return (
    <div className="tml-week-tabs tml-animate" style={{ marginTop: 8 }}>
      <button
        className={`tml-week-tab${activeWeek === null ? ' tml-week-tab--active' : ''}`}
        onClick={() => onSelect(null)}
      >
        전체
      </button>
      {weeks.map((week) => (
        <button
          key={week}
          className={`tml-week-tab${activeWeek === week ? ' tml-week-tab--active' : ''}`}
          onClick={() => onSelect(week)}
        >
          {week}주차
        </button>
      ))}
    </div>
  )
}

// ── LectureCard ──

interface LectureCardProps {
  lecture: Lecture
  onProcess: (lectureId: string) => void
  onViewResults: (lectureId: string) => void
  onProcessComplete: (lectureId: string) => void
  onProcessError: (lectureId: string) => void
}

function LectureCard({ lecture, onProcess, onViewResults, onProcessComplete, onProcessError }: LectureCardProps) {
  const { lecture_id, date, day_of_week, week, course_name, status, result_summary } = lecture
  const gradient = getLectureThumbnailGradient(date, week)

  return (
    <div className="tml-lecture-card tml-card">
      {/* 썸네일 placeholder */}
      <div className="tml-lecture-card__thumb" style={{ background: gradient }}>
        <span className="tml-lecture-card__date-badge">
          {date.slice(5)} ({day_of_week})
        </span>
      </div>

      {/* 카드 본문 */}
      <div className="tml-lecture-card__body">
        <p className="tml-lecture-card__course">{course_name}</p>
        <p className="tml-lecture-card__week-label">Week {week}</p>

        <hr className="tml-lecture-card__rule" />

        {status === 'idle' && (
          <div className="tml-lecture-card__footer">
            <button
              className="btn-primary"
              style={{ fontSize: '0.8125rem', padding: '6px 14px', width: '100%' }}
              onClick={() => onProcess(lecture_id)}
            >
              가져오기
            </button>
          </div>
        )}

        {status === 'processing' && (
          <div className="tml-lecture-card__footer">
            <ProcessingStatusUI
              lectureId={lecture_id}
              onComplete={() => onProcessComplete(lecture_id)}
              onError={() => onProcessError(lecture_id)}
            />
          </div>
        )}

        {status === 'completed' && result_summary && (
          <div className="tml-lecture-card__footer">
            <div className="tml-lecture-card__summary">
              <span>개념 {result_summary.concept_count}개</span>
              <span>퀴즈 {result_summary.quiz_count}개</span>
            </div>
            <button
              className="tml-lecture-card__result-btn"
              onClick={() => onViewResults(lecture_id)}
            >
              결과 보기 →
            </button>
          </div>
        )}

        {status === 'error' && (
          <div className="tml-lecture-card__footer">
            <p className="tml-lecture-card__error">오류가 발생했습니다</p>
            <button
              className="btn-primary"
              style={{
                fontSize: '0.8125rem',
                padding: '6px 14px',
                width: '100%',
                background: 'var(--tml-wrong)',
              }}
              onClick={() => onProcess(lecture_id)}
            >
              재시도
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── LectureCardSkeleton ──

function LectureCardSkeleton() {
  return (
    <div className="tml-lecture-card tml-card">
      <div
        className="tml-skeleton"
        style={{ height: 80, borderRadius: '5px 5px 0 0', flexShrink: 0 }}
      />
      <div className="tml-lecture-card__body">
        <div className="tml-skeleton" style={{ height: 13, width: '72%', borderRadius: 4, marginBottom: 8 }} />
        <div className="tml-skeleton" style={{ height: 11, width: '40%', borderRadius: 4, marginBottom: 12 }} />
        <div className="tml-skeleton" style={{ height: 32, borderRadius: 5 }} />
      </div>
    </div>
  )
}

// ── WeekGuideCard ──

interface WeekGuideCardProps {
  week: number
  lectureCount: number
  status: ProcessingStatus
  onProcess: (week: number) => void
  onViewResults: (week: number) => void
  onProcessComplete: (week: number) => void
  onProcessError: (week: number) => void
}

function WeekGuideCard({ week, lectureCount, status, onProcess, onViewResults, onProcessComplete, onProcessError }: WeekGuideCardProps) {
  return (
    <div className="tml-week-guide-card tml-card">
      <div className="tml-week-guide-card__bar" />
      <div className="tml-week-guide-card__content">
        <div>
          <p className="tml-week-guide-card__title">
            📚 {week}주차 전체 학습 가이드
          </p>
          <p className="tml-week-guide-card__desc">
            {lectureCount}개 강의 통합 분석 → 주차별 핵심 요약 &amp; 학습 가이드 생성
          </p>
        </div>

        <div style={{ flexShrink: 0 }}>
          {status === 'completed' ? (
            <button
              className="tml-lecture-card__result-btn"
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
              style={{ fontSize: '0.8125rem', padding: '6px 14px' }}
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

// ── WeekSection ──

interface WeekSectionProps {
  weekSummary: WeekSummary
  processingLectures: Set<string>
  processingWeeks: Set<number>
  onProcess: (lectureId: string) => void
  onViewResults: (lectureId: string) => void
  onProcessComplete: (lectureId: string) => void
  onProcessError: (lectureId: string) => void
  onProcessWeek: (week: number) => void
  onViewWeekResults: (week: number) => void
  onWeekProcessComplete: (week: number) => void
  onWeekProcessError: (week: number) => void
}

function WeekSection({
  weekSummary,
  processingLectures,
  processingWeeks,
  onProcess,
  onViewResults,
  onProcessComplete,
  onProcessError,
  onProcessWeek,
  onViewWeekResults,
  onWeekProcessComplete,
  onWeekProcessError,
}: WeekSectionProps) {
  const { week, lecture_count, completed_count, date_range, lectures } = weekSummary

  return (
    <section className="tml-week-section tml-animate">
      {/* 주차 헤더 */}
      <div className="tml-week-section__header">
        <div className="tml-week-section__title-row">
          <h2 className="tml-week-section__title">{week}주차</h2>
          <span className="tml-week-section__range">{date_range}</span>
        </div>
        <span className="tml-week-section__progress">
          {lecture_count}강의 · {completed_count}완료
        </span>
      </div>

      {/* 강의 카드 그리드 */}
      <div className="tml-lecture-grid">
        {lectures.map((lecture) => (
          <LectureCard
            key={lecture.lecture_id}
            lecture={{
              ...lecture,
              status: processingLectures.has(lecture.lecture_id) ? 'processing' : lecture.status,
            }}
            onProcess={onProcess}
            onViewResults={onViewResults}
            onProcessComplete={onProcessComplete}
            onProcessError={onProcessError}
          />
        ))}
      </div>

      {/* Mode B — 주차별 가이드 */}
      <WeekGuideCard
        week={week}
        lectureCount={lecture_count}
        status={processingWeeks.has(week) ? 'processing' : weekSummary.status}
        onProcess={onProcessWeek}
        onViewResults={onViewWeekResults}
        onProcessComplete={onWeekProcessComplete}
        onProcessError={onWeekProcessError}
      />
    </section>
  )
}

// ── Dashboard (메인 export) ──

export function Dashboard() {
  const [weeks, setWeeks] = useState<WeekSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [processingLectures, setProcessingLectures] = useState<Set<string>>(new Set())
  const [processingWeeks, setProcessingWeeks] = useState<Set<number>>(new Set())
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const activeWeek = searchParams.get('week') ? Number(searchParams.get('week')) : null

  useEffect(() => {
    fetchWeeks()
      .then(setWeeks)
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : '강의 목록을 불러오지 못했습니다.')
      })
      .finally(() => setLoading(false))
  }, [])

  const handleWeekSelect = useCallback(
    (week: number | null) => {
      if (week === null) {
        setSearchParams({})
      } else {
        setSearchParams({ week: String(week) })
      }
    },
    [setSearchParams],
  )

  const handleProcess = useCallback(async (lectureId: string) => {
    setProcessingLectures((prev) => new Set(prev).add(lectureId))
    try {
      await triggerLectureProcess(lectureId)
    } catch {
      setProcessingLectures((prev) => {
        const next = new Set(prev)
        next.delete(lectureId)
        return next
      })
    }
  }, [])

  const handleProcessComplete = useCallback(
    (lectureId: string) => {
      setProcessingLectures((prev) => {
        const next = new Set(prev)
        next.delete(lectureId)
        return next
      })
      navigate(`/lecture/${lectureId}`)
    },
    [navigate],
  )

  const handleProcessError = useCallback((lectureId: string) => {
    setProcessingLectures((prev) => {
      const next = new Set(prev)
      next.delete(lectureId)
      return next
    })
  }, [])

  const handleProcessWeek = useCallback(async (week: number) => {
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

  const handleWeekProcessComplete = useCallback(
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

  const handleWeekProcessError = useCallback((week: number) => {
    setProcessingWeeks((prev) => {
      const next = new Set(prev)
      next.delete(week)
      return next
    })
  }, [])

  // 전체 통계 계산
  const totalLectures = weeks.reduce((sum, w) => sum + w.lecture_count, 0)
  const completedLectures = weeks.reduce((sum, w) => sum + w.completed_count, 0)
  const totalQuizzes = weeks.reduce(
    (sum, w) =>
      sum + w.lectures.reduce((s, l) => s + (l.result_summary?.quiz_count ?? 0), 0),
    0,
  )

  const weekNumbers = weeks.map((w) => w.week)
  const filteredWeeks =
    activeWeek !== null ? weeks.filter((w) => w.week === activeWeek) : weeks

  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '40px 40px 80px' }}>

      {/* 페이지 헤더 */}
      <div className="tml-animate">
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '0.6875rem',
          fontWeight: 600,
          color: 'var(--tml-orange)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          margin: '0 0 8px',
        }}>
          Knowledge Dashboard
        </p>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          fontSize: '1.75rem',
          letterSpacing: '-0.02em',
          color: 'var(--tml-ink)',
          margin: '0 0 28px',
        }}>
          강의 목록
        </h1>
      </div>

      {/* 로딩 상태 */}
      {loading && (
        <div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 32 }}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="tml-skeleton"
                style={{ height: 80, flex: 1, borderRadius: 6 }}
              />
            ))}
          </div>
          <div className="tml-lecture-grid">
            {[...Array(5)].map((_, i) => (
              <LectureCardSkeleton key={i} />
            ))}
          </div>
        </div>
      )}

      {/* 에러 상태 */}
      {!loading && error && (
        <ErrorCard message={error} title="강의 목록 로드 실패" />
      )}

      {/* 통계 + 필터 + 주차 목록 */}
      {!loading && !error && (
        <>
          <DashboardStats
            totalLectures={totalLectures}
            completedLectures={completedLectures}
            totalQuizzes={totalQuizzes}
          />

          {weeks.length === 0 ? (
            <div
              className="tml-empty"
              style={{ padding: '48px 24px', textAlign: 'center' }}
            >
              <p style={{
                fontFamily: 'var(--font-body)',
                color: 'var(--tml-ink-muted)',
                margin: 0,
              }}>
                등록된 강의가 없습니다.
              </p>
            </div>
          ) : (
            <>
              <WeekFilter
                weeks={weekNumbers}
                activeWeek={activeWeek}
                onSelect={handleWeekSelect}
              />

              <div className="tml-week-content" style={{ display: 'flex', flexDirection: 'column', gap: 48 }}>
                {filteredWeeks.map((weekSummary) => (
                  <WeekSection
                    key={weekSummary.week}
                    weekSummary={weekSummary}
                    processingLectures={processingLectures}
                    processingWeeks={processingWeeks}
                    onProcess={handleProcess}
                    onViewResults={(id) => navigate(`/lecture/${id}`)}
                    onProcessComplete={handleProcessComplete}
                    onProcessError={handleProcessError}
                    onProcessWeek={handleProcessWeek}
                    onViewWeekResults={(w) => navigate(`/weekly/${w}`)}
                    onWeekProcessComplete={handleWeekProcessComplete}
                    onWeekProcessError={handleWeekProcessError}
                  />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </main>
  )
}
