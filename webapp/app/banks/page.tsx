"use client"

import { useEffect, useState } from "react"
import { apiFetch } from "@/lib/api"
import type { Bank } from "@/lib/types"
import { Trash2, ToggleLeft, ToggleRight, Plus, Landmark, Pencil } from "lucide-react"
import Modal from "@/components/Modal"

const EMPTY_FORM = { bank_name: "", account_number: "", account_holder: "", notes: "" }
const FIELDS: { key: keyof typeof EMPTY_FORM; label: string; required: boolean }[] = [
  { key: "bank_name", label: "Nama Bank", required: true },
  { key: "account_number", label: "Nomor Rekening", required: true },
  { key: "account_holder", label: "Atas Nama", required: true },
  { key: "notes", label: "Catatan (opsional)", required: false },
]

export default function BanksPage() {
  const [banks, setBanks] = useState<Bank[]>([])
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [editTarget, setEditTarget] = useState<Bank | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    apiFetch<Bank[]>("/banks")
      .then(setBanks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openAdd = () => { setForm(EMPTY_FORM); setShowAdd(true) }
  const openEdit = (b: Bank) => {
    setForm({ bank_name: b.bank_name, account_number: b.account_number, account_holder: b.account_holder, notes: b.notes })
    setEditTarget(b)
  }
  const closeModal = () => { setShowAdd(false); setEditTarget(null) }

  const toggle = async (b: Bank) => {
    await apiFetch(`/banks/${b.bank_id}`, { method: "PATCH", body: JSON.stringify({ is_active: !b.is_active }) })
    load()
  }

  const remove = async (id: number) => {
    if (!confirm("Hapus bank ini?")) return
    await apiFetch(`/banks/${id}`, { method: "DELETE" })
    load()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editTarget) {
        await apiFetch(`/banks/${editTarget.bank_id}`, { method: "PATCH", body: JSON.stringify(form) })
      } else {
        await apiFetch("/banks", { method: "POST", body: JSON.stringify(form) })
      }
      closeModal()
      load()
    } finally {
      setSaving(false)
    }
  }

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Bank</h1>
          <p className="text-sm text-slate-500 mt-0.5">Kelola rekening pembayaran</p>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors shadow-sm">
          <Plus size={15} /> Tambah Bank
        </button>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {banks.map((b) => (
            <div key={b.bank_id} className={`bg-white rounded-2xl border shadow-sm p-5 transition-all ${b.is_active ? "border-slate-100" : "border-slate-100 opacity-60"}`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-indigo-50 rounded-xl flex items-center justify-center">
                    <Landmark size={16} className="text-indigo-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">{b.bank_name}</p>
                    {b.is_active
                      ? <span className="text-xs text-emerald-600 font-medium">Aktif</span>
                      : <span className="text-xs text-slate-400 font-medium">Nonaktif</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => openEdit(b)} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Edit">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => toggle(b)} className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors" title="Toggle aktif">
                    {b.is_active ? <ToggleRight size={18} className="text-emerald-500" /> : <ToggleLeft size={18} />}
                  </button>
                  <button onClick={() => remove(b.bank_id)} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Hapus">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
              <p className="font-mono text-sm text-slate-700 font-medium">{b.account_number}</p>
              <p className="text-sm text-slate-500 mt-0.5">{b.account_holder}</p>
              {b.notes && <p className="text-xs text-slate-400 mt-2 bg-slate-50 rounded-lg px-3 py-2">{b.notes}</p>}
            </div>
          ))}
          {banks.length === 0 && (
            <div className="col-span-2 bg-white rounded-2xl border border-slate-100 py-12 text-center text-slate-400 text-sm">
              Belum ada rekening bank
            </div>
          )}
        </div>
      )}

      {(showAdd || editTarget) && (
        <Modal title={editTarget ? "Edit Bank" : "Tambah Bank"} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            {FIELDS.map(({ key, label, required }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">{label}</label>
                <input
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  required={required}
                  placeholder={label}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                />
              </div>
            ))}
            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl transition-colors disabled:opacity-60">
                {saving ? "Menyimpan..." : editTarget ? "Simpan Perubahan" : "Tambah"}
              </button>
              <button type="button" onClick={closeModal} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl transition-colors">
                Batal
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
