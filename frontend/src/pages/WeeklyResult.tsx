import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { SkeletonGroup, ErrorCard } from '../components/Skeleton'
import {
  fetchWeek,
  fetchWeekResults,
  fetchWeeks,
  triggerWeekProcess,
  ApiError,
} from '../services/api'
import type { WeekSummary, WeeklyOutputs } from '../types/models'

type PageState =
  | { tag: 'loading' }
  | { tag: 'not-found' }
  | { tag: 'not-processed'; week: WeekSummary; availableWeeks: number[] }
  | { tag: 'error'; message: string }
  | { tag: 'results'; week: WeekSummary; outputs: WeeklyOutputs; availableWeeks: number[] }

export function WeeklyResult() {
  const { week: weekParam } = useParams<{ week: string }>()
  const navigate = useNavigate()
  const week = Number(weekParam)

  const [state, setState] = useState<PageState>({ tag: 'loading' })
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!weekParam || isNaN(week)) {
        setState({ tag: 'not-found' })
        return
      }
      setState({ tag: 'loading' })
      try {
        const [weekData, allWeeks] = await Promise.all([
          fetchWeek(week),
          fetchWeeks(),
        ])
        if (cancelled) return
        const availableWeeks = allWeeks.map((w) => w.week).sort((a, b) => a - b)

        if (!availableWeeks.includes(week)) {
          setState({ tag: 'not-found' })
          return
        }

        if (weekData.status === 'completed') {
          const outputs = await fetchWeekResults(week)
          if (cancelled) return
          setState({ tag: 'results', week: weekData, outputs, availableWeeks })
        } else {
          setState({ tag: 'not-processed', week: weekData, availableWeeks })
        }
      } catch (err) {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 404) {
          setState({ tag: 'not-found' })
        } else {
          setState({
            tag: 'error',
            message: err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.',
          })
        }
      }
    }

    load()
    return () => { cancelled = true }
  }, [week, weekParam, reloadKey])

  const handleTrigger = async () => {
    try {
      await triggerWeekProcess(week)
      setReloadKey((k) => k + 1)
    } catch (err) {
      setState({
        tag: 'error',
        message: err instanceof Error ? err.message : '처리 시작에 실패했습니다.',
      })
    }
  }

  // ── 로딩 ──
  if (state.tag === 'loading') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <SkeletonGroup count={4} variant="card" />
      </main>
    )
  }

  // ── 404 ──
  if (state.tag === 'not-found') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn tml-animate" onClick={() => navigate('/')}>
          ← 대시보드
        </button>
        <div className="tml-animate" style={{ marginTop: 32 }}>
          <ErrorCard message="존재하지 않는 주차입니다. 대시보드에서 주차를 선택해 주세요." />
          <div style={{ marginTop: 20 }}>
            <Link
              to="/"
              className="btn-primary"
              style={{ display: 'inline-block', textDecoration: 'none' }}
            >
              대시보드로 돌아가기
            </Link>
          </div>
        </div>
      </main>
    )
  }

  // ── 에러 ──
  if (state.tag === 'error') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn tml-animate" onClick={() => navigate('/')}>
          ← 대시보드
        </button>
        <div className="tml-animate" style={{ marginTop: 32 }}>
          <ErrorCard message={state.message} />
        </div>
      </main>
    )
  }

  // ── 미처리 ──
  if (state.tag === 'not-processed') {
    const { week: weekData, availableWeeks } = state
    const currentIndex = availableWeeks.indexOf(week)
    const prevWeek = currentIndex > 0 ? availableWeeks[currentIndex - 1] : null
    const nextWeek = currentIndex < availableWeeks.length - 1 ? availableWeeks[currentIndex + 1] : null

    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn tml-animate" onClick={() => navigate('/')}>
          ← 대시보드
        </button>

        <div className="tml-animate" style={{ marginTop: 24, marginBottom: 32 }}>
          <WeekHeader weekData={weekData} prevWeek={prevWeek} nextWeek={nextWeek} />
        </div>

        <div className="tml-animate tml-card" style={{ padding: '32px', textAlign: 'center' }}>
          <p style={{
            fontFamily: 'var(--font-display)',
            fontSize: '1.125rem',
            fontWeight: 600,
            color: 'var(--tml-ink)',
            margin: '0 0 8px',
          }}>
            이 주차의 학습 가이드가 아직 생성되지 않았습니다.
          </p>
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.875rem',
            color: 'var(--tml-ink-muted)',
            margin: '0 0 24px',
          }}>
            {weekData.lecture_count}개 강의 중 {weekData.completed_count}개 분석 완료
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={handleTrigger}>
              지금 생성하기
            </button>
            <Link to="/" style={{
              display: 'inline-flex',
              alignItems: 'center',
              fontFamily: 'var(--font-body)',
              fontSize: '0.875rem',
              color: 'var(--tml-ink-muted)',
              textDecoration: 'none',
              padding: '8px 20px',
              border: '1px solid var(--tml-rule)',
              borderRadius: 6,
            }}>
              대시보드로 돌아가기
            </Link>
          </div>
        </div>
      </main>
    )
  }

  // ── 결과 ──
  const { week: weekData, outputs, availableWeeks } = state
  const guide = outputs.guides.find((g) => g.week === week) ?? outputs.guides[0] ?? null
  const currentIndex = availableWeeks.indexOf(week)
  const prevWeek = currentIndex > 0 ? availableWeeks[currentIndex - 1] : null
  const nextWeek = currentIndex < availableWeeks.length - 1 ? availableWeeks[currentIndex + 1] : null

  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
      {/* 뒤로가기 */}
      <button className="tml-back-btn tml-animate" onClick={() => navigate('/')}>
        ← 대시보드
      </button>

      {/* 주차 헤더 */}
      <div className="tml-animate" style={{ marginTop: 24, marginBottom: 32 }}>
        <WeekHeader weekData={weekData} prevWeek={prevWeek} nextWeek={nextWeek} />
      </div>

      {guide && (
        <div key={week}>
          {/* 핵심 요약 */}
          <div style={{ marginBottom: 40 }} className="tml-animate">
            <p className="section-label">핵심 요약</p>
            <div className="tml-guide-item">
              <div className="tml-guide-item__bar" />
              <div className="tml-guide-item__body">
                <span className="tml-guide-item__num">01</span>
                <p className="tml-guide-item__text">{guide.summary}</p>
              </div>
            </div>
          </div>

          {/* 핵심 개념 태그 */}
          {guide.key_concepts.length > 0 && (
            <div style={{ marginBottom: 40 }} className="tml-animate">
              <p className="section-label">핵심 개념</p>
              <div className="tml-concept-tags">
                {guide.key_concepts.map((concept, i) => (
                  <span key={i} className="tml-concept-tag">
                    {concept}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 이 주차의 강의 */}
      {weekData.lectures.length > 0 && (
        <div className="tml-animate">
          <p className="section-label">이 주차의 강의 — {weekData.lecture_count}개</p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: 12,
          }}>
            {weekData.lectures.map((lecture) => (
              <MiniLectureCard
                key={lecture.lecture_id}
                date={lecture.date}
                dayOfWeek={lecture.day_of_week}
                status={lecture.status}
                lectureId={lecture.lecture_id}
              />
            ))}
          </div>
        </div>
      )}
    </main>
  )
}

// ── 주차 헤더 ─────────────────────────────────────────────

interface WeekHeaderProps {
  weekData: WeekSummary
  prevWeek: number | null
  nextWeek: number | null
}

function WeekHeader({ weekData, prevWeek, nextWeek }: WeekHeaderProps) {
  const navigate = useNavigate()

  return (
    <div>
      <p style={{
        fontFamily: 'var(--font-body)',
        fontSize: '0.6875rem',
        fontWeight: 600,
        color: 'var(--tml-navy-mid)',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        margin: '0 0 12px',
      }}>
        1주치 전체 분석 · Mode B
      </p>

      <div className="tml-card" style={{ padding: '20px 24px' }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
          flexWrap: 'wrap',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                color: 'var(--tml-ink-muted)',
              }}>
                📅 {weekData.date_range}
              </span>
              <span style={{ color: 'var(--tml-rule-strong)', fontSize: '0.75rem' }}>·</span>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.75rem',
                color: 'var(--tml-ink-muted)',
              }}>
                {weekData.lecture_count}개 강의 통합
              </span>
            </div>
            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '1.5rem',
              letterSpacing: '-0.02em',
              color: 'var(--tml-ink)',
              margin: 0,
            }}>
              📚 {weekData.week}주차 학습 가이드
            </h1>
          </div>

          {/* 주차 네비게이션 */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={() => prevWeek !== null && navigate(`/weekly/${prevWeek}`)}
              disabled={prevWeek === null}
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.8125rem',
                color: prevWeek !== null ? 'var(--tml-ink-secondary)' : 'var(--tml-ink-muted)',
                background: 'none',
                border: '1px solid var(--tml-rule)',
                borderRadius: 6,
                padding: '6px 14px',
                cursor: prevWeek !== null ? 'pointer' : 'not-allowed',
                opacity: prevWeek !== null ? 1 : 0.4,
                transition: 'opacity 0.15s',
              }}
            >
              ← 이전 주차
            </button>
            <button
              onClick={() => nextWeek !== null && navigate(`/weekly/${nextWeek}`)}
              disabled={nextWeek === null}
              style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.8125rem',
                color: nextWeek !== null ? 'var(--tml-ink-secondary)' : 'var(--tml-ink-muted)',
                background: 'none',
                border: '1px solid var(--tml-rule)',
                borderRadius: 6,
                padding: '6px 14px',
                cursor: nextWeek !== null ? 'pointer' : 'not-allowed',
                opacity: nextWeek !== null ? 1 : 0.4,
                transition: 'opacity 0.15s',
              }}
            >
              다음 주차 →
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── 미니 강의 카드 ──────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  completed: '✅ 완료',
  processing: '⏳ 처리 중',
  idle: '⏳ 미처리',
  error: '❌ 오류',
}

