import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  MessageSquare, Mic, Globe, Clock, BookOpen, GraduationCap,
  Building, FileText, Users, ChevronRight, ArrowRight, CheckCircle, Send,
} from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { askQuestion } from '../services/api'

const features = [
  { icon: <MessageSquare size={22} />, title: 'Text & Voice Input',  desc: 'Ask by typing or speaking — UniConnect understands both and responds clearly.' },
  { icon: <BookOpen size={22} />,      title: 'Accurate Answers',    desc: 'Responses sourced directly from official UR documents and guidelines — not guesses.' },
  { icon: <Clock size={22} />,         title: 'Available 24 / 7',    desc: 'Get information at any time, even outside office hours or during busy periods.' },
  { icon: <Globe size={22} />,         title: 'Multilingual',         desc: 'Communicate in English or Kinyarwanda — your language, your choice.' },
]

const topics = [
  { icon: <GraduationCap size={20} />, label: 'Admissions & Applications',  q: 'What are the admission requirements at University of Rwanda?' },
  { icon: <BookOpen size={20} />,      label: 'Academic Programs',           q: 'What programs does the University of Rwanda offer?' },
  { icon: <FileText size={20} />,      label: 'Registration & Records',      q: 'How do I register for courses at University of Rwanda?' },
  { icon: <Building size={20} />,      label: 'Campus Facilities',           q: 'What facilities are available on campus at University of Rwanda?' },
  { icon: <Users size={20} />,         label: 'Student Services',            q: 'What student services are available at University of Rwanda?' },
  { icon: <Globe size={20} />,         label: 'Scholarships & Fees',         q: 'What scholarships are available at University of Rwanda?' },
]

const suggestions = [
  'What are the admission requirements for Computer Engineering?',
  'When does semester registration open?',
  'How do I apply for a scholarship?',
  'What programs are offered at UR-CST?',
  'Where is the UR library located?',
]

const steps = [
  { number: '01', title: 'Ask Your Question',               desc: 'Type your question or tap the microphone to speak. Use English or Kinyarwanda.' },
  { number: '02', title: 'AI Searches the Knowledge Base',  desc: 'UniConnect searches through official UR documents and previously verified answers.' },
  { number: '03', title: 'Receive a Clear Answer',          desc: 'Get an accurate, concise response in seconds. The system only answers what it knows.' },
]

const stats = [
  { value: '5,000+', label: 'Active Students' },
  { value: '24 / 7', label: 'Availability' },
  { value: '3',      label: 'Languages Supported' },
  { value: '<2s',    label: 'Response Time' },
]

/* ── Mini markdown renderer (glass / dark background) ──────────────────────── */
function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i} className="font-semibold text-white">{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*'))
      return <em key={i} className="italic">{part.slice(1, -1)}</em>
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i} className="bg-white/20 px-1 rounded text-[9px] font-mono">{part.slice(1, -1)}</code>
    return part
  })
}

