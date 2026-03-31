import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import './index.css'
import { Dashboard } from './pages/Dashboard'
import { LecturesPage } from './pages/LecturesPage'
import { LectureResult } from './pages/LectureResult'
import { QuizPage } from './pages/QuizPage'
import { GuidesPage } from './pages/GuidesPage'
import { WeeklyResult } from './pages/WeeklyResult'
import { NotFound } from './pages/NotFound'
import { ErrorBoundary } from './components/ErrorBoundary'

// ── 헤더 탭 네비게이션 ──

const NAV_ITEMS: { label: string; to: string; match: (p: string) => boolean }[] = [
  { label: '대시보드', to: '/', match: (p) => p === '/' },
  { label: '강의 목록', to: '/lectures', match: (p) => p === '/lectures' || p.startsWith('/lecture') },
  { label: '학습 가이드', to: '/guides', match: (p) => p === '/guides' || p.startsWith('/weekly') },
]

function HeaderNav() {
  const { pathname } = useLocation()

  return (
    <nav className="tml-header__nav" style={{ flex: 1 }}>
      {NAV_ITEMS.map(({ label, to, match }) => (
        <Link
          key={to}
          to={to}
          className={`tml-header__nav-item${match(pathname) ? ' tml-header__nav-item--active' : ''}`}
        >
          {label}
        </Link>
      ))}
    </nav>
  )
}

// ── 컨텍스트 브레드크럼 (상세 페이지) ──

function NavBreadcrumb() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)

  // /lecture/:id/quiz
  if (segments[0] === 'lecture' && segments[1] && segments[2] === 'quiz') {
    return (
      <nav className="tml-header__breadcrumb">
        <Link to="/lectures" className="tml-header__back">← 강의 목록</Link>
        <span className="tml-header__breadcrumb-sep">/</span>
        <Link to={`/lecture/${segments[1]}`} className="tml-header__back">강의 결과</Link>
        <span className="tml-header__breadcrumb-sep">/</span>
        <span className="tml-header__breadcrumb-current">퀴즈</span>
      </nav>
    )
  }

  // /lecture/:id
  if (segments[0] === 'lecture' && segments[1]) {
    return (
      <nav className="tml-header__breadcrumb">
        <Link to="/lectures" className="tml-header__back">← 강의 목록</Link>
        <span className="tml-header__breadcrumb-sep">/</span>
        <span className="tml-header__breadcrumb-current">강의 결과</span>
      </nav>
    )
  }

  // /weekly/:week
  if (segments[0] === 'weekly' && segments[1]) {
    return (
      <nav className="tml-header__breadcrumb">
        <Link to="/guides" className="tml-header__back">← 학습 가이드</Link>
        <span className="tml-header__breadcrumb-sep">/</span>
        <span className="tml-header__breadcrumb-current">{segments[1]}주차 학습 가이드</span>
      </nav>
    )
  }

  return null
}

function isDetailPage(pathname: string): boolean {
  const s = pathname.split('/').filter(Boolean)
  return (s[0] === 'lecture' && !!s[1]) || (s[0] === 'weekly' && !!s[1])
}

function App() {
  const [dark, setDark] = useState<boolean>(() => {
    return localStorage.getItem('tml-theme') === 'dark'
  })
  const { pathname } = useLocation()
  const showBreadcrumb = isDetailPage(pathname)

  useEffect(() => {
    if (dark) {
      document.documentElement.setAttribute('data-theme', 'dark')
      localStorage.setItem('tml-theme', 'dark')
    } else {
      document.documentElement.removeAttribute('data-theme')
      localStorage.setItem('tml-theme', 'light')
    }
  }, [dark])

  return (
    <div style={{ minHeight: '100vh', background: 'var(--tml-bg)', color: 'var(--tml-ink)' }}>
      {/* 헤더 */}
      <header className="tml-header">
        {/* 로고 */}
        <Link to="/" className="tml-header__logo">
          <div className="tml-header__icon" aria-hidden="true">
            <img src="/likelion-logo.png" alt="알려주사자 로고" className="tml-header__logo-img" />
          </div>
          <span className="tml-header__wordmark">알려주사자</span>
        </Link>

        {/* 탭 네비게이션 */}
        <HeaderNav />

        {/* 다크/라이트 토글 */}
        <button
          className="tml-header__toggle"
          onClick={() => setDark((d) => !d)}
          title={dark ? '라이트 모드로 전환' : '다크 모드로 전환'}
          aria-label={dark ? '라이트 모드로 전환' : '다크 모드로 전환'}
        >
          ◑
        </button>
      </header>

      {/* 브레드크럼 (상세 페이지에서만) */}
      {showBreadcrumb && (
        <div style={{
          maxWidth: 1280, margin: '0 auto', padding: '28px 40px 20px',
        }}>
          <NavBreadcrumb />
        </div>
      )}

      <ErrorBoundary>
        <Routes>
          {/* 탭 라우트 */}
          <Route path="/" element={<Dashboard />} />
          <Route path="/lectures" element={<LecturesPage />} />
          <Route path="/guides" element={<GuidesPage />} />

          {/* 상세 라우트 */}
          <Route path="/lecture/:id" element={<LectureResult />} />
          <Route path="/lecture/:id/quiz" element={<QuizPage />} />
          <Route path="/weekly/:week" element={<WeeklyResult />} />

          {/* 리다이렉트 */}
          <Route path="/lecture" element={<Navigate to="/lectures" replace />} />
          <Route path="/weekly" element={<Navigate to="/guides" replace />} />

          {/* 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ErrorBoundary>
    </div>
  )
}

export default App
