import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import type { WeekSummary } from '../types/models'
import { fetchWeeks, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'

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

// ── RecentLectureCard ──

interface RecentLectureCardProps {
  lectureId: string
  date: string
  dayOfWeek: string
  week: number
  courseName: string
  conceptCount: number
  quizCount: number
}

function RecentLectureCard({ lectureId, date, dayOfWeek, week, courseName, conceptCount, quizCount }: RecentLectureCardProps) {
  return (
    <Link
      to={`/lecture/${lectureId}`}
      className="tml-card"
      style={{
        display: 'flex', alignItems: 'center', gap: 16, padding: '16px 20px',
        textDecoration: 'none', color: 'inherit',
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--tml-orange)'
        ;(e.currentTarget as HTMLElement).style.boxShadow = '0 2px 8px var(--tml-shadow-hover)'
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--tml-rule)'
        ;(e.currentTarget as HTMLElement).style.boxShadow = 'none'
      }}
    >
      <div style={{
        width: 44, height: 44, borderRadius: 8,
        background: 'var(--tml-orange)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
      }}>
        W{week}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{
          fontFamily: 'var(--font-body)', fontSize: '0.875rem', fontWeight: 600,
          color: 'var(--tml-ink)', margin: '0 0 2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {date} ({dayOfWeek}) · {courseName}
        </p>
        <p style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)', margin: 0,
        }}>
          개념 {conceptCount}개 · 퀴즈 {quizCount}개
        </p>
      </div>
      <span style={{ fontFamily: 'var(--font-body)', fontSize: '0.8125rem', color: 'var(--tml-orange)', flexShrink: 0 }}>
        →
      </span>
    </Link>
  )
}

// ── WeekGuideStatusCard ──

interface WeekGuideStatusCardProps {
  week: number
  lectureCount: number
  completedCount: number
  status: string
}

function WeekGuideStatusCard({ week, lectureCount, completedCount, status }: WeekGuideStatusCardProps) {
  const isCompleted = status === 'completed'
  return (
    <Link
      to={isCompleted ? `/weekly/${week}` : '/guides'}
      className="tml-card"
      style={{
        display: 'flex', alignItems: 'center', gap: 16, padding: '16px 20px',
        textDecoration: 'none', color: 'inherit',
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--tml-navy-mid)'
        ;(e.currentTarget as HTMLElement).style.boxShadow = '0 2px 8px var(--tml-shadow-hover)'
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.borderColor = 'var(--tml-rule)'
        ;(e.currentTarget as HTMLElement).style.boxShadow = 'none'
      }}
    >
      <div style={{
        width: 44, height: 44, borderRadius: 8,
        background: 'var(--tml-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#fff', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
      }}>
        W{week}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{
          fontFamily: 'var(--font-body)', fontSize: '0.875rem', fontWeight: 600,
          color: 'var(--tml-ink)', margin: '0 0 2px',
        }}>
          {week}주차 학습 가이드
        </p>
        <p style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)', margin: 0,
        }}>
          {lectureCount}강의 · {completedCount}완료
        </p>
      </div>
      <span style={{
        fontFamily: 'var(--font-body)', fontSize: '0.75rem', fontWeight: 600, flexShrink: 0,
        color: isCompleted ? 'var(--tml-correct)' : 'var(--tml-ink-muted)',
      }}>
        {isCompleted ? '완료' : '미생성'}
      </span>
    </Link>
  )
}

// ── Dashboard ──

export function Dashboard() {
  const [weeks, setWeeks] = useState<WeekSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWeeks()
      .then(setWeeks)
      .catch((err) => {
        setError(err instanceof ApiError ? err.detail : '데이터를 불러오지 못했습니다.')
      })
      .finally(() => setLoading(false))
  }, [])

  const totalLectures = weeks.reduce((sum, w) => sum + w.lecture_count, 0)
  const completedLectures = weeks.reduce((sum, w) => sum + w.completed_count, 0)
  const totalQuizzes = weeks.reduce(
    (sum, w) =>
      sum + w.lectures.reduce((s, l) => s + (l.result_summary?.quiz_count ?? 0), 0),
    0,
  )

  // 최근 완료 강의 (최대 3개)
  const recentCompleted = weeks
    .flatMap((w) => w.lectures)
    .filter((l) => l.status === 'completed' && l.result_summary)
    .slice(0, 3)

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
          대시보드
        </h1>
      </div>

      {/* 로딩 */}
      {loading && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 32 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="tml-skeleton" style={{ height: 80, flex: 1, borderRadius: 6 }} />
          ))}
        </div>
      )}

      {/* 에러 */}
      {!loading && error && (
        <ErrorCard message={error} title="데이터 로드 실패" />
      )}

      {/* 콘텐츠 */}
      {!loading && !error && (
        <>
          {/* 통계 */}
          <DashboardStats
            totalLectures={totalLectures}
            completedLectures={completedLectures}
            totalQuizzes={totalQuizzes}
          />

          {/* 2컬럼 레이아웃 */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 5fr) minmax(0, 3fr)',
            gap: 32,
            marginTop: 36,
          }}>
            {/* 왼쪽: 최근 완료 강의 */}
            <div className="tml-animate">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <p className="section-label" style={{ margin: 0 }}>최근 분석 완료</p>
                <Link to="/lectures" style={{
                  fontFamily: 'var(--font-body)', fontSize: '0.8125rem',
                  color: 'var(--tml-orange)', textDecoration: 'none', fontWeight: 600,
                }}>
                  전체 보기 →
                </Link>
              </div>
              {recentCompleted.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {recentCompleted.map((l) => (
                    <RecentLectureCard
                      key={l.lecture_id}
                      lectureId={l.lecture_id}
                      date={l.date}
                      dayOfWeek={l.day_of_week}
                      week={l.week}
                      courseName={l.course_name}
                      conceptCount={l.result_summary!.concept_count}
                      quizCount={l.result_summary!.quiz_count}
                    />
                  ))}
                </div>
              ) : (
                <div className="tml-card" style={{ padding: '32px 24px', textAlign: 'center' }}>
                  <p style={{ fontFamily: 'var(--font-body)', color: 'var(--tml-ink-muted)', margin: '0 0 16px', fontSize: '0.875rem' }}>
                    아직 분석된 강의가 없습니다.
                  </p>
                  <Link to="/lectures" className="btn-primary" style={{ textDecoration: 'none' }}>
                    강의 가져오기 →
                  </Link>
                </div>
              )}
            </div>

            {/* 오른쪽: 학습 가이드 상태 */}
            <div className="tml-animate">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <p className="section-label" style={{ margin: 0 }}>학습 가이드</p>
                <Link to="/guides" style={{
                  fontFamily: 'var(--font-body)', fontSize: '0.8125rem',
                  color: 'var(--tml-navy-mid)', textDecoration: 'none', fontWeight: 600,
                }}>
                  전체 보기 →
                </Link>
              </div>
              {weeks.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {weeks.map((ws) => (
                    <WeekGuideStatusCard
                      key={ws.week}
                      week={ws.week}
                      lectureCount={ws.lecture_count}
                      completedCount={ws.completed_count}
                      status={ws.status}
                    />
                  ))}
                </div>
              ) : (
                <div className="tml-card" style={{ padding: '32px 24px', textAlign: 'center' }}>
                  <p style={{ fontFamily: 'var(--font-body)', color: 'var(--tml-ink-muted)', margin: 0, fontSize: '0.875rem' }}>
                    등록된 주차가 없습니다.
                  </p>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </main>
  )
}
