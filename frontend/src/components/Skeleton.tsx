/* Skeleton.tsx — 로딩 스켈레톤 컴포넌트 (오렌지 shimmer) */

import type { CSSProperties } from 'react'

/* ── 기본 단형 스켈레톤 ── */
interface SkeletonProps {
  height?: number | string
  width?: number | string
  borderRadius?: number | string
  style?: CSSProperties
}

export function Skeleton({
  height = 72,
  width = '100%',
  borderRadius = 6,
  style,
}: SkeletonProps) {
  return (
    <div
      className="tml-skeleton"
      style={{ height, width, borderRadius, ...style }}
    />
  )
}

/* ── 텍스트 줄 스켈레톤 ── */
export function SkeletonText({ lines = 3 }: { lines?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {[...Array(lines)].map((_, i) => (
        <div
          key={i}
          className="tml-skeleton"
          style={{
            height: 15,
            width: i === lines - 1 ? '58%' : '100%',
            borderRadius: 4,
          }}
        />
      ))}
    </div>
  )
}

/* ── 컨셉 카드 스켈레톤 (세로 바 + 줄) ── */
export function SkeletonCard() {
  return (
    <div
      className="tml-card"
      style={{ padding: '16px 18px 16px 0', display: 'flex', gap: 0 }}
    >
      {/* 오렌지 shimmer 세로 바 */}
      <div
        className="tml-skeleton"
        style={{ width: 3, minHeight: 64, flexShrink: 0, marginRight: 16, borderRadius: 2 }}
      />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, paddingRight: 8 }}>
        <div className="tml-skeleton" style={{ height: 15, width: '52%', borderRadius: 4 }} />
        <div className="tml-skeleton" style={{ height: 13, width: '78%', borderRadius: 4 }} />
        <div className="tml-skeleton" style={{ height: 13, width: '38%', borderRadius: 4 }} />
      </div>
    </div>
  )
}

/* ── 에러 카드 ── */
interface ErrorCardProps {
  message: string
  title?: string
}

export function ErrorCard({ message, title = '오류가 발생했습니다' }: ErrorCardProps) {
  return (
    <div className="tml-error-card">
      <div className="tml-error-card__bar" />
      <div className="tml-error-card__content">
        <span className="tml-error-card__title">{title}</span>
        <p className="tml-error-card__msg">{message}</p>
      </div>
    </div>
  )
}

/* ── 스켈레톤 그룹 (로딩 화면 전체) ── */
interface SkeletonGroupProps {
  count?: number
  variant?: 'card' | 'simple'
}

export function SkeletonGroup({ count = 3, variant = 'card' }: SkeletonGroupProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {[...Array(count)].map((_, i) =>
        variant === 'card'
          ? <SkeletonCard key={i} />
          : <Skeleton key={i} height={72} />
      )}
    </div>
  )
}
