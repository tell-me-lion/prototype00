import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import type { WeekSummary } from '../types/models'
import { fetchWeeks, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProgressRing } from '../components/ProgressRing'
import { ActivityHeatmap } from '../components/ActivityHeatmap'

/* ── useCountUp ── */

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

/* ── StatCard ── */

interface StatCardProps {
  label: string
  value: number
  accent: string
  delay: number
}

function StatCard({ label, value, accent, delay }: StatCardProps) {
  const display = useCountUp(value)
  return (
    <div className="tml-stat tml-dashboard-stagger" style={{ animationDelay: `${delay}ms` }}>
      <div className="tml-stat__dot" style={{ background: accent }} />
      <span className="tml-stat__label">{label}</span>
      <span className="tml-stat__value">{display}</span>
    </div>
  )
}

/* ── RecentLectureCard (vertical tile) ── */

interface RecentLectureCardProps {
  lectureId: string
  date: string
  dayOfWeek: string
  week: number
  courseName: string
  conceptCount: number
  quizCount: number
  delay: number
}

function RecentLectureCard({
  lectureId, date, dayOfWeek, week, courseName,
  conceptCount, quizCount, delay,
}: RecentLectureCardProps) {
  return (
    <Link
      to={`/lecture/${lectureId}`}
      className="tml-card tml-lecture-tile tml-dashboard-stagger"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="tml-lecture-tile__header">
        <span className="tml-lecture-tile__week">W{week}</span>
        <span className="tml-lecture-tile__arrow">→</span>
      </div>
      <p className="tml-lecture-tile__date">{date} ({dayOfWeek})</p>
      <p className="tml-lecture-tile__course">{courseName}</p>
      <div className="tml-lecture-tile__stats">
        <span className="tml-lecture-tile__stat">
          <span className="tml-lecture-tile__stat-dot" style={{ background: 'var(--tml-quiz-code)' }} />
          개념 {conceptCount}
        </span>
        <span className="tml-lecture-tile__stat">
          <span className="tml-lecture-tile__stat-dot" style={{ background: 'var(--tml-quiz-fill)' }} />
          퀴즈 {quizCount}
        </span>
      </div>
    </Link>
  )
}

/* ── Dashboard ── */

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
  const percent = totalLectures > 0 ? Math.round((completedLectures / totalLectures) * 100) : 0

  const recentCompleted = allLectures
    .filter((l) => l.status === 'completed' && l.result_summary)
    .slice(0, 3)

  const nextLecture = allLectures.find((l) => l.status === 'idle')

  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '40px 40px 80px' }}>
      {/* 로딩 */}
      {loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="tml-skeleton" style={{ height: 220, borderRadius: 16 }} />
          <div style={{ display: 'flex', gap: 12 }}>
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="tml-skeleton" style={{ height: 120, flex: 1, borderRadius: 12 }} />
            ))}
          </div>
        </div>
      )}

      {/* 에러 */}
      {!loading && error && <ErrorCard message={error} title="데이터 로드 실패" />}

      {/* 콘텐츠 */}
      {!loading && !error && (
        <>
          {/* ── 히어로 ── */}
          <section className="tml-hero tml-animate">
            <div className="tml-hero__decor" aria-hidden="true">
              <div className="tml-hero__ring tml-hero__ring--1" />
              <div className="tml-hero__ring tml-hero__ring--2" />
              <div className="tml-hero__ring tml-hero__ring--3" />
              <div className="tml-hero__glow" />
            </div>

            <div className="tml-hero__content">
              <ProgressRing completed={completedLectures} total={totalLectures} />
              <div className="tml-hero__info">
                <p className="tml-hero__eyebrow">Learning Progress</p>
                <h1 className="tml-hero__title">학습 진행률</h1>
                <p className="tml-hero__desc">
                  {totalLectures > 0 ? (
                    <>
                      전체 <strong>{totalLectures}개</strong> 강의 중{' '}
                      <strong>{completedLectures}개</strong> 분석 완료
                      {remainingCount > 0 && (
                        <>, <strong>{remainingCount}개</strong> 남음</>
                      )}
                    </>
                  ) : (
                    '등록된 강의가 없습니다.'
                  )}
                </p>
                {nextLecture && (
                  <Link to="/lectures" className="tml-hero__cta">
                    다음 강의 분석하기
                    <span className="tml-hero__cta-arrow">→</span>
                  </Link>
                )}
              </div>
            </div>

            <div className="tml-hero__bar">
              <div className="tml-hero__bar-fill" style={{ width: `${percent}%` }} />
            </div>
          </section>

          {/* ── 벤토 그리드 ── */}
          <div className="tml-bento tml-animate">
            <StatCard label="전체 강의" value={totalLectures} accent="var(--tml-orange)" delay={0} />
            <StatCard label="분석 완료" value={completedLectures} accent="var(--tml-navy-mid)" delay={80} />
            <StatCard label="생성 퀴즈" value={totalQuizzes} accent="var(--tml-quiz-fill)" delay={160} />
            <StatCard label="핵심 개념" value={totalConcepts} accent="var(--tml-quiz-code)" delay={240} />
            <div
              className="tml-bento__map tml-card tml-dashboard-stagger"
              style={{ animationDelay: '120ms' }}
            >
              <p className="tml-bento__map-label">주간 활동</p>
              <ActivityHeatmap lectures={allLectures} />
            </div>
          </div>

          {/* ── 최근 완료 강의 ── */}
          <div className="tml-animate">
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'center', marginBottom: 16,
            }}>
              <p className="section-label" style={{ margin: 0, paddingTop: 0, borderTop: 'none' }}>
                최근 분석 완료
              </p>
              <Link
                to="/lectures"
                style={{
                  fontFamily: 'var(--font-body)', fontSize: '0.8125rem',
                  color: 'var(--tml-orange)', textDecoration: 'none', fontWeight: 600,
                }}
              >
                전체 보기 →
              </Link>
            </div>
            {recentCompleted.length > 0 ? (
              <div className="tml-recent-grid">
                {recentCompleted.map((l, i) => (
                  <RecentLectureCard
                    key={l.lecture_id}
                    lectureId={l.lecture_id}
                    date={l.date}
                    dayOfWeek={l.day_of_week}
                    week={l.week}
                    courseName={l.course_name}
                    conceptCount={l.result_summary!.concept_count}
                    quizCount={l.result_summary!.quiz_count}
                    delay={i * 80}
                  />
                ))}
              </div>
            ) : (
              <div className="tml-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
                <p style={{
                  fontFamily: 'var(--font-body)', color: 'var(--tml-ink-muted)',
                  margin: '0 0 16px', fontSize: '0.875rem',
                }}>
                  아직 분석된 강의가 없습니다.
                </p>
                <Link to="/lectures" className="btn-primary" style={{ textDecoration: 'none' }}>
                  강의 가져오기 →
                </Link>
              </div>
            )}
          </div>
        </>
      )}
    </main>
  )
}
