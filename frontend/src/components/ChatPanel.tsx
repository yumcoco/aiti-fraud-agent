import { useState, useRef, useEffect } from 'react'
import { streamChat } from '../api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Session {
  id: string
  title: string
  messageCount: number
}

interface Props {
  accountContext: string | null
  triggerMessage?: string | null
  onTriggerConsumed?: () => void
}

const DEFAULT_CHIPS = [
  'Analyze account C1427122202',
  'Recent blocks',
  'Top risk accounts today',
  'What is the current block rate?',
  'Explain fraud ring detection',
]

export default function ChatPanel({ accountContext, triggerMessage, onTriggerConsumed }: Props) {
  const [sessions, setSessions] = useState<Session[]>([
    { id: 'session-001', title: 'New investigation', messageCount: 0 }
  ])
  const [currentSession, setCurrentSession] = useState('session-001')
  const [messages, setMessages] = useState<Message[]>([{
    role: 'assistant',
    content: 'I can analyze accounts, query the fraud network graph, and generate compliance reports. Use a quick action below or type your question.',
  }])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [statusText, setStatusText] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (triggerMessage && !isStreaming) {
      sendMessage(triggerMessage)
      onTriggerConsumed?.()
    }
  }, [triggerMessage])

  const sendMessage = (text: string) => {
    if (!text.trim() || isStreaming) return
    setInput('')
    setIsStreaming(true)
    setStatusText('')

    setMessages(prev => [...prev, { role: 'user', content: text }])

    let assistantContent = ''
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    streamChat(
      currentSession, text, accountContext,
      (token) => {
        assistantContent += token
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
          return updated
        })
      },
      (status) => setStatusText(status),
      () => {
        setIsStreaming(false)
        setStatusText('')
        setSessions(prev => prev.map(s =>
          s.id === currentSession
            ? { ...s, messageCount: s.messageCount + 2, title: text.slice(0, 30) }
            : s
        ))
      },
      (err) => {
        setIsStreaming(false)
        setStatusText('')
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: `Error: ${err}` }
          return updated
        })
      }
    )
  }

  const newSession = () => {
    const id = `session-${Date.now()}`
    setSessions(prev => [{ id, title: 'New investigation', messageCount: 0 }, ...prev])
    setCurrentSession(id)
    setMessages([{
      role: 'assistant',
      content: 'New session started. Use a quick action or type an account ID to begin.',
    }])
  }

  return (
    <div style={{
      background: 'var(--surface)',
      borderRadius: 'var(--radius)',
      border: '0.5px solid var(--border)',
      display: 'flex',
      height: '100%',
      overflow: 'hidden',
    }}>

      {/* Session sidebar */}
      <div style={{ width: 140, borderRight: '0.5px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 8, borderBottom: '0.5px solid var(--border)' }}>
          <button onClick={newSession} style={{
            width: '100%', background: 'var(--ing)', color: '#fff',
            border: 'none', borderRadius: 'var(--radius-sm)', padding: '6px 0', fontWeight: 500,
          }}>+ New session</button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px' }}>
          {sessions.map(s => (
            <div key={s.id} onClick={() => setCurrentSession(s.id)} style={{
              padding: '6px 8px', borderRadius: 'var(--radius-sm)', cursor: 'pointer', marginBottom: 2,
              background: s.id === currentSession ? 'var(--ing-light)' : 'transparent',
              border: `0.5px solid ${s.id === currentSession ? 'var(--ing-border)' : 'transparent'}`,
              color: s.id === currentSession ? 'var(--ing-dark)' : 'var(--text-secondary)',
            }}>
              <div style={{ fontSize: 11, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.title}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                {s.messageCount} messages
              </div>
            </div>
          ))}
        </div>
        <div style={{ padding: '8px 10px', borderTop: '0.5px solid var(--border)', fontSize: 10, color: 'var(--text-muted)' }}>
          investigator · admin
        </div>
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>

        {/* Header */}
        <div style={{
          padding: '10px 14px', borderBottom: '0.5px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontWeight: 500, fontSize: 13 }}>Investigation assistant</div>
            <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 1 }}>
              Tool-calling enabled · grounded responses
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 6, height: 6, borderRadius: '50%',
              background: isStreaming ? 'var(--ing)' : 'var(--passed)',
            }} />
            <span style={{ fontSize: 10, color: 'var(--text-secondary)' }}>
              {isStreaming ? 'Analyzing...' : 'Ready'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '10px 14px',
          display: 'flex', flexDirection: 'column', gap: 10,
        }}>
          {statusText && (
            <div style={{ fontSize: 11, color: 'var(--ing)', fontStyle: 'italic' }}>
              {statusText}
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div style={{
                background: msg.role === 'user' ? 'var(--ing)' : 'var(--bg)',
                borderRadius: msg.role === 'user' ? '8px 0 8px 8px' : '0 8px 8px 8px',
                padding: '8px 12px',
                maxWidth: '90%',
                border: msg.role === 'assistant' ? '0.5px solid var(--border)' : 'none',
              }}>
                <div style={{
                  fontSize: 12,
                  color: msg.role === 'user' ? '#fff' : 'var(--text-primary)',
                  lineHeight: 1.6,
                  whiteSpace: 'pre-wrap',
                }}>
                  {msg.content || (isStreaming && i === messages.length - 1 ? '▋' : '')}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick chips */}
        <div style={{ padding: '8px 14px 0', display: 'flex', flexWrap: 'wrap', gap: 5 }}>
          {DEFAULT_CHIPS.map(chip => (
            <button key={chip} onClick={() => setInput(chip)} style={{
              background: 'var(--ing-light)', color: 'var(--ing-dark)',
              border: '0.5px solid var(--ing-border)', borderRadius: 12,
              padding: '3px 10px', fontSize: 11,
            }}>{chip}</button>
          ))}
        </div>

        {/* Input */}
        <div style={{ padding: '8px 14px 12px' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
              placeholder="Ask about an account or transaction..."
              disabled={isStreaming}
              style={{
                flex: 1, border: '0.5px solid var(--border)',
                borderRadius: 'var(--radius-sm)', padding: '7px 10px',
                fontSize: 12, outline: 'none', background: 'var(--bg)',
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={isStreaming || !input.trim()}
              style={{
                background: isStreaming || !input.trim() ? 'var(--ing-border)' : 'var(--ing)',
                color: '#fff', border: 'none',
                borderRadius: 'var(--radius-sm)', padding: '7px 14px',
                fontSize: 12, fontWeight: 500,
              }}
            >Send</button>
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 5 }}>
            Tool-grounded responses · no hallucination · session memory active
          </div>
        </div>
      </div>
    </div>
  )
}