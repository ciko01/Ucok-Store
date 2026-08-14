"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useAuth } from "@/context/AuthContext"
import {
  LayoutDashboard, ShoppingBag, Users, ArrowUpCircle,
  Receipt, BarChart2, Landmark, Settings, ScrollText,
  Store, LogOut, ChevronRight, Megaphone, FolderOpen, Crown, Ticket, CheckCircle2, Trash2,
} from "lucide-react"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/store", label: "Toko", icon: Store },
  { href: "/products", label: "Produk", icon: ShoppingBag },
  { href: "/users", label: "Pengguna", icon: Users },
  { href: "/membership", label: "Membership", icon: Crown },
  { href: "/topup", label: "Top-up", icon: ArrowUpCircle },
  { href: "/vouchers", label: "Voucher", icon: Ticket },
  { href: "/transactions", label: "Transaksi", icon: Receipt },
  { href: "/stats", label: "Statistik", icon: BarChart2 },
  { href: "/banks", label: "Bank", icon: Landmark },
  { href: "/broadcast", label: "Broadcast", icon: Megaphone },
  { href: "/file-manager", label: "File Manager", icon: FolderOpen },
  { href: "/web-checker", label: "Web Checker", icon: CheckCircle2 },
  { href: "/cleanup", label: "Cookie Cleanup", icon: Trash2 },
  { href: "/logs", label: "Log Admin", icon: ScrollText },
  { href: "/settings", label: "Pengaturan", icon: Settings },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { admin, logout } = useAuth()

  return (
    <aside className="w-60 bg-white border-r border-slate-100 flex flex-col h-screen sticky top-0">
      <div className="px-5 py-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center flex-shrink-0">
            <ShoppingBag size={16} className="text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-900 text-sm leading-tight">Ucok Store</p>
            <p className="text-xs text-slate-400">Admin Panel</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon size={16} className={active ? "text-indigo-600" : "text-slate-400 group-hover:text-slate-600"} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={14} className="text-indigo-400" />}
            </Link>
          )
        })}
      </nav>

      {admin && (
        <div className="px-3 py-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-slate-50">
            <div className="w-7 h-7 bg-indigo-100 rounded-lg flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-bold text-indigo-600">{admin.username[0].toUpperCase()}</span>
            </div>
            <span className="text-sm font-medium text-slate-700 flex-1 truncate">{admin.username}</span>
            <button onClick={logout} className="text-slate-400 hover:text-red-500 transition-colors" title="Logout">
              <LogOut size={15} />
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}
