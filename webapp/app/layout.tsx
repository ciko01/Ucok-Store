import type { Metadata } from "next"
import { Geist } from "next/font/google"
import "./globals.css"
import { AuthProvider } from "@/context/AuthContext"
import AppShell from "@/components/AppShell"

const geist = Geist({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Ucok Store — Admin",
  description: "Dashboard admin Ucok Store",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body className={`${geist.className} bg-slate-50 text-slate-900 antialiased`}>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  )
}