interface MiniLectureCardProps {
  date: string
  dayOfWeek: string
  status: string
  lectureId: string
}

function MiniLectureCard({ date, dayOfWeek, status, lectureId }: MiniLectureCardProps) {
  const navigate = useNavigate()
  const isCompleted = status === 'completed'

  const mmdd = date.slice(5).replace('-', '/')

  return (
    <button
      onClick={() => isCompleted && navigate(`/lecture/${lectureId}`)}
      style={{
        background: 'var(--tml-bg-raised)',
        border: '1px solid var(--tml-rule)',
        borderRadius: 8,
        padding: '16px 14px',
        textAlign: 'left',
        cursor: isCompleted ? 'pointer' : 'default',
        transition: 'border-color 0.15s, box-shadow 0.15s',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
      onMouseEnter={(e) => {
        if (isCompleted) {
          ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--tml-navy-mid)'
          ;(e.currentTarget as HTMLButtonElement).style.boxShadow = '0 2px 8px var(--tml-shadow-hover)'
        }
      }}
      onMouseLeave={(e) => {
        ;(e.currentTarget as HTMLButtonElement).style.borderColor = 'var(--tml-rule)'
        ;(e.currentTarget as HTMLButtonElement).style.boxShadow = 'none'
      }}
    >
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.8125rem',
        fontWeight: 600,
        color: 'var(--tml-ink)',
      }}>
        {mmdd} {dayOfWeek}
      </span>
      <span style={{
        fontFamily: 'var(--font-body)',
        fontSize: '0.75rem',
        color: isCompleted ? 'var(--tml-navy-mid)' : 'var(--tml-ink-muted)',
      }}>
        {STATUS_LABEL[status] ?? '알 수 없음'}
      </span>
    </button>
  )
}
