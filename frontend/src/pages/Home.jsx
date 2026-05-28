import { Link } from 'react-router-dom'
import {
  MessageSquare, Mic, Globe, Clock, BookOpen, GraduationCap,
  Building, FileText, Users, ChevronRight, ArrowRight, CheckCircle
} from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'

const features = [
  {
    icon: <MessageSquare size={22} />,
    title: 'Text & Voice Input',
    desc: 'Ask by typing or speaking — UniConnect understands both and responds clearly.',
  },
  {
    icon: <BookOpen size={22} />,
    title: 'Accurate Answers',
    desc: 'Responses sourced directly from official UR documents and guidelines — not guesses.',
  },
  {
    icon: <Clock size={22} />,
    title: 'Available 24 / 7',
    desc: 'Get information at any time, even outside office hours or during busy periods.',
  },
  {
    icon: <Globe size={22} />,
    title: 'Multilingual',
    desc: 'Communicate in English or Kinyarwanda — your language, your choice.',
  },
]

const topics = [
  { icon: <GraduationCap size={20} />, label: 'Admissions & Applications' },
  { icon: <BookOpen size={20} />,      label: 'Academic Programs' },
  { icon: <FileText size={20} />,      label: 'Registration & Records' },
  { icon: <Building size={20} />,      label: 'Campus Facilities' },
  { icon: <Users size={20} />,         label: 'Student Services' },
  { icon: <Globe size={20} />,         label: 'Scholarships & Fees' },
]

const steps = [
  {
    number: '01',
    title: 'Ask Your Question',
    desc: 'Type your question or tap the microphone to speak. Use English or Kinyarwanda.',
  },
  {
    number: '02',
    title: 'AI Searches the Knowledge Base',
    desc: 'UniConnect searches through official UR documents and previously verified answers.',
  },
  {
    number: '03',
    title: 'Receive a Clear Answer',
    desc: 'Get an accurate, concise response in seconds. The system only answers what it knows.',
  },
]

