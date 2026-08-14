"use client"

import { useEffect, useState } from "react"
import { apiFetch, formatRupiah } from "@/lib/api"
import type { Product, Bank } from "@/lib/types"
import { Package, CreditCard, Tag } from "lucide-react"

export default function StorePage() {
  const [products, setProducts] = useState<Product[]>([])
  const [banks, setBanks] = useState<Bank[]>([])
  const [error, setError] = useState("")

  useEffect(() => {
    Promise.all([
      apiFetch<Product[]>("/products?active_only=true"),
      apiFetch<Bank[]>("/banks?active_only=true"),
    ])
      .then(([p, b]) => { setProducts(p); setBanks(b) })
      .catch((e) => setError(e.message))
  }, [])

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Toko</h1>
        <p className="text-sm text-slate-500 mt-0.5">Tampilan katalog produk aktif</p>
      </div>

      {banks.length > 0 && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard size={16} className="text-slate-400" />
            <h2 className="font-semibold text-slate-800">Rekening Pembayaran</h2>
          </div>
          <div className="flex flex-wrap gap-3">
            {banks.map((b) => (
              <div key={b.bank_id} className="border border-slate-100 bg-slate-50 rounded-xl px-4 py-3 text-sm">
                <p className="font-semibold text-indigo-600">{b.bank_name}</p>
                <p className="font-mono text-slate-700 mt-0.5">{b.account_number}</p>
                <p className="text-slate-500 text-xs">{b.account_holder}</p>
                {b.notes && <p className="text-slate-400 text-xs mt-1">{b.notes}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <div className="flex items-center gap-2 mb-4">
          <Tag size={16} className="text-slate-400" />
          <h2 className="font-semibold text-slate-800">Katalog Produk</h2>
          <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">{products.length} produk</span>
        </div>
        {products.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-100 py-12 text-center text-slate-400 text-sm">
            Belum ada produk aktif
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.map((p) => (
              <div key={p.product_id} className="bg-white rounded-2xl border border-slate-100 shadow-sm p-5 flex flex-col gap-3 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-slate-800 truncate">{p.name}</p>
                    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full mt-1 ${p.category === "otomatis" ? "bg-emerald-50 text-emerald-700" : "bg-blue-50 text-blue-700"}`}>
                      {p.category}
                    </span>
                  </div>
                  <div className="w-9 h-9 bg-slate-50 rounded-xl flex items-center justify-center flex-shrink-0 ml-3">
                    <Package size={16} className="text-slate-300" />
                  </div>
                </div>
                {p.description && <p className="text-xs text-slate-500 leading-relaxed">{p.description}</p>}
                <div className="flex items-center justify-between mt-auto pt-2 border-t border-slate-50">
                  <span className="font-bold text-indigo-600 text-base">{formatRupiah(p.price)}</span>
                  <span className={`text-xs font-medium ${p.available_stock === 0 && p.category === "otomatis" ? "text-red-500" : "text-emerald-600"}`}>
                    {p.has_variants ? "Ada varian" : p.category === "otomatis" ? `Stok: ${p.available_stock}` : "Manual"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
