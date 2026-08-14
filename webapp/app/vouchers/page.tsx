"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah, formatDate } from "@/lib/api"
import { Plus, Pencil, Trash2, Copy, ToggleLeft, ToggleRight, Ticket, RefreshCw, Users, X, Check, Zap } from "lucide-react"
import Modal from "@/components/Modal"

interface Voucher {
  voucher_id: number
  code: string
  type: string
  amount: number
  max_claims: number
  claimed_count: number
  per_user: number
  is_active: boolean
  expires_at: string | null
  description: string
  created_at: string
  is_expired: boolean
  remaining_claims: number
}

interface Claim {
  user_id: number
  full_name: string
  username: string | null
  amount: number
  claimed_at: string
}

const EMPTY_FORM = {
  code: "", type: "saldo", amount: "", max_claims: "0",
  per_user: "1", expires_at: "", description: "", count: "1",
}

function StatusBadge({ v }: { v: Voucher }) {
  if (v.is_expired) return <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">Kadaluarsa</span>
  if (!v.is_active) return <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-0.5 rounded-full">Nonaktif</span>
  if (v.max_claims > 0 && v.claimed_count >= v.max_claims) return <span className="text-xs font-medium text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full">Habis</span>
  return <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Aktif</span>
}

export default function VouchersPage() {
  const [vouchers, setVouchers] = useState<Voucher[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [modal, setModal] = useState<"create" | "generate" | "edit" | "claims" | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editTarget, setEditTarget] = useState<Voucher | null>(null)
  const [claims, setClaims] = useState<Claim[]>([])
  const [claimsVoucher, setClaimsVoucher] = useState<Voucher | null>(null)
  const [saving, setSaving] = useState(false)
  const [copied, setCopied] = useState<string | null>(null)
  const [generatedCodes, setGeneratedCodes] = useState<string[]>([])

  const load = () => {
    setLoading(true)
    apiFetch<Voucher[]>("/vouchers")
      .then(setVouchers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopied(code)
    setTimeout(() => setCopied(null), 2000)
  }

  const toggleActive = async (v: Voucher) => {
    await apiFetch(`/vouchers/${v.voucher_id}`, { method: "PATCH", body: JSON.stringify({ is_active: !v.is_active }) })
    load()
  }

  const deleteVoucher = async (id: number) => {
    if (!confirm("Hapus voucher ini? Semua riwayat klaim juga akan dihapus.")) return
    await apiFetch(`/vouchers/${id}`, { method: "DELETE" })
    load()
  }

  const openClaims = async (v: Voucher) => {
    setClaimsVoucher(v)
    const data = await apiFetch<Claim[]>(`/vouchers/${v.voucher_id}/claims`)
    setClaims(data)
    setModal("claims")
  }

  const openEdit = (v: Voucher) => {
    setEditTarget(v)
    setForm({
      code: v.code, type: v.type, amount: String(v.amount),
      max_claims: String(v.max_claims), per_user: String(v.per_user),
      expires_at: v.expires_at ? v.expires_at.slice(0, 16) : "",
      description: v.description, count: "1",
    })
    setModal("edit")
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        code: form.code || undefined,
        type: form.type,
        amount: parseInt(form.amount) || 0,
        max_claims: parseInt(form.max_claims) || 0,
        per_user: parseInt(form.per_user) || 1,
        expires_at: form.expires_at || null,
        description: form.description,
      }
      await apiFetch("/vouchers", { method: "POST", body: JSON.stringify(payload) })
      setModal(null); setForm(EMPTY_FORM); load()
    } finally { setSaving(false) }
  }

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setGeneratedCodes([])
    try {
      const count = Math.min(parseInt(form.count) || 1, 500)
      const payload = {
        type: form.type,
        amount: parseInt(form.amount) || 0,
        max_claims: parseInt(form.max_claims) || 0,
        per_user: parseInt(form.per_user) || 1,
        expires_at: form.expires_at || null,
        description: form.description,
      }
      const result = await apiFetch<Voucher[]>(`/vouchers/generate?count=${count}`, { method: "POST", body: JSON.stringify(payload) })
      setGeneratedCodes(result.map(v => v.code))
      load()
    } finally { setSaving(false) }
  }

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editTarget) return
    setSaving(true)
    try {
      await apiFetch(`/vouchers/${editTarget.voucher_id}`, {
        method: "PATCH",
        body: JSON.stringify({
          amount: parseInt(form.amount) || 0,
          max_claims: parseInt(form.max_claims) || 0,
          per_user: parseInt(form.per_user) || 1,
          expires_at: form.expires_at || null,
          description: form.description,
        }),
      })
      setModal(null); setEditTarget(null); load()
    } finally { setSaving(false) }
  }

  const stats = {
    total: vouchers.length,
    active: vouchers.filter(v => v.is_active && !v.is_expired).length,
    totalClaimed: vouchers.reduce((s, v) => s + v.claimed_count, 0),
    totalValue: vouchers.reduce((s, v) => s + v.claimed_count * v.amount, 0),
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Voucher</h1>
          <p className="text-sm text-slate-500 mt-0.5">Buat dan kelola kode voucher untuk user</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => { setModal("generate"); setForm(EMPTY_FORM); setGeneratedCodes([]) }}
            className="flex items-center gap-1.5 text-sm font-medium px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors">
            <Zap size={14} /> Generate
          </button>
          <button onClick={() => { setModal("create"); setForm(EMPTY_FORM) }}
            className="flex items-center gap-1.5 text-sm font-medium px-4 py-2.5 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors">
            <Plus size={14} /> Buat Voucher
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Voucher", value: stats.total },
          { label: "Aktif", value: stats.active },
          { label: "Total Diklaim", value: stats.totalClaimed },
          { label: "Total Value Diklaim", value: formatRupiah(stats.totalValue) },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
            <p className="text-xs text-slate-500 font-medium">{s.label}</p>
            <p className="text-xl font-bold text-slate-900 mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {error && <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>}

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Kode</th>
              <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Nilai</th>
              <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Klaim</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Expired</th>
              <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading && <tr><td colSpan={6} className="px-5 py-8 text-center text-slate-400 text-sm">Memuat...</td></tr>}
            {!loading && vouchers.length === 0 && (
              <tr><td colSpan={6} className="px-5 py-12 text-center">
                <Ticket size={32} className="text-slate-200 mx-auto mb-2" />
                <p className="text-slate-400 text-sm">Belum ada voucher</p>
              </td></tr>
            )}
            {vouchers.map(v => (
              <tr key={v.voucher_id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-2">
                    <code className="text-sm font-bold text-indigo-700 bg-indigo-50 px-2.5 py-1 rounded-lg tracking-wider">{v.code}</code>
                    <button onClick={() => copyCode(v.code)} className="text-slate-400 hover:text-indigo-600 transition-colors" title="Copy kode">
                      {copied === v.code ? <Check size={14} className="text-emerald-500" /> : <Copy size={13} />}
                    </button>
                  </div>
                  {v.description && <p className="text-xs text-slate-400 mt-0.5 truncate max-w-xs">{v.description}</p>}
                </td>
                <td className="px-5 py-3.5 text-right font-semibold text-emerald-600">{formatRupiah(v.amount)}</td>
                <td className="px-5 py-3.5 text-center">
                  <button onClick={() => openClaims(v)} className="text-xs text-slate-600 hover:text-indigo-600 transition-colors">
                    <span className="font-semibold">{v.claimed_count}</span>
                    {v.max_claims > 0 && <span className="text-slate-400">/{v.max_claims}</span>}
                    {v.per_user === 1 && <span className="ml-1 text-slate-400 text-xs">1x/user</span>}
                  </button>
                </td>
                <td className="px-5 py-3.5 text-slate-400 text-xs">
                  {v.expires_at ? v.expires_at.slice(0, 10) : "—"}
                </td>
                <td className="px-5 py-3.5 text-center"><StatusBadge v={v} /></td>
                <td className="px-5 py-3.5">
                  <div className="flex items-center justify-center gap-1">
                    <button onClick={() => toggleActive(v)} className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" title="Toggle aktif">
                      {v.is_active ? <ToggleRight size={16} className="text-emerald-500" /> : <ToggleLeft size={16} />}
                    </button>
                    <button onClick={() => openEdit(v)} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Edit">
                      <Pencil size={13} />
                    </button>
                    <button onClick={() => deleteVoucher(v.voucher_id)} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Hapus">
                      <Trash2 size={13} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Form fields reuse */}
      {(modal === "create" || modal === "edit" || modal === "generate") && (
        <Modal
          title={modal === "create" ? "Buat Voucher" : modal === "generate" ? "Generate Voucher" : "Edit Voucher"}
          onClose={() => { setModal(null); setGeneratedCodes([]) }}
        >
          <form onSubmit={modal === "edit" ? handleEdit : modal === "generate" ? handleGenerate : handleCreate} className="space-y-4">
            {modal === "create" && (
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Kode Voucher <span className="text-slate-400">(kosongkan = auto)</span></label>
                <input value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  placeholder="Contoh: UCOK2024"
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-mono uppercase tracking-wider focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            )}
            {modal === "generate" && (
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Jumlah Kode</label>
                <input type="number" min="1" max="500" value={form.count} onChange={e => setForm({ ...form, count: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Nilai (Rp)</label>
                <input type="number" min="0" required value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })}
                  placeholder="10000"
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Maks. Klaim <span className="text-slate-400">(0=∞)</span></label>
                <input type="number" min="0" value={form.max_claims} onChange={e => setForm({ ...form, max_claims: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Limit per User</label>
                <select value={form.per_user} onChange={e => setForm({ ...form, per_user: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500">
                  <option value="1">1x per user</option>
                  <option value="0">Tidak dibatasi</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Expired</label>
                <input type="datetime-local" value={form.expires_at} onChange={e => setForm({ ...form, expires_at: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Deskripsi (opsional)</label>
              <input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Contoh: Voucher promo Lebaran 2024"
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </div>

            {/* Generated codes result */}
            {generatedCodes.length > 0 && (
              <div className="bg-slate-50 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-slate-600">{generatedCodes.length} kode berhasil dibuat</p>
                  <button type="button" onClick={() => { navigator.clipboard.writeText(generatedCodes.join("\n")); setCopied("all") }}
                    className="text-xs text-indigo-600 hover:underline flex items-center gap-1">
                    {copied === "all" ? <><Check size={12} /> Tersalin</> : <><Copy size={12} /> Salin semua</>}
                  </button>
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {generatedCodes.map(c => (
                    <div key={c} className="flex items-center justify-between bg-white rounded-lg px-3 py-1.5">
                      <code className="text-sm font-bold text-indigo-700 tracking-wider">{c}</code>
                      <button type="button" onClick={() => copyCode(c)} className="text-slate-400 hover:text-indigo-600">
                        {copied === c ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving}
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl disabled:opacity-60">
                {saving ? "Menyimpan..." : modal === "generate" ? `Generate ${form.count} Kode` : modal === "edit" ? "Simpan" : "Buat Voucher"}
              </button>
              <button type="button" onClick={() => { setModal(null); setGeneratedCodes([]) }}
                className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl">
                {generatedCodes.length > 0 ? "Tutup" : "Batal"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Claims modal */}
      {modal === "claims" && claimsVoucher && (
        <Modal title={`Riwayat Klaim — ${claimsVoucher.code}`} onClose={() => setModal(null)}>
          <div className="space-y-3">
            <div className="flex items-center gap-3 bg-slate-50 rounded-xl px-4 py-3 text-sm">
              <code className="font-bold text-indigo-700">{claimsVoucher.code}</code>
              <span className="text-slate-300">·</span>
              <span className="text-slate-600">{formatRupiah(claimsVoucher.amount)} per klaim</span>
              <span className="text-slate-300">·</span>
              <span className="font-semibold text-slate-700">{claimsVoucher.claimed_count} klaim</span>
            </div>
            {claims.length === 0 ? (
              <p className="text-center text-slate-400 text-sm py-6">Belum ada yang memakai voucher ini</p>
            ) : (
              <div className="max-h-72 overflow-y-auto divide-y divide-slate-50">
                {claims.map((c, i) => (
                  <div key={i} className="flex items-center justify-between py-2.5">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{c.full_name}</p>
                      <p className="text-xs text-slate-400">{c.username ? `@${c.username}` : `ID: ${c.user_id}`}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-emerald-600">{formatRupiah(c.amount)}</p>
                      <p className="text-xs text-slate-400">{formatDate(c.claimed_at)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  )
}
