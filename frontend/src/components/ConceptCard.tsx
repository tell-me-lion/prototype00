interface Concept {
  week: number | null
  lecture_id: string
  concept: string
  importance: number
  evidence_facts: string[]
  meta: Record<string, string>
}

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
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.6875rem',
            color: 'var(--tml-ink-muted)',
          }}>
            {concept.lecture_id}
          </span>
          {concept.meta.topic && (
            <span className="badge-orange">{concept.meta.topic}</span>
          )}
          <span className="badge-navy">개념</span>
        </div>
      </div>
    </div>
  )
}
