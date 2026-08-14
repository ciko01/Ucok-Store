const PROXY = "/api/proxy"

export function getAuthToken(): string {
  if (typeof window === "undefined") return ""
  return localStorage.getItem("admin_token") || ""
}

export function setAuthToken(token: string): void {
  localStorage.setItem("admin_token", token)
}

export function clearAuthToken(): void {
  localStorage.removeItem("admin_token")
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAuthToken()
  const res = await fetch(`${PROXY}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || "Request gagal")
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export function getDownloadUrl(path: string): string {
  const token = getAuthToken()
  return `/api/proxy/filemanager/download?path=${encodeURIComponent(path)}${token ? `&_token=${encodeURIComponent(token)}` : ""}`
}

export function formatRupiah(amount: number): string {
  return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", minimumFractionDigits: 0 }).format(amount)
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString("id-ID", { dateStyle: "medium", timeStyle: "short" })
}
