import { useState, useRef, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Send, Mic, MicOff, Square, Volume2, RotateCcw, ChevronDown, ArrowLeft, Sparkles, X, RefreshCw } from 'lucide-react'
import { askQuestion, getToken, clearAuth } from '../services/api'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const GREETING = {
  id: 0,
  role: 'assistant',
  text: "Hello! I'm UniConnect, your University of Rwanda assistant. Ask me anything about admissions, academic programs, registration, campus facilities, scholarships, or student services — in English or Kinyarwanda.",
  time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
}

const SUGGESTIONS = [
  'What are the admission requirements for Computer Engineering?',
  'When does semester registration open?',
  'How do I apply for a scholarship at UR?',
  'Where is the UR library located?',
  'What documents do I need for registration?',
  'Does UR offer part-time programs?',
]

/* ── Typing indicator ── */
function TypingIndicator() {
  return (
    <div className="flex items-end gap-2.5 mb-5">
      <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-[10px] font-bold shrink-0 shadow-sm">
        UC
      </div>
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-5 py-3.5 shadow-sm">
        <div className="flex items-center gap-1.5 h-4">
          <span className="w-2.5 h-2.5 rounded-full bg-primary/50 typing-dot" />
          <span className="w-2.5 h-2.5 rounded-full bg-primary/50 typing-dot" />
          <span className="w-2.5 h-2.5 rounded-full bg-primary/50 typing-dot" />
        </div>
      </div>
    </div>
  )
}

/* ── Markdown components for bot messages ── */
const mdComponents = {
  p: ({ children }) => (
    <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
  ),
  strong: ({ children }) => (
    <strong className="font-semibold text-slate-800">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-slate-700">{children}</em>
  ),
  ul: ({ children }) => (
    <ul className="mt-1.5 mb-2 space-y-1 pl-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mt-1.5 mb-2 space-y-1 pl-1 list-none counter-reset-item">{children}</ol>
  ),
  li: ({ children, node, ...props }) => {
    const isOrdered = node?.parent?.tagName === 'ol'
    return (
      <li className="flex items-start gap-2 text-sm leading-relaxed">
        {!isOrdered && (
          <span className="mt-[7px] w-1.5 h-1.5 rounded-full bg-primary/70 shrink-0" />
        )}
        <span className="flex-1">{children}</span>
      </li>
    )
  },
  h1: ({ children }) => (
    <h1 className="text-base font-bold text-slate-800 mt-3 mb-1.5 first:mt-0">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-sm font-bold text-slate-800 mt-3 mb-1.5 first:mt-0">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-slate-700 mt-2 mb-1 first:mt-0">{children}</h3>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-2 border-primary/30 pl-3 my-2 text-slate-600 italic text-sm">
      {children}
    </blockquote>
  ),
  code: ({ inline, children }) =>
    inline ? (
      <code className="bg-primary/8 text-primary px-1.5 py-0.5 rounded text-xs font-mono">
        {children}
      </code>
    ) : (
      <pre className="bg-gray-50 border border-gray-200 rounded-lg p-3 my-2 overflow-x-auto text-xs font-mono text-slate-700">
        <code>{children}</code>
      </pre>
    ),
  hr: () => <hr className="my-3 border-gray-200" />,
}

