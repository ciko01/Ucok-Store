"use client"

import { useEffect, useRef } from "react"
import {
  Pencil, Trash2, Download, Copy, Scissors, ClipboardPaste,
  Package, PackageOpen, FolderOpen, FileText, Eye,
} from "lucide-react"

export interface ContextMenuItem {
  label: string
  icon: React.ElementType
  onClick: () => void
  danger?: boolean
  disabled?: boolean
  divider?: boolean
}

interface Props {
  x: number
  y: number
  items: ContextMenuItem[]
  onClose: () => void
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent && e.key !== "Escape") return
      if (e instanceof MouseEvent && ref.current?.contains(e.target as Node)) return
      onClose()
    }
    document.addEventListener("mousedown", close)
    document.addEventListener("keydown", close)
    return () => {
      document.removeEventListener("mousedown", close)
      document.removeEventListener("keydown", close)
    }
  }, [onClose])

  useEffect(() => {
    if (!ref.current) return
    const menu = ref.current
    const rect = menu.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight
    if (rect.right > vw) menu.style.left = `${x - rect.width}px`
    if (rect.bottom > vh) menu.style.top = `${y - rect.height}px`
  }, [x, y])

  return (
    <div
      ref={ref}
      className="fixed z-[100] bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 min-w-[180px]"
      style={{ top: y, left: x }}
    >
      {items.map((item, i) => (
        <div key={i}>
          {item.divider && i > 0 && <div className="my-1 border-t border-slate-100" />}
          <button
            disabled={item.disabled}
            onClick={() => { item.onClick(); onClose() }}
            className={`w-full flex items-center gap-2.5 px-3.5 py-2 text-sm transition-colors text-left disabled:opacity-40 ${
              item.danger
                ? "text-red-600 hover:bg-red-50"
                : "text-slate-700 hover:bg-slate-50"
            }`}
          >
            <item.icon size={14} className={item.danger ? "text-red-500" : "text-slate-400"} />
            {item.label}
          </button>
        </div>
      ))}
    </div>
  )
}
