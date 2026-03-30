import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { QuizCard } from '../components/QuizCard'
import { SkeletonGroup, ErrorCard } from '../components/Skeleton'
import { fetchLecture, fetchLectureResults, ApiError } from '../services/api'
import type { Lecture, LectureOutputs } from '../types/models'

type PageState =
  | { tag: 'loading' }
  | { tag: 'not-found' }
  | { tag: 'not-ready'; lecture: Lecture }
  | { tag: 'error'; message: string }
  | { tag: 'ready'; lecture: Lecture; outputs: LectureOutputs }

export function QuizPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [state, setState] = useState<PageState>({ tag: 'loading' })
  const [mcqIndex, setMcqIndex] = useState(0)

  useEffect(() => {
    let cancelled = false

    async function load() {
      if (!id) { setState({ tag: 'not-found' }); return }
      setState({ tag: 'loading' })
      try {
        const lecture = await fetchLecture(id)
        if (cancelled) return

        if (lecture.status !== 'completed') {
          setState({ tag: 'not-ready', lecture })
          return
        }

        const outputs = await fetchLectureResults(id)
        if (cancelled) return
        setState({ tag: 'ready', lecture, outputs })
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
        <button className="tml-back-btn tml-animate" onClick={() => navigate('/lectures')}>
          ← 강의 목록
        </button>
        <div className="tml-animate" style={{ marginTop: 32 }}>
          <ErrorCard message="존재하지 않는 강의입니다." />
        </div>
      </main>
    )
  }

  // ── 미처리 ──
  if (state.tag === 'not-ready') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn tml-animate" onClick={() => navigate(`/lecture/${id}`)}>
          ← 강의 결과
        </button>
        <div className="tml-animate tml-card" style={{ marginTop: 32, padding: 32, textAlign: 'center' }}>
          <p style={{
            fontFamily: 'var(--font-display)', fontSize: '1.125rem',
            fontWeight: 600, color: 'var(--tml-ink)', margin: '0 0 8px',
          }}>
            이 강의는 아직 분석되지 않았습니다.
          </p>
          <p style={{
            fontFamily: 'var(--font-body)', fontSize: '0.875rem',
            color: 'var(--tml-ink-muted)', margin: '0 0 24px',
          }}>
            강의 분석을 먼저 진행해 주세요.
          </p>
          <Link to={`/lecture/${id}`} className="btn-primary" style={{ textDecoration: 'none' }}>
            강의 결과 페이지로
          </Link>
        </div>
      </main>
    )
  }

  // ── 에러 ──
  if (state.tag === 'error') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn tml-animate" onClick={() => navigate(`/lecture/${id}`)}>
          ← 강의 결과
        </button>
        <div className="tml-animate" style={{ marginTop: 32 }}>
          <ErrorCard message={state.message} />
        </div>
      </main>
    )
  }

  // ── 퀴즈 렌더링 ──
  const { lecture, outputs } = state
  const { quizzes } = outputs

  const mcqQuizzes   = quizzes.filter((q) => q.type === 'mcq')
  const shortQuizzes = quizzes.filter((q) => q.type === 'short')
  const fillQuizzes  = quizzes.filter((q) => q.type === 'fill')
  const codeQuizzes  = quizzes.filter((q) => q.type === 'code')

  const typeCounts = [
    { label: '객관식', count: mcqQuizzes.length },
    { label: '주관식', count: shortQuizzes.length },
    { label: '빈칸', count: fillQuizzes.length },
    { label: '코드', count: codeQuizzes.length },
  ].filter((t) => t.count > 0)

  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
      {/* 뒤로가기 */}
      <button className="tml-back-btn tml-animate" onClick={() => navigate(`/lecture/${id}`)}>
        ← 강의 결과
      </button>

      {/* 퀴즈 헤더 */}
      <div className="tml-animate" style={{ marginTop: 24, marginBottom: 32 }}>
        <p style={{
          fontFamily: 'var(--font-body)', fontSize: '0.6875rem', fontWeight: 600,
          color: 'var(--tml-orange)', letterSpacing: '0.1em', textTransform: 'uppercase',
          margin: '0 0 12px',
        }}>
          퀴즈 풀기 · Mode A
        </p>

        <div className="tml-card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6, flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: 'var(--tml-ink-muted)' }}>
                  {lecture.date} ({lecture.day_of_week})
                </span>
                <span style={{ color: 'var(--tml-rule-strong)', fontSize: '0.75rem' }}>·</span>
                <span className="badge-orange">Week {lecture.week}</span>
              </div>
              <h1 style={{
                fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.5rem',
                letterSpacing: '-0.02em', color: 'var(--tml-ink)', margin: '0 0 4px',
              }}>
                퀴즈
              </h1>
              <p style={{
                fontFamily: 'var(--font-body)', fontSize: '0.875rem',
                color: 'var(--tml-ink-secondary)', margin: 0,
              }}>
                {lecture.course_name} · 총 {quizzes.length}문항
              </p>
            </div>

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              {typeCounts.map(({ label, count }) => (
                <div key={label} style={{ textAlign: 'center' }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: '1.25rem',
                    fontWeight: 600, color: 'var(--tml-orange)', lineHeight: 1,
                  }}>
                    {count}
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-body)', fontSize: '0.6875rem',
                    color: 'var(--tml-ink-muted)', marginTop: 2,
                  }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 퀴즈 콘텐츠 */}
      {quizzes.length === 0 ? (
        <p style={{ fontFamily: 'var(--font-body)', color: 'var(--tml-ink-muted)', fontSize: '0.875rem' }}>
          이 강의에는 퀴즈가 없습니다.
        </p>
      ) : (
        <div>
          {/* 객관식 */}
          {mcqQuizzes.length > 0 && (
            <div style={{ marginBottom: 40 }} className="tml-animate">
              <p className="section-label">객관식</p>
              <QuizCard
                key={`mcq-${mcqIndex}`}
                quiz={mcqQuizzes[mcqIndex]}
                quizIndex={mcqIndex}
                totalInType={mcqQuizzes.length}
                onNext={mcqIndex + 1 < mcqQuizzes.length ? () => setMcqIndex((i) => i + 1) : undefined}
              />
            </div>
          )}

          {/* 주관식 */}
          {shortQuizzes.length > 0 && (
            <div style={{ marginBottom: 40 }} className="tml-animate">
              <p className="section-label">주관식</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {shortQuizzes.map((q, i) => (
                  <QuizCard key={q.quiz_id} quiz={q} quizIndex={i} totalInType={shortQuizzes.length} />
                ))}
              </div>
            </div>
          )}

          {/* 빈칸 채우기 */}
          {fillQuizzes.length > 0 && (
            <div style={{ marginBottom: 40 }} className="tml-animate">
              <p className="section-label">빈칸 채우기</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {fillQuizzes.map((q, i) => (
                  <QuizCard key={q.quiz_id} quiz={q} quizIndex={i} totalInType={fillQuizzes.length} />
                ))}
              </div>
            </div>
          )}

          {/* 코드 실행형 */}
          {codeQuizzes.length > 0 && (
            <div className="tml-animate">
              <p className="section-label">코드 실행형</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {codeQuizzes.map((q, i) => (
                  <QuizCard key={q.quiz_id} quiz={q} quizIndex={i} totalInType={codeQuizzes.length} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </main>
  )
}
