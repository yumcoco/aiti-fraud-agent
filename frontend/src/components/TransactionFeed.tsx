import { useState, useMemo } from 'react'

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
  const [filterDecision, setFilterDecision] = useState('all')
  const [filterReport, setFilterReport] = useState('all')
  const [filterDate, setFilterDate] = useState('all')

  const filtered = useMemo(() => {
    return decisions.filter(d => {
      // Decision filter
      if (filterDecision !== 'all' && d.decision !== filterDecision) return false

      // Report status filter
      if (filterReport !== 'all' && d.report_status !== filterReport) return false

      // Date filter
      if (filterDate !== 'all') {
        const created = new Date(d.created_at)
        const now = new Date()
        const diffDays = (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24)
        if (filterDate === 'today' && diffDays > 1) return false
        if (filterDate === '7days' && diffDays > 7) return false
      }

      return true
    })
  }, [decisions, filterDecision, filterReport, filterDate])

  const fmt = (amount: number) =>
    new Intl.NumberFormat('nl-NL', { style: 'currency', currency: 'EUR' }).format(amount)

  const fmtTime = (iso: string) => {
    if (!iso) return '—'
    return new Date(iso).toLocaleTimeString('nl-NL', {
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  }

  const selectStyle = {
    border: '0.5px solid var(--border)',
    borderRadius: 'var(--radius-sm)',
    padding: '3px 8px',
    fontSize: 11,
    color: 'var(--text-secondary)',
    background: 'var(--bg)',
    outline: 'none',
    cursor: 'pointer',
  }

  return (
    <div style={{
      background: 'var(--surface)',
      borderRadius: 'var(--radius)',
      border: '0.5px solid var(--border)',
      padding: 12,
    }}>
      {/* Header + filters */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontWeight: 500, fontSize: 13 }}>Live transaction feed</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            {filtered.length}/{decisions.length}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <select value={filterDate} onChange={e => setFilterDate(e.target.value)} style={selectStyle}>
            <option value="all">All dates</option>
            <option value="today">Today</option>
            <option value="7days">Last 7 days</option>
          </select>
          <select value={filterDecision} onChange={e => setFilterDecision(e.target.value)} style={selectStyle}>
            <option value="all">All decisions</option>
            <option value="block">BLOCKED</option>
            <option value="pass">PASSED</option>
          </select>
          <select value={filterReport} onChange={e => setFilterReport(e.target.value)} style={selectStyle}>
            <option value="all">All reports</option>
            <option value="verified">Verified</option>
            <option value="requires_review">Requires review</option>
            <option value="pending_manual_review">Pending review</option>
            <option value="n/a">N/A</option>
          </select>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--passed)' }} />
            <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Live · 2s</span>
          </div>
        </div>
      </div>

      {/* Column headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '70px 90px 90px 55px 70px 100px 1fr',
        fontSize: 10,
        color: 'var(--text-secondary)',
        textTransform: 'uppercase',
        letterSpacing: '0.4px',
        paddingBottom: 6,
        borderBottom: '0.5px solid var(--border)',
        marginBottom: 4,
      }}>
        <span>Time</span>
        <span>Account</span>
        <span>Amount</span>
        <span>Score</span>
        <span>Decision</span>
        <span>Report</span>
        <span>Action</span>
      </div>

      {/* Rows */}
      <div style={{ maxHeight: 260, overflowY: 'auto' }}>
        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px 0', fontSize: 12 }}>
            No transactions match filters
          </div>
        )}
        {filtered.map((d) => {
          const isBlock = d.decision === 'block'
          const isSelected = selected?.transaction_id === d.transaction_id
          return (
            <div
              key={d.transaction_id}
              onClick={() => onSelect(d)}
              style={{
                display: 'grid',
                gridTemplateColumns: '70px 90px 90px 55px 70px 100px 1fr',
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
              <span style={{
                fontSize: 10,
                color: d.report_status === 'verified'
                  ? 'var(--passed)'
                  : d.report_status === 'requires_review'
                    ? '#E65100'
                    : d.report_status === 'pending_manual_review'
                      ? 'var(--blocked)'
                      : 'var(--text-muted)',
              }}>
                {d.report_status === 'n/a' ? '—' : d.report_status.replace(/_/g, ' ')}
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