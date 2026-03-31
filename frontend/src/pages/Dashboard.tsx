import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import type { WeekSummary } from '../types/models'
import { fetchWeeks, ApiError } from '../services/api'
import { ErrorCard } from '../components/Skeleton'
import { ProgressRing } from '../components/ProgressRing'
import { ActivityHeatmap } from '../components/ActivityHeatmap'

/* ── useScrollReveal ── */
function useScrollReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) {
      el.classList.add('tml-revealed')
      return
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add('tml-revealed')
          observer.unobserve(el)
        }
      },
      { threshold: 0.15 },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])
  return ref
}

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

/* ── StatChip (compact inline) ── */

interface StatChipProps {
  label: string
  value: number
  accent: string
  delay: number
}

function StatChip({ label, value, accent, delay }: StatChipProps) {
  const display = useCountUp(value)
  return (
    <div
      className="tml-stat-chip tml-dashboard-stagger"
      style={{ animationDelay: `${delay}ms` }}
    >
      <span className="tml-stat-chip__dot" style={{ background: accent }} />
      <span className="tml-stat-chip__label">{label}</span>
      <span className="tml-stat-chip__value">{display}</span>
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
          <span className="tml-lecture-tile__mini-bar">
            <span
              className="tml-lecture-tile__mini-bar-fill"
              style={{ width: `${Math.min(conceptCount * 10, 100)}%`, background: 'var(--tml-quiz-code)' }}
            />
          </span>
        </span>
        <span className="tml-lecture-tile__stat">
          <span className="tml-lecture-tile__stat-dot" style={{ background: 'var(--tml-quiz-fill)' }} />
          퀴즈 {quizCount}
          <span className="tml-lecture-tile__mini-bar">
            <span
              className="tml-lecture-tile__mini-bar-fill"
              style={{ width: `${Math.min(quizCount * 10, 100)}%`, background: 'var(--tml-quiz-fill)' }}
            />
          </span>
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
      {/* 레이어 1: 메쉬 그라디언트 */}
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
      {/* 레이어 4: 마우스 글레어 */}
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
          <p className="tml-hero__subtitle">
            강의 녹화본에서 핵심 개념·퀴즈를 자동 생성합니다
          </p>
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

  /* 이번 주 (마지막 주차) 데이터 */
  const currentWeek = weeks.length > 0 ? weeks[weeks.length - 1] : null
  const weekPercent = currentWeek
    ? Math.round((currentWeek.completed_count / currentWeek.lecture_count) * 100)
    : 0

  return (
    <div className="tml-dashboard-bg">
      <main style={{ maxWidth: 1280, margin: '0 auto', padding: '40px 40px 80px' }}>
        {/* 로딩 */}
        {loading && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="tml-skeleton" style={{ height: 220, borderRadius: 16 }} />
            <div style={{ display: 'flex', gap: 12 }}>
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="tml-skeleton" style={{ height: 48, flex: 1, borderRadius: 12 }} />
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

            {/* ── 스탯 칩 (인라인) ── */}
            <div className="tml-stat-chips tml-animate">
              <StatChip label="전체 강의" value={totalLectures} accent="var(--tml-orange)" delay={0} />
              <StatChip label="분석 완료" value={completedLectures} accent="var(--tml-navy-mid)" delay={80} />
              <StatChip label="생성 퀴즈" value={totalQuizzes} accent="var(--tml-quiz-fill)" delay={160} />
              <StatChip label="핵심 개념" value={totalConcepts} accent="var(--tml-quiz-code)" delay={240} />
            </div>

            {/* ── 메인 콘텐츠 2컬럼 ── */}
            <div className="tml-dash-grid tml-animate" style={{ animationDelay: '120ms' }}>
              {/* 이번 주 학습 요약 */}
              <div className="tml-glass-card tml-dashboard-stagger" style={{ animationDelay: '120ms' }}>
                <p className="tml-glass-card__label">
                  <span className="tml-glass-card__pulse" />
                  이번 주 학습 요약
                </p>
                {currentWeek ? (
                  <div className="tml-glass-card__body">
                    <div className="tml-glass-card__row">
                      <span className="tml-glass-card__key">주차</span>
                      <span className="tml-glass-card__val">{currentWeek.week}주차</span>
                    </div>
                    <div className="tml-glass-card__row">
                      <span className="tml-glass-card__key">강의 수</span>
                      <span className="tml-glass-card__val">{currentWeek.lecture_count}개</span>
                    </div>
                    <div className="tml-glass-card__row">
                      <span className="tml-glass-card__key">완료율</span>
                      <span className="tml-glass-card__val">{weekPercent}%</span>
                    </div>
                    <div className="tml-glass-card__bar-wrap">
                      <div className="tml-glass-card__bar">
                        <div className="tml-glass-card__bar-fill" style={{ width: `${weekPercent}%` }} />
                      </div>
                    </div>
                    <Link to={`/weekly/${currentWeek.week}`} className="tml-glass-card__cta">
                      주차 가이드 보기 →
                    </Link>
                  </div>
                ) : (
                  <p className="tml-glass-card__empty">등록된 주차 데이터가 없습니다.</p>
                )}
              </div>

              {/* 빠른 시작 */}
              <div className="tml-glass-card tml-dashboard-stagger" style={{ animationDelay: '200ms' }}>
                <p className="tml-glass-card__label">
                  <span className="tml-glass-card__pulse" />
                  빠른 시작
                </p>
                <div className="tml-glass-card__body">
                  <p className="tml-glass-card__desc">
                    강의를 선택하면 AI가 핵심 개념, 학습 포인트, 퀴즈를 자동으로 생성합니다.
                  </p>
                  <Link to="/lectures" className="tml-glass-card__btn">
                    새 강의 분석하기 →
                  </Link>
                  <Link to="/lectures" className="tml-glass-card__link">
                    전체 강의 목록 보기
                  </Link>
                </div>
              </div>
            </div>

            {/* ── 최근 완료 강의 ── */}
            <ScrollRevealSection>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', marginBottom: 16,
              }}>
                <p className="tml-dash-section-label">
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
                <div className="tml-glass-card" style={{ padding: '48px 24px', textAlign: 'center' }}>
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
            </ScrollRevealSection>

            {/* ── Activity Heatmap (하단 독립 섹션) ── */}
            <ScrollRevealSection>
              <div className="tml-glass-card tml-heatmap-section">
                <p className="tml-glass-card__label">
                  <span className="tml-glass-card__pulse" />
                  ACTIVITY
                </p>
                <ActivityHeatmap lectures={allLectures} />
              </div>
            </ScrollRevealSection>
          </>
        )}
      </main>
    </div>
  )
}

/* ── ScrollRevealSection ── */

function ScrollRevealSection({ children }: { children: React.ReactNode }) {
  const ref = useScrollReveal<HTMLDivElement>()
  return (
    <div ref={ref} className="tml-scroll-reveal">
      {children}
    </div>
  )
}
