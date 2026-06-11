import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, HelpCircle, BarChart2, Download,
  Database, Settings, LogOut, Menu, X, Plus, Edit2, Trash2,
  CheckCircle, AlertCircle, Search, TrendingUp, Users, Clock,
  ThumbsUp, FileText, Save, RefreshCw, Upload, Globe, UserPlus,
  ShieldCheck, ShieldOff, Eye, Key, History, ArrowUpRight,
  BookOpen, Filter, Calendar, ChevronDown, ChevronUp, Zap,
} from 'lucide-react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import {
  getStats, getQueryTrend, getCategoryBreakdown, getTopTopics, getRecentActivity,
  listDocuments, uploadDocument, deleteDocument, ingestUrl,
  listUnresolved, answerQuestion, ignoreQuestion, setQuestionStatus, pushToFaq,
  getAllChatHistory,
  listUsers, createUser, updateUser, deleteUser, suspendUser, activateUser,
  resetUserPassword, getUserQueryHistory, getUserStats,
  listFaqs, createFaq, updateFaq, deleteFaq,
  getSettings, saveSettings,
  downloadExport,
  clearAuth,
} from '../services/api'

/* ─── Nav ──────────────────────────────────────────────────────────────────── */
const NAV = [
  { key: 'overview',    label: 'Overview',           icon: <LayoutDashboard size={18} /> },
  { key: 'analytics',   label: 'Analytics',          icon: <BarChart2 size={18} /> },
  { key: 'faqs',        label: 'FAQs Manager',        icon: <HelpCircle size={18} /> },
  { key: 'unanswered',  label: 'Unanswered Queries',  icon: <MessageSquare size={18} /> },
  { key: 'users',       label: 'User Management',     icon: <Users size={18} /> },
  { key: 'knowledge',   label: 'Knowledge Base',      icon: <Database size={18} /> },
  { key: 'logs',        label: 'Export Logs',         icon: <Download size={18} /> },
  { key: 'settings',    label: 'Settings',            icon: <Settings size={18} /> },
]

