import type { LearningPoint } from '../types/models'

interface LearningPointCardProps {
  point: LearningPoint
}

export function LearningPointCard({ point }: LearningPointCardProps) {
  return (
    <div className="tml-card learning-point-card">
      <div className="lp-bar" />
      <div style={{ flex: 1 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          gap: 12,
          marginBottom: 10,
        }}>
          <span className="concept-name">{point.concept}</span>
          <span className="concept-score">×{point.importance.toFixed(2)}</span>
        </div>
        {point.definition && (
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.8125rem',
            color: 'var(--tml-ink-secondary)',
            margin: '0 0 10px',
            lineHeight: 1.5,
          }}>
            {point.definition}
          </p>
        )}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            color: 'var(--tml-ink-muted)',
          }}>
            {point.lecture_id}
          </span>
          <span className="badge-navy">학습포인트</span>
        </div>
      </div>
    </div>
  )
}
