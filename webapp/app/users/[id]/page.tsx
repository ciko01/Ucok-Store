"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { apiFetch, formatRupiah, formatDate } from "@/lib/api"
import type { User, Transaction } from "@/lib/types"
import { ArrowLeft, ShoppingBag, TrendingUp, Receipt } from "lucide-react"

interface UserMembership {
  tier_name: string
  badge: string
  is_active: boolean
  expires_at: string | null
  discount_percent: number
  bonus_multiplier: number
}

const TYPE_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  purchase: { label: "Pembelian", color: "text-indigo-700", bg: "bg-indigo-50" },
  topup:    { label: "Top-up",    color: "text-emerald-700", bg: "bg-emerald-50" },
  bonus:    { label: "Bonus",     color: "text-amber-700",   bg: "bg-amber-50" },
  refund:   { label: "Refund",    color: "text-rose-700",    bg: "bg-rose-50" },
}

export default function UserDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [membership, setMembership] = useState<UserMembership | null>(null)
  const [filter, setFilter] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    setLoading(true)
    Promise.all([
      apiFetch<User>(`/users/${id}`),
      apiFetch<Transaction[]>(`/users/${id}/transactions?limit=100`),
      apiFetch<UserMembership>(`/membership/users/${id}`).catch(() => null),
    ])
      .then(([u, t, m]) => { setUser(u); setTransactions(t); setMembership(m) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  const filtered = filter
    ? transactions.filter(t => t.transaction_type === filter)
    : transactions

  const totalPurchase = transactions.filter(t => t.transaction_type === "purchase").reduce((s, t) => s + t.amount, 0)
  const totalTopup = transactions.filter(t => t.transaction_type === "topup").reduce((s, t) => s + t.amount, 0)
  const purchaseCount = transactions.filter(t => t.transaction_type === "purchase").length

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>
  if (loading) return <div className="text-slate-400 text-sm p-2">Memuat...</div>
  if (!user) return null

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/users")} className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-900">{user.full_name}</h1>
          <p className="text-sm text-slate-500">{user.username ? `@${user.username}` : `ID: ${user.user_id}`}</p>
        </div>
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs text-slate-500 font-medium">Saldo</p>
          <p className="text-xl font-bold text-emerald-600 mt-1">{formatRupiah(user.balance)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs text-slate-500 font-medium">Total Belanja</p>
          <p className="text-xl font-bold text-indigo-600 mt-1">{formatRupiah(totalPurchase)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs text-slate-500 font-medium">Total Top-up</p>
          <p className="text-xl font-bold text-slate-800 mt-1">{formatRupiah(totalTopup)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4">
          <p className="text-xs text-slate-500 font-medium">Jumlah Order</p>
          <p className="text-xl font-bold text-slate-800 mt-1">{purchaseCount}</p>
        </div>
      </div>

      {/* Membership */}
      {membership && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <h2 className="font-semibold text-slate-800 mb-3">Membership</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1.5 rounded-full ${
              membership.tier_name === "Admin" ? "bg-purple-100 text-purple-700" :
              membership.tier_name === "Gold"  ? "bg-amber-100 text-amber-700" :
              membership.tier_name === "Silver"? "bg-slate-200 text-slate-700" :
              membership.tier_name === "Bronze"? "bg-orange-100 text-orange-700" :
              "bg-slate-100 text-slate-600"
            }`}>
              {membership.badge} {membership.tier_name}
            </span>
            {membership.is_active
              ? <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full font-medium">Aktif</span>
              : <span className="text-xs text-red-500 bg-red-50 px-2 py-0.5 rounded-full font-medium">Expired</span>}
            {membership.expires_at && <span className="text-xs text-slate-400">Hingga: {membership.expires_at.slice(0, 10)}</span>}
            {membership.discount_percent > 0 && <span className="text-xs text-slate-500">Diskon {membership.discount_percent}%</span>}
            {membership.bonus_multiplier > 1 && <span className="text-xs text-slate-500">Bonus ×{membership.bonus_multiplier}</span>}
          </div>
        </div>
      )}

      {/* Transaction history */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Receipt size={16} className="text-slate-400" />
            <h2 className="font-semibold text-slate-800">Riwayat Transaksi</h2>
            <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{transactions.length}</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            {["", "purchase", "topup", "bonus"].map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${filter === f ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
                {f || "Semua"}
              </button>
            ))}
          </div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Deskripsi</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tipe</th>
              <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Jumlah</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Waktu</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map(t => {
              const cfg = TYPE_CONFIG[t.transaction_type]
              return (
                <tr key={t.transaction_id} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3.5 text-slate-700 max-w-xs truncate">{t.description || "—"}</td>
                  <td className="px-5 py-3.5">
                    <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${cfg ? `${cfg.bg} ${cfg.color}` : "bg-slate-100 text-slate-600"}`}>
                      {cfg?.label || t.transaction_type}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-right font-semibold text-slate-800">{formatRupiah(t.amount)}</td>
                  <td className="px-5 py-3.5 text-slate-400 text-xs">{formatDate(t.created_at)}</td>
                </tr>
              )
            })}
            {filtered.length === 0 && (
              <tr><td colSpan={4} className="px-5 py-8 text-center text-slate-400 text-sm">Belum ada transaksi</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
