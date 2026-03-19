import { useState, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { WeekTab } from '../components/WeekTab'
import { SkeletonGroup, ErrorCard } from '../components/Skeleton'

interface LearningGuide {
  week: number
  summary: string
  key_concepts: string[]
  meta: Record<string, string>
}

type WeeklyStep = 'upload' | 'loading' | 'ready' | 'error'

export function Weekly() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [step, setStep] = useState<WeeklyStep>('upload')
  const [files, setFiles] = useState<File[]>([])
  const [guides, setGuides] = useState<LearningGuide[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? [])
    setFiles(selected)
  }

  const handleAnalyze = async () => {
    if (files.length === 0) return
    setStep('loading')
    try {
      const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
      const res = await fetch(`${API}/api/learning-guides`)
      if (!res.ok) throw new Error('데이터를 불러오는 데 실패했습니다.')
      const data = res.json() as Promise<LearningGuide[]>
      const resolved = await data
      setGuides(resolved)
      if (resolved.length > 0) {
        setSearchParams({ week: String(resolved[0].week) }, { replace: true })
      }
      setStep('ready')
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다.')
      setStep('error')
    }
  }

  const handleReset = () => {
    setStep('upload')
    setFiles([])
    setGuides([])
    setErrorMsg(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const weeks = guides.map((g) => g.week)
  const rawWeek = Number(searchParams.get('week') ?? weeks[0] ?? 1)
  const activeWeek = weeks.includes(rawWeek) ? rawWeek : (weeks[0] ?? 1)
  const activeGuide = guides.find((g) => g.week === activeWeek) ?? null

  const handleSelectWeek = (week: number) => {
    setSearchParams({ week: String(week) })
  }

  // 로딩
  if (step === 'loading') {
    return (
      <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
        <SkeletonGroup count={3} variant="card" />
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
                color: 'var(--tml-navy-mid)',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                margin: '0 0 16px',
              }}>
                1주치 전체 분석 · Mode B
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
                1주치 스크립트를<br />
                <span style={{ color: 'var(--tml-navy-mid)' }}>분석합니다.</span>
              </h1>
              <p style={{
                fontFamily: 'var(--font-body)',
                fontSize: '0.875rem',
                color: 'var(--tml-ink-muted)',
                margin: 0,
                lineHeight: 1.6,
              }}>
                1주치 강의 스크립트 전체를 업로드하면 주차별 학습 가이드와 핵심 요약을 생성합니다.
              </p>
            </div>

            {/* 다중 파일 업로드 영역 */}
            <div
              className="tml-animate tml-empty tml-dropzone"
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt"
                multiple
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              {files.length > 0 ? (
                <div className="tml-weekly-filelist">
                  {files.map((f, i) => (
                    <div key={i} className="tml-weekly-filelist__item">
                      <span className="tml-weekly-filelist__name">{f.name}</span>
                      <span className="tml-weekly-filelist__size">{(f.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="tml-dropzone__placeholder">
                  <span className="tml-dropzone__icon tml-dropzone__icon--muted">📂</span>
                  <span className="tml-dropzone__hint">클릭하여 파일 선택</span>
                  <span className="tml-dropzone__sub">.txt 파일 여러 개 선택 가능</span>
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
                  ...(files.length === 0 ? { opacity: 0.4, cursor: 'not-allowed', pointerEvents: 'none' } : {}),
                }}
              >
                분석 시작하기
              </button>
            </div>
          </div>

          {/* 오른쪽: Mode B 안내 */}
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
              Mode B 안내
            </p>

            <div className="tml-card" style={{ padding: '20px 18px', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {[
                { num: '01', text: '1주치 강의 스크립트 파일(.txt)을 모두 선택합니다.' },
                { num: '02', text: '각 스크립트가 개별 전처리 후 주차 단위로 통합됩니다.' },
                { num: '03', text: '주차별 학습 가이드와 핵심 요약이 자동 생성됩니다.' },
              ].map(({ num, text }) => (
                <div key={num} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.6875rem',
                    color: 'var(--tml-navy-mid)',
                    fontWeight: 500,
                    flexShrink: 0,
                    marginTop: 2,
                  }}>
                    {num}
                  </span>
                  <p style={{
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.8125rem',
                    color: 'var(--tml-ink-secondary)',
                    margin: 0,
                    lineHeight: 1.65,
                  }}>
                    {text}
                  </p>
                </div>
              ))}
            </div>
          </div>

        </div>
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
          color: 'var(--tml-navy-mid)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          margin: '0 0 12px',
        }}>
          1주치 전체 분석 · Mode B
        </p>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontWeight: 700,
          fontSize: '2rem',
          letterSpacing: '-0.02em',
          color: 'var(--tml-ink)',
          margin: '0 0 8px',
        }}>
          주차별 학습 가이드
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
            {files.length}개 파일 분석 완료
          </span>
          <span style={{ color: 'var(--tml-rule-strong)', fontSize: '0.75rem' }}>·</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--tml-ink-muted)' }}>
            {weeks.length}주차 데이터
          </span>
        </div>
      </div>

      {/* 주차 탭 */}
      <div className="tml-animate">
        <WeekTab
          weeks={weeks}
          activeWeek={activeWeek}
          onSelect={handleSelectWeek}
        />
      </div>

      {/* 주차 콘텐츠 — key로 탭 전환 시 fade 재실행 */}
      {activeGuide && (
        <div key={activeWeek} className="tml-week-content">

          {/* 학습 가이드 섹션 */}
          <div style={{ marginBottom: 40 }}>
            <p className="section-label">학습 가이드</p>
            <div className="tml-guide-item">
              <div className="tml-guide-item__bar" />
              <div className="tml-guide-item__body">
                <span className="tml-guide-item__num">01</span>
                <p className="tml-guide-item__text">{activeGuide.summary}</p>
              </div>
            </div>
          </div>

          {/* 핵심 요약 섹션 */}
          <div>
            <p className="section-label">핵심 요약</p>
            <div className="tml-concept-tags">
              {activeGuide.key_concepts.map((concept, i) => (
                <span key={i} className="tml-concept-tag">
                  {concept}
                </span>
              ))}
            </div>
          </div>

        </div>
      )}
    </main>
  )
}
