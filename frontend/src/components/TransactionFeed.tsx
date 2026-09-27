interface Decision {
  transaction_id: string
  account_id: string
  dest_account: string
  amount: number
  type: string
  decision: string
  risk_score: number | null
  report_status: string
  created_at: string
}

interface Props {
  decisions: Decision[]
  onSelect: (d: Decision) => void
  selected: Decision | null
}

export default function TransactionFeed({ decisions, onSelect, selected }: Props) {
  const fmt = (amount: number) =>
    new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(amount)

  const fmtTime = (iso: string) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleTimeString('nl-NL', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  }

  return (
    <div style={{
      background: 'var(--surface)',
      borderRadius: 'var(--radius)',
      border: '0.5px solid var(--border)',
      padding: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontWeight: 500, fontSize: 13 }}>Live transaction feed</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--passed)' }} />
          <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Live · 2s</span>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '70px 90px 90px 55px 70px 1fr',
        fontSize: 10,
        color: 'var(--text-secondary)',
        textTransform: 'uppercase',
        letterSpacing: '0.4px',
        paddingBottom: 6,
        borderBottom: '0.5px solid var(--border)',
        marginBottom: 4,
      }}>
        <span>Time</span><span>Account</span><span>Amount</span>
        <span>Score</span><span>Status</span><span>Action</span>
      </div>

      <div style={{ maxHeight: 260, overflowY: 'auto' }}>
        {decisions.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px 0', fontSize: 12 }}>
            Waiting for transactions...
          </div>
        )}
        {decisions.map((d) => {
          const isBlock = d.decision === 'block'
          const isSelected = selected?.transaction_id === d.transaction_id
          return (
            <div
              key={d.transaction_id}
              onClick={() => onSelect(d)}
              style={{
                display: 'grid',
                gridTemplateColumns: '70px 90px 90px 55px 70px 1fr',
                padding: '5px 4px',
                borderBottom: '0.5px solid var(--border)',
                alignItems: 'center',
                fontSize: 11,
                cursor: 'pointer',
                background: isSelected
                  ? 'var(--ing-light)'
                  : isBlock
                    ? 'rgba(211,47,47,0.04)'
                    : 'transparent',
                borderRadius: 3,
              }}
            >
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
                {fmtTime(d.created_at)}
              </span>
              <span style={{
                color: isBlock ? 'var(--blocked)' : 'var(--text-primary)',
                fontWeight: isBlock ? 500 : 400,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>{d.account_id}</span>
              <span>{d.amount ? fmt(d.amount) : '—'}</span>
              <span style={{
                fontWeight: 500,
                color: d.risk_score === null
                  ? 'var(--text-muted)'
                  : d.risk_score > 0.7 ? 'var(--blocked)'
                  : d.risk_score > 0.4 ? '#E65100'
                  : 'var(--passed)',
              }}>
                {d.risk_score !== null ? d.risk_score.toFixed(2) : '—'}
              </span>
              <span>
                <span style={{
                  fontSize: 10, fontWeight: 600,
                  color: isBlock ? 'var(--blocked)' : 'var(--passed)',
                  background: isBlock ? 'var(--blocked-bg)' : 'var(--passed-bg)',
                  padding: '2px 5px', borderRadius: 3,
                }}>
                  {d.decision.toUpperCase()}
                </span>
              </span>
              <span style={{ color: 'var(--ing)', textDecoration: 'underline', fontSize: 11 }}>
                {isBlock ? 'View SAR' : 'Analyze'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}