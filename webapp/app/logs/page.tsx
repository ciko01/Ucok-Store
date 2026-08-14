"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatDate } from "@/lib/api"
import type { AdminLog } from "@/lib/types"
import { ScrollText } from "lucide-react"

export default function LogsPage() {
  const [logs, setLogs] = useState<AdminLog[]>([])
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<AdminLog[]>("/logs?limit=100")
      .then(setLogs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Log Admin</h1>
        <p className="text-sm text-slate-500 mt-0.5">Riwayat aktivitas admin bot</p>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Admin</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Detail</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Waktu</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {logs.map((l) => (
                <tr key={l.log_id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 bg-indigo-50 rounded-lg flex items-center justify-center">
                        <span className="text-xs font-bold text-indigo-600">{l.admin_name[0]?.toUpperCase()}</span>
                      </div>
                      <span className="font-medium text-slate-700">{l.admin_name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <span className="inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700">
                      {l.action}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-slate-500 max-w-xs truncate">{l.detail || "—"}</td>
                  <td className="px-5 py-4 text-slate-400 text-xs">{formatDate(l.created_at)}</td>
                </tr>
              ))}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-5 py-12 text-center">
                    <ScrollText size={32} className="text-slate-200 mx-auto mb-2" />
                    <p className="text-slate-400 text-sm">Belum ada log aktivitas</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
