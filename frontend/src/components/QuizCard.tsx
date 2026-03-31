import { useState } from 'react'
import type { Quiz } from '../types/models'
import { CodeEditor } from './CodeEditor'
import { OutputPanel, runTestCases } from './OutputPanel'
import type { TestResult } from './OutputPanel'
import { executeCode } from '../services/piston'

interface QuizCardProps {
  quiz: Quiz
  quizIndex: number
  totalInType: number
  onNext?: () => void
}

const CIRCLE_NUMS = ['①', '②', '③', '④', '⑤', '⑥']

function answerStr(a: string | string[] | null): string {
  return Array.isArray(a) ? a.join(', ') : (a ?? '')
}

/* ── MCQ: 페이지네이션형 ─────────────────────────────── */
function McqCard({ quiz, quizIndex, totalInType, onNext }: QuizCardProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const submitted = selected !== null
  const isCorrect = selected === answerStr(quiz.answer)

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--mcq">MCQ</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      <p className="quiz-question">{quiz.question}</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {quiz.options?.map((opt, i) => {
          const isAnswer = opt === answerStr(quiz.answer)
          const isSelected = selected === opt
          let bg = 'var(--tml-bg-raised)'
          let border = '1px solid var(--tml-rule)'
          let textColor = 'var(--tml-ink-secondary)'
          if (submitted) {
            if (isAnswer)                { bg = 'var(--tml-correct-bg)'; border = '1px solid var(--tml-correct)'; textColor = 'var(--tml-correct)' }
            else if (isSelected)         { bg = 'var(--tml-wrong-bg)'; border = '1px solid var(--tml-wrong)'; textColor = 'var(--tml-wrong)' }
            else                         { textColor = 'var(--tml-ink-muted)' }
          }
          return (
            <button
              key={i}
              onClick={() => { if (!submitted) setSelected(opt) }}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 16px',
                background: bg, border, borderRadius: 6,
                cursor: submitted ? 'default' : 'pointer',
                pointerEvents: submitted ? 'none' : 'auto',
                textAlign: 'left',
                transition: 'background 0.15s ease, border-color 0.15s ease',
                width: '100%',
              }}
            >
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8125rem', color: submitted ? textColor : 'var(--tml-ink-muted)', flexShrink: 0 }}>
                {CIRCLE_NUMS[i]}
              </span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: '0.875rem', color: textColor, fontWeight: submitted && isAnswer ? 600 : 400, flex: 1 }}>
                {opt}
              </span>
              {submitted && isAnswer && <span style={{ color: 'var(--tml-correct)', flexShrink: 0 }}>✓</span>}
              {submitted && isSelected && !isAnswer && <span style={{ color: 'var(--tml-wrong)', flexShrink: 0 }}>✗</span>}
            </button>
          )
        })}
      </div>

      {submitted && (
        <div style={{ marginTop: 20 }}>
          <div className={`quiz-feedback ${isCorrect ? 'quiz-feedback--correct' : 'quiz-feedback--wrong'}`}>
            {isCorrect ? '✓ 정답입니다!' : '✗ 오답입니다.'}
          </div>
          <div className="quiz-explanation">
            <span className="quiz-explanation__icon">💡</span>
            <p className="quiz-explanation__text">{quiz.explanation}</p>
          </div>
          {onNext && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn-primary" onClick={onNext}>다음 문제 →</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── SHORT: 플래시카드형 ─────────────────────────────── */
function ShortCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [flipped, setFlipped] = useState(false)

  return (
    <div
      className={`tml-card quiz-type-card quiz-flash-card${flipped ? ' quiz-flash-card--flipped' : ''}`}
      onClick={!flipped ? () => setFlipped(true) : undefined}
      style={{ cursor: flipped ? 'default' : 'pointer' }}
    >
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--short">주관식</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      {!flipped ? (
        <>
          <p className="quiz-question">{quiz.question}</p>
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 16 }}>
            <span style={{ fontFamily: 'var(--font-body)', fontSize: '0.8125rem', color: 'var(--tml-ink-muted)' }}>
              클릭하여 정답 확인 ▾
            </span>
          </div>
        </>
      ) : (
        <>
          <div style={{ marginBottom: 20 }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)', margin: '0 0 8px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              정답
            </p>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '1.5rem', fontWeight: 700, color: 'var(--tml-orange)', margin: 0, letterSpacing: '-0.02em' }}>
              {answerStr(quiz.answer)}
            </p>
          </div>
          <div className="quiz-explanation" style={{ marginBottom: 24 }}>
            <span className="quiz-explanation__icon">💡</span>
            <p className="quiz-explanation__text">{quiz.explanation}</p>
          </div>
          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <button
              onClick={(e) => { e.stopPropagation(); setFlipped(false) }}
              className="quiz-reset-btn"
            >
              다시 보기
            </button>
          </div>
        </>
      )}
    </div>
  )
}

