import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, Link, useLocation } from 'react-router-dom'
import './index.css'
import { Dashboard } from './pages/Dashboard'
import { LectureResult } from './pages/LectureResult'
import { WeeklyResult } from './pages/WeeklyResult'
import { NotFound } from './pages/NotFound'
import { ErrorBoundary } from './components/ErrorBoundary'

// ── 컨텍스트 네비게이션 (Option C) ──

function NavBreadcrumb() {
  const { pathname } = useLocation()
  const segments = pathname.split('/').filter(Boolean)

  if (pathname === '/') return null

  if (segments[0] === 'lecture' && segments[1]) {
    return (
      <nav className="tml-header__breadcrumb">
        <Link to="/" className="tml-header__back">← 대시보드</Link>
        <span className="tml-header__breadcrumb-sep">/</span>
        <span className="tml-header__breadcrumb-current">강의 결과</span>
      </nav>
    )
  }

  if (segments[0] === 'weekly' && segments[1]) {
    return (
      <nav className="tml-header__breadcrumb">
        <Link to="/" className="tml-header__back">← 대시보드</Link>
        <span className="tml-header__breadcrumb-sep">/</span>
        <span className="tml-header__breadcrumb-current">{segments[1]}주차 학습 가이드</span>
      </nav>
    )
  }

  return null
}

function App() {
  const [dark, setDark] = useState<boolean>(() => {
    return localStorage.getItem('tml-theme') === 'dark'
  })

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
        {/* 로고 — 클릭 시 대시보드로 이동 */}
        <Link to="/" className="tml-header__logo">
          <div className="tml-header__icon" aria-hidden="true">
            <img src="/likelion-logo.png" alt="알려주사자 로고" className="tml-header__logo-img" />
          </div>
          <span className="tml-header__wordmark">알려주사자</span>
        </Link>

        {/* 컨텍스트 브레드크럼 */}
        <NavBreadcrumb />

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

      <ErrorBoundary>
        <Routes>
          {/* 메인 대시보드 */}
          <Route path="/" element={<Dashboard />} />

          {/* Mode A: 단일 강의 */}
          <Route path="/lecture/:id" element={<LectureResult />} />

          {/* Mode B: 주차별 가이드 */}
          <Route path="/weekly/:week" element={<WeeklyResult />} />

          {/* 하위 호환 리다이렉트 */}
          <Route path="/lecture" element={<Navigate to="/" replace />} />
          <Route path="/weekly" element={<Navigate to="/" replace />} />

          {/* 404 */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </ErrorBoundary>
    </div>
  )
}

export default App
