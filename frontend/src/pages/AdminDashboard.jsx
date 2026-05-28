import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  listDocuments, uploadDocument, deleteDocument,
  listUnresolved, answerQuestion, ignoreQuestion,
  getAllChatHistory, clearAuth,
} from '../services/api'
import {
  LayoutDashboard, MessageSquare, HelpCircle, BarChart2, Download,
  Database, Settings, LogOut, Menu, X, Plus, Edit2, Trash2,
  CheckCircle, AlertCircle, Search, Filter, ChevronDown,
  TrendingUp, Users, Clock, ThumbsUp, FileText, Eye, Save,
  RefreshCw, Upload
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'

/* ── Mock data ─────────────────────────────────────────────── */
const queryTrend = [
  { day: 'Mon', queries: 42 }, { day: 'Tue', queries: 68 }, { day: 'Wed', queries: 55 },
  { day: 'Thu', queries: 91 }, { day: 'Fri', queries: 76 }, { day: 'Sat', queries: 34 },
  { day: 'Sun', queries: 28 },
]
const topTopics = [
  { topic: 'Admissions',    count: 120 },
  { topic: 'Registration',  count: 98 },
  { topic: 'Scholarships',  count: 74 },
  { topic: 'Programs',      count: 65 },
  { topic: 'Fees',          count: 53 },
  { topic: 'Campus',        count: 41 },
]
const categoryPie = [
  { name: 'Admissions',   value: 32, color: '#00628b' },
  { name: 'Academic',     value: 25, color: '#30a1c6' },
  { name: 'Admin',        value: 20, color: '#364f68' },
  { name: 'Campus Life',  value: 13, color: '#e8a800' },
  { name: 'Other',        value: 10, color: '#94a3b8' },
]

const INITIAL_FAQS = [
  { id: 1, category: 'Admissions', question: 'What are the requirements to apply for undergraduate programs?', answer: 'Applicants must have A-level certificates with required subject combinations. Applications are done through the national selection portal.', status: 'active' },
  { id: 2, category: 'Registration', question: 'When does semester registration open?', answer: 'Semester registration typically opens two weeks before the start of each semester. Check the academic calendar for exact dates.', status: 'active' },
  { id: 3, category: 'Scholarships', question: 'How can I apply for a government scholarship?', answer: 'Government scholarships are processed through the Rwanda Education Board (REB). Visit the REB portal to check eligibility and apply.', status: 'active' },
  { id: 4, category: 'Campus', question: 'Where is the main campus library?', answer: 'The main library is located at UR-CST campus in Kigali. Opening hours are Monday–Friday 8 AM – 8 PM and Saturday 9 AM – 5 PM.', status: 'active' },
  { id: 5, category: 'Programs', question: 'Does UR offer evening or part-time programs?', answer: 'Yes, UR offers some evening and part-time programs particularly at postgraduate level. Contact the academic registrar for the current list.', status: 'draft' },
]

const UNANSWERED = [
  { id: 1, question: 'What is the process to transfer from another university to UR?', asked: '2025-01-14 10:22', count: 8 },
  { id: 2, question: 'Are there sports facilities available for students?', asked: '2025-01-13 16:05', count: 5 },
  { id: 3, question: 'How do I request a transcript?', asked: '2025-01-13 09:14', count: 12 },
  { id: 4, question: 'What student clubs are available on campus?', asked: '2025-01-12 14:30', count: 3 },
  { id: 5, question: 'Is there accommodation available for international students?', asked: '2025-01-12 11:55', count: 7 },
]

const LOGS = [
  { id: 1, time: '2025-01-14 10:45', question: 'Admission requirements for Computer Engineering', answered: true, confidence: 0.92 },
  { id: 2, time: '2025-01-14 10:22', question: 'Transfer process from another university', answered: false, confidence: 0.14 },
  { id: 3, time: '2025-01-14 09:58', question: 'Semester registration deadline', answered: true, confidence: 0.88 },
  { id: 4, time: '2025-01-14 09:30', question: 'How to apply for scholarship', answered: true, confidence: 0.95 },
  { id: 5, time: '2025-01-14 08:55', question: 'Sports facilities on campus', answered: false, confidence: 0.22 },
]

/* ── Nav items ────────────────────────────────────────────── */
const NAV = [
  { key: 'overview',    label: 'Overview',           icon: <LayoutDashboard size={18} /> },
  { key: 'analytics',   label: 'Analytics',          icon: <BarChart2 size={18} /> },
  { key: 'faqs',        label: 'FAQs Manager',        icon: <HelpCircle size={18} /> },
  { key: 'unanswered',  label: 'Unanswered Queries',  icon: <MessageSquare size={18} /> },
  { key: 'knowledge',   label: 'Knowledge Base',      icon: <Database size={18} /> },
  { key: 'logs',        label: 'Export Logs',         icon: <Download size={18} /> },
  { key: 'settings',    label: 'Settings',            icon: <Settings size={18} /> },
]

/* ─────────────────────────────────────────────────────────── */
/*  Section components                                         */
/* ─────────────────────────────────────────────────────────── */

function Overview() {
  const cards = [
    { label: 'Queries Today',      value: '94',   sub: '+12% vs yesterday',  color: 'text-primary',       icon: <MessageSquare size={20} /> },
    { label: 'Answered',           value: '81',   sub: '86% answer rate',    color: 'text-green-600',     icon: <CheckCircle size={20} /> },
    { label: 'Unanswered',         value: '13',   sub: 'Needs review',       color: 'text-amber-500',     icon: <AlertCircle size={20} /> },
    { label: 'Unique Users',       value: '62',   sub: 'Today',              color: 'text-slate-ur',      icon: <Users size={20} /> },
  ]
  const recent = [
    { q: 'What is the deadline for semester registration?', time: '2 min ago',  ok: true },
    { q: 'Transfer process from another university',         time: '18 min ago', ok: false },
    { q: 'How to pay tuition fees online?',                  time: '32 min ago', ok: true },
    { q: 'Is there a health center on campus?',              time: '1 hr ago',   ok: false },
    { q: 'Requirements for Masters in Data Science',         time: '1 hr ago',   ok: true },
  ]

  return (
    <div className="space-y-7">
      <div>
        <h2 className="text-xl font-bold text-slate-ur mb-1">Dashboard Overview</h2>
        <p className="text-gray-400 text-sm">Monday, 14 January 2025</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(c => (
          <div key={c.label} className="card p-5 border border-gray-100">
            <div className={`${c.color} mb-3`}>{c.icon}</div>
            <div className="text-2xl font-extrabold text-slate-dark mb-0.5">{c.value}</div>
            <div className="text-xs font-semibold text-slate-ur">{c.label}</div>
            <div className="text-xs text-gray-400 mt-0.5">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* Mini chart + recent */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Queries This Week</h3>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={queryTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
              <Line type="monotone" dataKey="queries" stroke="#00628b" strokeWidth={2.5} dot={{ r: 3, fill: '#00628b' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {recent.map((r, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className={`mt-0.5 shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${r.ok ? 'bg-green-50' : 'bg-amber-50'}`}>
                  {r.ok
                    ? <CheckCircle size={10} className="text-green-500" />
                    : <AlertCircle size={10} className="text-amber-500" />
                  }
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-dark truncate">{r.q}</p>
                  <p className="text-[10px] text-gray-400">{r.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function Analytics() {
  return (
    <div className="space-y-7">
      <h2 className="text-xl font-bold text-slate-ur">Analytics</h2>

      {/* KPI row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Queries (30d)', value: '1,847', icon: <TrendingUp size={16} className="text-primary" /> },
          { label: 'Avg. Response Time', value: '1.3s',   icon: <Clock size={16} className="text-primary-light" /> },
          { label: 'Satisfaction Rate',  value: '91%',    icon: <ThumbsUp size={16} className="text-green-500" /> },
        ].map(k => (
          <div key={k.label} className="card p-4 border border-gray-100 flex items-center gap-3">
            {k.icon}
            <div>
              <div className="text-xl font-extrabold text-slate-dark">{k.value}</div>
              <div className="text-xs text-gray-400">{k.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Query Volume — Last 7 Days</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={queryTrend} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
              <Bar dataKey="queries" fill="#00628b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Query Category Breakdown</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={categoryPie} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
                dataKey="value" paddingAngle={3}>
                {categoryPie.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
              <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card p-5 border border-gray-100">
        <h3 className="font-semibold text-slate-ur text-sm mb-4">Top 6 Topics Asked</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={topTopics} layout="vertical" barSize={16}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} />
            <YAxis dataKey="topic" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} width={85} />
            <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
            <Bar dataKey="count" fill="#30a1c6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function FAQManager() {
  const [faqs, setFaqs]         = useState(INITIAL_FAQS)
  const [search, setSearch]     = useState('')
  const [editing, setEditing]   = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm]         = useState({ category: '', question: '', answer: '', status: 'active' })

  const filtered = faqs.filter(f =>
    f.question.toLowerCase().includes(search.toLowerCase()) ||
    f.category.toLowerCase().includes(search.toLowerCase())
  )

  const openNew = () => {
    setForm({ category: '', question: '', answer: '', status: 'active' })
    setEditing(null)
    setShowForm(true)
  }

  const openEdit = (faq) => {
    setForm({ ...faq })
    setEditing(faq.id)
    setShowForm(true)
  }

  const saveForm = () => {
    if (!form.question || !form.answer) return
    if (editing) {
      setFaqs(prev => prev.map(f => f.id === editing ? { ...form, id: editing } : f))
    } else {
      setFaqs(prev => [...prev, { ...form, id: Date.now() }])
    }
    setShowForm(false)
  }

  const deleteFaq = (id) => setFaqs(prev => prev.filter(f => f.id !== id))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-xl font-bold text-slate-ur">FAQs Manager</h2>
        <button onClick={openNew} className="btn-primary py-2 px-4 text-sm">
          <Plus size={15} /> Add FAQ
        </button>
      </div>

      {/* Search */}
      <div className="relative max-w-xs">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search FAQs…"
          className="input-field pl-9 py-2 text-sm"
        />
      </div>

      {/* Table */}
      <div className="card border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left">
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider">Category</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider">Question</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider hidden lg:table-cell">Status</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(faq => (
              <tr key={faq.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                <td className="px-5 py-3.5">
                  <span className="px-2.5 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full">
                    {faq.category}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-slate-dark max-w-xs truncate">{faq.question}</td>
                <td className="px-5 py-3.5 hidden lg:table-cell">
                  <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                    faq.status === 'active'
                      ? 'bg-green-50 text-green-600'
                      : 'bg-amber-50 text-amber-600'
                  }`}>
                    {faq.status}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => openEdit(faq)} className="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors">
                      <Edit2 size={15} />
                    </button>
                    <button onClick={() => deleteFaq(faq.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                      <Trash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-10 text-gray-400 text-sm">No FAQs found.</div>
        )}
      </div>

      {/* Modal / Form */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-7">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-bold text-slate-ur">{editing ? 'Edit FAQ' : 'New FAQ'}</h3>
              <button onClick={() => setShowForm(false)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400">
                <X size={18} />
              </button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-ur mb-1">Category</label>
                  <input value={form.category} onChange={e => setForm(f => ({...f, category: e.target.value}))}
                    className="input-field py-2 text-sm" placeholder="e.g. Admissions" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-ur mb-1">Status</label>
                  <select value={form.status} onChange={e => setForm(f => ({...f, status: e.target.value}))}
                    className="input-field py-2 text-sm">
                    <option value="active">Active</option>
                    <option value="draft">Draft</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Question</label>
                <input value={form.question} onChange={e => setForm(f => ({...f, question: e.target.value}))}
                  className="input-field py-2 text-sm" placeholder="Enter the question" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Answer</label>
                <textarea value={form.answer} onChange={e => setForm(f => ({...f, answer: e.target.value}))}
                  className="input-field py-2 text-sm resize-none" rows={4} placeholder="Enter the answer" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
              <button onClick={saveForm} className="btn-primary py-2 px-5 text-sm">
                <Save size={14} /> Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function UnansweredQueries() {
  const [queries, setQueries]     = useState([])
  const [loading, setLoading]     = useState(true)
  const [active, setActive]       = useState(null)
  const [answer, setAnswer]       = useState('')
  const [search, setSearch]       = useState('')
  const [saving, setSaving]       = useState(false)
  const [error, setError]         = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const data = await listUnresolved('pending')
      setQueries(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = queries.filter(q =>
    q.question.toLowerCase().includes(search.toLowerCase())
  )

  const resolveQuery = async (id) => {
    if (!answer.trim()) return
    setSaving(true)
    try {
      await answerQuestion(id, answer)
      setQueries(prev => prev.filter(q => q.id !== id))
      setActive(null)
      setAnswer('')
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const dismissQuery = async (id) => {
    try {
      await ignoreQuestion(id)
      setQueries(prev => prev.filter(q => q.id !== id))
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-ur">Unanswered Queries</h2>
          <p className="text-gray-400 text-sm mt-0.5">
            {loading ? 'Loading…' : `${queries.length} question${queries.length !== 1 ? 's' : ''} awaiting review`}
          </p>
        </div>
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search…" className="input-field pl-9 py-2 text-sm w-52" />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      <div className="space-y-3">
        {loading ? (
          <div className="card border border-gray-100 p-10 text-center text-gray-400 text-sm">Loading…</div>
        ) : filtered.map(q => (
          <div key={q.id} className="card border border-gray-100 overflow-hidden">
            <div className="p-5 flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-5 h-5 bg-amber-50 rounded-full flex items-center justify-center shrink-0">
                    <AlertCircle size={11} className="text-amber-500" />
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(q.created_at).toLocaleString()}
                    {q.confidence_score != null && ` · Confidence: ${(q.confidence_score * 100).toFixed(0)}%`}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-dark">{q.question}</p>
                {q.ai_attempt && (
                  <p className="text-xs text-gray-400 mt-1 italic">AI attempt: {q.ai_attempt}</p>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={() => { setActive(active === q.id ? null : q.id); setAnswer('') }}
                  className="btn-primary py-1.5 px-3 text-xs">
                  {active === q.id ? 'Cancel' : 'Add Answer'}
                </button>
                <button onClick={() => dismissQuery(q.id)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                  <Trash2 size={14} />
                </button>
              </div>
            </div>

            {active === q.id && (
              <div className="px-5 pb-5 border-t border-gray-50 pt-4 bg-gray-50/50">
                <label className="block text-xs font-medium text-slate-ur mb-2">Your Answer</label>
                <textarea value={answer} onChange={e => setAnswer(e.target.value)}
                  className="input-field resize-none text-sm" rows={3}
                  placeholder="Type the correct answer…" />
                <div className="flex justify-end gap-2 mt-3">
                  <button onClick={() => resolveQuery(q.id)} disabled={!answer.trim() || saving}
                    className="btn-primary py-2 px-4 text-xs disabled:opacity-50">
                    {saving ? <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <CheckCircle size={13} />}
                    Save & Mark Resolved
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}

        {!loading && filtered.length === 0 && (
          <div className="card border border-gray-100 p-14 text-center text-gray-400 text-sm">
            <CheckCircle size={32} className="mx-auto mb-3 text-green-300" />
            No unanswered queries. All caught up!
          </div>
        )}
      </div>
    </div>
  )
}

function KnowledgeBase() {
  const [docs, setDocs]         = useState([])
  const [loading, setLoading]   = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadPct, setUploadPct] = useState(0)
  const [error, setError]       = useState('')
  const fileRef = useRef()

  const load = async () => {
    setLoading(true)
    try {
      const data = await listDocuments()
      setDocs(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadPct(0)
    setError('')
    try {
      await uploadDocument(file, setUploadPct)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
      setUploadPct(0)
      e.target.value = ''
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this document? This cannot be undone.')) return
    try {
      await deleteDocument(id)
      setDocs(prev => prev.filter(d => d.id !== id))
    } catch (e) {
      setError(e.message)
    }
  }

  const fmt = (bytes) => {
    if (!bytes) return '—'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const statusColor = (s) => {
    if (s === 'completed') return 'bg-green-50 text-green-600'
    if (s === 'failed')    return 'bg-red-50 text-red-600'
    if (s === 'processing') return 'bg-blue-50 text-primary'
    return 'bg-gray-50 text-gray-500'
  }
  const statusLabel = (s) => {
    if (s === 'completed')  return 'Indexed'
    if (s === 'failed')     return 'Failed'
    if (s === 'processing') return 'Processing…'
    return s
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-ur">Knowledge Base</h2>
          <p className="text-gray-400 text-sm mt-0.5">Documents used to answer student queries</p>
        </div>
        <div className="flex items-center gap-2">
          {uploading && (
            <span className="text-xs text-primary font-medium">{uploadPct}%</span>
          )}
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="btn-primary py-2 px-4 text-sm disabled:opacity-60"
          >
            {uploading ? (
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Upload size={14} />
            )}
            {uploading ? 'Uploading…' : 'Upload Document'}
          </button>
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleUpload} />
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      <div className="card border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left">
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider">Document</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider">Size</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider">Uploaded</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider">Status</th>
              <th className="px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-10 text-gray-400 text-sm">Loading…</td></tr>
            ) : docs.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-10 text-gray-400 text-sm">No documents uploaded yet.</td></tr>
            ) : docs.map((doc) => (
              <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <FileText size={15} className="text-primary shrink-0" />
                    <span className="text-slate-dark font-medium truncate max-w-[200px]">{doc.filename}</span>
                  </div>
                </td>
                <td className="px-5 py-3.5 text-gray-500">{fmt(doc.file_size)}</td>
                <td className="px-5 py-3.5 text-gray-500">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td>
                <td className="px-5 py-3.5">
                  <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${statusColor(doc.is_processed)}`}>
                    {statusLabel(doc.is_processed)}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => load()} className="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors" title="Refresh">
                      <RefreshCw size={14} />
                    </button>
                    <button onClick={() => handleDelete(doc.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors" title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function ExportLogs() {
  const [allLogs, setAllLogs]   = useState([])
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')
  const [filter, setFilter]     = useState('all')

  useEffect(() => {
    getAllChatHistory()
      .then(data => setAllLogs(data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = allLogs.filter(l => {
    if (filter === 'answered')   return l.is_resolved === 'resolved'
    if (filter === 'unanswered') return l.is_resolved !== 'resolved'
    return true
  })

  const downloadCSV = () => {
    const header = 'Timestamp,Question,Status,Confidence\n'
    const rows = filtered.map(l =>
      `"${l.created_at}","${l.question.replace(/"/g, '""')}","${l.is_resolved}",${l.confidence_score ?? ''}`
    ).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url  = URL.createObjectURL(blob)
    const a    = document.createElement('a')
    a.href = url; a.download = `uniconnect_logs.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-slate-ur">Export Logs</h2>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {/* Filter bar */}
      <div className="card p-5 border border-gray-100 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-ur mb-1">Filter</label>
          <select value={filter} onChange={e => setFilter(e.target.value)} className="input-field py-2 text-sm">
            <option value="all">All queries</option>
            <option value="answered">Answered only</option>
            <option value="unanswered">Unanswered only</option>
          </select>
        </div>
        <button onClick={downloadCSV} disabled={loading || filtered.length === 0} className="btn-primary py-2 px-5 text-sm disabled:opacity-60">
          <Download size={14} /> Download CSV
        </button>
      </div>

      {/* Preview table */}
      <div className="card border border-gray-100 overflow-x-auto">
        <div className="px-5 py-3.5 border-b border-gray-100 flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-ur">
            {loading ? 'Loading…' : `Preview (${filtered.length} entries)`}
          </span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left">
              <th className="px-5 py-3 font-semibold text-slate-ur text-xs uppercase tracking-wider">Timestamp</th>
              <th className="px-5 py-3 font-semibold text-slate-ur text-xs uppercase tracking-wider">Question</th>
              <th className="px-5 py-3 font-semibold text-slate-ur text-xs uppercase tracking-wider">Status</th>
              <th className="px-5 py-3 font-semibold text-slate-ur text-xs uppercase tracking-wider">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="text-center py-8 text-gray-400 text-sm">Loading…</td></tr>
            ) : filtered.map(l => {
              const resolved   = l.is_resolved === 'resolved'
              const confidence = l.confidence_score ?? 0
              return (
                <tr key={l.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                  <td className="px-5 py-3 text-gray-500 whitespace-nowrap text-xs">
                    {new Date(l.created_at).toLocaleString()}
                  </td>
                  <td className="px-5 py-3 text-slate-dark max-w-xs truncate">{l.question}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${
                      resolved ? 'bg-green-50 text-green-600' : 'bg-amber-50 text-amber-600'
                    }`}>
                      {resolved ? 'Answered' : 'Unanswered'}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{
                          width: `${confidence * 100}%`,
                          backgroundColor: confidence > 0.7 ? '#22c55e' : confidence > 0.4 ? '#e8a800' : '#ef4444',
                        }} />
                      </div>
                      <span className="text-xs text-gray-500">{(confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function SettingsSection() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-xl font-bold text-slate-ur">Settings</h2>

      <div className="card border border-gray-100 divide-y divide-gray-100">
        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">General</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">System Name</label>
              <input defaultValue="UniConnect" className="input-field py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">Default Language</label>
              <select className="input-field py-2 text-sm">
                <option>English</option>
                <option>Kinyarwanda</option>
              </select>
            </div>
          </div>
        </div>

        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">AI Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">LLM Provider</label>
              <select className="input-field py-2 text-sm">
                <option>Google Gemini</option>
                <option>OpenAI GPT</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">API Key</label>
              <input type="password" defaultValue="••••••••••••••••" className="input-field py-2 text-sm" />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs font-medium text-slate-ur">Confidence Threshold</div>
                <div className="text-[11px] text-gray-400 mt-0.5">Below this, the system says it doesn't know</div>
              </div>
              <span className="font-semibold text-primary text-sm">60%</span>
            </div>
          </div>
        </div>

        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Notifications</h3>
          <div className="space-y-3">
            {[
              'Email alert when unanswered queries exceed 10',
              'Weekly analytics summary email',
            ].map(label => (
              <label key={label} className="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" defaultChecked className="w-4 h-4 accent-primary" />
                <span className="text-sm text-slate-dark">{label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button className="btn-primary py-2.5 px-6 text-sm">
          <Save size={14} /> Save Settings
        </button>
      </div>
    </div>
  )
}

/* ─── Main AdminDashboard ──────────────────────────────────── */
export default function AdminDashboard() {
  const [active, setActive]       = useState('overview')
  const [sideOpen, setSideOpen]   = useState(false)
  const [unresolvedCount, setUnresolvedCount] = useState(null)
  const navigate                  = useNavigate()

  useEffect(() => {
    listUnresolved('pending')
      .then(data => setUnresolvedCount(data.length))
      .catch(() => {})
  }, [])

  const sections = {
    overview:   <Overview />,
    analytics:  <Analytics />,
    faqs:       <FAQManager />,
    unanswered: <UnansweredQueries />,
    knowledge:  <KnowledgeBase />,
    logs:       <ExportLogs />,
    settings:   <SettingsSection />,
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-60 bg-slate-dark text-white flex flex-col
        transition-transform duration-300
        ${sideOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:static lg:translate-x-0
      `}>
        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/10 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-bold text-white text-xs shrink-0">
            UC
          </div>
          <div>
            <div className="text-white font-bold text-sm">UniConnect</div>
            <div className="text-white/40 text-[10px]">Admin Portal</div>
          </div>
          <button className="lg:hidden ml-auto text-white/50 hover:text-white" onClick={() => setSideOpen(false)}>
            <X size={18} />
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(item => (
            <button
              key={item.key}
              onClick={() => { setActive(item.key); setSideOpen(false) }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                active === item.key
                  ? 'bg-primary text-white'
                  : 'text-white/60 hover:text-white hover:bg-white/5'
              }`}
            >
              {item.icon}
              {item.label}
              {item.key === 'unanswered' && unresolvedCount > 0 && (
                <span className="ml-auto text-[10px] bg-amber-400 text-white font-bold px-1.5 py-0.5 rounded-full">{unresolvedCount}</span>
              )}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-3 py-4 border-t border-white/10">
          <button
            onClick={() => { clearAuth(); navigate('/admin/login') }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors"
          >
            <LogOut size={17} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sideOpen && (
        <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setSideOpen(false)} />
      )}

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="bg-white border-b border-gray-100 px-5 py-4 flex items-center gap-4 shrink-0">
          <button className="lg:hidden p-1.5 rounded-lg text-gray-500 hover:bg-gray-100 transition-colors"
            onClick={() => setSideOpen(true)}>
            <Menu size={20} />
          </button>
          <div className="flex-1">
            <h1 className="font-bold text-slate-ur text-sm">{NAV.find(n => n.key === active)?.label}</h1>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-ur">Admin User</div>
              <div className="text-[10px] text-gray-400">University of Rwanda</div>
            </div>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">
              A
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          {sections[active]}
        </main>
      </div>
    </div>
  )
}
