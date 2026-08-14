"use client"

import { useState } from "react"
import { apiFetch } from "@/lib/api"
import { Send, Users, CheckCircle, XCircle, Megaphone } from "lucide-react"

interface BroadcastResult {
  total: number
  success: number
  failed: number
}

const TEMPLATES = [
  { label: "Promo", text: "🎉 <b>PROMO SPESIAL!</b>\n\nDapatkan penawaran terbaik hari ini.\nCek katalog produk kami sekarang! 🛒" },
  { label: "Maintenance", text: "🛠️ <b>Pemberitahuan Maintenance</b>\n\nBot akan mengalami gangguan sementara untuk pemeliharaan sistem.\nMohon maaf atas ketidaknyamanannya. ⏳" },
  { label: "Stok Baru", text: "📦 <b>Stok Baru Tersedia!</b>\n\nProduk baru telah ditambahkan ke toko kami.\nSegera cek sebelum kehabisan! 🔥" },
]

export default function BroadcastPage() {
  const [message, setMessage] = useState("")
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState<BroadcastResult | null>(null)
  const [error, setError] = useState("")
  const [preview, setPreview] = useState(false)

  const send = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return
    if (!confirm(`Kirim pesan ini ke SEMUA pengguna?`)) return
    setSending(true)
    setResult(null)
    setError("")
    try {
      const res = await apiFetch<BroadcastResult>("/broadcast", {
        method: "POST",
        body: JSON.stringify({ message, parse_mode: "HTML" }),
      })
      setResult(res)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Broadcast</h1>
        <p className="text-sm text-slate-500 mt-0.5">Kirim pesan ke semua pengguna bot</p>
      </div>

      {result && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5">
          <p className="text-sm font-semibold text-slate-800 mb-3">Hasil Broadcast</p>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-slate-50 rounded-xl p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <Users size={14} className="text-slate-400" />
                <span className="text-xs text-slate-500 font-medium">Total</span>
              </div>
              <p className="text-2xl font-bold text-slate-800">{result.total}</p>
            </div>
            <div className="bg-emerald-50 rounded-xl p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <CheckCircle size={14} className="text-emerald-500" />
                <span className="text-xs text-emerald-600 font-medium">Berhasil</span>
              </div>
              <p className="text-2xl font-bold text-emerald-700">{result.success}</p>
            </div>
            <div className="bg-red-50 rounded-xl p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1">
                <XCircle size={14} className="text-red-400" />
                <span className="text-xs text-red-500 font-medium">Gagal</span>
              </div>
              <p className="text-2xl font-bold text-red-600">{result.failed}</p>
            </div>
          </div>
          {result.failed > 0 && (
            <p className="text-xs text-slate-400 mt-3">Gagal biasanya karena user memblokir bot atau akun tidak aktif.</p>
          )}
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>
      )}

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
        <div className="mb-4">
          <p className="text-sm font-semibold text-slate-700 mb-2">Template Cepat</p>
          <div className="flex flex-wrap gap-2">
            {TEMPLATES.map((t) => (
              <button
                key={t.label}
                onClick={() => setMessage(t.text)}
                className="text-xs font-medium px-3 py-1.5 bg-slate-100 hover:bg-indigo-50 hover:text-indigo-700 text-slate-600 rounded-lg transition-colors"
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={send} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-slate-600">Pesan (support HTML Telegram)</label>
              <button
                type="button"
                onClick={() => setPreview(!preview)}
                className="text-xs text-indigo-600 hover:underline"
              >
                {preview ? "Edit" : "Preview"}
              </button>
            </div>
            {preview ? (
              <div
                className="w-full min-h-[160px] border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 bg-slate-50 whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ __html: message.replace(/\n/g, "<br>") }}
              />
            ) : (
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
                rows={7}
                placeholder={"Tulis pesan broadcast...\n\nSupport HTML Telegram:\n<b>tebal</b>, <i>miring</i>, <code>kode</code>"}
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none font-mono"
              />
            )}
            <p className="text-xs text-slate-400 mt-1.5">{message.length} karakter</p>
          </div>

          <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 text-xs text-amber-700">
            ⚠️ Pesan akan dikirim ke <b>semua pengguna</b> yang pernah menggunakan bot. Pastikan isi pesan sudah benar sebelum mengirim.
          </div>

          <button
            type="submit"
            disabled={sending || !message.trim()}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 rounded-xl text-sm transition-colors disabled:opacity-60 shadow-sm"
          >
            {sending ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Mengirim...
              </>
            ) : (
              <>
                <Send size={15} />
                Kirim Broadcast
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
