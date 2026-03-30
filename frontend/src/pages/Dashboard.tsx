import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type { WeekSummary } from '../types/models'
import { fetchWeeks, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProgressRing } from '../components/ProgressRing'
import { ActivityHeatmap } from '../components/ActivityHeatmap'
import { ConceptCloud } from '../components/ConceptCloud'

// ── useCountUp 훅 ──

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

// ── StatCard ──

interface StatCardProps {
  label: string
  value: number
  icon: string
  delay: number
}

function StatCard({ label, value, icon, delay }: StatCardProps) {
  const display = useCountUp(value)
  return (
    <div
      className="tml-stat-card tml-card tml-dashboard-stagger"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="tml-stat-card__header">
        <span className="tml-stat-card__icon">{icon}</span>
        <span className="tml-stat-card__label">{label}</span>
      </div>
      <span className="tml-stat-card__value">{display}</span>
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
      className="tml-card tml-recent-card"
    >
      <div className="tml-recent-card__badge">
        W{week}
      </div>
      <div className="tml-recent-card__body">
        <p className="tml-recent-card__title">
          {date} ({dayOfWeek}) · {courseName}
        </p>
        <p className="tml-recent-card__meta">
          개념 {conceptCount}개 · 퀴즈 {quizCount}개
        </p>
      </div>
      <span className="tml-recent-card__arrow">→</span>
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
  const totalConcepts = weeks.reduce(
    (sum, w) =>
      sum + w.lectures.reduce((s, l) => s + (l.result_summary?.concept_count ?? 0), 0),
    0,
  )

  const allLectures = weeks.flatMap((w) => w.lectures)
  const remainingCount = totalLectures - completedLectures

  // 최근 완료 강의 (최대 3개)
  const recentCompleted = allLectures
    .filter((l) => l.status === 'completed' && l.result_summary)
    .slice(0, 3)

  // 다음 분석할 강의
  const nextLecture = allLectures.find((l) => l.status === 'idle')

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
          {[1, 2, 3, 4].map((i) => (
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
          {/* ── 히어로: 프로그레스 링 + 환영 메시지 ── */}
          <div className="tml-dashboard-hero tml-animate">
            <ProgressRing completed={completedLectures} total={totalLectures} />
            <div className="tml-dashboard-hero__text">
              <h2 className="tml-dashboard-hero__greeting">
                학습 진행률
              </h2>
              <p className="tml-dashboard-hero__summary">
                {totalLectures > 0 ? (
                  <>
                    전체 <strong>{totalLectures}개</strong> 강의 중{' '}
                    <strong>{completedLectures}개</strong> 분석 완료
                    {remainingCount > 0 && <>, <strong>{remainingCount}개</strong> 남음</>}
                  </>
                ) : (
                  '등록된 강의가 없습니다.'
                )}
              </p>
              {nextLecture && (
                <Link
                  to="/lectures"
                  className="btn-primary"
                  style={{ textDecoration: 'none', display: 'inline-block', marginTop: 12 }}
                >
                  다음 강의 분석하기 →
                </Link>
              )}
            </div>
          </div>

          {/* ── 통계 카드 4개 ── */}
          <div className="tml-dashboard-stats tml-animate">
            <StatCard label="전체 강의" value={totalLectures} icon="📚" delay={0} />
            <StatCard label="분석 완료" value={completedLectures} icon="✅" delay={100} />
            <StatCard label="생성 퀴즈" value={totalQuizzes} icon="❓" delay={200} />
            <StatCard label="핵심 개념" value={totalConcepts} icon="💡" delay={300} />
          </div>

          {/* ── 2컬럼: 최근 완료 + 히트맵 ── */}
          <div className="tml-dashboard-grid tml-animate">
            {/* 왼쪽: 최근 완료 강의 */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <p className="section-label" style={{ margin: 0, paddingTop: 0, borderTop: 'none' }}>최근 분석 완료</p>
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

            {/* 오른쪽: 활동 히트맵 */}
            <div>
              <p className="section-label" style={{ margin: '0 0 16px', paddingTop: 0, borderTop: 'none' }}>주간 활동</p>
              <div className="tml-card" style={{ padding: '20px' }}>
                <ActivityHeatmap lectures={allLectures} />
              </div>
            </div>
          </div>

          {/* ── 개념 클라우드 ── */}
          {allLectures.some((l) => l.status === 'completed') && (
            <div className="tml-animate" style={{ marginTop: 36 }}>
              <p className="section-label" style={{ margin: '0 0 16px' }}>최근 학습 키워드</p>
              <div className="tml-card" style={{ padding: '24px' }}>
                <ConceptCloud lectures={allLectures} />
              </div>
            </div>
          )}
        </>
      )}
    </main>
  )
}
