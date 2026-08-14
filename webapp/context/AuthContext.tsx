"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { useRouter } from "next/navigation"
import { apiFetch, setAuthToken, clearAuthToken, getAuthToken } from "@/lib/api"

interface Admin {
  admin_id: number
  username: string
}

interface AuthContextType {
  admin: Admin | null
  loading: boolean
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({ admin: null, loading: true, logout: async () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<Admin | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      setLoading(false)
      return
    }
    apiFetch<Admin>("/auth/me")
      .then(setAdmin)
      .catch(() => {
        clearAuthToken()
        setAdmin(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const logout = async () => {
    clearAuthToken()
    setAdmin(null)
    router.push("/login")
  }

  return <AuthContext.Provider value={{ admin, loading, logout }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
