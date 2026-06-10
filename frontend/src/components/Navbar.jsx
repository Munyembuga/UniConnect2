import { useState, useEffect } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { Menu, X, LogIn, LogOut, LayoutDashboard } from 'lucide-react'
import { getToken, getUser, clearAuth } from '../services/api'

const navLinks = [
  { label: 'Home', to: '/' },
  { label: 'Chat', to: '/chat' },
  { label: 'About', to: '/#about' },
]

export default function Navbar() {
  const [menuOpen, setMenuOpen]   = useState(false)
  const [scrolled, setScrolled]   = useState(false)
  const location                  = useLocation()
  const navigate                  = useNavigate()
  const token                     = getToken()
  const user                      = getUser()
  const isAdmin                   = user?.role === 'admin'

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll)
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => { setMenuOpen(false) }, [location])

  const handleLogout = () => {
    clearAuth()
    navigate('/')
  }

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      scrolled ? 'bg-primary shadow-lg' : 'bg-primary'
    }`}>
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Logo */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center font-bold text-white text-sm tracking-wide group-hover:bg-white/25 transition-colors">
              UC
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-white font-bold text-base tracking-wide">UniConnect</span>
              <span className="text-primary-100 text-[10px] font-medium tracking-wider uppercase">University of Rwanda</span>
            </div>
          </Link>

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-1">
            {navLinks.map(link => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive && !link.to.includes('#')
                      ? 'bg-white/20 text-white'
                      : 'text-white/80 hover:text-white hover:bg-white/10'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>

          {/* Desktop right — auth buttons */}
          <div className="hidden md:flex items-center gap-2">
            {token ? (
              <>
                {isAdmin && (
                  <Link
                    to="/admin"
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                  >
                    <LayoutDashboard size={15} />
                    Dashboard
                  </Link>
                )}
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-primary bg-white rounded-lg hover:bg-primary-50 transition-colors"
                >
                  <LogOut size={15} />
                  Sign Out
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-semibold text-primary bg-white rounded-lg hover:bg-primary-50 transition-colors"
              >
                <LogIn size={15} />
                Sign In
              </Link>
            )}
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden p-2 rounded-lg text-white hover:bg-white/10 transition-colors"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Toggle menu"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden border-t border-white/10 py-3 space-y-1">
            {navLinks.map(link => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive && !link.to.includes('#')
                      ? 'bg-white/20 text-white'
                      : 'text-white/80 hover:text-white hover:bg-white/10'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}

            <div className="pt-2 border-t border-white/10 mt-2">
              {token ? (
                <>
                  {isAdmin && (
                    <Link
                      to="/admin"
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white/80 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                      <LayoutDashboard size={15} />
                      Dashboard
                    </Link>
                  )}
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-4 py-2.5 mt-1 text-sm font-semibold text-primary bg-white rounded-lg text-center justify-center"
                  >
                    <LogOut size={15} />
                    Sign Out
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  className="flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-primary bg-white rounded-lg"
                >
                  <LogIn size={15} />
                  Sign In
                </Link>
              )}
            </div>
          </div>
        )}
      </nav>
    </header>
  )
}
