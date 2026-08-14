"use client"

import { useEffect, useState, useRef } from "react"
import { apiFetch, formatRupiah } from "@/lib/api"
import { ShieldAlert, Users, RefreshCw, Gift, Share2 } from "lucide-react"

interface Setting { key: string; value: string }
interface QueueStatus {
  max_concurrent: number; active: number; queued: number
  active_users: number[]; queued_users: number[]
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Setting[]>([])
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null)
  const [error, setError] = useState("")
  const [saving, setSaving] = useState<string | null>(null)
  const [saved, setSaved] = useState<string | null>(null)
  const [msgValue, setMsgValue] = useState("")
  const [maxConcurrent, setMaxConcurrent] = useState("0")
  const [bonusBase, setBonusBase] = useState("500")
  const [bonusStep, setBonusStep] = useState("500")
  const [bonusMaxStreak, setBonusMaxStreak] = useState("7")
  const [referralBonus, setReferralBonus] = useState("2000")
  const pollRef = useRef<NodeJS.Timeout | null>(null)

  const load = () => {
    apiFetch<Setting[]>("/settings").then((data) => {
      setSettings(data)
      setMsgValue(data.find(s => s.key === "maintenance_message")?.value ?? "")
      setMaxConcurrent(data.find(s => s.key === "max_concurrent_users")?.value ?? "0")
      setBonusBase(data.find(s => s.key === "daily_bonus_base")?.value ?? "500")
      setBonusStep(data.find(s => s.key === "daily_bonus_step")?.value ?? "500")
      setBonusMaxStreak(data.find(s => s.key === "daily_bonus_max_streak")?.value ?? "7")
      setReferralBonus(data.find(s => s.key === "referral_bonus")?.value ?? "2000")
    }).catch(e => setError(e.message))
  }

  const loadQueueStatus = () => apiFetch<QueueStatus>("/settings/queue/status").then(setQueueStatus).catch(() => {})

  useEffect(() => {
    load(); loadQueueStatus()
    pollRef.current = setInterval(loadQueueStatus, 3000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const getValue = (key: string) => settings.find(s => s.key === key)?.value ?? ""

  const save = async (key: string, value: string) => {
    setSaving(key)
    try {
      await apiFetch(`/settings/${key}`, { method: "PUT", body: JSON.stringify({ value }) })
      setSaved(key); setTimeout(() => setSaved(null), 2000); load()
    } finally { setSaving(null) }
  }

  const isMaintenanceOn = getValue("maintenance_mode") === "on"

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Pengaturan Bot</h1>
        <p className="text-sm text-slate-500 mt-0.5">Konfigurasi perilaku bot Telegram</p>
      </div>

      {error && <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>}

      {/* Maintenance */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm divide-y divide-slate-50">
        <div className="px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className={`p-2 rounded-xl mt-0.5 ${isMaintenanceOn ? "bg-amber-50" : "bg-slate-50"}`}>
                <ShieldAlert size={16} className={isMaintenanceOn ? "text-amber-500" : "text-slate-400"} />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-800">Mode Maintenance</p>
                <p className="text-xs text-slate-400 mt-0.5">Nonaktifkan bot sementara untuk semua pengguna</p>
                {isMaintenanceOn && <span className="inline-flex items-center text-xs font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full mt-1.5">Sedang aktif</span>}
              </div>
            </div>
            <button onClick={() => save("maintenance_mode", isMaintenanceOn ? "off" : "on")} disabled={saving === "maintenance_mode"}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 disabled:opacity-60 ${isMaintenanceOn ? "bg-amber-500" : "bg-slate-200"}`}>
              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${isMaintenanceOn ? "translate-x-6" : "translate-x-1"}`} />
            </button>
          </div>
        </div>
        <div className="px-6 py-5">
          <p className="text-sm font-semibold text-slate-800 mb-1">Pesan Maintenance</p>
          <p className="text-xs text-slate-400 mb-3">Pesan yang ditampilkan ke user saat maintenance aktif.</p>
          <textarea value={msgValue} onChange={e => setMsgValue(e.target.value)} rows={3}
            placeholder="Contoh: Server sedang update, kembali dalam 1 jam..."
            className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition resize-none" />
          <div className="flex items-center gap-3 mt-2">
            <button onClick={() => save("maintenance_message", msgValue)} disabled={saving === "maintenance_message"}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-4 py-2 rounded-lg disabled:opacity-60">
              {saving === "maintenance_message" ? "Menyimpan..." : "Simpan Pesan"}
            </button>
            {saved === "maintenance_message" && <span className="text-xs text-emerald-600 font-medium">Tersimpan ✓</span>}
          </div>
        </div>
      </div>

      {/* Concurrency Queue */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm">
        <div className="px-6 py-5 border-b border-slate-50">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-xl bg-indigo-50 mt-0.5">
              <Users size={16} className="text-indigo-500" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-800">Maks. User Bersamaan</p>
              <p className="text-xs text-slate-400 mt-0.5 mb-4">Batasi berapa user yang bisa aktif di bot secara bersamaan. Set 0 untuk tidak dibatasi.</p>
              <div className="flex items-center gap-3">
                <input type="number" min="0" max="100" value={maxConcurrent} onChange={e => setMaxConcurrent(e.target.value)}
                  className="w-24 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500" />
                <button onClick={() => save("max_concurrent_users", maxConcurrent)} disabled={saving === "max_concurrent_users"}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-4 py-2.5 rounded-xl disabled:opacity-60">
                  {saving === "max_concurrent_users" ? "Menyimpan..." : "Simpan"}
                </button>
                {saved === "max_concurrent_users" && <span className="text-xs text-emerald-600 font-medium">Tersimpan ✓</span>}
              </div>
            </div>
          </div>
        </div>
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Status Antrian (live)</p>
            <button onClick={loadQueueStatus} className="text-slate-400 hover:text-slate-600"><RefreshCw size={13} /></button>
          </div>
          {queueStatus ? (
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-slate-800">{queueStatus.max_concurrent === 0 ? "∞" : queueStatus.max_concurrent}</p>
                <p className="text-xs text-slate-400 mt-0.5">Maks. slot</p>
              </div>
              <div className="bg-emerald-50 rounded-xl p-3 text-center">
                <p className="text-2xl font-bold text-emerald-700">{queueStatus.active}</p>
                <p className="text-xs text-emerald-500 mt-0.5">Aktif sekarang</p>
              </div>
              <div className={`rounded-xl p-3 text-center ${queueStatus.queued > 0 ? "bg-amber-50" : "bg-slate-50"}`}>
                <p className={`text-2xl font-bold ${queueStatus.queued > 0 ? "text-amber-700" : "text-slate-400"}`}>{queueStatus.queued}</p>
                <p className={`text-xs mt-0.5 ${queueStatus.queued > 0 ? "text-amber-500" : "text-slate-400"}`}>Antrian</p>
              </div>
            </div>
          ) : <p className="text-xs text-slate-400">Memuat status...</p>}
        </div>
      </div>

      {/* Bonus Harian */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <div className="flex items-start gap-3 mb-5">
          <div className="p-2 rounded-xl bg-amber-50 mt-0.5"><Gift size={16} className="text-amber-500" /></div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Bonus Harian</p>
            <p className="text-xs text-slate-400 mt-0.5">Bonus = Base + (Step x (streak-1)), maksimal di streak tertentu.</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-5">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Base (Rp) <span className="text-slate-400 font-normal">— hari ke-1</span></label>
            <input type="number" min="0" step="100" value={bonusBase} onChange={e => setBonusBase(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Step (Rp) <span className="text-slate-400 font-normal">— kenaikan/hari</span></label>
            <input type="number" min="0" step="100" value={bonusStep} onChange={e => setBonusStep(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Max Streak <span className="text-slate-400 font-normal">— cap hari</span></label>
            <input type="number" min="1" max="30" value={bonusMaxStreak} onChange={e => setBonusMaxStreak(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
        </div>
        <div className="bg-slate-50 rounded-xl p-4 mb-4">
          <p className="text-xs font-semibold text-slate-600 mb-3 uppercase tracking-wide">Preview Bonus per Hari</p>
          <div className="grid grid-cols-4 gap-2">
            {Array.from({ length: Math.min(parseInt(bonusMaxStreak) || 7, 8) }, (_, i) => {
              const streak = i + 1
              const base = parseInt(bonusBase) || 0
              const step = parseInt(bonusStep) || 0
              const maxS = parseInt(bonusMaxStreak) || 7
              const effective = Math.min(streak, maxS)
              const amount = base + step * (effective - 1)
              return (
                <div key={streak} className={`rounded-xl p-2.5 text-center ${streak === parseInt(bonusMaxStreak) ? "bg-amber-50 border border-amber-100" : "bg-white border border-slate-100"}`}>
                  <p className="text-xs text-slate-400 mb-0.5">Hari {streak}{streak === parseInt(bonusMaxStreak) ? " 🔥" : ""}</p>
                  <p className="text-sm font-bold text-slate-800">{formatRupiah(amount)}</p>
                </div>
              )
            })}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={async () => {
            setSaving("bonus")
            try {
              await Promise.all([
                apiFetch("/settings/daily_bonus_base", { method: "PUT", body: JSON.stringify({ value: bonusBase }) }),
                apiFetch("/settings/daily_bonus_step", { method: "PUT", body: JSON.stringify({ value: bonusStep }) }),
                apiFetch("/settings/daily_bonus_max_streak", { method: "PUT", body: JSON.stringify({ value: bonusMaxStreak }) }),
              ])
              setSaved("bonus"); setTimeout(() => setSaved(null), 2000); load()
            } finally { setSaving(null) }
          }} disabled={saving === "bonus"} className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-4 py-2.5 rounded-xl disabled:opacity-60">
            {saving === "bonus" ? "Menyimpan..." : "Simpan Konfigurasi Bonus"}
          </button>
          {saved === "bonus" && <span className="text-xs text-emerald-600 font-medium">Tersimpan ✓</span>}
        </div>
      </div>

      {/* Referral */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <div className="flex items-start gap-3 mb-5">
          <div className="p-2 rounded-xl bg-emerald-50 mt-0.5"><Share2 size={16} className="text-emerald-500" /></div>
          <div>
            <p className="text-sm font-semibold text-slate-800">Program Referral</p>
            <p className="text-xs text-slate-400 mt-0.5">
              User yang mengajak teman mendapat bonus saat teman melakukan pembelian pertama. Gunakan <code className="bg-slate-100 px-1 rounded">/ref</code> untuk link.
            </p>
          </div>
        </div>
        <div className="flex items-end gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1.5">Bonus per Referral (Rp)</label>
            <input type="number" min="0" step="500" value={referralBonus} onChange={e => setReferralBonus(e.target.value)}
              className="w-36 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          </div>
          <div className="flex items-center gap-3 pb-0.5">
            <button onClick={() => save("referral_bonus", referralBonus)} disabled={saving === "referral_bonus"}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-4 py-2.5 rounded-xl disabled:opacity-60">
              {saving === "referral_bonus" ? "Menyimpan..." : "Simpan"}
            </button>
            {saved === "referral_bonus" && <span className="text-xs text-emerald-600 font-medium">Tersimpan ✓</span>}
          </div>
        </div>
        <p className="text-xs text-slate-400 mt-3">Set ke 0 untuk menonaktifkan program referral.</p>
      </div>

      {/* All settings */}
      {settings.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <h2 className="font-semibold text-slate-800 mb-4">Semua Setting</h2>
          <div className="space-y-2">
            {settings.map(s => (
              <div key={s.key} className="flex items-center gap-3 bg-slate-50 rounded-xl px-4 py-3">
                <code className="text-xs font-mono text-indigo-600 flex-shrink-0">{s.key}</code>
                <span className="text-slate-300">·</span>
                <span className="text-sm text-slate-600 truncate">{s.value || <span className="text-slate-300 italic">kosong</span>}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}