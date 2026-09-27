import { useState, useEffect, useCallback } from 'react'
import { getRecentDecisions, submitFIU } from '../api/client'
import MetricCards from './MetricCards'
import TransactionFeed from './TransactionFeed'
import BlockRateChart from './BlockRateChart'
import ChatPanel from './ChatPanel'
import SARModal from './SARModal'

interface Decision {
  transaction_id: string
  account_id: string
  dest_account: string
  amount: number
  type: string
  decision: string
  risk_score: number | null
  sar_report: string | null
  report_status: string
  created_at: string
}

export default function Dashboard({ onLogout }: { onLogout: () => void }) {
  const [decisions, setDecisions] = useState<Decision[]>([])
  const [selected, setSelected] = useState<Decision | null>(null)
  const [sarExpanded, setSarExpanded] = useState(false)
  const [sarModalOpen, setSarModalOpen] = useState(false)
  const [fiuStatus, setFiuStatus] = useState<string | null>(null)
  const [triggerMessage, setTriggerMessage] = useState<string | null>(null)

  const fetchDecisions = useCallback(async () => {
    try {
      const data = await getRecentDecisions(100)
      setDecisions(data)
    } catch (err) {
      console.error('Failed to fetch decisions', err)
    }
  }, [])

  useEffect(() => {
    fetchDecisions()
    const interval = setInterval(fetchDecisions, 2000)
    return () => clearInterval(interval)
  }, [fetchDecisions])

  const handleSelect = (d: Decision) => {
    setSelected(d)
    setSarExpanded(d.decision === 'block')
    setSarModalOpen(false)
    setFiuStatus(null)
    if (d.decision === 'pass') {
      setTriggerMessage(`Analyze account ${d.account_id}`)
    }
  }

  const handleFIU = async () => {
    if (!selected) return
    try {
      const res = await submitFIU(selected.transaction_id)
      setFiuStatus(`Submitted · Ref: ${res.reference_number}`)
    } catch {
      setFiuStatus('Submission failed')
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>

      {/* Header */}
      <div style={{
        background: 'var(--ing)', height: 48,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 20px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: 16 }}>@ Sha Li</span>
          <span style={{ color: 'rgba(255,255,255,0.5)' }}>|</span>
          <span style={{ color: '#fff', fontSize: 13 }}>FEC Fraud Intelligence Platform</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#7FFF7F' }} />
          <span style={{ color: 'rgba(255,255,255,0.85)', fontSize: 11 }}>Live</span>
          <span style={{ color: 'rgba(255,255,255,0.7)', fontSize: 11 }}>admin</span>
          <button
            onClick={() => { localStorage.removeItem('token'); onLogout() }}
            style={{
              background: 'rgba(255,255,255,0.15)', color: '#fff',
              border: '0.5px solid rgba(255,255,255,0.3)',
              borderRadius: 'var(--radius-sm)', padding: '4px 10px', fontSize: 11,
            }}
          >Sign out</button>
        </div>
      </div>

      {/* Metric cards */}
      <div style={{ padding: '12px 20px 0' }}>
        <MetricCards decisions={decisions} />
      </div>

      {/* Main content */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 400px',
        gap: 12,
        padding: '12px 20px',
        height: 'calc(100vh - 130px)',
      }}>

        {/* Left */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>
          <TransactionFeed
            decisions={decisions}
            onSelect={handleSelect}
            selected={selected}
          />
          <BlockRateChart decisions={decisions} />

          {/* SAR panel */}
          {selected && selected.decision === 'block' && sarExpanded && (
            <div style={{
              background: 'var(--surface)',
              borderRadius: 'var(--radius)',
              border: '0.5px solid var(--border)',
              padding: 16, flex: 1, overflowY: 'auto',
            }}>
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'flex-start', marginBottom: 12,
              }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>SAR Report</div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {selected.account_id} · score {selected.risk_score?.toFixed(2)}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {fiuStatus && (
                    <span style={{
                      fontSize: 11, color: 'var(--passed)',
                      background: 'var(--passed-bg)',
                      padding: '3px 8px', borderRadius: 3,
                    }}>{fiuStatus}</span>
                  )}
                  <button onClick={() => setSarModalOpen(true)} style={{
                    background: 'transparent', color: 'var(--ing)',
                    border: '0.5px solid var(--ing)',
                    borderRadius: 'var(--radius-sm)', padding: '5px 10px', fontSize: 11,
                  }}>Full view</button>
                  <button onClick={handleFIU} style={{
                    background: 'var(--ing)', color: '#fff', border: 'none',
                    borderRadius: 'var(--radius-sm)', padding: '5px 12px',
                    fontSize: 11, fontWeight: 500,
                  }}>Submit to FIU</button>
                  <button onClick={() => setSarExpanded(false)} style={{
                    background: 'transparent', color: 'var(--text-secondary)',
                    border: '0.5px solid var(--border)',
                    borderRadius: 'var(--radius-sm)', padding: '5px 10px', fontSize: 11,
                  }}>Close</button>
                </div>
              </div>

              {selected.sar_report ? (
                <pre style={{
                  fontSize: 12, lineHeight: 1.7,
                  color: 'var(--text-primary)',
                  whiteSpace: 'pre-wrap', fontFamily: 'inherit',
                }}>
                  {selected.sar_report}
                </pre>
              ) : (
                <div style={{
                  color: 'var(--text-muted)', fontSize: 12,
                  padding: '20px 0', textAlign: 'center',
                }}>
                  {selected.report_status === 'pending_manual_review'
                    ? 'Report pending manual review'
                    : 'No SAR report available'}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right: Chat */}
        <ChatPanel
          accountContext={selected?.account_id || null}
          triggerMessage={triggerMessage}
          onTriggerConsumed={() => setTriggerMessage(null)}
        />
      </div>

      {/* SAR Modal */}
      {sarModalOpen && selected && (
        <SARModal
          report={selected.sar_report}
          accountId={selected.account_id}
          riskScore={selected.risk_score || 0}
          transactionId={selected.transaction_id}
          onClose={() => setSarModalOpen(false)}
          onSubmitFIU={handleFIU}
          fiuStatus={fiuStatus}
        />
      )}
    </div>
  )
}