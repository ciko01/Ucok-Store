"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah } from "@/lib/api"
import type { RevenuePoint, TopBuyer } from "@/lib/types"
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid,
} from "recharts"

export default function StatsPage() {
  const [revenue, setRevenue] = useState<RevenuePoint[]>([])
  const [topBuyers, setTopBuyers] = useState<TopBuyer[]>([])
  const [days, setDays] = useState(30)
  const [error, setError] = useState("")

  useEffect(() => {
    Promise.all([
      apiFetch<RevenuePoint[]>(`/stats/revenue?days=${days}`),
      apiFetch<TopBuyer[]>("/stats/top-buyers?limit=10"),
    ])
      .then(([r, t]) => { setRevenue(r); setTopBuyers(t) })
      .catch((e) => setError(e.message))
  }, [days])

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  const tooltipStyle = {
    contentStyle: { borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.05)" }
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Statistik & Laporan</h1>
          <p className="text-sm text-slate-500 mt-0.5">Analisis performa penjualan</p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${days === d ? "bg-indigo-600 text-white shadow-sm" : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"}`}
            >
              {d} hari
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <h2 className="font-semibold text-slate-800 mb-5">Omzet Harian</h2>
        {revenue.length === 0 ? (
          <p className="text-slate-400 text-sm py-8 text-center">Belum ada data</p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={revenue}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip {...tooltipStyle} formatter={(v) => [formatRupiah(Number(v)), "Omzet"]} />
              <Bar dataKey="revenue" fill="#6366f1" radius={[6, 6, 0, 0]} name="Omzet" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <h2 className="font-semibold text-slate-800 mb-5">Jumlah Transaksi Harian</h2>
        {revenue.length === 0 ? (
          <p className="text-slate-400 text-sm py-8 text-center">Belum ada data</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={revenue}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} axisLine={false} tickLine={false} />
              <Tooltip {...tooltipStyle} />
              <Line type="monotone" dataKey="transactions" stroke="#10b981" strokeWidth={2.5} dot={false} name="Transaksi" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <h2 className="font-semibold text-slate-800 mb-5">Top 10 Pembeli</h2>
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
                  <p className="text-xs text-slate-400">{b.total_purchases} transaksi</p>
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
