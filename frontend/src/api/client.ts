import axios from 'axios'

const BASE_URL = 'http://localhost:8000'

const api = axios.create({ baseURL: BASE_URL })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const token = localStorage.getItem('token')
      if (token) {
        // 已登录状态收到 401 才跳转
        localStorage.removeItem('token')
        window.location.href = '/'
      }
      // 登录时的 401 直接 reject，让 LoginPage 的 catch 处理
    }
    return Promise.reject(err)
  }
)

export default api

export const login = async (username: string, password: string) => {
  const res = await api.post('/auth/login', { username, password })
  return res.data.access_token
}

export const getRecentDecisions = async (limit = 100) => {
  const res = await api.get(`/api/v1/decisions/recent?limit=${limit}`)
  return res.data
}

export const getDecision = async (transactionId: string) => {
  const res = await api.get(`/api/v1/decision/${transactionId}`)
  return res.data
}

export const submitFIU = async (transactionId: string) => {
  const res = await api.post(`/api/v1/report/fiu/${transactionId}`)
  return res.data
}

export const streamChat = (
  sessionId: string,
  message: string,
  accountContext: string | null,
  onToken: (token: string) => void,
  onStatus: (status: string) => void,
  onDone: () => void,
  onError: (err: string) => void
) => {
  const token = localStorage.getItem('token')
  fetch(`${BASE_URL}/api/v1/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      account_context: accountContext,
    }),
  }).then(async (res) => {
    const reader = res.body!.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const text = decoder.decode(value)
      const lines = text.split('\n')
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.type === 'token') onToken(data.content)
          else if (data.type === 'status') onStatus(data.content)
          else if (data.type === 'done') onDone()
          else if (data.type === 'error') onError(data.content)
        } catch {}
      }
    }
  }).catch(onError)
}