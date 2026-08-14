"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah, formatDate } from "@/lib/api"
import type { TopUpRequest } from "@/lib/types"
import { CheckCircle, XCircle, Clock, CheckCheck, X } from "lucide-react"

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: "Pending", color: "text-amber-700", bg: "bg-amber-50" },
  approved: { label: "Disetujui", color: "text-emerald-700", bg: "bg-emerald-50" },
  rejected: { label: "Ditolak", color: "text-red-700", bg: "bg-red-50" },
}

export default function TopUpPage() {
  const [requests, setRequests] = useState<TopUpRequest[]>([])
  const [statusFilter, setStatusFilter] = useState("pending")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  const load = (s: string) => {
    setLoading(true)
    apiFetch<TopUpRequest[]>(`/topup?status=${s}`)
      .then(setRequests)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(statusFilter) }, [statusFilter])

  const approve = async (id: number) => {
    await apiFetch(`/topup/${id}/approve`, { method: "POST" })
    load(statusFilter)
  }

  const reject = async (id: number) => {
    if (!confirm("Tolak request ini?")) return
    await apiFetch(`/topup/${id}/reject`, { method: "POST" })
    load(statusFilter)
  }

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Top-up Saldo</h1>
        <p className="text-sm text-slate-500 mt-0.5">Kelola permintaan top-up dari pengguna</p>
      </div>

      <div className="flex gap-2">
        {["pending", "approved", "rejected"].map((s) => {
          const cfg = STATUS_CONFIG[s]
          return (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                statusFilter === s
                  ? `${cfg.bg} ${cfg.color} shadow-sm`
                  : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
              }`}
            >
              {cfg.label}
            </button>
          )
        })}
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Pengguna</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Jumlah</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Waktu</th>
                {statusFilter === "pending" && <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {requests.map((r) => {
                const cfg = STATUS_CONFIG[r.status] || STATUS_CONFIG.pending
                return (
                  <tr key={r.request_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-4">
                      <p className="font-medium text-slate-800">{r.full_name}</p>
                      <p className="text-xs text-slate-400">{r.username ? `@${r.username}` : `ID: ${r.user_id}`}</p>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <span className="font-bold text-emerald-600">{formatRupiah(r.amount)}</span>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full ${cfg.bg} ${cfg.color}`}>
                        {cfg.label}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-400 text-xs">{formatDate(r.created_at)}</td>
                    {statusFilter === "pending" && (
                      <td className="px-5 py-4">
                        <div className="flex items-center justify-center gap-2">
                          <button onClick={() => approve(r.request_id)} className="flex items-center gap-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                            <CheckCircle size={13} /> Setujui
                          </button>
                          <button onClick={() => reject(r.request_id)} className="flex items-center gap-1.5 bg-red-50 hover:bg-red-100 text-red-600 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                            <XCircle size={13} /> Tolak
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                )
              })}
              {requests.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-slate-400 text-sm">Tidak ada request {statusFilter}</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
