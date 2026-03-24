import { useState, useEffect } from 'react'
import { Routes, Route, NavLink, Link } from 'react-router-dom'
import './index.css'
import { Home } from './pages/Home'
import { Lecture } from './pages/Lecture'
import { Weekly } from './pages/Weekly'

const NAV_ITEMS: { label: string; to: string }[] = [
  { label: '홈', to: '/' },
  { label: '단일 강의', to: '/lecture' },
  { label: '주차별 가이드', to: '/weekly' },
]

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
        {/* 로고 — 클릭 시 홈으로 이동 */}
        <Link to="/" className="tml-header__logo">
          <div className="tml-header__icon" aria-hidden="true">
            <img src="/likelion-logo.png" alt="알려주사자 로고" className="tml-header__logo-img" />
          </div>
          <span className="tml-header__wordmark">알려주사자</span>
        </Link>

        {/* 네비게이션 */}
        <nav className="tml-header__nav">
          {NAV_ITEMS.map(({ label, to }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `tml-header__nav-item${isActive ? ' tml-header__nav-item--active' : ''}`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

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

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/lecture" element={<Lecture />} />
        <Route path="/weekly" element={<Weekly />} />
      </Routes>
    </div>
  )
}

export default App
