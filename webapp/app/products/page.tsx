"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch, formatRupiah } from "@/lib/api"
import type { Product } from "@/lib/types"
import { Trash2, ToggleLeft, ToggleRight, Package, Plus, Pencil, Layers } from "lucide-react"
import Modal from "@/components/Modal"
import Link from "next/link"
import StockSourcePicker from "@/components/StockSourcePicker"

interface ProductForm {
  name: string
  category: string
  price: string
  description: string
  custom_id: string
  stock_source: string
  stock_config: string
}

const EMPTY_FORM: ProductForm = { name: "", category: "otomatis", price: "", description: "", custom_id: "", stock_source: "database", stock_config: "" }

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [editTarget, setEditTarget] = useState<Product | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState<ProductForm>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const [newProductId, setNewProductId] = useState<number | null>(null)
  const router = useRouter()

  const load = () => {
    setLoading(true)
    apiFetch<Product[]>("/products")
      .then(setProducts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openAdd = () => { setForm(EMPTY_FORM); setShowAdd(true) }
  const openEdit = (p: Product) => {
    setForm({ name: p.name, category: p.category, price: String(p.price), description: p.description, custom_id: p.custom_id, stock_source: p.stock_source || "database", stock_config: p.stock_config || "" })
    setEditTarget(p)
  }
  const closeModal = () => { setShowAdd(false); setEditTarget(null) }

  const toggleActive = async (p: Product) => {
    await apiFetch(`/products/${p.product_id}`, { method: "PATCH", body: JSON.stringify({ is_active: !p.is_active }) })
    load()
  }

  const deleteProduct = async (id: number) => {
    if (!confirm("Hapus produk ini?")) return
    await apiFetch(`/products/${id}`, { method: "DELETE" })
    load()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    const payload = { ...form, price: parseInt(form.price) || 0 }
    try {
      if (editTarget) {
        await apiFetch(`/products/${editTarget.product_id}`, { method: "PATCH", body: JSON.stringify(payload) })
        closeModal()
        load()
      } else {
        const created = await apiFetch<{ product_id: number }>("/products", { method: "POST", body: JSON.stringify(payload) })
        closeModal()
        load()
        setNewProductId(created.product_id)
      }
    } finally {
      setSaving(false)
    }
  }

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Produk</h1>
          <p className="text-sm text-slate-500 mt-0.5">Kelola semua produk toko</p>
        </div>
        <button onClick={openAdd} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2.5 rounded-xl transition-colors shadow-sm">
          <Plus size={15} /> Tambah Produk
        </button>
      </div>

      {newProductId && (
        <div className="bg-indigo-50 border border-indigo-100 rounded-2xl px-5 py-4 flex items-center justify-between">
          <p className="text-sm text-indigo-700 font-medium">Produk berhasil dibuat. Mau tambah varian?</p>
          <div className="flex gap-2">
            <Link href={`/products/${newProductId}/variants`} className="bg-indigo-600 text-white text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-indigo-700 transition-colors">
              Kelola Varian
            </Link>
            <button onClick={() => setNewProductId(null)} className="text-indigo-400 hover:text-indigo-600 text-xs px-2">
              Nanti
            </button>
          </div>
        </div>
      )}
      {loading ? (
        <div className="text-slate-400 text-sm">Memuat...</div>
      ) : (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Produk</th>
                <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Kategori</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Harga</th>
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Stok</th>
                <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {products.map((p) => (
                <tr key={p.product_id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Package size={14} className="text-slate-400" />
                      </div>
                      <div>
                        <p className="font-medium text-slate-800">{p.name}</p>
                        {p.description && <p className="text-xs text-slate-400 truncate max-w-xs">{p.description}</p>}
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`inline-flex items-center text-xs font-medium px-2.5 py-1 rounded-full ${p.category === "otomatis" ? "bg-emerald-50 text-emerald-700" : "bg-blue-50 text-blue-700"}`}>
                      {p.category}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-right font-semibold text-slate-800">{formatRupiah(p.price)}</td>
                  <td className="px-5 py-4 text-right">
                    <span className={`text-sm font-medium ${p.available_stock === 0 && p.category === "otomatis" ? "text-red-500" : "text-slate-700"}`}>
                      {p.has_variants ? "—" : p.available_stock}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-center">
                    <button onClick={() => toggleActive(p)}>
                      {p.is_active ? <ToggleRight size={22} className="text-emerald-500" /> : <ToggleLeft size={22} className="text-slate-300" />}
                    </button>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex items-center justify-center gap-1.5">
                      <Link href={`/products/${p.product_id}/variants`} className="p-1.5 text-slate-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors" title="Kelola Varian">
                        <Layers size={14} />
                      </Link>
                      <button onClick={() => openEdit(p)} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors" title="Edit">
                        <Pencil size={14} />
                      </button>
                      <button onClick={() => deleteProduct(p.product_id)} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Hapus">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {products.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-12 text-center text-slate-400 text-sm">Belum ada produk</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {(showAdd || editTarget) && (
        <Modal title={editTarget ? "Edit Produk" : "Tambah Produk"} onClose={closeModal}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Nama Produk</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required placeholder="Nama produk" className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Kategori</label>
                <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition bg-white">
                  <option value="otomatis">Otomatis</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Harga (Rp)</label>
                <input type="number" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required placeholder="0" min="0" className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition" />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Deskripsi</label>
              <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} placeholder="Deskripsi produk (opsional)" className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Custom ID</label>
              <input value={form.custom_id} onChange={(e) => setForm({ ...form, custom_id: e.target.value })} placeholder="Custom ID (opsional)" className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition" />
            </div>
            <StockSourcePicker
              source={form.stock_source}
              config={form.stock_config}
              onChange={(s, c) => setForm({ ...form, stock_source: s, stock_config: c })}
            />
            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl transition-colors disabled:opacity-60">
                {saving ? "Menyimpan..." : editTarget ? "Simpan Perubahan" : "Tambah Produk"}
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