/* ─── Toast system ─────────────────────────────────────────────────────────── */
function useToast() {
  const [toasts, setToasts] = useState([])
  const toast = useCallback((msg, type = 'success') => {
    const id = Date.now()
    setToasts(t => [...t, { id, msg, type }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 3500)
  }, [])
  return { toasts, toast }
}

function ToastContainer({ toasts }) {
  if (!toasts.length) return null
  return (
    <div className="fixed top-4 right-4 z-[9999] space-y-2 pointer-events-none">
      {toasts.map(t => (
        <div key={t.id} className={`flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-lg text-sm font-medium pointer-events-auto animate-fade-in
          ${t.type === 'error' ? 'bg-red-600 text-white' : t.type === 'warning' ? 'bg-amber-500 text-white' : 'bg-green-600 text-white'}`}>
          {t.type === 'error' ? <AlertCircle size={15} /> : <CheckCircle size={15} />}
          {t.msg}
        </div>
      ))}
    </div>
  )
}

/* ─── Confirm Modal ────────────────────────────────────────────────────────── */
function ConfirmModal({ open, title, message, onConfirm, onCancel, danger = true }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[9990] flex items-center justify-center bg-black/40 backdrop-blur-sm px-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
        <h3 className="font-bold text-slate-ur mb-2">{title}</h3>
        <p className="text-sm text-gray-500 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="btn-outline py-2 px-5 text-sm">Cancel</button>
          <button onClick={onConfirm} className={`py-2 px-5 text-sm rounded-xl font-semibold transition-colors ${danger ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-primary text-white hover:bg-primary-dark'}`}>
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

/* ─── Shared hooks ─────────────────────────────────────────────────────────── */
function useAsync(fn, deps = []) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const reload = useCallback(async () => {
    setLoading(true); setError('')
    try { setData(await fn()) } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { reload() }, [reload])
  return { data, loading, error, reload }
}

/* ─── Shared UI ────────────────────────────────────────────────────────────── */
function StatCard({ label, value, sub, color, icon, loading }) {
  return (
    <div className="card p-5 border border-gray-100">
      <div className={`${color} mb-3`}>{icon}</div>
      <div className="text-2xl font-extrabold text-slate-dark mb-0.5">
        {loading ? <span className="block w-12 h-7 bg-gray-100 rounded animate-pulse" /> : (value ?? '—')}
      </div>
      <div className="text-xs font-semibold text-slate-ur">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function ErrorBanner({ msg }) {
  if (!msg) return null
  return <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm flex items-center gap-2"><AlertCircle size={15} />{msg}</div>
}

function Badge({ status }) {
  const map = {
    active:       'bg-green-50 text-green-700',
    resolved:     'bg-green-50 text-green-700',
    answered:     'bg-green-50 text-green-700',
    pending:      'bg-amber-50 text-amber-700',
    under_review: 'bg-blue-50 text-blue-700',
    added_to_kb:  'bg-purple-50 text-purple-700',
    ignored:      'bg-gray-50 text-gray-500',
    draft:        'bg-amber-50 text-amber-700',
    archived:     'bg-gray-50 text-gray-500',
    unresolved:   'bg-red-50 text-red-600',
    suspended:    'bg-red-50 text-red-500',
    inactive:     'bg-red-50 text-red-500',
  }
  const label = {
    under_review: 'Under Review',
    added_to_kb:  'Added to KB',
  }[status] || status
  return (
    <span className={`px-2.5 py-1 text-xs font-medium rounded-full capitalize ${map[status] || 'bg-gray-50 text-gray-500'}`}>
      {label}
    </span>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   OVERVIEW
═══════════════════════════════════════════════════════════════════════════ */
function Overview({ toast }) {
  const { data: stats, loading: sl, reload: reloadStats } = useAsync(getStats)
  const { data: trend, loading: tl }                      = useAsync(() => getQueryTrend(7))
  const { data: activity, loading: al }                   = useAsync(() => getRecentActivity(8))

  const fmtMs = (ms) => ms == null ? '—' : ms < 1000 ? `${ms}ms` : `${(ms/1000).toFixed(1)}s`

  const cards = [
    { label: 'Total Queries',    value: stats?.total_queries,    sub: `${stats?.queries_today ?? '—'} today`,              color: 'text-primary',   icon: <MessageSquare size={20} /> },
    { label: 'Answered',         value: stats?.answered_queries, sub: `${stats ? Math.round(stats.answer_rate * 100) : '—'}% answer rate`, color: 'text-green-600', icon: <CheckCircle size={20} /> },
    { label: 'Unanswered',       value: stats?.unanswered_queries, sub: `${stats?.pending_reviews ?? '—'} need review`,    color: 'text-amber-500', icon: <AlertCircle size={20} /> },
    { label: 'Registered Users', value: stats?.total_users,     sub: `${stats?.active_users ?? '—'} active (30d)`,         color: 'text-slate-ur',  icon: <Users size={20} /> },
    { label: 'This Week',        value: stats?.queries_this_week, sub: 'queries in last 7 days',                            color: 'text-blue-500',  icon: <TrendingUp size={20} /> },
    { label: 'Knowledge Docs',   value: stats?.total_documents,  sub: `${stats?.processed_documents ?? '—'} indexed`,      color: 'text-purple-500',icon: <Database size={20} /> },
    { label: 'Active FAQs',      value: stats?.faq_count,        sub: 'published entries',                                  color: 'text-pink-500',  icon: <BookOpen size={20} /> },
    { label: 'Avg Response',     value: fmtMs(stats?.avg_response_time_ms), sub: 'per AI query',                           color: 'text-teal-500',  icon: <Zap size={20} /> },
  ]

  return (
    <div className="space-y-7">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-ur mb-1">Dashboard Overview</h2>
          <p className="text-gray-400 text-sm">{new Date().toLocaleDateString('en-US', { weekday:'long', year:'numeric', month:'long', day:'numeric' })}</p>
        </div>
        <button onClick={reloadStats} className="p-2 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors" title="Refresh">
          <RefreshCw size={16} />
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map(c => <StatCard key={c.label} {...c} loading={sl} />)}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Query Volume — Last 7 Days</h3>
          {tl ? (
            <div className="h-44 flex items-center justify-center">
              <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} allowDecimals={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
                <Line type="monotone" dataKey="queries" stroke="#00628b" strokeWidth={2.5} dot={{ r: 3, fill: '#00628b' }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Recent Activity</h3>
          {al ? (
            <div className="space-y-3">{[...Array(5)].map((_, i) => <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />)}</div>
          ) : (
            <div className="space-y-3">
              {(activity || []).slice(0, 6).map((r, i) => (
                <div key={i} className="flex items-start gap-3">
                  <span className={`mt-0.5 shrink-0 w-4 h-4 rounded-full flex items-center justify-center ${r.ok ? 'bg-green-50' : 'bg-amber-50'}`}>
                    {r.ok ? <CheckCircle size={10} className="text-green-500" /> : <AlertCircle size={10} className="text-amber-500" />}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-dark truncate">{r.text}</p>
                    <p className="text-[10px] text-gray-400">{new Date(r.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              ))}
              {!activity?.length && <p className="text-sm text-gray-400 text-center py-4">No activity yet.</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   ANALYTICS
═══════════════════════════════════════════════════════════════════════════ */
function Analytics() {
  const [days, setDays]      = useState(7)
  const { data: stats }      = useAsync(getStats)
  const { data: trend }      = useAsync(() => getQueryTrend(days), [days])
  const { data: cats }       = useAsync(getCategoryBreakdown)
  const { data: topics }     = useAsync(() => getTopTopics(8))

  return (
    <div className="space-y-7">
      <h2 className="text-xl font-bold text-slate-ur">Analytics</h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Queries',   value: stats?.total_queries,  icon: <TrendingUp size={16} className="text-primary" /> },
          { label: 'Answer Rate',     value: stats ? `${Math.round(stats.answer_rate * 100)}%` : '—', icon: <ThumbsUp size={16} className="text-green-500" /> },
          { label: 'Pending Reviews', value: stats?.pending_reviews, icon: <Clock size={16} className="text-amber-500" /> },
          { label: 'Active Users (30d)', value: stats?.active_users, icon: <Users size={16} className="text-blue-500" /> },
        ].map(k => (
          <div key={k.label} className="card p-4 border border-gray-100 flex items-center gap-3">
            {k.icon}
            <div>
              <div className="text-xl font-extrabold text-slate-dark">{k.value ?? '—'}</div>
              <div className="text-xs text-gray-400">{k.label}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card p-5 border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-ur text-sm">Query Volume</h3>
            <select value={days} onChange={e => setDays(Number(e.target.value))} className="text-xs border border-gray-200 rounded-lg px-2 py-1 text-slate-ur">
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={trend || []} barSize={28}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94a3b8' }} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0' }} />
              <Bar dataKey="queries" fill="#00628b" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5 border border-gray-100">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Query Category Breakdown</h3>
          {cats?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={cats} cx="50%" cy="50%" innerRadius={55} outerRadius={85} dataKey="value" paddingAngle={3}>
                  {cats.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                <Legend iconType="circle" iconSize={10} wrapperStyle={{ fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="h-44 flex items-center justify-center text-gray-400 text-sm">No data yet — ask some questions first.</div>}
        </div>
      </div>

      <div className="card p-5 border border-gray-100">
        <h3 className="font-semibold text-slate-ur text-sm mb-4">Top Topics Asked</h3>
        {topics?.length ? (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={topics} layout="vertical" barSize={18}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} allowDecimals={false} />
              <YAxis dataKey="topic" type="category" tick={{ fontSize: 11, fill: '#94a3b8' }} width={100} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Bar dataKey="count" fill="#30a1c6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : <div className="h-32 flex items-center justify-center text-gray-400 text-sm">No data yet</div>}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   FAQ MANAGER
═══════════════════════════════════════════════════════════════════════════ */
function FAQManager({ toast }) {
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch]   = useState('')
  const { data: faqs, loading, error, reload } = useAsync(() => listFaqs(statusFilter || null, search || null), [statusFilter, search])
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [saving, setSaving]   = useState(false)
  const [saveErr, setSaveErr] = useState('')
  const [form, setForm] = useState({ question: '', answer: '', category: 'General', status: 'active' })
  const [confirmDel, setConfirmDel] = useState(null)

  const CATEGORIES = ['General', 'Admissions', 'Registration', 'Scholarships', 'Fees', 'Programs', 'Exams', 'Campus Life', 'Accommodation', 'Administration']

  const openNew  = () => { setForm({ question: '', answer: '', category: 'General', status: 'active' }); setEditing(null); setShowForm(true); setSaveErr('') }
  const openEdit = (f) => { setForm({ question: f.question, answer: f.answer, category: f.category || 'General', status: f.status }); setEditing(f.id); setShowForm(true); setSaveErr('') }

  const saveForm = async () => {
    if (!form.question.trim() || !form.answer.trim()) return
    setSaving(true); setSaveErr('')
    try {
      if (editing) await updateFaq(editing, form)
      else await createFaq(form.question, form.answer, form.category, form.status)
      setShowForm(false); reload()
      toast(editing ? 'FAQ updated' : 'FAQ created')
    } catch (e) { setSaveErr(e.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    try { await deleteFaq(id); reload(); toast('FAQ deleted'); setConfirmDel(null) }
    catch (e) { toast(e.message, 'error') }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-xl font-bold text-slate-ur">FAQs Manager</h2>
        <button onClick={openNew} className="btn-primary py-2 px-4 text-sm flex items-center gap-1.5"><Plus size={15} /> Add FAQ</button>
      </div>

      <ErrorBanner msg={error} />

      <div className="flex gap-3 flex-wrap">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search FAQs…" className="input-field pl-9 py-2 text-sm w-56" />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input-field py-2 text-sm">
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="draft">Draft</option>
          <option value="archived">Archived</option>
        </select>
      </div>

      <div className="card border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left">
              {['Category', 'Question', 'Views', 'Status', 'Updated', 'Actions'].map(h => (
                <th key={h} className={`px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider ${h === 'Actions' ? 'text-right' : ''} ${['Views','Updated'].includes(h) ? 'hidden lg:table-cell' : ''}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-10"><div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" /></td></tr>
            ) : (faqs || []).length === 0 ? (
              <tr><td colSpan={6} className="text-center py-14 text-gray-400 text-sm">
                <BookOpen size={32} className="mx-auto mb-2 text-gray-200" />No FAQs found.</td></tr>
            ) : (faqs || []).map(faq => (
              <tr key={faq.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                <td className="px-5 py-3.5">
                  <span className="px-2.5 py-1 bg-primary/10 text-primary text-xs font-medium rounded-full">{faq.category}</span>
                </td>
                <td className="px-5 py-3.5 text-slate-dark max-w-xs truncate" title={faq.question}>{faq.question}</td>
                <td className="px-5 py-3.5 text-gray-400 text-xs hidden lg:table-cell">{faq.view_count ?? 0}</td>
                <td className="px-5 py-3.5 hidden lg:table-cell"><Badge status={faq.status} /></td>
                <td className="px-5 py-3.5 text-gray-400 text-xs hidden lg:table-cell">{new Date(faq.updated_at).toLocaleDateString()}</td>
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => openEdit(faq)} className="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors" title="Edit"><Edit2 size={15} /></button>
                    <button onClick={() => setConfirmDel(faq.id)} className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors" title="Delete"><Trash2 size={15} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-5 py-3 border-t border-gray-50 text-xs text-gray-400">{(faqs || []).length} FAQs shown</div>
      </div>

      <ConfirmModal
        open={!!confirmDel}
        title="Delete FAQ"
        message="This FAQ will be permanently removed."
        onConfirm={() => handleDelete(confirmDel)}
        onCancel={() => setConfirmDel(null)}
      />

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-7 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-bold text-slate-ur">{editing ? 'Edit FAQ' : 'New FAQ'}</h3>
              <button onClick={() => setShowForm(false)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <ErrorBanner msg={saveErr} />
            <div className="space-y-4 mt-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-ur mb-1">Category</label>
                  <select value={form.category} onChange={e => setForm(f => ({...f, category: e.target.value}))} className="input-field py-2 text-sm">
                    {CATEGORIES.map(c => <option key={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-ur mb-1">Status</label>
                  <select value={form.status} onChange={e => setForm(f => ({...f, status: e.target.value}))} className="input-field py-2 text-sm">
                    <option value="active">Active</option>
                    <option value="draft">Draft</option>
                    <option value="archived">Archived</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Question</label>
                <input value={form.question} onChange={e => setForm(f => ({...f, question: e.target.value}))} className="input-field py-2 text-sm" placeholder="Enter the question" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Answer</label>
                <textarea value={form.answer} onChange={e => setForm(f => ({...f, answer: e.target.value}))} className="input-field py-2 text-sm resize-none" rows={5} placeholder="Enter the answer" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowForm(false)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
              <button onClick={saveForm} disabled={saving} className="btn-primary py-2 px-5 text-sm disabled:opacity-60 flex items-center gap-2">
                {saving ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={14} />}
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   UNANSWERED QUERIES
═══════════════════════════════════════════════════════════════════════════ */
function UnansweredQueries({ toast }) {
  const [statusFilter, setStatusFilter] = useState('pending')
  const { data: queries, loading, error, reload } = useAsync(() => listUnresolved(statusFilter), [statusFilter])
  const [active, setActive]     = useState(null)
  const [answer, setAnswer]     = useState('')
  const [faqModal, setFaqModal] = useState(null)
  const [faqAnswer, setFaqAnswer] = useState('')
  const [faqCategory, setFaqCategory] = useState('General')
  const [saving, setSaving]     = useState(false)
  const [saveErr, setSaveErr]   = useState('')
  const [search, setSearch]     = useState('')

  const CATEGORIES = ['General', 'Admissions', 'Registration', 'Scholarships', 'Fees', 'Programs', 'Exams', 'Campus Life', 'Accommodation', 'Administration']
  const STATUS_OPTIONS = [
    { val: 'pending',      label: 'Pending' },
    { val: 'under_review', label: 'Under Review' },
    { val: 'answered',     label: 'Answered' },
    { val: 'added_to_kb',  label: 'Added to KB' },
    { val: 'ignored',      label: 'Ignored' },
    { val: 'all',          label: 'All' },
  ]

  const filtered = (queries || []).filter(q => q.question.toLowerCase().includes(search.toLowerCase()))

  const resolveQuery = async (id) => {
    if (!answer.trim()) return
    setSaving(true); setSaveErr('')
    try { await answerQuestion(id, answer); setActive(null); setAnswer(''); reload(); toast('Answer saved') }
    catch (e) { setSaveErr(e.message) }
    finally { setSaving(false) }
  }

  const changeStatus = async (id, status) => {
    try { await setQuestionStatus(id, status); reload(); toast(`Status updated to "${status}"`) }
    catch (e) { toast(e.message, 'error') }
  }

  const handlePushToFaq = async () => {
    if (!faqAnswer.trim()) return
    setSaving(true)
    try {
      await pushToFaq(faqModal, faqAnswer, faqCategory)
      setFaqModal(null); setFaqAnswer(''); reload()
      toast('Question added to FAQ')
    } catch (e) { toast(e.message, 'error') }
    finally { setSaving(false) }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-ur">Unanswered Queries</h2>
          <p className="text-gray-400 text-sm mt-0.5">
            {loading ? 'Loading…' : `${filtered.length} question${filtered.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search…" className="input-field pl-9 py-2 text-sm w-48" />
          </div>
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input-field py-2 text-sm">
            {STATUS_OPTIONS.map(o => <option key={o.val} value={o.val}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <ErrorBanner msg={error || saveErr} />

      <div className="space-y-3">
        {loading ? (
          <div className="card border border-gray-100 p-10 text-center"><div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" /></div>
        ) : filtered.length === 0 ? (
          <div className="card border border-gray-100 p-14 text-center text-gray-400 text-sm">
            <CheckCircle size={32} className="mx-auto mb-3 text-green-300" />
            No questions found for this filter.
          </div>
        ) : filtered.map(q => (
          <div key={q.id} className="card border border-gray-100 overflow-hidden">
            <div className="p-5 flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <Badge status={q.status} />
                  {q.category && <span className="px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full">{q.category}</span>}
                  <span className="text-xs text-gray-400">
                    {new Date(q.created_at).toLocaleString()}
                    {q.confidence_score != null && ` · ${(q.confidence_score * 100).toFixed(0)}% confidence`}
                  </span>
                </div>
                <p className="text-sm font-medium text-slate-dark">{q.question}</p>
                {q.ai_attempt && (
                  <p className="text-xs text-gray-400 mt-1.5 italic line-clamp-2">AI attempt: {q.ai_attempt}</p>
                )}
                {q.admin_answer && (
                  <div className="mt-2 p-2.5 bg-green-50 rounded-lg border border-green-100">
                    <p className="text-xs text-green-700 font-medium mb-0.5">Admin answer:</p>
                    <p className="text-xs text-green-600">{q.admin_answer}</p>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1 shrink-0 flex-wrap justify-end">
                {q.status === 'pending' && (
                  <>
                    <button onClick={() => { setActive(active === q.id ? null : q.id); setAnswer('') }}
                      className="btn-primary py-1.5 px-3 text-xs flex items-center gap-1">
                      <Edit2 size={12} /> {active === q.id ? 'Cancel' : 'Answer'}
                    </button>
                    <button onClick={() => { setFaqModal(q.id); setFaqAnswer(q.admin_answer || ''); setFaqCategory(q.category || 'General') }}
                      className="py-1.5 px-3 text-xs rounded-xl border border-primary/30 text-primary hover:bg-primary/5 transition-colors flex items-center gap-1">
                      <BookOpen size={12} /> Push to FAQ
                    </button>
                    <button onClick={() => changeStatus(q.id, 'under_review')}
                      className="py-1.5 px-3 text-xs rounded-xl border border-blue-200 text-blue-600 hover:bg-blue-50 transition-colors">
                      Review
                    </button>
                    <button onClick={() => changeStatus(q.id, 'ignored')}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors" title="Ignore">
                      <Trash2 size={14} />
                    </button>
                  </>
                )}
                {q.status !== 'pending' && q.status !== 'resolved' && (
                  <button onClick={() => changeStatus(q.id, 'resolved')}
                    className="py-1.5 px-3 text-xs rounded-xl border border-green-200 text-green-600 hover:bg-green-50 transition-colors flex items-center gap-1">
                    <CheckCircle size={12} /> Mark Resolved
                  </button>
                )}
              </div>
            </div>
            {active === q.id && (
              <div className="px-5 pb-5 border-t border-gray-50 pt-4 bg-gray-50/50">
                <label className="block text-xs font-medium text-slate-ur mb-2">Your Answer</label>
                <textarea value={answer} onChange={e => setAnswer(e.target.value)} className="input-field resize-none text-sm" rows={3} placeholder="Type the correct answer…" />
                <div className="flex justify-end gap-2 mt-3">
                  <button onClick={() => resolveQuery(q.id)} disabled={!answer.trim() || saving} className="btn-primary py-2 px-4 text-xs disabled:opacity-50 flex items-center gap-1.5">
                    {saving ? <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <CheckCircle size={13} />}
                    Save & Mark Resolved
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Push to FAQ modal */}
      {faqModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-7">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-bold text-slate-ur">Push to FAQ</h3>
              <button onClick={() => setFaqModal(null)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Category</label>
                <select value={faqCategory} onChange={e => setFaqCategory(e.target.value)} className="input-field py-2 text-sm">
                  {['General','Admissions','Registration','Scholarships','Fees','Programs','Exams','Campus Life','Accommodation','Administration'].map(c => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Answer <span className="text-red-400">*</span></label>
                <textarea value={faqAnswer} onChange={e => setFaqAnswer(e.target.value)} className="input-field resize-none text-sm" rows={4} placeholder="Write the FAQ answer…" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setFaqModal(null)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
              <button onClick={handlePushToFaq} disabled={!faqAnswer.trim() || saving} className="btn-primary py-2 px-5 text-sm disabled:opacity-60 flex items-center gap-2">
                {saving ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <BookOpen size={14} />}
                Add to FAQ
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   USER MANAGEMENT
═══════════════════════════════════════════════════════════════════════════ */
function UserManagement({ toast }) {
  const [search, setSearch]     = useState('')
  const [roleFilter, setRole]   = useState('all')
  const { data: users, loading, error, reload } = useAsync(() => listUsers({ search: search || undefined, role: roleFilter !== 'all' ? roleFilter : undefined }), [search, roleFilter])
  const [showCreate, setShowCreate] = useState(false)
  const [editModal, setEditModal]   = useState(null)
  const [historyModal, setHistoryModal] = useState(null)
  const [resetModal, setResetModal]     = useState(null)
  const [confirmDel, setConfirmDel]     = useState(null)
  const [saving, setSaving]   = useState(false)
  const [saveErr, setSaveErr] = useState('')
  const [createForm, setCreateForm] = useState({ email: '', full_name: '', password: '', role: 'student' })
  const [editForm, setEditForm]     = useState({ full_name: '', role: 'student' })
  const [newPassword, setNewPassword] = useState('')
  const [history, setHistory]   = useState(null)
  const [histLoading, setHistLoading] = useState(false)

  const openHistory = async (user) => {
    setHistoryModal(user)
    setHistLoading(true)
    try {
      const data = await getUserQueryHistory(user.id, 30)
      setHistory(data)
    } catch (e) { setHistory([]) }
    finally { setHistLoading(false) }
  }

  const handleCreate = async () => {
    if (!createForm.email || !createForm.password || !createForm.full_name) return
    setSaving(true); setSaveErr('')
    try {
      await createUser(createForm.email, createForm.password, createForm.full_name, createForm.role)
      setShowCreate(false)
      setCreateForm({ email: '', full_name: '', password: '', role: 'student' })
      reload(); toast('User created')
    } catch (e) { setSaveErr(e.message) }
    finally { setSaving(false) }
  }

  const handleEdit = async () => {
    if (!editModal) return
    setSaving(true); setSaveErr('')
    try {
      await updateUser(editModal.id, editForm)
      setEditModal(null); reload(); toast('User updated')
    } catch (e) { setSaveErr(e.message) }
    finally { setSaving(false) }
  }

  const handleResetPassword = async () => {
    if (!newPassword.trim() || newPassword.length < 8) return
    setSaving(true)
    try {
      await resetUserPassword(resetModal.id, newPassword)
      setResetModal(null); setNewPassword(''); toast('Password reset successfully')
    } catch (e) { toast(e.message, 'error') }
    finally { setSaving(false) }
  }

  const handleSuspend  = async (id) => { try { await suspendUser(id); reload(); toast('User suspended') } catch (e) { toast(e.message, 'error') } }
  const handleActivate = async (id) => { try { await activateUser(id); reload(); toast('User activated') } catch (e) { toast(e.message, 'error') } }
  const handleDelete   = async (id) => {
    try { await deleteUser(id); reload(); toast('User deleted'); setConfirmDel(null) }
    catch (e) { toast(e.message, 'error') }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h2 className="text-xl font-bold text-slate-ur">User Management</h2>
        <button onClick={() => { setShowCreate(true); setSaveErr('') }} className="btn-primary py-2 px-4 text-sm flex items-center gap-1.5"><UserPlus size={15} /> Add User</button>
      </div>

      <ErrorBanner msg={error} />

      <div className="flex gap-3 flex-wrap">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or email…" className="input-field pl-9 py-2 text-sm w-64" />
        </div>
        <select value={roleFilter} onChange={e => setRole(e.target.value)} className="input-field py-2 text-sm">
          <option value="all">All</option>
          <option value="student">Students</option>
          <option value="admin">Admins</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <div className="card border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left">
              {['User', 'Role', 'Status', 'Registered', 'Actions'].map(h => (
                <th key={h} className={`px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider ${h === 'Actions' ? 'text-right' : ''} ${['Status','Registered'].includes(h) ? 'hidden lg:table-cell' : ''}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-10"><div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" /></td></tr>
            ) : (users || []).length === 0 ? (
              <tr><td colSpan={5} className="text-center py-14 text-gray-400 text-sm">No users found.</td></tr>
            ) : (users || []).map(u => (
              <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold shrink-0">
                      {u.full_name?.charAt(0)?.toUpperCase() || '?'}
                    </div>
                    <div>
                      <p className="font-medium text-slate-dark">{u.full_name}</p>
                      <p className="text-xs text-gray-400">{u.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`px-2.5 py-1 text-xs font-semibold rounded-full ${u.role === 'admin' ? 'bg-purple-50 text-purple-600' : 'bg-primary/10 text-primary'}`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-5 py-3.5 hidden lg:table-cell">
                  <Badge status={u.is_active ? 'active' : 'suspended'} />
                </td>
                <td className="px-5 py-3.5 text-gray-400 text-xs hidden lg:table-cell">{new Date(u.created_at).toLocaleDateString()}</td>
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={() => openHistory(u)} title="View history" className="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors"><History size={14} /></button>
                    <button onClick={() => { setEditModal(u); setEditForm({ full_name: u.full_name, role: u.role }); setSaveErr('') }} title="Edit" className="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors"><Edit2 size={14} /></button>
                    <button onClick={() => { setResetModal(u); setNewPassword('') }} title="Reset password" className="p-1.5 rounded-lg text-gray-400 hover:text-amber-500 hover:bg-amber-50 transition-colors"><Key size={14} /></button>
                    {u.is_active
                      ? <button onClick={() => handleSuspend(u.id)} title="Suspend" className="p-1.5 rounded-lg text-gray-400 hover:text-amber-500 hover:bg-amber-50 transition-colors"><ShieldOff size={14} /></button>
                      : <button onClick={() => handleActivate(u.id)} title="Activate" className="p-1.5 rounded-lg text-gray-400 hover:text-green-500 hover:bg-green-50 transition-colors"><ShieldCheck size={14} /></button>
                    }
                    <button onClick={() => setConfirmDel(u.id)} title="Delete" className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="px-5 py-3 border-t border-gray-50 text-xs text-gray-400">{(users || []).length} user{(users || []).length !== 1 ? 's' : ''} shown</div>
      </div>

      <ConfirmModal open={!!confirmDel} title="Delete User" message="This user and all their data will be permanently removed." onConfirm={() => handleDelete(confirmDel)} onCancel={() => setConfirmDel(null)} />

      {/* Create user modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-7">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-bold text-slate-ur">Add New User</h3>
              <button onClick={() => setShowCreate(false)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <ErrorBanner msg={saveErr} />
            <div className="space-y-4 mt-3">
              {[['Full Name','text','full_name','Full name'],['Email','email','email','email@example.com'],['Password','password','password','Min 8 characters']].map(([label, type, key, placeholder]) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-slate-ur mb-1">{label}</label>
                  <input type={type} value={createForm[key]} onChange={e => setCreateForm(f => ({...f, [key]: e.target.value}))} className="input-field py-2 text-sm" placeholder={placeholder} />
                </div>
              ))}
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Role</label>
                <select value={createForm.role} onChange={e => setCreateForm(f => ({...f, role: e.target.value}))} className="input-field py-2 text-sm">
                  <option value="student">Student</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setShowCreate(false)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
              <button onClick={handleCreate} disabled={saving} className="btn-primary py-2 px-5 text-sm disabled:opacity-60 flex items-center gap-2">
                {saving ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <UserPlus size={14} />}
                Create User
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit user modal */}
      {editModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-7">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-bold text-slate-ur">Edit User</h3>
              <button onClick={() => setEditModal(null)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <ErrorBanner msg={saveErr} />
            <div className="space-y-4 mt-3">
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Full Name</label>
                <input value={editForm.full_name} onChange={e => setEditForm(f => ({...f, full_name: e.target.value}))} className="input-field py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1">Role</label>
                <select value={editForm.role} onChange={e => setEditForm(f => ({...f, role: e.target.value}))} className="input-field py-2 text-sm">
                  <option value="student">Student</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => setEditModal(null)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
              <button onClick={handleEdit} disabled={saving} className="btn-primary py-2 px-5 text-sm disabled:opacity-60 flex items-center gap-2">
                {saving ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={14} />}
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Reset password modal */}
      {resetModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-7">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-bold text-slate-ur">Reset Password</h3>
              <button onClick={() => setResetModal(null)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <p className="text-sm text-gray-500 mb-4">Set a new password for <strong>{resetModal.full_name}</strong>.</p>
            <input type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} className="input-field py-2 text-sm" placeholder="New password (min 8 chars)" />
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => setResetModal(null)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
              <button onClick={handleResetPassword} disabled={newPassword.length < 8 || saving} className="btn-primary py-2 px-5 text-sm disabled:opacity-60 flex items-center gap-2">
                {saving ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Key size={14} />}
                Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Query history modal */}
      {historyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-7 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between mb-5 shrink-0">
              <div>
                <h3 className="font-bold text-slate-ur">Query History</h3>
                <p className="text-xs text-gray-400 mt-0.5">{historyModal.full_name} · {historyModal.email}</p>
              </div>
              <button onClick={() => { setHistoryModal(null); setHistory(null) }} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-2.5">
              {histLoading ? (
                <div className="text-center py-8"><div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" /></div>
              ) : (history || []).length === 0 ? (
                <p className="text-center text-gray-400 text-sm py-8">No queries yet.</p>
              ) : (history || []).map(h => (
                <div key={h.id} className="p-3.5 border border-gray-100 rounded-xl">
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <p className="text-sm font-medium text-slate-dark">{h.question}</p>
                    <Badge status={h.is_resolved} />
                  </div>
                  {h.answer && <p className="text-xs text-gray-500 line-clamp-2">{h.answer}</p>}
                  <div className="flex items-center gap-3 mt-2 text-[11px] text-gray-400">
                    {h.category && <span className="px-2 py-0.5 bg-primary/10 text-primary rounded-full">{h.category}</span>}
                    {h.confidence_score != null && <span>{(h.confidence_score * 100).toFixed(0)}% confidence</span>}
                    {h.response_time_ms != null && <span>{h.response_time_ms}ms</span>}
                    <span className="ml-auto">{new Date(h.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   KNOWLEDGE BASE
═══════════════════════════════════════════════════════════════════════════ */
function KnowledgeBase({ toast }) {
  const { data: docs, loading, error, reload } = useAsync(listDocuments)
  const [showModal, setShowModal]   = useState(false)
  const [tab, setTab]               = useState('document')
  const [uploading, setUploading]   = useState(false)
  const [uploadPct, setUploadPct]   = useState(0)
  const [urlInput, setUrlInput]     = useState('')
  const [urlTitle, setUrlTitle]     = useState('')
  const [ingesting, setIngesting]   = useState(false)
  const [modalErr, setModalErr]     = useState('')
  const [confirmDel, setConfirmDel] = useState(null)
  const fileRef = useRef()

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return
    setUploading(true); setUploadPct(0); setModalErr('')
    try { await uploadDocument(file, setUploadPct); setShowModal(false); reload(); toast('Document uploaded — processing in background') }
    catch (e) { setModalErr(e.message) }
    finally { setUploading(false); setUploadPct(0); e.target.value = '' }
  }

  const handleIngestUrl = async () => {
    if (!urlInput.trim()) return
    setIngesting(true); setModalErr('')
    try { await ingestUrl(urlInput.trim(), urlTitle.trim()); setShowModal(false); setUrlInput(''); setUrlTitle(''); reload(); toast('Website added — scraping in background') }
    catch (e) { setModalErr(e.message) }
    finally { setIngesting(false) }
  }

  const handleDelete = async (id) => {
    try { await deleteDocument(id); reload(); toast('Source deleted'); setConfirmDel(null) }
    catch (e) { toast(e.message, 'error') }
  }

  const fmt  = (b) => !b ? '—' : b < 1024*1024 ? (b/1024).toFixed(0)+' KB' : (b/(1024*1024)).toFixed(1)+' MB'
  const sCol = (s) => ({completed:'bg-green-50 text-green-600',failed:'bg-red-50 text-red-600',processing:'bg-blue-50 text-primary'}[s]||'bg-gray-50 text-gray-500')
  const sLbl = (s) => ({completed:'Indexed',failed:'Failed',processing:'Processing…',pending:'Pending'}[s]||s)

  const total = (docs || []).length
  const indexed = (docs || []).filter(d => d.is_processed === 'completed').length
  const failed  = (docs || []).filter(d => d.is_processed === 'failed').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold text-slate-ur">Knowledge Base</h2>
          <p className="text-gray-400 text-sm mt-0.5">Documents and web sources powering the AI assistant</p>
        </div>
        <button onClick={() => { setShowModal(true); setTab('document'); setModalErr('') }} className="btn-primary py-2 px-4 text-sm flex items-center gap-1.5">
          <Plus size={14} /> Add Knowledge
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Sources', value: total, color: 'text-primary' },
          { label: 'Indexed',       value: indexed, color: 'text-green-600' },
          { label: 'Failed',        value: failed,  color: 'text-red-500' },
        ].map(c => (
          <div key={c.label} className="card p-4 border border-gray-100 text-center">
            <div className={`text-2xl font-extrabold ${c.color}`}>{c.value}</div>
            <div className="text-xs text-gray-500 mt-1">{c.label}</div>
          </div>
        ))}
      </div>

      <ErrorBanner msg={error} />

      <div className="card border border-gray-100 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-left">
              {['Source','Type','Size','Added','Status','Actions'].map(h => (
                <th key={h} className={`px-5 py-3.5 font-semibold text-slate-ur text-xs uppercase tracking-wider ${h==='Actions'?'text-right':''}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-10"><div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" /></td></tr>
            ) : !(docs || []).length ? (
              <tr><td colSpan={6} className="text-center py-14 text-gray-400 text-sm">
                <Database size={32} className="mx-auto mb-2 text-gray-200" />No knowledge sources yet.</td></tr>
            ) : (docs || []).map(doc => (
              <tr key={doc.id} className="border-b border-gray-50 hover:bg-gray-50/60 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2 max-w-[220px]">
                    {doc.document_type === 'url' ? <Globe size={15} className="text-primary shrink-0" /> : <FileText size={15} className="text-primary shrink-0" />}
                    <div className="min-w-0">
                      <p className="text-slate-dark font-medium truncate">{doc.filename.replace(/\.txt$/, '')}</p>
                      {doc.source_url && <a href={doc.source_url} target="_blank" rel="noreferrer" className="text-[11px] text-primary hover:underline truncate block max-w-[200px]">{doc.source_url}</a>}
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`px-2 py-0.5 text-[11px] font-semibold rounded uppercase ${doc.document_type === 'url' ? 'bg-indigo-50 text-indigo-600' : 'bg-primary/10 text-primary'}`}>
                    {doc.document_type === 'url' ? 'Web' : doc.document_type?.toUpperCase()}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-gray-500">{fmt(doc.file_size)}</td>
                <td className="px-5 py-3.5 text-gray-500 whitespace-nowrap">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td>
                <td className="px-5 py-3.5">
                  <span className={`px-2.5 py-1 text-xs font-medium rounded-full ${sCol(doc.is_processed)}`}>{sLbl(doc.is_processed)}</span>
                </td>
                <td className="px-5 py-3.5 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <button onClick={reload} title="Refresh status" className="p-1.5 rounded-lg text-gray-400 hover:text-primary hover:bg-primary/5 transition-colors"><RefreshCw size={14} /></button>
                    <button onClick={() => setConfirmDel(doc.id)} title="Delete" className="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ConfirmModal open={!!confirmDel} title="Delete Source" message="This document and its embeddings will be permanently removed." onConfirm={() => handleDelete(confirmDel)} onCancel={() => setConfirmDel(null)} />

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm px-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-7">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-bold text-slate-ur text-lg">Add Knowledge Source</h3>
              <button onClick={() => setShowModal(false)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"><X size={18} /></button>
            </div>
            <div className="flex bg-gray-100 rounded-xl p-1 gap-1 mb-6">
              {[{key:'document',icon:<FileText size={15}/>,label:'Document'},{key:'url',icon:<Globe size={15}/>,label:'Website Link'}].map(({key,icon,label}) => (
                <button key={key} onClick={() => { setTab(key); setModalErr('') }}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${tab===key?'bg-white text-primary shadow-sm':'text-gray-500 hover:text-slate-ur'}`}>
                  {icon} {label}
                </button>
              ))}
            </div>
            <ErrorBanner msg={modalErr} />
            {tab === 'document' ? (
              <div>
                <div onClick={() => !uploading && fileRef.current?.click()} className="border-2 border-dashed border-gray-200 rounded-xl p-8 text-center cursor-pointer hover:border-primary/40 hover:bg-primary/2 transition-all">
                  {uploading ? (
                    <div className="space-y-2">
                      <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" />
                      <p className="text-sm text-primary font-medium">Uploading… {uploadPct}%</p>
                      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className="h-full bg-primary rounded-full transition-all" style={{ width: `${uploadPct}%` }} /></div>
                    </div>
                  ) : (
                    <><Upload size={28} className="text-gray-300 mx-auto mb-3" /><p className="text-sm font-semibold text-slate-ur">Click to choose a file</p><p className="text-xs text-gray-400 mt-1">PDF, DOCX, or TXT — up to 50 MB</p></>
                  )}
                </div>
                <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleUpload} />
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-ur mb-1.5">Website URL <span className="text-red-400">*</span></label>
                  <input type="url" value={urlInput} onChange={e => setUrlInput(e.target.value)} placeholder="https://ur.ac.rw/page..." className="input-field" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-ur mb-1.5">Custom Title <span className="text-gray-400">(optional)</span></label>
                  <input type="text" value={urlTitle} onChange={e => setUrlTitle(e.target.value)} placeholder="e.g. UR Scholarship 2026" className="input-field" />
                </div>
                <div className="flex justify-end gap-3 pt-2">
                  <button onClick={() => setShowModal(false)} className="btn-outline py-2 px-5 text-sm">Cancel</button>
                  <button onClick={handleIngestUrl} disabled={!urlInput.trim() || ingesting} className="btn-primary py-2 px-5 text-sm disabled:opacity-60 flex items-center gap-2">
                    {ingesting ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Globe size={14} />}
                    {ingesting ? 'Scraping…' : 'Add Website'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   EXPORT LOGS
═══════════════════════════════════════════════════════════════════════════ */
function ExportLogs({ toast }) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate]     = useState('')
  const [statusFilter, setStatus] = useState('')
  const [exporting, setExporting] = useState('')

  const handleExport = async (type, params = {}) => {
    setExporting(type)
    try {
      await downloadExport(type, { start_date: startDate, end_date: endDate, status: statusFilter, ...params })
      toast(`${type} export downloaded`)
    } catch (e) { toast(e.message, 'error') }
    finally { setExporting('') }
  }

  const exports = [
    { key: 'queries',    label: 'Chat Queries',      icon: <MessageSquare size={18} className="text-primary" />,    desc: 'All chat history with timestamps, categories, and confidence scores.' },
    { key: 'users',      label: 'User List',          icon: <Users size={18} className="text-blue-500" />,           desc: 'All registered users with roles and registration dates.' },
    { key: 'unanswered', label: 'Unanswered Queries', icon: <AlertCircle size={18} className="text-amber-500" />,    desc: 'All flagged queries with admin answers and status.' },
  ]

  return (
    <div className="space-y-7">
      <h2 className="text-xl font-bold text-slate-ur">Export Logs</h2>

      <div className="card p-5 border border-gray-100">
        <h3 className="font-semibold text-slate-ur text-sm mb-4 flex items-center gap-2"><Filter size={15} /> Filters</h3>
        <div className="flex gap-4 flex-wrap">
          <div>
            <label className="block text-xs font-medium text-slate-ur mb-1">Start Date</label>
            <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="input-field py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-ur mb-1">End Date</label>
            <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="input-field py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-ur mb-1">Query Status</label>
            <select value={statusFilter} onChange={e => setStatus(e.target.value)} className="input-field py-2 text-sm">
              <option value="">All</option>
              <option value="resolved">Answered</option>
              <option value="unresolved">Unanswered</option>
            </select>
          </div>
          {(startDate || endDate || statusFilter) && (
            <button onClick={() => { setStartDate(''); setEndDate(''); setStatus('') }} className="text-xs text-gray-400 hover:text-red-500 mt-5">Clear filters</button>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {exports.map(({ key, label, icon, desc }) => (
          <div key={key} className="card p-5 border border-gray-100 flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center shrink-0">{icon}</div>
              <div>
                <p className="font-semibold text-slate-ur text-sm">{label}</p>
                <p className="text-xs text-gray-400 mt-0.5">CSV format</p>
              </div>
            </div>
            <p className="text-xs text-gray-500 flex-1">{desc}</p>
            <button
              onClick={() => handleExport(key)}
              disabled={!!exporting}
              className="btn-primary py-2 px-4 text-sm disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {exporting === key ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Download size={14} />}
              {exporting === key ? 'Downloading…' : 'Download CSV'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   SETTINGS
═══════════════════════════════════════════════════════════════════════════ */
function SettingsSection({ toast }) {
  const { data: settings, loading, error, reload } = useAsync(getSettings)
  const [form, setForm]     = useState({})
  const [saving, setSaving] = useState(false)
  const [saveErr, setSaveErr] = useState('')

  useEffect(() => { if (settings) setForm(settings) }, [settings])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSave = async () => {
    setSaving(true); setSaveErr('')
    try { await saveSettings(form); reload(); toast('Settings saved') }
    catch (e) { setSaveErr(e.message); toast(e.message, 'error') }
    finally { setSaving(false) }
  }

  if (loading) return <div className="flex items-center justify-center py-20"><div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin" /></div>

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-xl font-bold text-slate-ur">Settings</h2>
      <ErrorBanner msg={error || saveErr} />

      <div className="card border border-gray-100 divide-y divide-gray-100">
        {/* General */}
        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">General</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">System Name</label>
              <input value={form.system_name||''} onChange={e=>set('system_name',e.target.value)} className="input-field py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">Description</label>
              <input value={form.system_description||''} onChange={e=>set('system_description',e.target.value)} className="input-field py-2 text-sm" />
            </div>
          </div>
        </div>

        {/* AI */}
        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">AI Configuration</h3>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1.5">Gemini Model</label>
                <input value={form.gemini_model||''} onChange={e=>set('gemini_model',e.target.value)} className="input-field py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1.5">OpenRouter Model</label>
                <input value={form.openrouter_model||''} onChange={e=>set('openrouter_model',e.target.value)} className="input-field py-2 text-sm" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1.5">Temperature</label>
                <input type="number" step="0.1" min="0" max="2" value={form.temperature||''} onChange={e=>set('temperature',e.target.value)} className="input-field py-2 text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-ur mb-1.5">Max Tokens</label>
                <input type="number" value={form.max_tokens||''} onChange={e=>set('max_tokens',e.target.value)} className="input-field py-2 text-sm" />
              </div>
            </div>
          </div>
        </div>

        {/* RAG */}
        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">RAG Pipeline</h3>
          <div className="grid grid-cols-2 gap-4">
            {[
              ['Chunk Size', 'chunk_size'], ['Chunk Overlap', 'chunk_overlap'],
              ['Top-K Retrieval', 'similarity_top_k'], ['Confidence Threshold', 'confidence_threshold'],
            ].map(([label, key]) => (
              <div key={key}>
                <label className="block text-xs font-medium text-slate-ur mb-1.5">{label}</label>
                <input type="number" step={key === 'confidence_threshold' ? '0.05' : '1'} value={form[key]||''} onChange={e=>set(key,e.target.value)} className="input-field py-2 text-sm" />
              </div>
            ))}
          </div>
        </div>

        {/* Access Control */}
        <div className="p-5">
          <h3 className="font-semibold text-slate-ur text-sm mb-4">Access Control</h3>
          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={form.allow_registration === 'true'} onChange={e=>set('allow_registration', e.target.checked ? 'true' : 'false')} className="w-4 h-4 accent-primary" />
              <div>
                <span className="text-sm text-slate-dark">Allow student self-registration</span>
                <p className="text-xs text-gray-400">When disabled, only admins can create accounts</p>
              </div>
            </label>
            <div>
              <label className="block text-xs font-medium text-slate-ur mb-1.5">Rate Limit (requests/min per IP)</label>
              <input type="number" value={form.rate_limit||''} onChange={e=>set('rate_limit',e.target.value)} className="input-field py-2 text-sm w-32" />
            </div>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button onClick={handleSave} disabled={saving} className="btn-primary py-2.5 px-6 text-sm disabled:opacity-60 flex items-center gap-2">
          {saving ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Save size={14} />}
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN ADMIN DASHBOARD
═══════════════════════════════════════════════════════════════════════════ */
export default function AdminDashboard() {
  const [active, setActive]     = useState('overview')
  const [sideOpen, setSideOpen] = useState(false)
  const { data: stats }         = useAsync(getStats)
  const navigate                = useNavigate()
  const { toasts, toast }       = useToast()

  const sections = {
    overview:   <Overview toast={toast} />,
    analytics:  <Analytics />,
    faqs:       <FAQManager toast={toast} />,
    unanswered: <UnansweredQueries toast={toast} />,
    users:      <UserManagement toast={toast} />,
    knowledge:  <KnowledgeBase toast={toast} />,
    logs:       <ExportLogs toast={toast} />,
    settings:   <SettingsSection toast={toast} />,
  }

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      <ToastContainer toasts={toasts} />

      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 w-60 bg-slate-dark text-white flex flex-col transition-transform duration-300 ${sideOpen ? 'translate-x-0' : '-translate-x-full'} lg:static lg:translate-x-0`}>
        <div className="px-5 py-5 border-b border-white/10 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-bold text-white text-xs shrink-0">UC</div>
          <div>
            <div className="text-white font-bold text-sm">UniConnect</div>
            <div className="text-white/40 text-[10px]">Admin Portal</div>
          </div>
          <button className="lg:hidden ml-auto text-white/50 hover:text-white" onClick={() => setSideOpen(false)}><X size={18} /></button>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(item => (
            <button key={item.key} onClick={() => { setActive(item.key); setSideOpen(false) }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${active===item.key ? 'bg-primary text-white' : 'text-white/60 hover:text-white hover:bg-white/5'}`}>
              {item.icon}
              {item.label}
              {item.key === 'unanswered' && (stats?.pending_reviews > 0) && (
                <span className="ml-auto text-[10px] bg-amber-400 text-white font-bold px-1.5 py-0.5 rounded-full">{stats.pending_reviews}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="px-3 py-4 border-t border-white/10">
          <button onClick={() => { clearAuth(); navigate('/login') }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
            <LogOut size={17} /> Sign Out
          </button>
        </div>
      </aside>

      {sideOpen && <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setSideOpen(false)} />}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <header className="bg-white border-b border-gray-100 px-5 py-4 flex items-center gap-4 shrink-0">
          <button className="lg:hidden p-1.5 rounded-lg text-gray-500 hover:bg-gray-100" onClick={() => setSideOpen(true)}><Menu size={20} /></button>
          <div className="flex-1">
            <h1 className="font-bold text-slate-ur text-sm">{NAV.find(n => n.key === active)?.label}</h1>
          </div>
          <div className="flex items-center gap-2.5">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-semibold text-slate-ur">Admin</div>
              <div className="text-[10px] text-gray-400">University of Rwanda</div>
            </div>
            <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-white text-xs font-bold">A</div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-6">{sections[active]}</main>
      </div>
    </div>
  )
}
