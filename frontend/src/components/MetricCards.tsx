interface Decision {
  decision: string
  risk_score: number | null
}

interface Props {
  decisions: Decision[]
}

export default function MetricCards({ decisions }: Props) {
  const total = decisions.length
  const blocked = decisions.filter(d => d.decision === 'block').length
  const blockRate = total > 0 ? ((blocked / total) * 100).toFixed(2) : '0.00'
  const scores = decisions.filter(d => d.risk_score !== null).map(d => d.risk_score as number)
  const avgScore = scores.length > 0
    ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2)
    : '—'

  const cards = [
    { label: 'Total today', value: total.toLocaleString(), unit: 'transactions', highlight: false, danger: false },
    { label: 'Blocked', value: blocked.toLocaleString(), unit: 'high risk', highlight: false, danger: true },
    { label: 'Block rate', value: `${blockRate}%`, unit: 'last session', highlight: true, danger: false },
    { label: 'Avg risk score', value: avgScore, unit: 'all transactions', highlight: false, danger: false },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8 }}>
      {cards.map((card, i) => (
        <div key={i} style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius)',
          border: card.highlight ? '2px solid var(--ing)' : '0.5px solid var(--border)',
          padding: '10px 12px',
        }}>
          <div style={{
            fontSize: 10,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.4px',
            marginBottom: 4,
          }}>{card.label}</div>
          <div style={{
            fontSize: 22,
            fontWeight: 500,
            color: card.highlight ? 'var(--ing)' : card.danger ? 'var(--blocked)' : 'var(--text-primary)',
          }}>{card.value}</div>
          <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2 }}>{card.unit}</div>
        </div>
      ))}
    </div>
  )
}