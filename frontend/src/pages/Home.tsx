import { useNavigate } from 'react-router-dom'

const OUTPUT_TAGS: { label: string; color: string; bg: string }[] = [
  { label: '핵심 개념', color: 'var(--tml-orange-dark)', bg: 'var(--tml-orange-light)' },
  { label: '학습 포인트', color: 'var(--tml-navy-mid)', bg: 'var(--tml-navy-light)' },
  { label: 'MCQ 퀴즈', color: 'var(--tml-orange-dark)', bg: 'var(--tml-orange-light)' },
  { label: '주관식', color: 'var(--tml-navy-mid)', bg: 'var(--tml-navy-light)' },
  { label: '빈칸 채우기', color: 'var(--tml-quiz-fill)', bg: 'var(--tml-quiz-fill-bg)' },
  { label: '코드 실행형', color: 'var(--tml-quiz-code)', bg: 'var(--tml-quiz-code-bg)' },
  { label: '주차별 가이드', color: 'var(--tml-navy-mid)', bg: 'var(--tml-navy-light)' },
]

const STATS: { label: string; value: string; mono: boolean }[] = [
  { label: '강의 스크립트', value: '15개', mono: true },
  { label: '지원 퀴즈 유형', value: '4종', mono: true },
  { label: '상태', value: '더미 데이터', mono: false },
]

export function Home() {
  const navigate = useNavigate()

  return (
    <main style={{ maxWidth: 1120, margin: '0 auto', padding: '56px 40px 80px' }}>
      <div className="tml-home-grid">

        {/* ── 히어로 섹션 ── */}
        <section className="tml-hero-glow">

          <p className="tml-animate" style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: 'var(--tml-orange)',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            margin: '0 0 24px',
          }}>
            Knowledge Dashboard
          </p>

          <h1 className="tml-animate" style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 700,
            fontSize: 'clamp(2rem, 3.5vw, 3rem)',
            letterSpacing: '-0.02em',
            lineHeight: 1.1,
            color: 'var(--tml-ink)',
            margin: '0 0 20px',
          }}>
            강의를<br />
            <span style={{ color: 'var(--tml-orange)' }}>핵심으로.</span>
          </h1>

          <p className="tml-animate" style={{
            fontFamily: 'var(--font-body)',
            fontSize: '1rem',
            lineHeight: 1.7,
            color: 'var(--tml-ink-secondary)',
            margin: '0 0 36px',
            maxWidth: 480,
          }}>
            STT 스크립트를 입력하면 핵심 개념, 학습 포인트, 퀴즈를 자동 생성합니다.
            강의 한 편 또는 1주치 전체를 분석하세요.
          </p>

          <div className="tml-animate" style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
            <button className="btn-primary" onClick={() => navigate('/lecture')}>강의 분석 시작하기</button>
            <button
              onClick={() => navigate('/weekly')}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--tml-ink-secondary)',
                fontSize: '0.875rem',
                fontFamily: 'var(--font-body)',
                cursor: 'pointer',
                padding: '10px 4px',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              주차별 가이드 보기 <span style={{ color: 'var(--tml-orange)' }}>→</span>
            </button>
          </div>

          <hr className="tml-animate" style={{
            border: 'none',
            borderTop: '1px solid var(--tml-rule)',
            margin: '48px 0 36px',
          }} />

          <div className="tml-animate" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {OUTPUT_TAGS.map(({ label, color, bg }) => (
              <span key={label} style={{
                background: bg,
                color,
                fontSize: '0.6875rem',
                fontWeight: 600,
                padding: '3px 10px',
                borderRadius: 4,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                fontFamily: 'var(--font-body)',
              }}>
                {label}
              </span>
            ))}
          </div>

        </section>

        {/* ── 사이드 패널 ── */}
        <aside style={{ display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 8 }}>

          <p style={{
            fontSize: '0.6875rem',
            fontWeight: 600,
            color: 'var(--tml-ink-muted)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            margin: '0 0 4px',
            fontFamily: 'var(--font-body)',
          }}>
            분석 모드
          </p>

          {/* Mode A 카드 */}
          <div className="tml-animate tml-card tml-mode-card" onClick={() => navigate('/lecture')} style={{ cursor: 'pointer' }}>
            <div className="tml-mode-card__bar" style={{ background: 'var(--tml-orange)' }} />
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: 10 }}>
                <span className="badge-orange">Mode A</span>
              </div>
              <h3 style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '0.9375rem',
                color: 'var(--tml-ink)',
                margin: '0 0 8px',
                letterSpacing: '-0.01em',
              }}>
                단일 강의 분석
              </h3>
              <p style={{
                fontSize: '0.8125rem',
                lineHeight: 1.6,
                color: 'var(--tml-ink-secondary)',
                margin: 0,
                fontFamily: 'var(--font-body)',
              }}>
                강의 스크립트 1개 → 핵심 개념, 학습 포인트, 퀴즈 자동 생성
              </p>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {['핵심 개념', '학습 포인트', '퀴즈 4종'].map((t) => (
                  <span key={t} style={{
                    fontSize: '0.6875rem',
                    color: 'var(--tml-ink-muted)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Mode B 카드 */}
          <div className="tml-animate tml-card tml-mode-card" onClick={() => navigate('/weekly')} style={{ cursor: 'pointer' }}>
            <div className="tml-mode-card__bar" style={{ background: 'var(--tml-navy-mid)' }} />
            <div style={{ flex: 1 }}>
              <div style={{ marginBottom: 10 }}>
                <span className="badge-navy">Mode B</span>
              </div>
              <h3 style={{
                fontFamily: 'var(--font-display)',
                fontWeight: 600,
                fontSize: '0.9375rem',
                color: 'var(--tml-ink)',
                margin: '0 0 8px',
                letterSpacing: '-0.01em',
              }}>
                주차별 학습 가이드
              </h3>
              <p style={{
                fontSize: '0.8125rem',
                lineHeight: 1.6,
                color: 'var(--tml-ink-secondary)',
                margin: 0,
                fontFamily: 'var(--font-body)',
              }}>
                1주치 전체 스크립트 → 주차별 학습 가이드 & 핵심 요약 통합 생성
              </p>
              <div style={{ marginTop: 14, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {['학습 가이드', '핵심 요약', '주차 통합'].map((t) => (
                  <span key={t} style={{
                    fontSize: '0.6875rem',
                    color: 'var(--tml-ink-muted)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    #{t}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 통계 카드 */}
          <div className="tml-animate tml-card" style={{ padding: '16px 18px' }}>
            <p style={{
              fontSize: '0.6875rem',
              fontWeight: 600,
              color: 'var(--tml-ink-muted)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              margin: '0 0 14px',
              fontFamily: 'var(--font-body)',
            }}>
              현재 데이터
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {STATS.map(({ label, value, mono }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8125rem', color: 'var(--tml-ink-secondary)', fontFamily: 'var(--font-body)' }}>
                    {label}
                  </span>
                  <span style={{
                    fontFamily: mono ? 'var(--font-mono)' : 'var(--font-body)',
                    fontSize: '0.8125rem',
                    color: label === '상태' ? 'var(--tml-ink-muted)' : 'var(--tml-ink)',
                  }}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </aside>
      </div>
    </main>
  )
}
