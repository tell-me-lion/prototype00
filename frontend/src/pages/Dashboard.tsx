import { useState, useEffect, useRef, useCallback } from 'react'
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

/* ── HeroCard (3D tilt + aurora) ── */

interface HeroCardProps {
  completedLectures: number
  totalLectures: number
  remainingCount: number
  percent: number
  hasNext: boolean
}

function HeroCard({ completedLectures, totalLectures, remainingCount, percent, hasNext }: HeroCardProps) {
  const cardRef = useRef<HTMLElement>(null)
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 })
  const [isHovering, setIsHovering] = useState(false)
  const rafId = useRef(0)

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height
    cancelAnimationFrame(rafId.current)
    rafId.current = requestAnimationFrame(() => setMousePos({ x, y }))
  }, [])

  const tiltX = isHovering ? (mousePos.y - 0.5) * -8 : 0
  const tiltY = isHovering ? (mousePos.x - 0.5) * 8 : 0
  const glareX = mousePos.x * 100
  const glareY = mousePos.y * 100

  return (
    <section
      ref={cardRef}
      className="tml-hero tml-animate"
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => { setIsHovering(false); setMousePos({ x: 0.5, y: 0.5 }) }}
      style={{
        transform: `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg)`,
        transition: isHovering ? 'transform 0.1s ease-out' : 'transform 0.4s ease-out',
      }}
    >
      {/* 레이어 1: 메쉬 그라디언트 (애니메이션) */}
      <div className="tml-hero__mesh" aria-hidden="true" />

      {/* 레이어 2: 노이즈 텍스처 */}
      <div className="tml-hero__noise" aria-hidden="true" />

      {/* 레이어 3: 플로팅 오브 */}
      <div className="tml-hero__decor" aria-hidden="true">
        <div className="tml-hero__orb tml-hero__orb--1" />
        <div className="tml-hero__orb tml-hero__orb--2" />
        <div className="tml-hero__orb tml-hero__orb--3" />
        <div className="tml-hero__orb tml-hero__orb--4" />
      </div>

      {/* 레이어 4: 마우스 따라가는 글레어 */}
      {isHovering && (
        <div
          className="tml-hero__glare"
          style={{
            background: `radial-gradient(circle at ${glareX}% ${glareY}%, rgba(255,140,0,0.15) 0%, transparent 60%)`,
          }}
        />
      )}

      {/* 레이어 5: 스캔라인 */}
      <div className="tml-hero__scanline" aria-hidden="true" />

      {/* 콘텐츠 */}
      <div className="tml-hero__content">
        <ProgressRing completed={completedLectures} total={totalLectures} />
        <div className="tml-hero__info">
          <p className="tml-hero__eyebrow">Learning Progress</p>
          <h1 className="tml-hero__title">
            <span className="tml-hero__title-gradient">학습 진행률</span>
          </h1>
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
          {hasNext && (
            <Link to="/lectures" className="tml-hero__cta">
              <span className="tml-hero__cta-pulse" />
              다음 강의 분석하기
              <span className="tml-hero__cta-arrow">→</span>
            </Link>
          )}
        </div>
      </div>

      {/* 프로그레스 바 */}
      <div className="tml-hero__bar">
        <div className="tml-hero__bar-fill" style={{ width: `${percent}%` }} />
        <div className="tml-hero__bar-glow" style={{ left: `${percent}%` }} />
      </div>

      {/* 하단 빛 보더 */}
      <div className="tml-hero__border-glow" aria-hidden="true" />
    </section>
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
          <HeroCard
            completedLectures={completedLectures}
            totalLectures={totalLectures}
            remainingCount={remainingCount}
            percent={percent}
            hasNext={!!nextLecture}
          />

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