function MiniMarkdown({ text }) {
  const lines = text.split('\n')
  const blocks = []
  let i = 0

  while (i < lines.length) {
    const raw = lines[i]
    const line = raw.trim()
    if (!line) { i++; continue }

    // Table (pipe-separated with separator row)
    if (line.startsWith('|')) {
      const tableLines = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i].trim())
        i++
      }
      const parseRow = (r) => r.split('|').slice(1, -1).map(c => c.trim())
      const nonSep = tableLines.filter(l => !/^\|[\s\-:|]+\|$/.test(l))
      if (nonSep.length > 1) {
        blocks.push({ type: 'table', header: parseRow(nonSep[0]), rows: nonSep.slice(1).map(parseRow) })
      }
      continue
    }

    // Bullet list (* or - or •)
    if (/^[\*\-•]\s+/.test(line)) {
      const items = []
      while (i < lines.length && /^[\*\-•]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[\*\-•]\s+/, ''))
        i++
      }
      blocks.push({ type: 'bullets', items })
      continue
    }

    // Numbered list
    if (/^\d+[\.\)]\s+/.test(line)) {
      const items = []
      while (i < lines.length && /^\d+[\.\)]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+[\.\)]\s+/, ''))
        i++
      }
      blocks.push({ type: 'numbered', items })
      continue
    }

    // Heading
    if (/^#{1,3}\s+/.test(line)) {
      blocks.push({ type: 'heading', text: line.replace(/^#{1,3}\s+/, '') })
      i++; continue
    }

    // Plain paragraph — collect consecutive non-special lines
    const paras = []
    while (i < lines.length) {
      const l = lines[i].trim()
      if (!l) { i++; break }
      if (/^[\*\-•\d|#]/.test(l)) break
      paras.push(l)
      i++
    }
    if (paras.length) blocks.push({ type: 'para', text: paras.join(' ') })
  }

  return (
    <div className="space-y-2 text-[11px] leading-relaxed text-white/90">
      {blocks.map((block, idx) => {
        if (block.type === 'heading') return (
          <p key={idx} className="font-bold text-white text-xs">{renderInline(block.text)}</p>
        )
        if (block.type === 'para') return (
          <p key={idx}>{renderInline(block.text)}</p>
        )
        if (block.type === 'bullets') return (
          <ul key={idx} className="space-y-1.5 pl-0.5">
            {block.items.map((item, j) => (
              <li key={j} className="flex gap-2 items-start">
                <span className="mt-[3px] w-1.5 h-1.5 rounded-full bg-primary-light shrink-0" />
                <span>{renderInline(item)}</span>
              </li>
            ))}
          </ul>
        )
        if (block.type === 'numbered') return (
          <ol key={idx} className="space-y-1.5 pl-0.5">
            {block.items.map((item, j) => (
              <li key={j} className="flex gap-2 items-start">
                <span className="text-primary-light font-bold shrink-0 leading-tight">{j + 1}.</span>
                <span>{renderInline(item)}</span>
              </li>
            ))}
          </ol>
        )
        if (block.type === 'table') return (
          <div key={idx} className="overflow-x-auto rounded-lg border border-white/15 mt-1">
            <table className="w-full text-[10px]">
              <thead>
                <tr className="border-b border-white/15 bg-white/10">
                  {block.header.map((h, j) => (
                    <th key={j} className="px-2 py-1 text-left font-semibold text-white whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {block.rows.map((row, j) => (
                  <tr key={j} className={j % 2 === 0 ? '' : 'bg-white/5'}>
                    {row.map((cell, k) => (
                      <td key={k} className="px-2 py-1 text-white/80">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
        return null
      })}
    </div>
  )
}

/* ── Mini-chat widget (hero card) ──────────────────────────────────────────── */
const INITIAL = [{
  role: 'bot',
  text: "Hi! I'm UniConnect. Ask me anything about UR admissions, programs, scholarships, or campus life.",
}]

function MiniChat({ suggestions }) {
  const [messages, setMessages] = useState(INITIAL)
  const [input, setInput]       = useState('')
  const [typing, setTyping]     = useState(false)
  const msgsRef = useRef(null)  // scroll container — NOT the page
  const inputRef = useRef(null)

  // Scroll only within the card, never the page
  useEffect(() => {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight
    }
  }, [messages, typing])

  const send = async (text) => {
    const q = (text || input).trim()
    if (!q || typing) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', text: q }])
    setTyping(true)
    try {
      const data = await askQuestion(q)
      setMessages(prev => [...prev, {
        role: 'bot',
        text: data.answer || "I couldn't find an answer. Try rephrasing your question.",
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'bot',
        text: 'Something went wrong. Please try again.',
      }])
    } finally {
      setTyping(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="float-card w-full max-w-[360px] bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6 shadow-2xl flex flex-col" style={{ height: 440 }}>
      {/* Header — unchanged styling */}
      <div className="flex items-center gap-3 pb-4 border-b border-white/10 mb-4 shrink-0">
        <div className="w-9 h-9 rounded-full bg-primary-light flex items-center justify-center text-white font-bold text-xs shadow-sm">UC</div>
        <div>
          <div className="text-white text-sm font-semibold">UniConnect</div>
          <div className="flex items-center gap-1.5 text-primary-light text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            Online · Ready to help
          </div>
        </div>
        <div className="ml-auto flex gap-1">
          <span className="w-2 h-2 rounded-full bg-white/20" />
          <span className="w-2 h-2 rounded-full bg-white/20" />
          <span className="w-2 h-2 rounded-full bg-white/20" />
        </div>
      </div>

      {/* Messages */}
      <div ref={msgsRef} className="flex-1 overflow-y-auto space-y-3 pr-1 mb-4 scrollbar-hide">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start items-end gap-2'}`}>
            {m.role === 'bot' && (
              <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-[10px] font-bold shrink-0">UC</div>
            )}
            <div className={`text-white rounded-2xl px-3.5 py-2.5 max-w-[86%] ${
              m.role === 'user'
                ? 'bg-primary-light/85 rounded-tr-sm shadow-sm text-xs leading-relaxed'
                : 'bg-white/15 rounded-tl-sm'
            }`}>
              {m.role === 'user' ? m.text : <MiniMarkdown text={m.text} />}
            </div>
          </div>
        ))}
        {typing && (
          <div className="flex items-end gap-2">
            <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-white text-[10px] font-bold shrink-0">UC</div>
            <div className="bg-white/15 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-1.5 h-3.5">
                <span className="w-2 h-2 rounded-full bg-white/60 typing-dot" />
                <span className="w-2 h-2 rounded-full bg-white/60 typing-dot" />
                <span className="w-2 h-2 rounded-full bg-white/60 typing-dot" />
              </div>
            </div>
          </div>
        )}
        {messages.length === 1 && !typing && (
          <div className="space-y-1.5 pt-1">
            <p className="text-white/40 text-[10px] font-semibold uppercase tracking-wider">Try asking:</p>
            {suggestions.slice(0, 3).map(s => (
              <button key={s} onClick={() => send(s)}
                className="w-full text-left text-xs text-white/70 hover:text-white bg-white/5 hover:bg-white/12 border border-white/10 rounded-xl px-3 py-2 transition-all duration-150 truncate">
                {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Input — same look as before, but now functional */}
      <div className="flex items-center gap-2.5 bg-white/12 border border-white/15 rounded-xl px-3.5 py-2.5 shrink-0">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Type your question…"
          disabled={typing}
          className="flex-1 bg-transparent text-white text-sm outline-none placeholder-white/35 font-medium disabled:opacity-50"
        />
        <button
          onClick={() => send()}
          disabled={!input.trim() || typing}
          className="text-white/50 hover:text-white disabled:opacity-30 transition-colors shrink-0"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  )
}

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      {/* ── HERO ───────────────────────────────────────────────── */}
      <section className="relative bg-hero-gradient pt-24 pb-24 md:pt-36 md:pb-32 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden pointer-events-none select-none">
          <div className="absolute -top-32 -right-32 w-[500px] h-[500px] rounded-full bg-white/5 blur-3xl" />
          <div className="absolute bottom-0 -left-16 w-80 h-80 rounded-full bg-primary-light/10 blur-2xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[300px] rounded-full bg-primary-dark/20 blur-3xl" />
        </div>

        <div className="relative max-w-6xl mx-auto px-6 sm:px-8 lg:px-12">
          <div className="grid lg:grid-cols-2 gap-14 items-center">

            {/* Left — copy + search */}
            <div>
              <span className="hero-badge inline-flex items-center gap-2 px-4 py-2 bg-white/10 border border-white/15 text-white/90 text-xs font-semibold rounded-full tracking-wider uppercase mb-7" style={{ animationDelay: '0s' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                University of Rwanda · Student Support
              </span>

              <h1 className="hero-animate text-4xl md:text-5xl lg:text-[3.4rem] font-extrabold text-white leading-[1.1] mb-6 text-balance" style={{ animationDelay: '0.12s' }}>
                Your University of Rwanda,
                <br />
                <span className="text-primary-light">Answered Instantly</span>
              </h1>

              <p className="hero-animate text-white/70 text-lg leading-relaxed mb-9 max-w-[480px]" style={{ animationDelay: '0.26s' }}>
                UniConnect is your intelligent campus guide. Ask about admissions,
                registration, academic programs, scholarships, or campus life —
                and get accurate answers in seconds.
              </p>

              <div className="hero-animate flex flex-wrap gap-4" style={{ animationDelay: '0.4s' }}>
                <Link to="/chat" className="btn-primary text-base px-8 py-3.5 shadow-lg hover:shadow-xl">
                  Start Chatting
                  <ArrowRight size={18} />
                </Link>
                <a href="#how-it-works" className="inline-flex items-center gap-2 px-8 py-3.5 rounded-lg border-2 border-white/30 text-white font-semibold text-base hover:bg-white/10 hover:border-white/50 transition-all duration-200 active:scale-95">
                  How It Works
                </a>
              </div>
            </div>

            {/* Right — real mini-chat */}
            <div className="hero-animate hidden lg:flex justify-center lg:justify-end" style={{ animationDelay: '0.2s' }}>
              <MiniChat suggestions={suggestions} />
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
              UniConnect combines modern AI with official UR data to give you reliable, instant support — wherever you are.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map(f => (
              <div key={f.title} className="card p-7 flex flex-col gap-4 hover:border-primary/30 transition-all duration-300 hover:-translate-y-0.5">
                <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary">{f.icon}</div>
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
            <p className="section-subtitle mx-auto text-center">Three simple steps from question to answer.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-10 relative">
            <div className="hidden md:block absolute top-10 left-[28%] right-[28%] h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent" />
            {steps.map((step, i) => (
              <div key={step.number} className="relative text-center flex flex-col items-center gap-4 group">
                <div className={`w-20 h-20 rounded-2xl flex flex-col items-center justify-center shadow-md z-10 transition-all duration-300 group-hover:scale-105 group-hover:shadow-lg ${i === 1 ? 'bg-primary text-white' : 'bg-white border-2 border-primary text-primary'}`}>
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
                Whether it's about your first year or a postgraduate application — we have you covered.
              </p>
              <button onClick={() => goToChat('What can UniConnect help me with?')} className="btn-primary">
                Ask a Question Now
                <ChevronRight size={18} />
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              {topics.map(t => (
                <button
                  key={t.label}
                  onClick={() => goToChat(t.q)}
                  className="card p-5 flex flex-col items-start gap-3 hover:border-primary/40 hover:-translate-y-0.5 transition-all duration-200 group text-left"
                >
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors duration-200">
                    {t.icon}
                  </div>
                  <span className="text-sm font-semibold text-slate-ur leading-snug">{t.label}</span>
                </button>
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
            UniConnect only answers from verified sources. If it doesn't know, it tells you so —
            and flags the question for staff review. No hallucinations, no guessing.
          </p>
          <div className="flex flex-wrap justify-center gap-6 md:gap-10 text-sm text-white/70">
            {['Sourced from official UR documents', 'Flags unanswered questions for review', 'Continuously improved by administrators'].map(pt => (
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
          <button onClick={() => navigate('/chat')} className="btn-primary text-base px-10 py-4 shadow-lg hover:shadow-xl">
            Open UniConnect
            <ArrowRight size={18} />
          </button>
        </div>
      </section>

      <Footer />
    </div>
  )
}
