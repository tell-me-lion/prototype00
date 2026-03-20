import { useState, useRef } from 'react'
import { ConceptCard } from '../components/ConceptCard'
import { QuizCard } from '../components/QuizCard'
import { SkeletonGroup, ErrorCard } from '../components/Skeleton'

interface Concept {
  week: number | null
  lecture_id: string
  concept: string
  importance: number
  evidence_facts: string[]
  meta: Record<string, string>
}

interface LearningPoint {
  week: number | null
  lecture_id: string
  concept: string
  importance: number
  evidence_facts: string[]
  meta: Record<string, string>
}

interface Quiz {
  quiz_id: string
  status: string
  type: 'mcq' | 'short' | 'fill' | 'code'
  question: string
  options: string[] | null
  answer: string
  explanation: string
  validation_log: Record<string, unknown>
  meta: Record<string, string>
}

// 이력 항목 — localStorage에 저장; 나중에 Supabase로 교체
interface LectureHistory {
  id: string
  filename: string
  lectureId: string
  conceptNames: string[]
  learningPointNames: string[]
  analyzedAt: string
}

const HISTORY_KEY = 'tml-lecture-history'
const HISTORY_MAX = 10

function loadHistory(): LectureHistory[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]')
  } catch {
    return []
  }
}

function saveHistory(entry: LectureHistory) {
  const prev = loadHistory().filter((h) => h.filename !== entry.filename)
  const next = [entry, ...prev].slice(0, HISTORY_MAX)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(next))
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

type LectureStep = 'upload' | 'loading' | 'results' | 'error' | 'quiz'

