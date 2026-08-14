"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah, formatDate } from "@/lib/api"
import type { Transaction } from "@/lib/types"

const TYPE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  purchase: { label: "Pembelian", color: "text-indigo-700", bg: "bg-indigo-50" },
  topup: { label: "Top-up", color: "text-emerald-700", bg: "bg-emerald-50" },
  bonus: { label: "Bonus", color: "text-amber-700", bg: "bg-amber-50" },
  refund: { label: "Refund", color: "text-rose-700", bg: "bg-rose-50" },
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [typeFilter, setTypeFilter] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  const load = (t: string) => {
    setLoading(true)
    const q = t ? `?transaction_type=${t}&limit=100` : "?limit=100"
    apiFetch<Transaction[]>(`/transactions${q}`)
      .then(setTransactions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(typeFilter) }, [typeFilter])

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Transaksi</h1>
        <p className="text-sm text-slate-500 mt-0.5">Riwayat semua transaksi</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {[
          { key: "", label: "Semua" },
          { key: "purchase", label: "Pembelian" },
          { key: "topup", label: "Top-up" },
          { key: "bonus", label: "Bonus" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTypeFilter(key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              typeFilter === key
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Deskripsi</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tipe</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">User ID</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Jumlah</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Waktu</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {transactions.map((t) => {
                const cfg = TYPE_CONFIG[t.transaction_type]
                return (
                  <tr key={t.transaction_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-4 text-slate-700 max-w-xs truncate">{t.description || "—"}</td>
                    <td className="px-5 py-4">
                      {cfg ? (
                        <span className={`inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full ${cfg.bg} ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-600">
                          {t.transaction_type}
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-4 font-mono text-xs text-slate-400">{t.user_id}</td>
                    <td className="px-5 py-4 text-right font-semibold text-slate-800">{formatRupiah(t.amount)}</td>
                    <td className="px-5 py-4 text-slate-400 text-xs">{formatDate(t.created_at)}</td>
                  </tr>
                )
              })}
              {transactions.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-slate-400 text-sm">Belum ada transaksi</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
