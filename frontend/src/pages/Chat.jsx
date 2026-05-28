import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Send, Mic, MicOff, Volume2, RotateCcw, ChevronDown, ArrowLeft, Sparkles } from 'lucide-react'
import { askQuestion, getToken, clearAuth } from '../services/api'

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
      <div className={`max-w-[75%] md:max-w-[62%] flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-5 py-3.5 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-primary text-white rounded-tr-sm shadow-md'
            : 'bg-white text-slate-dark border border-gray-200 rounded-tl-sm shadow-sm'
        }`}>
          <p className="whitespace-pre-wrap">{msg.text}</p>

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

/* ── Main Chat page ── */
export default function Chat() {
  const [messages, setMessages]       = useState([GREETING])
  const [input, setInput]             = useState('')
  const [isTyping, setIsTyping]       = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [lang, setLang]               = useState('EN')
  const [showSuggestions, setShowSuggestions] = useState(true)
  const navigate = useNavigate()

  /* Redirect to login if not authenticated */
  useEffect(() => {
    if (!getToken()) navigate('/login', { replace: true })
  }, [])

  /* Refs for voice — state in closures won't update, refs do */
  const isRecordingRef  = useRef(false)
  const recognitionRef  = useRef(null)
  const accumulatedRef  = useRef('')
  const bottomRef       = useRef(null)
  const textareaRef     = useRef(null)

  /* Keep ref in sync with state */
  const setRecording = (val) => {
    isRecordingRef.current = val
    setIsRecording(val)
  }

  /* Auto-scroll on new messages */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  /* Auto-resize textarea */
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [input])

  /* ── Send message ── */
  const sendMessage = async (text) => {
    const trimmed = text.trim()
    if (!trimmed) return

    /* Stop recording if active */
    if (isRecordingRef.current) stopRecording()

    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: trimmed,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setShowSuggestions(false)
    setIsTyping(true)

    try {
      const data = await askQuestion(trimmed)
      const botText = data.answer || "I couldn't find an answer in the knowledge base."
      const source  = data.sources?.length ? 'Knowledge Base' : null
      setIsTyping(false)
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: botText,
        source,
        confidence: data.confidence,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }])
    } catch (err) {
      setIsTyping(false)
      if (err.status === 401) {
        clearAuth()
        navigate('/login', { replace: true })
        return
      }
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        text: `Sorry, something went wrong: ${err.message}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }])
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  /* ── Voice: stop ── */
  const stopRecording = () => {
    /* Set ref BEFORE calling stop() so the onend handler doesn't restart */
    isRecordingRef.current = false
    setIsRecording(false)
    try { recognitionRef.current?.stop() } catch (_) {}
    recognitionRef.current = null
  }

  /* ── Voice: start ── */
  const startRecording = () => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRec) {
      alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.')
      return
    }

    const recognition = new SpeechRec()
    recognition.lang            = lang === 'RW' ? 'rw-RW' : 'en-US'
    recognition.continuous      = true   /* keep listening until explicitly stopped */
    recognition.interimResults  = true   /* show partial results in real time */
    recognition.maxAlternatives = 1

    /* Start fresh, but keep any text already typed */
    accumulatedRef.current = input.trim() ? input.trim() + ' ' : ''

    recognition.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) {
          accumulatedRef.current += e.results[i][0].transcript + ' '
        } else {
          interim += e.results[i][0].transcript
        }
      }
      /* Show accumulated + live interim text in the input */
      setInput(accumulatedRef.current + interim)
    }

    recognition.onerror = (e) => {
      /* 'aborted' means we called stop() — ignore it */
      if (e.error === 'aborted') return
      /* Any other error: stop cleanly */
      isRecordingRef.current = false
      setIsRecording(false)
      recognitionRef.current = null
    }

    recognition.onend = () => {
      /* If the browser stopped due to silence but user hasn't pressed Stop — restart */
      if (isRecordingRef.current) {
        try { recognition.start() } catch (_) { /* ignore race-condition errors */ }
      }
    }

    recognitionRef.current = recognition
    setRecording(true)
    recognition.start()
  }

  const toggleRecording = () => {
    if (isRecordingRef.current) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const clearChat = () => {
    if (isRecordingRef.current) stopRecording()
    setMessages([GREETING])
    setShowSuggestions(true)
    setInput('')
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* ── Header ── */}
      <header className="bg-primary text-white px-4 sm:px-6 py-3.5 flex items-center gap-4 shadow-lg shrink-0 z-10">
        <Link
          to="/"
          className="p-1.5 rounded-lg hover:bg-white/10 transition-colors text-white/80 hover:text-white"
          title="Back to home"
        >
          <ArrowLeft size={20} />
        </Link>

        <div className="w-10 h-10 rounded-full bg-white/15 border border-white/20 flex items-center justify-center font-bold text-sm shrink-0">
          UC
        </div>

        <div className="flex-1 min-w-0">
          <div className="font-semibold">UniConnect</div>
          <div className="text-primary-100 text-xs flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block animate-pulse" />
            Online · University of Rwanda Assistant
          </div>
        </div>

        {/* Language toggle */}
        <div className="flex items-center bg-white/10 rounded-xl p-1 gap-0.5">
          {['EN', 'RW'].map(l => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-150 ${
                lang === l ? 'bg-white text-primary shadow-sm' : 'text-white/70 hover:text-white'
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        <button
          onClick={clearChat}
          title="New conversation"
          className="p-1.5 rounded-lg text-white/60 hover:text-white hover:bg-white/10 transition-colors"
        >
          <RotateCcw size={17} />
        </button>
      </header>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto chat-bg">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
          {messages.map(msg => (
            <MessageBubble key={msg.id} msg={msg} />
          ))}

          {isTyping && <TypingIndicator />}

          {/* Suggested questions */}
          {showSuggestions && messages.length === 1 && (
            <div className="mt-4 mb-2">
              <p className="text-xs text-gray-500 font-semibold mb-3 flex items-center gap-1.5 uppercase tracking-wide">
                <ChevronDown size={13} />
                Suggested questions
              </p>
              <div className="flex flex-wrap gap-2">
                {SUGGESTIONS.map(q => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="text-xs px-4 py-2 bg-white border-2 border-primary/20 text-primary rounded-full
                               hover:bg-primary hover:text-white hover:border-primary transition-all duration-150
                               font-medium shadow-sm hover:shadow-md text-left"
                  >
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
      <div className="bg-white border-t-2 border-gray-200 shrink-0 z-10">
        {/* Recording indicator strip */}
        {isRecording && (
          <div className="bg-red-50 border-b border-red-100 px-4 py-2 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0" />
            <span className="text-xs font-semibold text-red-600">Recording…  Speak now, tap Stop when done</span>
            {/* Live waveform bars */}
            <div className="flex items-end gap-0.5 h-4 ml-auto">
              {[3, 5, 4, 6, 3].map((h, i) => (
                <span
                  key={i}
                  className="wave-bar w-1 bg-red-400 rounded-full"
                  style={{ height: `${h * 3}px` }}
                />
              ))}
            </div>
          </div>
        )}

        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-end gap-3">
          {/* Voice button */}
          <div className="flex flex-col items-center gap-1 shrink-0">
            <button
              onClick={toggleRecording}
              title={isRecording ? 'Tap to stop recording' : 'Tap to record voice'}
              className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 ${
                isRecording
                  ? 'bg-red-500 text-white border-2 border-red-600 recording-pulse'
                  : 'bg-primary/10 text-primary border-2 border-primary/30 hover:bg-primary hover:text-white hover:border-primary'
              }`}
            >
              {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
            <span className={`text-[10px] font-bold uppercase tracking-wide ${
              isRecording ? 'text-red-500' : 'text-gray-400'
            }`}>
              {isRecording ? 'Stop' : 'Voice'}
            </span>
          </div>

          {/* Textarea */}
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
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
              disabled={!input.trim()}
              title="Send message"
              className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-200 ${
                input.trim()
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