export function Lecture() {
  const [step, setStep] = useState<LectureStep>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [learningPoints, setLearningPoints] = useState<LearningPoint[]>([])
  const [quizzes, setQuizzes] = useState<Quiz[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [mcqIndex, setMcqIndex] = useState(0)
  const [history, setHistory] = useState<LectureHistory[]>(() => loadHistory())
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
  }

  const handleAnalyze = async () => {
    if (!file) return
    setStep('loading')
    try {
      const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const [conceptsRes, pointsRes, quizzesRes] = await Promise.all([
        fetch(`${API}/api/concepts`),
        fetch(`${API}/api/learning-points`),
        fetch(`${API}/api/quizzes`),
      ])
      if (!conceptsRes.ok || !pointsRes.ok || !quizzesRes.ok) {
        throw new Error('데이터를 불러오는 데 실패했습니다.')
      }
      const [conceptsData, pointsData, quizzesData] = await Promise.all([
        conceptsRes.json() as Promise<Concept[]>,
        pointsRes.json() as Promise<LearningPoint[]>,
        quizzesRes.json() as Promise<Quiz[]>,
      ])
      setConcepts(conceptsData)
      setLearningPoints(pointsData)
      setQuizzes(quizzesData)

      // 이력 저장
      const entry: LectureHistory = {
        id: crypto.randomUUID(),
        filename: file.name,
        lectureId: conceptsData[0]?.lecture_id ?? '—',
        conceptNames: conceptsData.map((c) => c.concept),
        learningPointNames: pointsData.map((lp) => lp.concept),
        analyzedAt: new Date().toISOString(),
      }
      saveHistory(entry)
      setHistory(loadHistory())

      setStep('results')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.')
      setStep('error')
    }
  }

  const handleReset = () => {
    setStep('upload')
    setFile(null)
    setConcepts([])
    setLearningPoints([])
    setQuizzes([])
    setErrorMsg(null)
    setMcqIndex(0)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const lectureId = concepts[0]?.lecture_id ?? '—'

  // 로딩
  if (step === 'loading') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <SkeletonGroup count={4} variant="card" />
      </main>
    )
  }

  // 에러
  if (step === 'error') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn" onClick={handleReset}>← 새 파일 분석</button>
        <div style={{ marginTop: 24 }}>
          <ErrorCard message={errorMsg ?? '알 수 없는 오류가 발생했습니다.'} />
        </div>
      </main>
    )
  }

  // 업로드
  if (step === 'upload') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '80px 40px 80px' }}>
        <div className="tml-upload-layout">

          {/* 왼쪽: 업로드 폼 */}
          <div>
            <div className="tml-animate" style={{ marginBottom: 40 }}>
              <p style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.6875rem',
                fontWeight: 600,
                color: 'var(--tml-orange)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                margin: '0 0 16px',
              }}>
                단일 강의 분석 · Mode A
              </p>
              <h1 style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 700,
                fontSize: '2rem',
                letterSpacing: '-0.02em',
                color: 'var(--tml-ink)',
                margin: '0 0 12px',
                lineHeight: 1.2,
              }}>
                강의 스크립트를<br />
                <span style={{ color: 'var(--tml-orange)' }}>분석합니다.</span>
              </h1>
              <p style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.875rem',
                color: 'var(--tml-ink-muted)',
                margin: 0,
                lineHeight: 1.6,
              }}>
                STT 스크립트 파일을 업로드하면 핵심 개념, 학습 포인트, 퀴즈를 자동 생성합니다.
              </p>
            </div>

            <div
              className="tml-animate tml-empty tml-dropzone"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              {file ? (
                <div className="tml-dropzone__selected">
                  <span className="tml-dropzone__icon">📄</span>
                  <span className="tml-dropzone__filename">{file.name}</span>
                  <span className="tml-dropzone__size">{(file.size / 1024).toFixed(1)} KB</span>
                </div>
              ) : (
                <div className="tml-dropzone__placeholder">
                  <span className="tml-dropzone__icon tml-dropzone__icon--muted">📄</span>
                  <span className="tml-dropzone__hint">클릭하여 파일 선택</span>
                  <span className="tml-dropzone__sub">.txt 파일만 지원됩니다</span>
                </div>
              )}
            </div>

            <div className="tml-animate" style={{ marginTop: 20 }}>
              <button
                className="btn-primary"
                onClick={handleAnalyze}
                style={{
                  width: '100%',
                  padding: '12px 24px',
                  fontSize: '0.9375rem',
                  ...(!file ? { opacity: 0.4, cursor: 'not-allowed', pointerEvents: 'none' } : {}),
                }}
              >
                분석 시작하기
              </button>
            </div>
          </div>

          {/* 오른쪽: 이전 분석 이력 */}
          <div className="tml-history-panel">
            <p style={{
              fontSize: '0.6875rem',
              fontWeight: 600,
              color: 'var(--tml-ink-muted)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              margin: '0 0 4px',
              fontFamily: 'var(--font-body)',
            }}>
              이전 분석 이력
            </p>

            {history.length === 0 ? (
              <div className="tml-card" style={{ padding: '20px 18px' }}>
                <p style={{
                  fontSize: '0.8125rem',
                  color: 'var(--tml-ink-muted)',
                  fontFamily: 'var(--font-body)',
                  margin: 0,
                  textAlign: 'center',
                }}>
                  아직 분석한 강의가 없습니다.
                </p>
              </div>
            ) : (
              history.map((h) => (
                <div key={h.id} className="tml-card tml-history-item" style={{ padding: '14px 16px' }}>
                  <div className="tml-history-item__title">{h.filename}</div>
                  <div className="tml-history-item__tags">
                    {h.conceptNames.slice(0, 3).map((name) => (
                      <span key={name} className="tml-history-item__tag">{name}</span>
                    ))}
                    {h.learningPointNames.slice(0, 2).map((name) => (
                      <span key={name} className="tml-history-item__tag" style={{ opacity: 0.7 }}>{name}</span>
                    ))}
                  </div>
                  <div className="tml-history-item__meta">
                    <span style={{ fontFamily: 'var(--font-mono)' }}>{h.lectureId}</span>
                    <span style={{ margin: '0 6px', color: 'var(--tml-rule-strong)' }}>·</span>
                    {formatDate(h.analyzedAt)}
                  </div>
                </div>
              ))
            )}
          </div>

        </div>
      </main>
    )
  }

  // 퀴즈 화면
  if (step === 'quiz') {
    const mcqQuizzes   = quizzes.filter((q) => q.type === 'mcq')
    const shortQuizzes = quizzes.filter((q) => q.type === 'short')
    const fillQuizzes  = quizzes.filter((q) => q.type === 'fill')
    const codeQuizzes  = quizzes.filter((q) => q.type === 'code')

    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <button className="tml-back-btn tml-animate" onClick={() => setStep('results')}>
          ← 분석 결과로
        </button>

        <div className="tml-animate" style={{ marginBottom: 40, marginTop: 24 }}>
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: 'var(--tml-orange)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            margin: '0 0 12px',
          }}>
            단일 강의 분석 · Mode A
          </p>
          <h1 style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            fontSize: '2rem',
            letterSpacing: '-0.02em',
            color: 'var(--tml-ink)',
            margin: '0 0 8px',
          }}>
            퀴즈
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
              {lectureId}
            </span>
            <span style={{ color: 'var(--tml-rule-strong)', fontSize: '0.75rem' }}>·</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
              {quizzes.length}문제
            </span>
          </div>
        </div>

        {/* 객관식 */}
        {mcqQuizzes.length > 0 && (
          <div className="tml-animate" style={{ marginBottom: 40 }}>
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
          <div className="tml-animate" style={{ marginBottom: 40 }}>
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
          <div className="tml-animate" style={{ marginBottom: 40 }}>
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
      </main>
    )
  }

  // 결과 화면
  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
      <button className="tml-back-btn tml-animate" onClick={handleReset}>
        ← 새 파일 분석
      </button>

      <div className="tml-animate" style={{ marginBottom: 40, marginTop: 24 }}>
        <p style={{
          fontFamily: 'var(--font-body)',
          fontSize: '0.6875rem',
          fontWeight: 600,
          color: 'var(--tml-orange)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          margin: '0 0 12px',
        }}>
          단일 강의 분석 · Mode A
        </p>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          fontSize: '2rem',
          letterSpacing: '-0.02em',
          color: 'var(--tml-ink)',
          margin: '0 0 8px',
        }}>
          강의 분석 결과
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
            {lectureId}
          </span>
          {file && (
            <>
              <span style={{ color: 'var(--tml-rule-strong)', fontSize: '0.75rem' }}>·</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
                {file.name}
              </span>
            </>
          )}
        </div>
      </div>

      {/* 핵심 개념 섹션 */}
      <div className="tml-animate">
        <p className="section-label">핵심 개념 — {concepts.length}개</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {concepts.map((c, i) => (
            <div key={`${c.lecture_id}-${c.concept}-${i}`} className="tml-animate">
              <ConceptCard concept={c} />
            </div>
          ))}
        </div>
      </div>

      {/* 학습 포인트 섹션 */}
      <div className="tml-animate" style={{ marginTop: 40 }}>
        <p className="section-label">학습 포인트 — {learningPoints.length}개</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {learningPoints.map((lp, i) => (
            <div key={`lp-${i}`} className="tml-card learning-point-item tml-animate">
              <span className="learning-point-check">✓</span>
              <span className="learning-point-text">{lp.concept}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 퀴즈 CTA */}
      <div className="tml-animate tml-quiz-cta" style={{ marginTop: 48 }}>
        <div>
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.875rem',
            color: 'var(--tml-ink-secondary)',
            margin: 0,
          }}>
            퀴즈 {quizzes.length}문제가 준비됐습니다.
          </p>
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.75rem',
            color: 'var(--tml-ink-muted)',
            margin: '4px 0 0',
          }}>
            MCQ · 주관식 · 빈칸 채우기 · 코드 실행형
          </p>
        </div>
        <button className="btn-primary" onClick={() => setStep('quiz')}>
          퀴즈 풀러 가기 →
        </button>
      </div>
    </main>
  )
}
