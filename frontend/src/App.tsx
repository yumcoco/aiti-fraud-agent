import { useState, useEffect } from 'react'
import LoginPage from './components/LoginPage'
import Dashboard from './components/Dashboard'
import './styles/tokens.css'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) setIsLoggedIn(true)
  }, [])

  return isLoggedIn
    ? <Dashboard />
    : <LoginPage onLogin={() => setIsLoggedIn(true)} />
}

export default App