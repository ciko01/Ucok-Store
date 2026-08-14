"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah, formatDate } from "@/lib/api"
import type { User } from "@/lib/types"
import { PlusCircle } from "lucide-react"
import Modal from "@/components/Modal"
import Link from "next/link"

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [topupTarget, setTopupTarget] = useState<User | null>(null)
  const [amount, setAmount] = useState("")
  const [desc, setDesc] = useState("")
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    apiFetch<User[]>("/users?limit=100")
      .then(setUsers)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const handleTopup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!topupTarget) return
    setSaving(true)
    try {
      await apiFetch(`/users/${topupTarget.user_id}/add-balance`, {
        method: "POST",
        body: JSON.stringify({ user_id: topupTarget.user_id, amount: parseInt(amount), description: desc || "Top-up manual via webapp" }),
      })
      setTopupTarget(null)
      setAmount("")
      setDesc("")
      load()
    } finally {
      setSaving(false)
    }
  }

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Pengguna</h1>
        <p className="text-sm text-slate-500 mt-0.5">{users.length} pengguna terdaftar</p>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Pengguna</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">User ID</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Saldo</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Bergabung</th>
                <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {users.map((u) => (
                <tr key={u.user_id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4">
                    <Link href={`/users/${u.user_id}`} className="flex items-center gap-3 group">
                      <div className="w-8 h-8 bg-indigo-50 rounded-xl flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-bold text-indigo-600">{u.full_name[0]}</span>
                      </div>
                      <div>
                        <p className="font-medium text-slate-800 group-hover:text-indigo-600 transition-colors">{u.full_name}</p>
                        <p className="text-xs text-slate-400">{u.username ? `@${u.username}` : "Tanpa username"}</p>
                      </div>
                    </Link>
                  </td>
                  <td className="px-5 py-4 font-mono text-xs text-slate-400">{u.user_id}</td>
                  <td className="px-5 py-4 text-right font-semibold text-emerald-600">{formatRupiah(u.balance)}</td>
                  <td className="px-5 py-4 text-slate-400 text-xs">{formatDate(u.first_seen_at)}</td>
                  <td className="px-5 py-4 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Link
                        href={`/users/${u.user_id}`}
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        Lihat Detail
                      </Link>
                      <button
                        onClick={() => { setTopupTarget(u); setAmount(""); setDesc("") }}
                        className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
                      >
                        <PlusCircle size={13} /> Tambah Saldo
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-slate-400 text-sm">Belum ada pengguna</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {topupTarget && (
        <Modal title={`Tambah Saldo — ${topupTarget.full_name}`} onClose={() => setTopupTarget(null)}>
          <form onSubmit={handleTopup} className="space-y-4">
            <div className="bg-slate-50 rounded-xl px-4 py-3 text-sm">
              <p className="text-slate-500">Saldo saat ini</p>
              <p className="font-bold text-slate-800 text-lg">{formatRupiah(topupTarget.balance)}</p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Jumlah (Rp)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                min="1"
                placeholder="Contoh: 50000"
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Keterangan</label>
              <input
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="Top-up manual via webapp"
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>
            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl transition-colors disabled:opacity-60">
                {saving ? "Menyimpan..." : "Tambah Saldo"}
              </button>
              <button type="button" onClick={() => setTopupTarget(null)} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl transition-colors">
                Batal
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