/* ── Message bubble ── */
function MessageBubble({ msg }) {
  const isUser = msg.role === 'user'
  const [speaking, setSpeaking] = useState(false)

  const speak = () => {
    if (!('speechSynthesis' in window)) return
    if (speaking) { window.speechSynthesis.cancel(); setSpeaking(false); return }
    const utterance = new SpeechSynthesisUtterance(msg.text)
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  return (
    <div className={`flex items-end gap-2.5 mb-5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0 mb-0.5 shadow-sm ${
        isUser ? 'bg-slate-ur' : 'bg-primary'
      }`}>
        {isUser ? 'You' : 'UC'}
      </div>

      {/* Bubble + meta */}
      <div className={`max-w-[75%] md:max-w-[65%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-5 py-3.5 rounded-2xl text-sm ${
          isUser
            ? 'bg-primary text-white rounded-tr-sm shadow-md'
            : 'bg-white text-slate-dark border border-gray-200 rounded-tl-sm shadow-sm'
        }`}>
          {isUser ? (
            /* User messages: plain text */
            <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
          ) : (
            /* Bot messages: full markdown rendering */
            <div className="prose-chat">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={mdComponents}
              >
                {msg.text}
              </ReactMarkdown>
            </div>
          )}

          {/* Source badge — bot only */}
          {msg.source && !isUser && (
            <div className="mt-2.5 pt-2.5 border-t border-gray-100 flex items-center gap-1.5">
              <Sparkles size={10} className="text-primary-light shrink-0" />
              <span className="text-[11px] text-gray-400 font-medium">{msg.source}</span>
            </div>
          )}
        </div>

        {/* Timestamp + TTS */}
        <div className={`flex items-center gap-2 mt-1.5 px-1 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
          <span className="text-[11px] text-gray-400">{msg.time}</span>
          {!isUser && (
            <button
              onClick={speak}
              title={speaking ? 'Stop listening' : 'Listen to this answer'}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[11px] font-medium transition-all duration-150 ${
                speaking
                  ? 'text-primary bg-primary/8'
                  : 'text-gray-400 hover:text-primary hover:bg-primary/5'
              }`}
            >
              <Volume2 size={12} />
              {speaking ? 'Playing…' : 'Listen'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Animated mic icon ── */
function MicIcon({ active }) {
  return (
    <span className="relative flex items-center justify-center w-full h-full">
      {active && (
        <>
          <span className="absolute inset-0 rounded-full bg-teal-400/30 animate-ping" />
          <span className="absolute inset-1 rounded-full bg-teal-400/20 animate-ping" style={{ animationDelay: '150ms' }} />
        </>
      )}
      <Mic size={20} />
    </span>
  )
}

/* ── Waveform bars ── */
function Waveform() {
  return (
    <div className="flex items-end gap-0.5 h-5">
      {[3, 6, 4, 7, 3, 5, 4].map((h, i) => (
        <span
          key={i}
          className="wave-bar w-1 bg-teal-500 rounded-full"
          style={{ height: `${h * 3}px`, animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  )
}

/* ── Recording timer ── */
function useTimer(active) {
  const [seconds, setSeconds] = useState(0)
  const ref = useRef(null)
  useEffect(() => {
    if (active) {
      setSeconds(0)
      ref.current = setInterval(() => setSeconds(s => s + 1), 1000)
    } else {
      clearInterval(ref.current)
    }
    return () => clearInterval(ref.current)
  }, [active])
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

/* ── Main Chat page ── */
export default function Chat() {
  const [messages, setMessages]         = useState([GREETING])
  const [input, setInput]               = useState('')
  const [isTyping, setIsTyping]         = useState(false)
  const [recordState, setRecordState]   = useState('idle') // idle | recording | done
  const [showSuggestions, setShowSuggestions] = useState(true)
  const navigate = useNavigate()

  const isRecordingRef  = useRef(false)
  const recognitionRef  = useRef(null)
  const accumulatedRef  = useRef('')
  const savedInputRef   = useRef('')       // text before recording started
  const bottomRef       = useRef(null)
  const textareaRef     = useRef(null)

  const timer = useTimer(recordState === 'recording')

  useEffect(() => { if (!getToken()) navigate('/login', { replace: true }) }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isTyping])
  useEffect(() => {
    const el = textareaRef.current; if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [input])

  const sendMessage = async (text) => {
    const trimmed = text.trim(); if (!trimmed) return
    if (isRecordingRef.current) stopRecording(false)

    const userMsg = { id: Date.now(), role: 'user', text: trimmed, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }
    setMessages(prev => [...prev, userMsg])
    setInput(''); setShowSuggestions(false); setIsTyping(true)
    try {
      const data = await askQuestion(trimmed)
      setIsTyping(false)
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant',
        text: data.answer || "I couldn't find an answer in the knowledge base.",
        source: data.sources?.length ? 'Knowledge Base' : null,
        confidence: data.confidence,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }])
    } catch (err) {
      setIsTyping(false)
      if (err.status === 401) { clearAuth(); navigate('/login', { replace: true }); return }
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: 'assistant',
        text: `Sorry, something went wrong: ${err.message}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }])
    }
  }

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input) } }

  const stopRecording = (keepText = true) => {
    isRecordingRef.current = false
    try { recognitionRef.current?.stop() } catch (_) {}
    recognitionRef.current = null
    if (!keepText) {
      setInput(savedInputRef.current)
      accumulatedRef.current = ''
      setRecordState('idle')
    } else {
      setRecordState('done')
    }
  }

  const cancelRecording = () => stopRecording(false)

  const retryRecording = () => {
    setInput(savedInputRef.current)
    accumulatedRef.current = ''
    setRecordState('idle')
    setTimeout(() => startRecording(), 50)
  }

  const startRecording = () => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRec) {
      alert('Voice input requires Chrome or Edge browser.')
      return
    }
    savedInputRef.current = input.trim()
    accumulatedRef.current = input.trim() ? input.trim() + ' ' : ''

    const recognition = new SpeechRec()
    recognition.lang = 'en-US'; recognition.continuous = true; recognition.interimResults = true; recognition.maxAlternatives = 1

    recognition.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) accumulatedRef.current += e.results[i][0].transcript + ' '
        else interim += e.results[i][0].transcript
      }
      setInput(accumulatedRef.current + interim)
    }
    recognition.onerror = (e) => {
      if (e.error === 'aborted') return
      isRecordingRef.current = false
      setRecordState('idle')
      recognitionRef.current = null
    }
    recognition.onend = () => {
      if (isRecordingRef.current) {
        try { recognition.start() } catch (_) {}
      }
    }

    recognitionRef.current = recognition
    isRecordingRef.current = true
    setRecordState('recording')
    recognition.start()
  }

  const clearChat = () => {
    if (isRecordingRef.current) stopRecording(false)
    setMessages([GREETING]); setShowSuggestions(true); setInput(''); setRecordState('idle')
  }

  const isRecording = recordState === 'recording'
  const isDone      = recordState === 'done'

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* ── Header ── */}
      <header className="bg-primary text-white px-4 sm:px-6 py-3.5 flex items-center gap-4 shadow-lg shrink-0 z-10">
        <Link to="/" className="p-1.5 rounded-lg hover:bg-white/10 transition-colors text-white/80 hover:text-white" title="Back to home"><ArrowLeft size={20} /></Link>
        <div className="w-10 h-10 rounded-full bg-white/15 border border-white/20 flex items-center justify-center font-bold text-sm shrink-0">UC</div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold">UniConnect</div>
          <div className="text-primary-100 text-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block animate-pulse" />
            Online · University of Rwanda Assistant
          </div>
        </div>
        <button onClick={clearChat} title="New conversation" className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"><RotateCcw size={17} /></button>
      </header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto chat-bg">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
          {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
          {isTyping && <TypingIndicator />}

          {showSuggestions && messages.length === 1 && (
            <div className="mt-4 mb-2">
              <p className="text-xs text-gray-500 font-semibold mb-3 flex items-center gap-1.5 uppercase tracking-wide">
                <ChevronDown size={13} /> Suggested questions
              </p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map(q => (
                  <button key={q} onClick={() => sendMessage(q)}
                    className="text-xs px-4 py-2 bg-white border-2 border-primary/20 text-primary rounded-full hover:bg-primary hover:text-white hover:border-primary transition-all duration-150 font-medium shadow-sm hover:shadow-md text-left">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} className="h-2" />
        </div>
      </div>

      {/* ── Input bar ── */}
      <div className="bg-white border-t-2 border-gray-100 shrink-0 z-10">
        {/* Recording indicator strip */}
        {isRecording && (
          <div className="bg-teal-50 border-b border-teal-100 px-4 py-2 flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse shrink-0" />
            <span className="text-xs font-semibold text-teal-700">Listening…</span>
            <span className="text-xs font-mono text-teal-600 tabular-nums">{timer}</span>
            <Waveform />
            <div className="ml-auto flex items-center gap-2">
              <button onClick={cancelRecording}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-gray-200 text-gray-500 text-xs hover:bg-gray-50 hover:text-gray-700 transition-colors">
                <X size={12} /> Cancel
              </button>
              <button onClick={() => stopRecording(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-teal-500 text-white text-xs hover:bg-teal-600 transition-colors">
                <Square size={11} /> Stop
              </button>
            </div>
          </div>
        )}

        {/* Post-recording action strip */}
        {isDone && input.trim() && (
          <div className="bg-slate-50 border-b border-slate-100 px-4 py-2 flex items-center gap-3">
            <CheckIcon />
            <span className="text-xs font-medium text-slate-600">Voice captured. Ready to send.</span>
            <div className="ml-auto flex items-center gap-2">
              <button onClick={retryRecording}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-gray-200 text-gray-500 text-xs hover:bg-gray-50 transition-colors">
                <RefreshCw size={11} /> Retry
              </button>
              <button onClick={() => { setInput(''); setRecordState('idle') }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-gray-200 text-gray-500 text-xs hover:bg-gray-50 transition-colors">
                <X size={11} /> Clear
              </button>
            </div>
          </div>
        )}

        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-end gap-3">
          {/* Voice button */}
          <div className="flex flex-col items-center gap-1 shrink-0">
            <button
              onClick={isRecording ? () => stopRecording(true) : startRecording}
              title={isRecording ? 'Stop recording' : 'Record voice input'}
              className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 ${
                isRecording
                  ? 'bg-teal-500 text-white border-2 border-teal-600 shadow-teal-200 shadow-lg'
                  : isDone
                  ? 'bg-teal-100 text-teal-600 border-2 border-teal-200'
                  : 'bg-primary/10 text-primary border-2 border-primary/30 hover:bg-primary hover:text-white hover:border-primary'
              }`}
            >
              {isRecording ? <MicIcon active={true} /> : <Mic size={20} />}
            </button>
            <span className={`text-[10px] font-bold uppercase tracking-wide ${isRecording ? 'text-teal-600' : 'text-gray-400'}`}>
              {isRecording ? timer : 'Voice'}
            </span>
          </div>

          {/* Textarea */}
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => { setInput(e.target.value); if (isDone) setRecordState('idle') }}
              onKeyDown={handleKeyDown}
              placeholder={isRecording ? 'Listening — your words will appear here…' : 'Type your question… (Enter to send)'}
              rows={1}
              className={`chat-input max-h-32 ${isRecording ? 'is-recording' : ''}`}
            />
          </div>

          {/* Send button */}
          <div className="flex flex-col items-center gap-1 shrink-0">
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isRecording}
              title="Send message"
              className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 ${
                input.trim() && !isRecording
                  ? 'bg-primary text-white border-2 border-primary-dark hover:bg-primary-dark shadow-md hover:shadow-lg active:scale-95'
                  : 'bg-gray-100 text-gray-300 border-2 border-gray-200 cursor-not-allowed'
              }`}
            >
              <Send size={18} />
            </button>
            <span className="text-[10px] font-bold uppercase tracking-wide text-gray-400">Send</span>
          </div>
        </div>

        <p className="text-center text-[11px] text-gray-400 pb-3 px-4">
          UniConnect may make mistakes. Verify important information with UR administrative offices.
        </p>
      </div>
    </div>
  )
}

function CheckIcon() {
  return <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-teal-500 shrink-0"><circle cx="7" cy="7" r="7" fill="currentColor" opacity="0.15"/><path d="M4 7l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
}
