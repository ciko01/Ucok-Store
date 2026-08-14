"use client"

import { useEffect, useState } from "react"
import { apiFetch } from "@/lib/api"
import { Database, FileText, FolderOpen, ChevronDown } from "lucide-react"

interface StokFile {
  filename: string
  lines: number
  size_bytes: number
}

interface StokFolder {
  foldername: string
  file_count: number
}

interface Props {
  source: string
  config: string
  onChange: (source: string, config: string) => void
}

const SOURCE_OPTIONS = [
  {
    value: "database",
    label: "Database",
    description: "Stok dari database (upload via bot/webapp)",
    icon: Database,
  },
  {
    value: "file_lines",
    label: "Baris File",
    description: "Setiap baris file = 1 item stok (dikonsumsi per pembelian)",
    icon: FileText,
  },
  {
    value: "folder_files",
    label: "Isi Folder",
    description: "Setiap file di folder = 1 item stok (file dipindah setelah dibeli)",
    icon: FolderOpen,
  },
]

export default function StockSourcePicker({ source, config, onChange }: Props) {
  const [files, setFiles] = useState<StokFile[]>([])
  const [folders, setFolders] = useState<StokFolder[]>([])
  const [preview, setPreview] = useState<string[] | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)

  useEffect(() => {
    if (source === "file_lines") {
      apiFetch<StokFile[]>("/stok/files").then(setFiles).catch(() => {})
    } else if (source === "folder_files") {
      apiFetch<StokFolder[]>("/stok/folders").then(setFolders).catch(() => {})
    }
  }, [source])

  useEffect(() => {
    if (source === "file_lines" && config) {
      setLoadingPreview(true)
      apiFetch<{ preview: string[]; total_lines: number }>(`/stok/files/${encodeURIComponent(config)}/preview?limit=3`)
        .then((r) => setPreview(r.preview))
        .catch(() => setPreview(null))
        .finally(() => setLoadingPreview(false))
    } else {
      setPreview(null)
    }
  }, [source, config])

  const selectedFile = files.find((f) => f.filename === config)
  const selectedFolder = folders.find((f) => f.foldername === config)

  return (
    <div className="space-y-3">
      <label className="block text-xs font-medium text-slate-600">Sumber Stok</label>
      <div className="grid grid-cols-3 gap-2">
        {SOURCE_OPTIONS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value, "")}
            className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-center transition-all ${
              source === value
                ? "border-indigo-500 bg-indigo-50 text-indigo-700"
                : "border-slate-200 hover:border-slate-300 text-slate-600"
            }`}
          >
            <Icon size={16} className={source === value ? "text-indigo-600" : "text-slate-400"} />
            <span className="text-xs font-medium leading-tight">{label}</span>
          </button>
        ))}
      </div>

      <p className="text-xs text-slate-400">
        {SOURCE_OPTIONS.find((o) => o.value === source)?.description}
      </p>

      {source === "file_lines" && (
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">
            Pilih File dari <code className="bg-slate-100 px-1 rounded">/stok</code>
          </label>
          {files.length === 0 ? (
            <p className="text-xs text-amber-600 bg-amber-50 rounded-xl px-3 py-2">
              Belum ada file di folder /stok. Tambahkan file .txt terlebih dahulu.
            </p>
          ) : (
            <div className="relative">
              <select
                value={config}
                onChange={(e) => onChange(source, e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition bg-white appearance-none pr-8"
              >
                <option value="">-- Pilih file --</option>
                {files.map((f) => (
                  <option key={f.filename} value={f.filename}>
                    {f.filename} — {f.lines} baris
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          )}
          {config && selectedFile && (
            <div className="mt-2 bg-slate-50 rounded-xl px-3 py-2.5 text-xs space-y-1">
              <p className="text-slate-500">
                <span className="font-semibold text-slate-700">{selectedFile.lines}</span> baris tersisa
              </p>
              {loadingPreview ? (
                <p className="text-slate-400">Memuat preview...</p>
              ) : preview && preview.length > 0 ? (
                <div>
                  <p className="text-slate-400 mb-1">Preview:</p>
                  {preview.map((line, i) => (
                    <p key={i} className="font-mono text-slate-600 truncate">{line}</p>
                  ))}
                  {selectedFile.lines > 3 && (
                    <p className="text-slate-400 mt-1">...dan {selectedFile.lines - 3} baris lainnya</p>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}

      {source === "folder_files" && (
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1.5">
            Pilih Subfolder dari <code className="bg-slate-100 px-1 rounded">/stok</code>
          </label>
          {folders.length === 0 ? (
            <p className="text-xs text-amber-600 bg-amber-50 rounded-xl px-3 py-2">
              Belum ada subfolder di /stok. Buat subfolder dan isi dengan file stok.
            </p>
          ) : (
            <div className="relative">
              <select
                value={config}
                onChange={(e) => onChange(source, e.target.value)}
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition bg-white appearance-none pr-8"
              >
                <option value="">-- Pilih folder --</option>
                {folders.map((f) => (
                  <option key={f.foldername} value={f.foldername}>
                    {f.foldername} — {f.file_count} file
                  </option>
                ))}
              </select>
              <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            </div>
          )}
          {config && selectedFolder && (
            <div className="mt-2 bg-slate-50 rounded-xl px-3 py-2.5 text-xs">
              <p className="text-slate-500">
                <span className="font-semibold text-slate-700">{selectedFolder.file_count}</span> file tersedia di folder ini
              </p>
              <p className="text-slate-400 mt-0.5">File akan dipindah ke subfolder <code>used/</code> setelah dibeli</p>
            </div>
          )}
        </div>
      )}

      {source === "database" && (
        <p className="text-xs text-slate-400 bg-slate-50 rounded-xl px-3 py-2">
          Stok dikelola dari database — upload via bot atau halaman stok.
        </p>
      )}
    </div>
  )
}
