interface Props {
  report: string | null
  accountId: string
  riskScore: number
  transactionId: string
  onClose: () => void
  onSubmitFIU: () => void
  fiuStatus: string | null
}

export default function SARModal({
  report, accountId, riskScore, transactionId,
  onClose, onSubmitFIU, fiuStatus
}: Props) {

  const handlePrint = () => window.print()

  // Parse sections from report text
  const parseReport = (text: string) => {
    const sections: { title: string; content: string }[] = []
    const lines = text.split('\n')
    let current: { title: string; content: string } | null = null

    for (const line of lines) {
      if (line.startsWith('## ')) {
        if (current) sections.push(current)
        current = { title: line.replace(/^##\s*/, '').replace(':', ''), content: '' }
      } else if (line.trim() && !line.startsWith('#') && line.trim() !== '---' && !line.startsWith('*Report')) {
        if (current) current.content += (current.content ? '\n' : '') + line.trim()
      }
    }
    if (current) sections.push(current)
    return sections
  }

  // Extract header fields
  const getField = (text: string, field: string) => {
    const match = text.match(new RegExp(`\\*\\*${field}:\\*\\*\\s*(.+)`))
    return match ? match[1].trim() : '—'
  }

  const sections = report ? parseReport(report) : []
  const caseId = report ? getField(report, 'Case ID') : '—'
  const involvedAccount = report ? getField(report, 'Involved account') : '—'
  const destAccount = report ? getField(report, 'Destination account') : '—'
  const amount = report ? getField(report, 'Amount') : '—'
  const timestamp = report ? getField(report, 'Timestamp') : '—'

  return (
    <div style={{
      position: 'fixed', inset: 0,
      background: 'rgba(0,0,0,0.55)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--bg)',
        borderRadius: 16,
        width: 820,
        maxHeight: '88vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 16px 48px rgba(0,0,0,0.22)',
        overflow: 'hidden',
      }}>

        {/* Header bar */}
        <div style={{
          background: 'var(--surface)',
          padding: '16px 24px',
          borderBottom: '0.5px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: 'var(--blocked-bg)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 16,
            }}>⚠</div>
            <div>
              <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--text-primary)' }}>
                Suspicious Activity Report
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 1 }}>
                {caseId} · {accountId}
              </div>
            </div>
            <span style={{
              background: 'var(--blocked-bg)',
              color: 'var(--blocked)',
              fontSize: 10, fontWeight: 700,
              padding: '3px 10px', borderRadius: 20,
              letterSpacing: '0.5px',
            }}>HIGH RISK</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            {fiuStatus && (
              <span style={{
                fontSize: 11, color: 'var(--passed)',
                background: 'var(--passed-bg)',
                padding: '4px 10px', borderRadius: 4,
              }}>{fiuStatus}</span>
            )}
            <button onClick={handlePrint} style={{
              background: 'transparent', color: 'var(--text-secondary)',
              border: '0.5px solid var(--border)',
              borderRadius: 6, padding: '5px 12px', fontSize: 11,
            }}>Print</button>
            <button onClick={onSubmitFIU} style={{
              background: 'var(--ing)', color: '#fff', border: 'none',
              borderRadius: 6, padding: '5px 14px', fontSize: 11, fontWeight: 500,
            }}>Submit to FIU</button>
            <button onClick={onClose} style={{
              background: 'transparent', color: 'var(--text-secondary)',
              border: '0.5px solid var(--border)',
              borderRadius: 6, padding: '5px 10px', fontSize: 13,
            }}>✕</button>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: 20, display: 'flex', flexDirection: 'column', gap: 12 }}>

          {!report ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0', fontSize: 12 }}>
              No SAR report available
            </div>
          ) : (
            <>
              {/* Case details card */}
              <div style={{
                background: 'var(--surface)',
                borderRadius: 10,
                border: '0.5px solid var(--border)',
                padding: '14px 18px',
              }}>
                <div style={{
                  fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
                  textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 12,
                }}>Case details</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px 24px' }}>
                  {[
                    { label: 'Case ID', value: caseId },
                    { label: 'Involved account', value: involvedAccount, highlight: true },
                    { label: 'Destination account', value: destAccount },
                    { label: 'Amount', value: amount, highlight: true },
                    { label: 'Timestamp', value: timestamp },
                    { label: 'Risk score', value: `${riskScore.toFixed(2)} / 1.00`, highlight: true },
                  ].map((f, i) => (
                    <div key={i}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{f.label}</div>
                      <div style={{
                        fontSize: 12, fontWeight: f.highlight ? 600 : 400,
                        color: f.highlight ? 'var(--blocked)' : 'var(--text-primary)',
                      }}>{f.value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Section cards */}
              {sections.map((sec, i) => (
                <div key={i} style={{
                  background: 'var(--surface)',
                  borderRadius: 10,
                  border: '0.5px solid var(--border)',
                  padding: '14px 18px',
                }}>
                  <div style={{
                    fontSize: 10, fontWeight: 600, color: 'var(--text-muted)',
                    textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 10,
                  }}>{sec.title}</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {sec.content.split('\n').map((line, j) => {
                      const isNumbered = line.match(/^\d+\./)
                      return (
                        <div key={j} style={{
                          display: 'flex', gap: 10,
                          fontSize: 12, lineHeight: 1.7,
                          color: 'var(--text-primary)',
                        }}>
                          {isNumbered && (
                            <div style={{
                              width: 3, borderRadius: 2,
                              background: 'var(--ing)',
                              flexShrink: 0, alignSelf: 'stretch',
                            }} />
                          )}
                          <span>{line.replace(/^\d+\.\s*/, '').replace(/\*\*/g, '')}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ))}

              {/* Risk verdict card */}
              <div style={{
                background: 'var(--blocked-bg)',
                borderRadius: 10,
                border: '0.5px solid #FFCDD2',
                padding: '14px 18px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}>
                <div>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#B71C1C', textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: 4 }}>
                    Risk verdict
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--blocked)' }}>HIGH RISK — Block recommended</div>
                </div>
                <div style={{
                  width: 48, height: 48, borderRadius: '50%',
                  background: 'var(--blocked)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontWeight: 700, fontSize: 13,
                }}>
                  {(riskScore * 100).toFixed(0)}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '10px 24px',
          borderTop: '0.5px solid var(--border)',
          background: 'var(--surface)',
          display: 'flex', justifyContent: 'space-between',
        }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            Generated by FEC Fraud Intelligence Platform · Anti-Fraud AI Agent
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            CONFIDENTIAL — FEC USE ONLY
          </div>
        </div>
      </div>
    </div>
  )
}