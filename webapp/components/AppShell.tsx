"use client"

import { usePathname, useRouter } from "next/navigation"
import { useEffect } from "react"
import Sidebar from "@/components/Sidebar"
import { useAuth } from "@/context/AuthContext"
import { getAuthToken } from "@/lib/api"

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const router = useRouter()
  const { loading } = useAuth()
  const isLogin = pathname === "/login"

  useEffect(() => {
    if (isLogin) return
    if (!loading && !getAuthToken()) {
      router.push("/login")
    }
  }, [loading, isLogin, router])

  if (isLogin) return <>{children}</>

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 p-6 overflow-auto">{children}</main>
      </div>
    </div>
  )
}
