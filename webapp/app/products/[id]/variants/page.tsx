"use client"

import { useEffect, useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { apiFetch, formatRupiah } from "@/lib/api"
import type { Product, Variant } from "@/lib/types"
import { Plus, Pencil, Trash2, ArrowLeft, Package } from "lucide-react"
import Modal from "@/components/Modal"
import StockSourcePicker from "@/components/StockSourcePicker"

interface VariantForm {
  name: string
  price: string
  custom_id: string
  stock_source: string
  stock_config: string
}

const EMPTY_FORM: VariantForm = { name: "", price: "", custom_id: "", stock_source: "database", stock_config: "" }

export default function VariantsPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [product, setProduct] = useState<Product | null>(null)
  const [variants, setVariants] = useState<Variant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [editTarget, setEditTarget] = useState<Variant | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<VariantForm>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([
      apiFetch<Product>(`/products/${id}`),
      apiFetch<Variant[]>(`/products/${id}/variants`),
    ])
      .then(([p, v]) => { setProduct(p); setVariants(v) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [id])

  const openAdd = () => { setForm(EMPTY_FORM); setShowAdd(true) }
  const openEdit = (v: Variant) => {
    setForm({ name: v.name, price: String(v.price), custom_id: v.custom_id, stock_source: v.stock_source || "database", stock_config: v.stock_config || "" })
    setEditTarget(v)
  }
  const closeModal = () => { setShowAdd(false); setEditTarget(null) }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const payload = { name: form.name, price: parseInt(form.price) || 0, custom_id: form.custom_id, stock_source: form.stock_source, stock_config: form.stock_config }
    try {
      if (editTarget) {
        await apiFetch(`/products/${id}/variants/${editTarget.variant_id}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        })
      } else {
        await apiFetch(`/products/${id}/variants`, {
          method: "POST",
          body: JSON.stringify(payload),
        })
      }
      closeModal()
      load()
    } finally {
      setSaving(false)
    }
  }

  const deleteVariant = async (variantId: number) => {
    if (!confirm("Hapus varian ini?")) return
    await apiFetch(`/products/${id}/variants/${variantId}`, { method: "DELETE" })
    load()
  }

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <button onClick={() => router.push("/products")} className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors">
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <h1 className="text-xl font-bold text-slate-900">
            Varian — {product?.name ?? "..."}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">{variants.length} varian terdaftar</p>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors shadow-sm">
          <Plus size={15} /> Tambah Varian
        </button>
      </div>

      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Nama Varian</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Harga</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Stok</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Custom ID</th>
                <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {variants.map((v) => (
                <tr key={v.variant_id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 bg-indigo-50 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Package size={13} className="text-indigo-400" />
                      </div>
                      <span className="font-medium text-slate-800">{v.name}</span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right font-semibold text-slate-800">{formatRupiah(v.price)}</td>
                  <td className="px-5 py-4 text-right">
                    <span className={`text-sm font-medium ${v.available_stock === 0 ? "text-red-500" : "text-emerald-600"}`}>
                      {v.available_stock}
                    </span>
                  </td>
                  <td className="px-5 py-4 font-mono text-xs text-slate-400">{v.custom_id || "—"}</td>
                  <td className="px-5 py-4">
                    <div className="flex items-center justify-center gap-1.5">
                      <button onClick={() => openEdit(v)} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Edit">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => deleteVariant(v.variant_id)} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Hapus">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {variants.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <Package size={32} className="text-slate-200 mx-auto mb-2" />
                    <p className="text-slate-400 text-sm">Belum ada varian</p>
                    <button onClick={openAdd} className="mt-3 text-indigo-600 text-sm font-medium hover:underline">
                      Tambah varian pertama
                    </button>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {(showAdd || editTarget) && (
        <Modal title={editTarget ? "Edit Varian" : "Tambah Varian"} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Nama Varian</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                placeholder="Contoh: 30 Hari, 1 Bulan, dll"
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Harga (Rp)</label>
              <input
                type="number"
                value={form.price}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                required
                min="0"
                placeholder="0"
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Custom ID (opsional)</label>
              <input
                value={form.custom_id}
                onChange={(e) => setForm({ ...form, custom_id: e.target.value })}
                placeholder="Custom ID"
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
              />
            </div>
            <StockSourcePicker
              source={form.stock_source}
              config={form.stock_config}
              onChange={(s, c) => setForm({ ...form, stock_source: s, stock_config: c })}
            />
            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl transition-colors disabled:opacity-60">
                {saving ? "Menyimpan..." : editTarget ? "Simpan Perubahan" : "Tambah Varian"}
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