const stats = [
  { value: '5,000+', label: 'Active Students' },
  { value: '24 / 7',  label: 'Availability' },
  { value: '3',       label: 'Languages Supported' },
  { value: '<2s',     label: 'Response Time' },
]

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* ── HERO ───────────────────────────────────────────────── */}
      <section className="relative bg-hero-gradient pt-24 pb-24 md:pt-36 md:pb-32 overflow-hidden">
        {/* Decorative background blobs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none select-none">
          <div className="absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full bg-white/5 blur-3xl" />
          <div className="absolute bottom-0 -left-16 w-80 h-80 rounded-full bg-primary-light/10 blur-2xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[300px] rounded-full bg-primary-dark/20 blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="grid lg:grid-cols-2 gap-14 items-center">

            {/* Left — copy */}
            <div>
              {/* Badge */}
              <span
                className="hero-badge inline-flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/15
                           text-white/90 text-xs font-semibold rounded-full tracking-wider uppercase mb-7"
                style={{ animationDelay: '0s' }}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                University of Rwanda · Student Support
              </span>

              <h1
                className="hero-animate text-4xl md:text-5xl lg:text-[3.4rem] font-extrabold text-white leading-[1.1] mb-6 text-balance"
                style={{ animationDelay: '0.12s' }}
              >
                Your University,
                <br />
                <span className="text-primary-light">Answered Instantly</span>
              </h1>

              <p
                className="hero-animate text-white/70 text-lg leading-relaxed mb-9 max-w-[480px]"
                style={{ animationDelay: '0.26s' }}
              >
                UniConnect is your intelligent campus guide. Ask about admissions,
                registration, academic programs, scholarships, or campus life —
                and get accurate answers in seconds.
              </p>

              <div
                className="hero-animate flex flex-wrap gap-4"
                style={{ animationDelay: '0.4s' }}
              >
                <Link
                  to="/chat"
                  className="btn-primary text-base px-8 py-3.5 shadow-lg hover:shadow-xl"
                >
                  Start Chatting
                  <ArrowRight size={18} />
                </Link>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg border-2 border-white/30
                             text-white font-semibold text-base hover:bg-white/10 hover:border-white/50
                             transition-all duration-200 active:scale-95"
                >
                  How It Works
                </a>
              </div>
            </div>

            {/* Right — chat preview card */}
            <div
              className="hero-animate hidden lg:flex justify-center lg:justify-end"
              style={{ animationDelay: '0.2s' }}
            >
              <div className="float-card w-full max-w-[360px] bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6 shadow-2xl">
                {/* Card header */}
                <div className="flex items-center gap-3 pb-4 border-b border-white/10 mb-5">
                  <div className="w-9 h-9 rounded-full bg-primary-light flex items-center justify-center text-white font-bold text-xs shadow-sm">
                    UC
                  </div>
                  <div>
                    <div className="text-white text-sm font-semibold">UniConnect</div>
                    <div className="flex items-center gap-1.5 text-primary-light text-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                      Online · Ready to help
                    </div>
                  </div>
                  {/* Decorative dots */}
                  <div className="ml-auto flex gap-1">
                    <span className="w-2 h-2 rounded-full bg-white/20" />
                    <span className="w-2 h-2 rounded-full bg-white/20" />
                    <span className="w-2 h-2 rounded-full bg-white/20" />
                  </div>
                </div>

                {/* Sample messages */}
                <div className="space-y-4 mb-5">
                  {/* User */}
                  <div className="flex justify-end">
                    <div className="bg-primary-light/85 text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[82%] shadow-sm leading-relaxed">
                      What are the admission requirements for Computer Engineering?
                    </div>
                  </div>
                  {/* Bot */}
                  <div className="flex justify-start">
                    <div className="bg-white/18 text-white text-sm rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[88%] leading-relaxed">
                      For Computer Engineering at UR-CST, you need A-level passes in
                      Mathematics and Physics or Chemistry, then qualify via the national
                      selection process.
                    </div>
                  </div>
                  {/* User */}
                  <div className="flex justify-end">
                    <div className="bg-primary-light/85 text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[82%] shadow-sm">
                      When does registration open?
                    </div>
                  </div>
                  {/* Typing */}
                  <div className="flex items-end gap-2">
                    <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-[10px] font-bold">
                      UC
                    </div>
                    <div className="bg-white/15 rounded-2xl rounded-tl-sm px-4 py-3">
                      <div className="flex items-center gap-1.5 h-3.5">
                        <span className="w-2 h-2 rounded-full bg-white/60 typing-dot" />
                        <span className="w-2 h-2 rounded-full bg-white/60 typing-dot" />
                        <span className="w-2 h-2 rounded-full bg-white/60 typing-dot" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Fake input */}
                <div className="flex items-center gap-2.5 bg-white/12 border border-white/15 rounded-xl px-4 py-2.5">
                  <input
                    readOnly
                    type="text"
                    placeholder="Type your question…"
                    className="flex-1 bg-transparent text-white/60 text-sm outline-none placeholder-white/35 font-medium"
                  />
                  <Mic size={16} className="text-white/50 shrink-0" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── STATS BAR ──────────────────────────────────────────── */}
      <section className="bg-slate-ur text-white py-10">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((s, i) => (
              <div key={s.label} className={`text-center ${i < 3 ? 'md:border-r md:border-white/15' : ''}`}>
                <div className="text-3xl font-extrabold text-white mb-1 tracking-tight">{s.value}</div>
                <div className="text-white/55 text-sm font-medium">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ───────────────────────────────────────────── */}
      <section className="py-20 bg-gray-50" id="about">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="text-center mb-14">
            <h2 className="section-title mb-4">Built for Every UR Student</h2>
            <p className="section-subtitle mx-auto text-center">
              UniConnect combines modern AI with official UR data to give you reliable,
              instant support — wherever you are.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map(f => (
              <div
                key={f.title}
                className="card p-7 flex flex-col gap-4 hover:border-primary/30 transition-all duration-300 hover:-translate-y-0.5"
              >
                <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                  {f.icon}
                </div>
                <div>
                  <h3 className="font-bold text-slate-ur mb-2">{f.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ───────────────────────────────────────── */}
      <section className="py-20 bg-white" id="how-it-works">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="text-center mb-16">
            <h2 className="section-title mb-4">How It Works</h2>
            <p className="section-subtitle mx-auto text-center">
              Three simple steps from question to answer.
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-10 relative">
            {/* Connecting line */}
            <div className="hidden md:block absolute top-10 left-[28%] right-[28%] h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

            {steps.map((step, i) => (
              <div
                key={step.number}
                className="relative text-center flex flex-col items-center gap-4 group"
              >
                <div className={`w-20 h-20 rounded-2xl flex flex-col items-center justify-center shadow-md z-10
                  transition-all duration-300 group-hover:scale-105 group-hover:shadow-lg ${
                  i === 1
                    ? 'bg-primary text-white'
                    : 'bg-white border-2 border-primary text-primary'
                }`}>
                  <span className="text-2xl font-extrabold leading-none">{step.number}</span>
                </div>
                <h3 className="font-bold text-slate-ur text-lg">{step.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed max-w-xs">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── TOPICS ─────────────────────────────────────────────── */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="grid lg:grid-cols-2 gap-14 items-center">
            <div>
              <h2 className="section-title mb-5">What Can You Ask?</h2>
              <p className="text-gray-500 leading-relaxed mb-8 text-base">
                UniConnect is trained on official University of Rwanda documents and guidelines.
                Whether it's about your first year or a postgraduate application — we have
                you covered.
              </p>
              <Link to="/chat" className="btn-primary">
                Ask a Question Now
                <ChevronRight size={18} />
              </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {topics.map(t => (
                <Link
                  key={t.label}
                  to="/chat"
                  className="card p-5 flex flex-col items-start gap-3 hover:border-primary/40
                             hover:-translate-y-0.5 transition-all duration-200 group"
                >
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary
                                  group-hover:bg-primary group-hover:text-white transition-colors duration-200">
                    {t.icon}
                  </div>
                  <span className="text-sm font-semibold text-slate-ur leading-snug">{t.label}</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── HONESTY BANNER ─────────────────────────────────────── */}
      <section className="bg-slate-dark py-20">
        <div className="max-w-4xl mx-auto px-6 sm:px-8 lg:px-12 text-center">
          <h2 className="text-white text-3xl md:text-4xl font-bold mb-5">Honest by Design</h2>
          <p className="text-white/60 text-base leading-relaxed mb-10 max-w-2xl mx-auto">
            UniConnect only answers from verified sources. If it doesn't know, it tells
            you so — and flags the question for staff review. No hallucinations, no guessing.
          </p>
          <div className="flex flex-wrap justify-center gap-6 md:gap-10 text-sm text-white/70">
            {[
              'Sourced from official UR documents',
              'Flags unanswered questions for review',
              'Continuously improved by administrators',
            ].map(pt => (
              <div key={pt} className="flex items-center gap-2.5">
                <CheckCircle size={16} className="text-primary-light shrink-0" />
                <span>{pt}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ────────────────────────────────────────────────── */}
      <section className="py-20 bg-white">
        <div className="max-w-3xl mx-auto px-6 sm:px-8 lg:px-12 text-center">
          <h2 className="section-title mb-5">Ready to Get Started?</h2>
          <p className="section-subtitle mx-auto text-center mb-9">
            Join University of Rwanda students who get faster, reliable answers through UniConnect.
          </p>
          <Link to="/chat" className="btn-primary text-base px-10 py-4 shadow-lg hover:shadow-xl">
            Open UniConnect
            <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  )
}
