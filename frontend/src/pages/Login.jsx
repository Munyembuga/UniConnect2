import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Eye, EyeOff, ArrowLeft, LogIn, UserPlus } from 'lucide-react'
import { login, register, getMe, clearAuth } from '../services/api'


export default function Login() {
  const [mode, setMode]           = useState('login')   // 'login' | 'register'
  const [form, setForm]           = useState({ email: '', password: '', full_name: '' })
  const [showPass, setShowPass]   = useState(false)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState('')
  const navigate = useNavigate()

  const handleChange = (e) =>
    setForm(f => ({ ...f, [e.target.name]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!form.email || !form.password) {
      setError('Please fill in all fields.')
      return
    }
    if (mode === 'register' && !form.full_name.trim()) {
      setError('Please enter your full name.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'register') {
        await register(form.email, form.password, form.full_name)
        // auto-login after register
      }
      await login(form.email, form.password)
      // fetch user profile, store it, then redirect based on role
      try {
        const me = await getMe()
        localStorage.setItem('user', JSON.stringify(me))
        navigate(me.role === 'admin' ? '/admin' : '/chat', { replace: true })
      } catch (_) {
        navigate('/chat', { replace: true })
      }
    } catch (err) {
      clearAuth()
      setError(err.message || 'Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <div className="bg-primary px-6 py-4 flex items-center gap-4">
        <Link to="/" className="flex items-center gap-2 text-white/80 hover:text-white text-sm transition-colors">
          <ArrowLeft size={16} />
          Back to UniConnect
        </Link>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-flex w-16 h-16 rounded-2xl bg-primary items-center justify-center text-white font-extrabold text-xl mb-5 shadow-lg">
              UC
            </div>
            <h1 className="text-2xl font-bold text-slate-ur mb-1">
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </h1>
            <p className="text-gray-400 text-sm">
              {mode === 'login'
                ? 'Sign in to continue'
                : 'Register to start asking questions'}
            </p>
          </div>

          {/* Tab toggle */}
          <div className="flex bg-gray-100 rounded-xl p-1 mb-6">
            {[['login', 'Sign In'], ['register', 'Register']].map(([key, label]) => (
              <button
                key={key}
                onClick={() => { setMode(key); setError('') }}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold transition-all duration-150 ${
                  mode === key
                    ? 'bg-white text-primary shadow-sm'
                    : 'text-gray-500 hover:text-slate-ur'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="card p-8 border border-gray-100">
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm">
                  {error}
                </div>
              )}

              {mode === 'register' && (
                <div>
                  <label className="block text-sm font-medium text-slate-ur mb-1.5">Full Name</label>
                  <input
                    type="text"
                    name="full_name"
                    value={form.full_name}
                    onChange={handleChange}
                    placeholder="Your full name"
                    className="input-field"
                    autoComplete="name"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-slate-ur mb-1.5">Email Address</label>
                <input
                  type="email"
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  className="input-field"
                  autoComplete="email"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-ur mb-1.5">Password</label>
                <div className="relative">
                  <input
                    type={showPass ? 'text' : 'password'}
                    name="password"
                    value={form.password}
                    onChange={handleChange}
                    placeholder="Enter your password"
                    className="input-field pr-11"
                    autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-slate-ur transition-colors"
                  >
                    {showPass ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary justify-center py-3.5 text-base mt-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    {mode === 'login' ? 'Signing in…' : 'Creating account…'}
                  </span>
                ) : mode === 'login' ? (
                  <><LogIn size={17} /> Sign In</>
                ) : (
                  <><UserPlus size={17} /> Create Account</>
                )}
              </button>
            </form>
          </div>

        </div>
      </div>
    </div>
  )
}
