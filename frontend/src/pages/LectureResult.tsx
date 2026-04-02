import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ConceptCard } from '../components/ConceptCard'
import { LearningPointCard } from '../components/LearningPointCard'
import { SkeletonGroup, ErrorCard } from '../components/Skeleton'
import { ProcessingStatus } from '../components/ProcessingStatus'
import {
  fetchLecture,
  fetchLectureResults,
  fetchLectureStatus,
  triggerLectureProcess,
  ApiError,
} from '../services/api'
import type { Lecture, LectureOutputs } from '../types/models'

type ResultSection = 'concepts' | 'learning-points'

type PageState =
  | { tag: 'loading' }
  | { tag: 'not-found' }
  | { tag: 'not-processed'; lecture: Lecture }
  | { tag: 'processing'; lecture: Lecture }
  | { tag: 'results'; lecture: Lecture; outputs: LectureOutputs }
  | { tag: 'error'; message: string }

const SECTION_TABS: { key: ResultSection; label: string }[] = [
  { key: 'concepts', label: '핵심 개념' },
  { key: 'learning-points', label: '학습 포인트' },
]

export function LectureResult() {
  const { id } = useParams<{ id: string }>()
  const [state, setState] = useState<PageState>({ tag: 'loading' })
  const [activeSection, setActiveSection] = useState<ResultSection>('concepts')

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!id) {
        setState({ tag: 'not-found' })
        return
      }
      setState({ tag: 'loading' })
      try {
        const [lecture, jobStatus] = await Promise.all([
          fetchLecture(id!),
          fetchLectureStatus(id!).catch(() => null),
        ])
        if (cancelled) return

        const isCompleted =
          lecture.status === 'completed' || jobStatus?.status === 'completed'
        const isProcessing =
          lecture.status === 'processing' || jobStatus?.status === 'processing'

        if (isCompleted) {
          const outputs = await fetchLectureResults(id!)
          if (cancelled) return
          setState({ tag: 'results', lecture, outputs })
        } else if (isProcessing) {
          setState({ tag: 'processing', lecture })
        } else {
          setState({ tag: 'not-processed', lecture })
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
  }, [id])

  const handleStartProcess = async () => {
    if (!id) return
    try {
      await triggerLectureProcess(id)
      if (state.tag !== 'not-processed' && state.tag !== 'results') return
      const { lecture } = state
      setState({ tag: 'processing', lecture })
    } catch (err) {
      setState({
        tag: 'error',
        message: err instanceof Error ? err.message : '처리 시작에 실패했습니다.',
      })
    }
  }

  const handleProcessingComplete = async () => {
    if (!id) return
    try {
      const [lecture, outputs] = await Promise.all([
        fetchLecture(id),
        fetchLectureResults(id),
      ])
      setState({ tag: 'results', lecture, outputs })
    } catch (err) {
      setState({
        tag: 'error',
        message: err instanceof Error ? err.message : '결과 로딩에 실패했습니다.',
      })
    }
  }

  // ── 로딩 ──
  if (state.tag === 'loading') {
    return (
      <main className="tml-page-container">
        <SkeletonGroup count={4} variant="card" />
      </main>
    )
  }

  // ── 존재하지 않는 강의 ──
  if (state.tag === 'not-found') {
    return (
      <main className="tml-page-container">
        <div className="tml-animate">
          <ErrorCard message="존재하지 않는 강의입니다. 강의 ID를 확인해 주세요." />
          <div style={{ marginTop: 20 }}>
            <Link
              to="/lectures"
              className="btn-primary"
              style={{ display: 'inline-block', textDecoration: 'none' }}
            >
              강의 목록으로 돌아가기
            </Link>
          </div>
        </div>
      </main>
    )
  }

  // ── 에러 ──
  if (state.tag === 'error') {
    return (
      <main className="tml-page-container">
        <div className="tml-animate">
          <ErrorCard message={state.message} />
        </div>
      </main>
    )
  }

  // ── 미처리 강의 ──
  if (state.tag === 'not-processed') {
    const { lecture } = state
    return (
      <main className="tml-page-container">
        <div className="tml-animate" style={{ marginBottom: 32 }}>
          <LectureHeader lecture={lecture} />
        </div>

        <div className="tml-animate tml-card" style={{ padding: '32px', textAlign: 'center' }}>
          <p style={{
            fontFamily: 'var(--font-display)',
            fontSize: '1.125rem',
            fontWeight: 600,
            color: 'var(--tml-ink)',
            margin: '0 0 8px',
          }}>
            이 강의는 아직 분석되지 않았습니다.
          </p>
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.875rem',
            color: 'var(--tml-ink-muted)',
            margin: '0 0 24px',
          }}>
            분석을 시작하면 핵심 개념, 학습 포인트, 퀴즈를 자동으로 생성합니다.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={handleStartProcess}>
              지금 분석하기
            </button>
            <Link to="/lectures" style={{
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
              강의 목록으로 돌아가기
            </Link>
          </div>
        </div>
      </main>
    )
  }

  // ── 처리 중 ──
  if (state.tag === 'processing') {
    const { lecture } = state
    return (
      <main className="tml-page-container">
        <div className="tml-animate" style={{ marginBottom: 32 }}>
          <LectureHeader lecture={lecture} />
        </div>

        <div className="tml-animate">
          <p className="section-label">처리 현황</p>
          <ProcessingStatus
            lectureId={lecture.lecture_id}
            onComplete={handleProcessingComplete}
          />
        </div>
      </main>
    )
  }

  // ── 결과 ──
  const { lecture, outputs } = state
  const { concepts, learning_points, quizzes } = outputs

  return (
    <main className="tml-page-container">
      {/* 강의 헤더 */}
      <div className="tml-animate" style={{ marginBottom: 32 }}>
        <LectureHeader lecture={lecture} outputs={outputs} />
      </div>

      {/* 섹션 탭 */}
      <div className="tml-animate tml-week-tabs" role="tablist" aria-label="강의 결과 섹션" style={{ marginBottom: 24 }}>
        {SECTION_TABS.map(({ key, label }) => (
          <button
            key={key}
            role="tab"
            aria-selected={activeSection === key}
            aria-controls={`tabpanel-${key}`}
            className={`tml-week-tab${activeSection === key ? ' tml-week-tab--active' : ''}`}
            onClick={() => setActiveSection(key)}
          >
            {label}
            {key === 'concepts' && (
              <span style={{ marginLeft: 6, fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
                {concepts.length}
              </span>
            )}
            {key === 'learning-points' && (
              <span style={{ marginLeft: 6, fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
                {learning_points.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* 섹션 콘텐츠 */}
      <div
        key={activeSection}
        role="tabpanel"
        id={`tabpanel-${activeSection}`}
        aria-label={SECTION_TABS.find(t => t.key === activeSection)?.label}
        style={{ animation: 'tml-rise 0.2s cubic-bezier(0.16, 1, 0.3, 1) both' }}
      >
        {/* 핵심 개념 */}
        {activeSection === 'concepts' && (
          <div>
            <p className="section-label">핵심 개념 — {concepts.length}개</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {concepts.map((c, i) => (
                <div key={`${c.lecture_id}-${c.concept}-${i}`} className="tml-animate">
                  <ConceptCard concept={c} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 학습 포인트 */}
        {activeSection === 'learning-points' && (
          <div>
            <p className="section-label">학습 포인트 — {learning_points.length}개</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {learning_points.map((lp, i) => (
                <div key={`lp-${i}`} className="tml-animate">
                  <LearningPointCard point={lp} />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 퀴즈 CTA */}
      {quizzes.length > 0 && (
        <div className="tml-quiz-cta tml-animate" style={{ marginTop: 32 }}>
          <div>
            <p style={{
              fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600,
              color: 'var(--tml-ink)', margin: '0 0 4px',
            }}>
              퀴즈 풀기
            </p>
            <p style={{
              fontFamily: 'var(--font-body)', fontSize: '0.8125rem',
              color: 'var(--tml-ink-muted)', margin: 0,
            }}>
              {quizzes.length}개의 퀴즈가 준비되어 있습니다
            </p>
          </div>
          <Link
            to={`/lecture/${id}/quiz`}
            className="btn-primary"
            style={{ textDecoration: 'none', flexShrink: 0 }}
          >
            퀴즈 시작 →
          </Link>
        </div>
      )}
    </main>
  )
}

// ── 강의 헤더 컴포넌트 ───────────────────────────────────

interface LectureHeaderProps {
  lecture: Lecture
  outputs?: LectureOutputs
}

function LectureHeader({ lecture, outputs }: LectureHeaderProps) {
  return (
    <div>
      <p style={{
        fontFamily: 'var(--font-body)',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: 'var(--tml-orange)',
        letterSpacing: '0.1em',
        textTransform: 'uppercase',
        margin: '0 0 12px',
      }}>
        단일 강의 분석 · Mode A
      </p>

      <div className="tml-card" style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
              <span style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.8125rem',
                color: 'var(--tml-ink-muted)',
              }}>
                📅 {lecture.date} ({lecture.day_of_week})
              </span>
              <span style={{ color: 'var(--tml-rule-strong)', fontSize: '0.75rem' }}>·</span>
              <span className="badge-orange">Week {lecture.week}</span>
            </div>

            <h1 style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 700,
              fontSize: '1.5rem',
              letterSpacing: '-0.02em',
              color: 'var(--tml-ink)',
              margin: '0 0 4px',
            }}>
              강의 결과
            </h1>
            <p style={{
              fontFamily: 'var(--font-body)',
              fontSize: '0.875rem',
              color: 'var(--tml-ink-secondary)',
              margin: 0,
            }}>
              {lecture.course_name}
            </p>
          </div>

          {outputs && (
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <ResultStat label="개념" value={outputs.concepts.length} />
              <ResultStat label="학습포인트" value={outputs.learning_points.length} />
              <ResultStat label="퀴즈" value={outputs.quizzes.length} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface ResultStatProps {
  label: string
  value: number
}

function ResultStat({ label, value }: ResultStatProps) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '1.25rem',
        fontWeight: 600,
        color: 'var(--tml-orange)',
        lineHeight: 1,
      }}>
        {value}
      </div>
      <div style={{
        fontFamily: 'var(--font-body)',
        fontSize: '0.75rem',
        color: 'var(--tml-ink-muted)',
        marginTop: 2,
      }}>
        {label}
      </div>
    </div>
  )
}
