import { Link } from 'react-router-dom'

export function NotFound() {
  return (
    <main className="tml-not-found tml-animate">
      <div className="tml-not-found__content">
        <span className="tml-not-found__icon" aria-hidden="true">🦁</span>
        <h1 className="tml-not-found__title">페이지를 찾을 수 없습니다</h1>
        <p className="tml-not-found__desc">요청한 페이지가 존재하지 않습니다.</p>
        <Link to="/" className="btn-primary tml-not-found__cta">
          대시보드로 돌아가기
        </Link>
      </div>
    </main>
  )
}
