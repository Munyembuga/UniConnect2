import { Link } from 'react-router-dom'
import { MapPin, Phone, Mail, ExternalLink } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="bg-primary-dark text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-14">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10">
          {/* Brand */}
          <div className="lg:col-span-2">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg bg-white/15 flex items-center justify-center font-bold text-white text-sm">
                UC
              </div>
              <div>
                <div className="font-bold text-lg">UniConnect</div>
                <div className="text-primary-100 text-xs font-medium tracking-wider uppercase">University of Rwanda</div>
              </div>
            </div>
            <p className="text-white/70 text-sm leading-relaxed max-w-sm">
              An AI-powered student support assistant providing instant, accurate information
              about academic programs, admissions, campus life, and administrative services at
              the University of Rwanda.
            </p>
          </div>

          {/* Quick links */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-white/50 mb-4">Quick Links</h4>
            <ul className="space-y-2.5 text-sm">
              {[
                { label: 'Start Chatting', to: '/chat' },
                { label: 'About UniConnect', to: '/#about' },
                { label: 'Admissions', to: '/chat' },
                { label: 'Academic Programs', to: '/chat' },
                { label: 'Admin Portal', to: '/admin/login' },
              ].map(link => (
                <li key={link.label}>
                  <Link
                    to={link.to}
                    className="text-white/70 hover:text-white transition-colors duration-150"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h4 className="font-semibold text-sm uppercase tracking-wider text-white/50 mb-4">University of Rwanda</h4>
            <ul className="space-y-3 text-sm text-white/70">
              <li className="flex items-start gap-2.5">
                <MapPin size={14} className="mt-0.5 shrink-0 text-primary-light" />
                <span>Kigali, Rwanda<br/>KN 7 Ave</span>
              </li>
              <li className="flex items-center gap-2.5">
                <Phone size={14} className="shrink-0 text-primary-light" />
                <span>+250 788 000 000</span>
              </li>
              <li className="flex items-center gap-2.5">
                <Mail size={14} className="shrink-0 text-primary-light" />
                <span>info@ur.ac.rw</span>
              </li>
              <li className="flex items-center gap-2.5">
                <ExternalLink size={14} className="shrink-0 text-primary-light" />
                <a
                  href="https://www.ur.ac.rw"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-white transition-colors"
                >
                  www.ur.ac.rw
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Copyright bar */}
      <div className="bg-primary border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-white/50">
          <p>© {new Date().getFullYear()} UniConnect — University of Rwanda. All rights reserved.</p>
          <p>Built for the UR Computer Engineering Final Year Project 2025–2026</p>
        </div>
      </div>
    </footer>
  )
}
