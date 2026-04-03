import { useState } from 'react'
import type { Quiz } from '../types/models'

interface QuizCardProps {
  quiz: Quiz
  quizIndex: number
  totalInType: number
  onNext?: () => void
}

const CIRCLE_NUMS = ['①', '②', '③', '④', '⑤', '⑥']

/* ── MCQ: 페이지네이션형 ─────────────────────────────── */
function McqCard({ quiz, quizIndex, totalInType, onNext }: QuizCardProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const submitted = selectedId !== null

  const correctChoice = quiz.choices?.find((c) => c.is_answer)
  const isCorrect = submitted && selectedId === correctChoice?.id

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--mcq">MCQ</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
        {quiz.difficulty && (
          <span className="quiz-meta-id" style={{ marginLeft: 8 }}>난이도: {quiz.difficulty}</span>
        )}
      </div>

      <p className="quiz-question">{quiz.question}</p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {quiz.choices?.map((choice, i) => {
          const isAnswer = choice.is_answer
          const isSelected = selectedId === choice.id
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
              key={choice.id}
              onClick={() => { if (!submitted) setSelectedId(choice.id) }}
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
                {CIRCLE_NUMS[i] ?? `(${i + 1})`}
              </span>
              <span style={{ fontFamily: 'var(--font-body)', fontSize: '0.875rem', color: textColor, fontWeight: submitted && isAnswer ? 600 : 400, flex: 1 }}>
                {choice.text}
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
          {quiz.source_text && (
            <div className="quiz-explanation" style={{ marginBottom: 8 }}>
              <span className="quiz-explanation__icon">📖</span>
              <p className="quiz-explanation__text" style={{ fontSize: '0.8125rem', color: 'var(--tml-ink-muted)' }}>{quiz.source_text}</p>
            </div>
          )}
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

/* ── OX: O/X 퀴즈형 ────────────────────────────────── */
function OxCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const submitted = selected !== null
  const isCorrect = submitted && selected === quiz.answers

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--short">O/X</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      <p className="quiz-question">{quiz.question}</p>

      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 16 }}>
        {['O', 'X'].map((opt) => {
          const isAnswer = opt === quiz.answers
          const isSelected = selected === opt
          let bg = 'var(--tml-bg-raised)'
          let border = '1px solid var(--tml-rule)'
          let textColor = 'var(--tml-ink-secondary)'
          if (submitted) {
            if (isAnswer)        { bg = 'var(--tml-correct-bg)'; border = '1px solid var(--tml-correct)'; textColor = 'var(--tml-correct)' }
            else if (isSelected) { bg = 'var(--tml-wrong-bg)'; border = '1px solid var(--tml-wrong)'; textColor = 'var(--tml-wrong)' }
          }
          return (
            <button
              key={opt}
              onClick={() => { if (!submitted) setSelected(opt) }}
              style={{
                width: 80, height: 80,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '2rem', fontWeight: 700,
                background: bg, border, borderRadius: 12,
                cursor: submitted ? 'default' : 'pointer',
                pointerEvents: submitted ? 'none' : 'auto',
                color: textColor,
                transition: 'all 0.15s ease',
              }}
            >
              {opt}
            </button>
          )
        })}
      </div>

      {submitted && (
        <>
          <div className={`quiz-feedback ${isCorrect ? 'quiz-feedback--correct' : 'quiz-feedback--wrong'}`}>
            {isCorrect ? '✓ 정답입니다!' : `✗ 오답입니다. 정답: ${quiz.answers}`}
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

/* ── FILL: 텍스트 입력형 ─────────────────────────────── */
function FillCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [value, setValue] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null)

  const handleSubmit = () => {
    if (!value.trim()) return
    setIsCorrect(value.trim().toLowerCase() === (quiz.answers ?? '').trim().toLowerCase())
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
                정답: {quiz.answers}
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

/* ── CODE: 코드 뷰어형 ──────────────────────────────── */
function CodeCard({ quiz, quizIndex, totalInType }: QuizCardProps) {
  const [showAnswer, setShowAnswer] = useState(false)

  return (
    <div className="tml-card quiz-type-card">
      <div className="quiz-type-card__meta">
        <span className="quiz-badge quiz-badge--code">코드 분석</span>
        <span className="quiz-meta-id">
          {quizIndex + 1} / {totalInType} · Q-{String(quizIndex + 1).padStart(3, '0')}
        </span>
      </div>

      <p className="quiz-question">{quiz.question}</p>

      {quiz.code_template && (
        <pre className="quiz-code-block quiz-code-block--question"><code>{quiz.code_template}</code></pre>
      )}

      <button className="quiz-reset-btn" onClick={() => setShowAnswer((s) => !s)}>
        정답 보기 {showAnswer ? '▴' : '▾'}
      </button>

      {showAnswer && (
        <div style={{ marginTop: 16 }}>
          {quiz.answers && (
            <pre className="quiz-code-block quiz-code-block--answer"><code>{quiz.answers}</code></pre>
          )}
          <div className="quiz-explanation">
            <span className="quiz-explanation__icon">💡</span>
            <p className="quiz-explanation__text">{quiz.explanation}</p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ── 진입점 ──────────────────────────────────────────── */
export function QuizCard({ quiz, quizIndex, totalInType, onNext }: QuizCardProps) {
  switch (quiz.question_type) {    case 'mcq':    case 'mcq_definition':
    case 'mcq_misconception':
      return <McqCard quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} onNext={onNext} />
    case 'ox_quiz':
      return <OxCard quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
    case 'fill_blank':
      return <FillCard quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
    case 'code_execution':
      return <CodeCard quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
    default:
      return <FillCard quiz={quiz} quizIndex={quizIndex} totalInType={totalInType} />
  }
}