/* ── FILL: 텍스트 입력형 ─────────────────────────────── */
function FillCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [value, setValue] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null)

  const handleSubmit = () => {
    if (!value.trim()) return
    setIsCorrect(value.trim().toLowerCase() === answerStr(quiz.answer).trim().toLowerCase())
    setSubmitted(true)
  }

  const inputBorder = submitted
    ? `1px solid ${isCorrect ? 'var(--tml-correct)' : 'var(--tml-wrong)'}`
    : '1px solid var(--tml-rule)'

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--fill">빈칸</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      <p className="quiz-question">{quiz.question}</p>

      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !submitted) handleSubmit() }}
          readOnly={submitted}
          placeholder="정답 입력..."
          style={{
            flex: 1,
            fontFamily: 'var(--font-mono)',
            fontSize: '0.875rem',
            padding: '8px 12px',
            background: 'var(--tml-bg-raised)',
            color: 'var(--tml-ink)',
            border: inputBorder,
            borderRadius: 4,
            outline: 'none',
            transition: 'border-color 0.15s ease',
          }}
        />
        {!submitted && (
          <button
            className="btn-primary"
            onClick={handleSubmit}
            style={!value.trim() ? { opacity: 0.4, cursor: 'not-allowed', pointerEvents: 'none' } : {}}
          >
            제출
          </button>
        )}
      </div>

      {submitted && (
        <>
          <div className={`quiz-feedback ${isCorrect ? 'quiz-feedback--correct' : 'quiz-feedback--wrong'}`}>
            <span>{isCorrect ? '✓ 정답입니다!' : '✗ 오답입니다.'}</span>
            {!isCorrect && (
              <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--tml-orange)', marginLeft: 12 }}>
                정답: {answerStr(quiz.answer)}
              </span>
            )}
          </div>
          <div className="quiz-explanation">
            <span className="quiz-explanation__icon">💡</span>
            <p className="quiz-explanation__text">{quiz.explanation}</p>
          </div>
        </>
      )}
    </div>
  )
}

/* ── CODE (정적): 코드 뷰어형 ────────────────────────── */
function StaticCodeCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [showAnswer, setShowAnswer] = useState(false)

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--code">코드</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      <p className="quiz-question">{quiz.question}</p>

      {quiz.code && (
        <pre className="quiz-code-block quiz-code-block--question"><code>{quiz.code}</code></pre>
      )}

      <button className="quiz-reset-btn" onClick={() => setShowAnswer((s) => !s)}>
        정답 보기 {showAnswer ? '▴' : '▾'}
      </button>

      {showAnswer && (
        <div style={{ marginTop: 16 }}>
          <pre className="quiz-code-block quiz-code-block--answer"><code>{answerStr(quiz.answer)}</code></pre>
          <div className="quiz-explanation">
            <span className="quiz-explanation__icon">💡</span>
            <p className="quiz-explanation__text">{quiz.explanation}</p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── CODE (인터랙티브): 에디터 + 실행 + 채점 ─────────── */
function InteractiveCodeCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [running, setRunning] = useState(false)
  const [stdout, setStdout] = useState<string | null>(null)
  const [stderr, setStderr] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<TestResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showAnswer, setShowAnswer] = useState(false)

  const allPassed = testResults?.every((r) => r.passed) ?? false
  const hasResult = stdout !== null || stderr !== null || error !== null

  const handleRun = async (code: string) => {
    setRunning(true)
    setStdout(null)
    setStderr(null)
    setTestResults(null)
    setError(null)

    try {
      const res = await executeCode(quiz.language ?? 'python', code)
      const out = res.run.stdout
      const err = res.compile?.stderr || res.run.stderr

      setStdout(out)
      setStderr(err || null)

      if (quiz.test_cases && quiz.test_cases.length > 0) {
        setTestResults(runTestCases(out, quiz.test_cases))
      } else if (quiz.expected_output) {
        setTestResults(runTestCases(out, [{ expected_output: quiz.expected_output }]))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '코드 실행 중 오류가 발생했습니다.')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--code">코드 실행</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      <p className="quiz-question">{quiz.question}</p>

      <CodeEditor
        language={quiz.language ?? 'python'}
        starterCode={quiz.starter_code ?? ''}
        onRun={handleRun}
        running={running}
      />

      <OutputPanel
        stdout={stdout}
        stderr={stderr}
        testResults={testResults}
        error={error}
      />

      {hasResult && testResults && (
        <div className={`quiz-feedback ${allPassed ? 'quiz-feedback--correct' : 'quiz-feedback--wrong'}`}>
          {allPassed ? '✓ 정답입니다!' : '✗ 테스트를 통과하지 못했습니다.'}
        </div>
      )}

      <button className="quiz-reset-btn" onClick={() => setShowAnswer((s) => !s)}>
        정답 보기 {showAnswer ? '▴' : '▾'}
      </button>

      {showAnswer && (
        <div style={{ marginTop: 16 }}>
          <pre className="quiz-code-block quiz-code-block--answer"><code>{answerStr(quiz.answer)}</code></pre>
          <div className="quiz-explanation">
            <span className="quiz-explanation__icon">💡</span>
            <p className="quiz-explanation__text">{quiz.explanation}</p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── CODE: 분기 — starter_code 유무로 인터랙티브/정적 결정 */
function CodeCard(props: QuizCardProps) {
  if (props.quiz.starter_code) {
    return <InteractiveCodeCard {...props} />
  }
  return <StaticCodeCard {...props} />
}

/* ── 진입점 ──────────────────────────────────────────── */
export function QuizCard({ quiz, quizIndex, totalInType, onNext }: QuizCardProps) {
  switch (quiz.type) {
    case 'mcq':   return <McqCard   quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} onNext={onNext} />
    case 'short': return <ShortCard quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
    case 'fill':  return <FillCard  quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
    case 'code':  return <CodeCard  quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
  }
}
