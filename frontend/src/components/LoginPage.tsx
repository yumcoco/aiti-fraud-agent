import { useState } from 'react'
import { login } from '../api/client'

interface Props {
  onLogin: () => void
}

export default function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('fraud2026')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    setLoading(true)
    setError('')
    try {
      const token = await login(username, password)
      localStorage.setItem('token', token)
      onLogin()
    } catch {
      setError('Access denied. Please use the demo credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{ width: 340 }}>

        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--ing)', marginBottom: 4 }}>
            FEC Fraud Intelligence
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>
            Investigator portal
          </div>
        </div>

        <div style={{
          background: 'var(--surface)',
          borderRadius: 'var(--radius-lg)',
          border: '0.5px solid var(--border)',
          padding: 24,
        }}>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              style={{
                width: '100%',
                border: '0.5px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 10px',
                fontSize: 13,
                outline: 'none',
              }}
            />
          </div>

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 4 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleLogin()}
              style={{
                width: '100%',
                border: '0.5px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                padding: '8px 10px',
                fontSize: 13,
                outline: 'none',
              }}
            />
          </div>

          <div style={{
            fontSize: 11,
            color: 'var(--text-secondary)',
            background: 'var(--bg)',
            border: '0.5px solid var(--border)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            marginBottom: 16,
          }}>
            Demo — username: <span style={{ color: 'var(--ing)', fontWeight: 500 }}>admin</span>
            {' '}· password: <span style={{ color: 'var(--ing)', fontWeight: 500 }}>fraud2026</span>
          </div>

          {error && (
            <div style={{ fontSize: 12, color: 'var(--blocked)', marginBottom: 12 }}>
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={handleLogin}
            disabled={loading}
            style={{
              width: '100%',
              background: loading ? 'var(--ing-border)' : 'var(--ing)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              padding: '10px',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </div>

        <div style={{ textAlign: 'center', marginTop: 16, fontSize: 11, color: 'var(--text-muted)' }}>
          Unauthorised access will be logged and reported
        </div>
      </div>
    </div>
  )
}