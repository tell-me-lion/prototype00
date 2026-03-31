import type { Concept } from '../types/models'

interface ConceptCardProps {
  concept: Concept
}

export function ConceptCard({ concept }: ConceptCardProps) {
  return (
    <div className="tml-card concept-card">
      <div className="concept-bar" />
      <div style={{ flex: 1 }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          gap: 12,
          marginBottom: 10,
        }}>
          <span className="concept-name">{concept.concept}</span>
          <span className="concept-score">×{concept.importance.toFixed(2)}</span>
        </div>
        {concept.definition && (
          <p style={{
            fontFamily: 'var(--font-body)',
            fontSize: '0.8125rem',
            color: 'var(--tml-ink-secondary)',
            margin: '0 0 10px',
            lineHeight: 1.5,
          }}>
            {concept.definition}
          </p>
        )}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.75rem',
            color: 'var(--tml-ink-muted)',
          }}>
            {concept.lecture_id}
          </span>
          <span className="badge-navy">개념</span>
        </div>
      </div>
    </div>
  )
}
