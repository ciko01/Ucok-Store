"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah } from "@/lib/api"
import type { Stats, RevenuePoint, TopBuyer } from "@/lib/types"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"
import { Users, ShoppingBag, TrendingUp, Clock, ArrowUpRight } from "lucide-react"

function StatCard({ label, value, icon: Icon, color, bg }: {
  label: string; value: string; icon: React.ElementType; color: string; bg: string
}) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500 font-medium">{label}</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{value}</p>
        </div>
        <div className={`p-2.5 rounded-xl ${bg}`}>
          <Icon size={18} className={color} />
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [revenue, setRevenue] = useState<RevenuePoint[]>([])
  const [topBuyers, setTopBuyers] = useState<TopBuyer[]>([])
  const [error, setError] = useState("")

  useEffect(() => {
    Promise.all([
      apiFetch<Stats>("/stats"),
      apiFetch<RevenuePoint[]>("/stats/revenue?days=30"),
      apiFetch<TopBuyer[]>("/stats/top-buyers?limit=5"),
    ])
      .then(([s, r, t]) => { setStats(s); setRevenue(r); setTopBuyers(t) })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return (
    <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>
  )
  if (!stats) return <div className="text-slate-400 text-sm p-2">Memuat...</div>

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">Ringkasan performa toko Anda</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Pengguna" value={stats.total_users.toLocaleString()} icon={Users} color="text-indigo-600" bg="bg-indigo-50" />
        <StatCard label="Total Transaksi" value={stats.total_transactions.toLocaleString()} icon={ShoppingBag} color="text-emerald-600" bg="bg-emerald-50" />
        <StatCard label="Total Omzet" value={formatRupiah(stats.total_revenue)} icon={TrendingUp} color="text-amber-600" bg="bg-amber-50" />
        <StatCard label="Top-up Pending" value={stats.pending_topups.toLocaleString()} icon={Clock} color="text-rose-600" bg="bg-rose-50" />
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold text-slate-800">Omzet 30 Hari Terakhir</h2>
          <span className="text-xs text-slate-400 bg-slate-50 px-3 py-1 rounded-full">30 hari</span>
        </div>
        {revenue.length === 0 ? (
          <p className="text-slate-400 text-sm py-8 text-center">Belum ada data transaksi</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={revenue}>
              <defs>
                <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)" }}
                formatter={(v) => [formatRupiah(Number(v)), "Omzet"]}
              />
              <Area type="monotone" dataKey="revenue" stroke="#6366f1" fill="url(#rev)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <h2 className="font-semibold text-slate-800 mb-5">Top Pembeli</h2>
        {topBuyers.length === 0 ? (
          <p className="text-slate-400 text-sm py-4 text-center">Belum ada data</p>
        ) : (
          <div className="space-y-3">
            {topBuyers.map((b) => (
              <div key={b.rank} className="flex items-center gap-4">
                <span className="w-6 text-center text-sm font-bold text-slate-300">{b.rank}</span>
                <div className="w-8 h-8 bg-indigo-50 rounded-xl flex items-center justify-center flex-shrink-0">
                  <span className="text-xs font-bold text-indigo-600">{b.full_name[0]}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{b.full_name}</p>
                  <p className="text-xs text-slate-400">{b.username ? `@${b.username}` : `${b.total_purchases} transaksi`}</p>
                </div>
                <span className="text-sm font-semibold text-emerald-600">{formatRupiah(b.total_spent)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
