"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { apiFetch, getAuthToken, getDownloadUrl } from "@/lib/api"
import {
  Folder, FileText, Upload, Trash2, Download,
  RefreshCw, ChevronRight, Home, Scissors, Copy, ClipboardPaste,
  FilePlus, FolderPlus, Pencil, X, PackageOpen, Package,
} from "lucide-react"
import ContextMenu, { ContextMenuItem } from "@/components/ContextMenu"

interface Entry { name: string; path: string; is_dir: boolean; size: number | null; modified: number }
interface Clipboard { paths: string[]; operation: "copy" | "cut" }
interface CtxState { x: number; y: number; entry: Entry }

function formatSize(b: number | null) {
  if (b === null) return "—"
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b/1024).toFixed(1)} KB`
  return `${(b/1048576).toFixed(1)} MB`
}
function formatDate(ts: number) {
  return new Date(ts*1000).toLocaleString("id-ID",{dateStyle:"short",timeStyle:"short"})
}

export default function FileManagerPage() {
  const [currentPath, setCurrentPath] = useState("")
  const [entries, setEntries] = useState<Entry[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [clipboard, setClipboard] = useState<Clipboard | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [modal, setModal] = useState<null|"create-file"|"create-folder"|"rename"|"zip"|"unzip"|"edit-file">(null)
  const [modalInput, setModalInput] = useState("")
  const [fileContent, setFileContent] = useState("")
  const [editingPath, setEditingPath] = useState("")
  const [uploadDrag, setUploadDrag] = useState(false)
  const [ctx, setCtx] = useState<CtxState | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const load = useCallback((path: string) => {
    setLoading(true); setError(""); setSelected(new Set())
    apiFetch<{path:string;entries:Entry[]}>(`/filemanager/list?path=${encodeURIComponent(path)}`)
      .then((r)=>{setEntries(r.entries);setCurrentPath(r.path)})
      .catch((e)=>setError(e.message))
      .finally(()=>setLoading(false))
  },[])

  useEffect(()=>{load("")},[load])

  const breadcrumbs = currentPath ? currentPath.split("/").filter(Boolean) : []

  const toggleSelect = (path: string, e: React.MouseEvent) => {
    e.stopPropagation()
    const next = new Set(selected)
    next.has(path) ? next.delete(path) : next.add(path)
    setSelected(next)
  }
  const selectAll = () => setSelected(selected.size===entries.length ? new Set() : new Set(entries.map(e=>e.path)))

  const handleDelete = async (paths?: string[]) => {
    const targets = paths ?? [...selected]
    if (!targets.length) return
    if (!confirm(`Hapus ${targets.length} item?`)) return
    await apiFetch("/filemanager/delete",{method:"POST",body:JSON.stringify({paths:targets})})
    load(currentPath)
  }

  const handleUpload = async (files: FileList | null) => {
    if (!files||!files.length) return
    const fd = new FormData()
    fd.append("path", currentPath)
    for (const f of Array.from(files)) fd.append("files", f)
    const token = getAuthToken()
    await fetch(`/api/proxy/filemanager/upload`, {
      method: "POST",
      headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: fd,
    })
    load(currentPath)
  }

  const handleDownload = (path: string) => {
    window.open(getDownloadUrl(path), "_blank")
  }

  const handleCreate = async () => {
    if (!modalInput.trim()) return
    await apiFetch("/filemanager/create",{method:"POST",body:JSON.stringify({path:currentPath,name:modalInput.trim(),kind:modal==="create-folder"?"folder":"file"})})
    setModal(null);setModalInput("");load(currentPath)
  }
  const handleRename = async () => {
    if (!modalInput.trim()||!editingPath) return
    await apiFetch("/filemanager/rename",{method:"POST",body:JSON.stringify({path:editingPath,new_name:modalInput.trim()})})
    setModal(null);setModalInput("");setEditingPath("");load(currentPath)
  }
  const handleCopy = (op:"copy"|"cut", paths?: string[]) => {
    const targets = paths ?? [...selected]
    if (!targets.length) return
    setClipboard({paths:targets,operation:op});setSelected(new Set())
  }
  const handlePaste = async () => {
    if (!clipboard) return
    await apiFetch("/filemanager/copy-move",{method:"POST",body:JSON.stringify({sources:clipboard.paths,destination:currentPath,operation:clipboard.operation==="cut"?"move":"copy"})})
    if (clipboard.operation==="cut") setClipboard(null)
    load(currentPath)
  }
  const handleZip = async () => {
    if (!modalInput.trim()) return
    const paths = selected.size ? [...selected] : entries.map(e=>e.path)
    await apiFetch("/filemanager/zip",{method:"POST",body:JSON.stringify({paths,zip_name:modalInput.trim(),destination:currentPath})})
    setModal(null);setModalInput("");load(currentPath)
  }
  const handleUnzip = async () => {
    if (!editingPath) return
    await apiFetch("/filemanager/unzip",{method:"POST",body:JSON.stringify({path:editingPath,destination:modalInput.trim()||currentPath})})
    setModal(null);setModalInput("");setEditingPath("");load(currentPath)
  }
  const handleEditFile = async () => {
    await apiFetch("/filemanager/write",{method:"POST",body:JSON.stringify({path:editingPath,content:fileContent})})
    setModal(null);setEditingPath("");setFileContent("");load(currentPath)
  }
  const openEditFile = async (entry: Entry) => {
    try {
      const r = await apiFetch<{content:string}>(`/filemanager/read?path=${encodeURIComponent(entry.path)}`)
      setFileContent(r.content);setEditingPath(entry.path);setModal("edit-file")
    } catch { alert("File tidak bisa diedit sebagai teks") }
  }

  const openCtx = (e: React.MouseEvent, entry: Entry) => {
    e.preventDefault();e.stopPropagation()
    if (!selected.has(entry.path)) setSelected(new Set([entry.path]))
    setCtx({x:e.clientX,y:e.clientY,entry})
  }

  const buildCtxItems = (entry: Entry): ContextMenuItem[] => {
    const isZip = entry.name.endsWith(".zip")
    const multi = selected.size > 1 && selected.has(entry.path)
    const targets = multi ? [...selected] : [entry.path]
    const items: ContextMenuItem[] = []

    if (entry.is_dir) {
      items.push({label:"Buka Folder",icon:Folder,onClick:()=>load(entry.path)})
    } else {
      items.push({label:"Edit File",icon:Pencil,onClick:()=>openEditFile(entry)})
    }
    items.push({label:"Download",icon:Download,onClick:()=>handleDownload(entry.path)})
    items.push({label:"Copy",icon:Copy,onClick:()=>handleCopy("copy",targets),divider:true})
    items.push({label:"Cut",icon:Scissors,onClick:()=>handleCopy("cut",targets)})
    if (clipboard) items.push({label:`Paste (${clipboard.paths.length})`,icon:ClipboardPaste,onClick:handlePaste})
    items.push({label:"Rename",icon:Pencil,divider:true,disabled:multi,onClick:()=>{setEditingPath(entry.path);setModalInput(entry.name);setModal("rename")}})
    items.push({label:multi?`Zip ${selected.size} item`:"Zip",icon:Package,onClick:()=>{setModal("zip");setModalInput("")}})
    if (isZip) items.push({label:"Unzip",icon:PackageOpen,onClick:()=>{setEditingPath(entry.path);setModalInput("");setModal("unzip")}})
    items.push({label:multi?`Hapus ${selected.size} item`:"Hapus",icon:Trash2,danger:true,divider:true,onClick:()=>handleDelete(targets)})
    return items
  }

  const btn = "flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-xl transition-colors"

  return (
    <div className="space-y-4 max-w-6xl" onClick={()=>setCtx(null)}>
      {ctx && <ContextMenu x={ctx.x} y={ctx.y} items={buildCtxItems(ctx.entry)} onClose={()=>setCtx(null)} />}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">File Manager</h1>
          <p className="text-sm text-slate-500 mt-0.5">Folder: /stok</p>
        </div>
        <button onClick={()=>load(currentPath)} className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl">
          <RefreshCw size={16}/>
        </button>
      </div>

      <div className="flex items-center gap-1 text-sm flex-wrap">
        <button onClick={()=>load("")} className="flex items-center gap-1 text-indigo-600 hover:underline font-medium">
          <Home size={14}/> stok
        </button>
        {breadcrumbs.map((crumb,i)=>{
          const path = breadcrumbs.slice(0,i+1).join("/")
          return <span key={path} className="flex items-center gap-1"><ChevronRight size={13} className="text-slate-300"/><button onClick={()=>load(path)} className="text-indigo-600 hover:underline">{crumb}</button></span>
        })}
      </div>

      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-3 flex items-center gap-2 flex-wrap">
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={e=>handleUpload(e.target.files)}/>
        <button onClick={()=>fileInputRef.current?.click()} className={`${btn} bg-indigo-600 text-white hover:bg-indigo-700`}><Upload size={13}/> Upload</button>
        <button onClick={()=>{setModal("create-folder");setModalInput("")}} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50`}><FolderPlus size={13}/> Folder</button>
        <button onClick={()=>{setModal("create-file");setModalInput("")}} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50`}><FilePlus size={13}/> File</button>
        <div className="w-px h-6 bg-slate-200"/>
        <button onClick={()=>handleCopy("copy")} disabled={!selected.size} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40`}><Copy size={13}/> Copy</button>
        <button onClick={()=>handleCopy("cut")} disabled={!selected.size} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40`}><Scissors size={13}/> Cut</button>
        <button onClick={handlePaste} disabled={!clipboard} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 disabled:opacity-40`}>
          <ClipboardPaste size={13}/> Paste {clipboard&&<span className="ml-1 bg-indigo-100 text-indigo-600 px-1 rounded-full text-xs">{clipboard.paths.length}</span>}
        </button>
        <div className="w-px h-6 bg-slate-200"/>
        <button onClick={()=>{setModal("zip");setModalInput("")}} className={`${btn} bg-white border border-slate-200 text-slate-700 hover:bg-slate-50`}><Package size={13}/> Zip</button>
        <div className="w-px h-6 bg-slate-200"/>
        <button onClick={()=>handleDelete()} disabled={!selected.size} className={`${btn} bg-white border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-40`}><Trash2 size={13}/> Hapus {selected.size>0&&`(${selected.size})`}</button>
        {selected.size>0&&<button onClick={()=>setSelected(new Set())} className="text-xs text-slate-400 hover:text-slate-600 ml-auto">Batal pilih</button>}
      </div>

      {clipboard&&(
        <div className="bg-amber-50 border border-amber-100 rounded-xl px-4 py-2.5 flex items-center justify-between text-xs">
          <span className="text-amber-700 font-medium">{clipboard.operation==="cut"?"✂️ Cut":"📋 Copy"}: {clipboard.paths.length} item</span>
          <button onClick={()=>setClipboard(null)} className="text-amber-400 hover:text-amber-600"><X size={14}/></button>
        </div>
      )}

      {error&&<div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>}

      <div
        className={`bg-white rounded-2xl border shadow-sm overflow-hidden transition-colors ${uploadDrag?"border-indigo-400 bg-indigo-50/50":"border-slate-100"}`}
        onDragOver={e=>{e.preventDefault();setUploadDrag(true)}}
        onDragLeave={()=>setUploadDrag(false)}
        onDrop={e=>{e.preventDefault();setUploadDrag(false);handleUpload(e.dataTransfer.files)}}
      >
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-4 py-3 w-8"><input type="checkbox" checked={selected.size===entries.length&&entries.length>0} onChange={selectAll} className="rounded"/></th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Nama</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Ukuran</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Diubah</th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Aksi</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading&&<tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400 text-sm">Memuat...</td></tr>}
            {!loading&&entries.length===0&&(
              <tr><td colSpan={5} className="px-4 py-12 text-center">
                <Upload size={28} className="text-slate-200 mx-auto mb-2"/>
                <p className="text-slate-400 text-sm">Folder kosong — drag & drop atau klik Upload</p>
              </td></tr>
            )}
            {entries.map(entry=>(
              <tr
                key={entry.path}
                className={`hover:bg-slate-50/50 transition-colors cursor-pointer select-none ${selected.has(entry.path)?"bg-indigo-50/60":""}`}
                onClick={e=>{if((e.target as HTMLElement).closest("button,input"))return;if(entry.is_dir)load(entry.path)}}
                onContextMenu={e=>openCtx(e,entry)}
              >
                <td className="px-4 py-3" onClick={e=>toggleSelect(entry.path,e)}>
                  <input type="checkbox" checked={selected.has(entry.path)} readOnly className="rounded pointer-events-none"/>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    {entry.is_dir?<Folder size={16} className="text-amber-400 flex-shrink-0"/>:<FileText size={16} className="text-slate-400 flex-shrink-0"/>}
                    <span className={`font-medium truncate max-w-xs ${entry.is_dir?"text-slate-800":"text-slate-700"}`}>{entry.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-right text-slate-400 text-xs">{formatSize(entry.size)}</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(entry.modified)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-1">
                    {!entry.is_dir&&<button onClick={()=>openEditFile(entry)} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg" title="Edit"><Pencil size={13}/></button>}
                    {entry.name.endsWith(".zip")&&<button onClick={()=>{setEditingPath(entry.path);setModalInput("");setModal("unzip")}} className="p-1.5 text-slate-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg" title="Unzip"><PackageOpen size={13}/></button>}
                    <button onClick={()=>{setEditingPath(entry.path);setModalInput(entry.name);setModal("rename")}} className="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg" title="Rename"><Pencil size={13}/></button>
                    <button onClick={()=>handleDownload(entry.path)} className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg" title="Download"><Download size={13}/></button>
                    <button onClick={()=>handleDelete([entry.path])} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg" title="Hapus"><Trash2 size={13}/></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-400 text-right">{entries.length} item · klik kanan untuk opsi · drag & drop untuk upload</p>

      {modal&&modal!=="edit-file"&&(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4" onClick={e=>{if(e.target===e.currentTarget)setModal(null)}}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm border border-slate-100">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800 text-sm">
                {modal==="create-folder"&&"Buat Folder"}{modal==="create-file"&&"Buat File"}{modal==="rename"&&"Rename"}{modal==="zip"&&"Zip"}{modal==="unzip"&&"Unzip"}
              </h2>
              <button onClick={()=>setModal(null)} className="text-slate-400 hover:text-slate-600"><X size={16}/></button>
            </div>
            <div className="px-6 py-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">
                  {modal==="zip"?"Nama file zip":modal==="unzip"?"Ekstrak ke (kosongkan = otomatis)":"Nama"}
                </label>
                <input
                  value={modalInput} onChange={e=>setModalInput(e.target.value)} autoFocus
                  placeholder={modal==="zip"?"archive.zip":modal==="unzip"?"nama folder tujuan...":"nama..."}
                  onKeyDown={e=>{if(e.key!=="Enter")return;modal==="rename"?handleRename():modal==="zip"?handleZip():modal==="unzip"?handleUnzip():handleCreate()}}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                {modal==="zip"&&<p className="text-xs text-slate-400 mt-1.5">{selected.size>0?`${selected.size} item dipilih akan di-zip`:"Semua item di folder ini akan di-zip"}</p>}
              </div>
              <div className="flex gap-3">
                <button onClick={modal==="rename"?handleRename:modal==="zip"?handleZip:modal==="unzip"?handleUnzip:handleCreate} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl">
                  {modal==="rename"?"Rename":modal==="zip"?"Zip":modal==="unzip"?"Ekstrak":"Buat"}
                </button>
                <button onClick={()=>setModal(null)} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl">Batal</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {modal==="edit-file"&&(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm p-4" onClick={e=>{if(e.target===e.currentTarget)setModal(null)}}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl border border-slate-100 flex flex-col max-h-[80vh]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-800 text-sm truncate">{editingPath}</h2>
              <button onClick={()=>setModal(null)} className="text-slate-400 hover:text-slate-600 ml-2 flex-shrink-0"><X size={16}/></button>
            </div>
            <div className="px-6 py-4 flex-1 overflow-auto">
              <textarea value={fileContent} onChange={e=>setFileContent(e.target.value)} className="w-full h-64 border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm font-mono text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"/>
              <p className="text-xs text-slate-400 mt-1">{fileContent.split("\n").length} baris · {fileContent.length} karakter</p>
            </div>
            <div className="px-6 py-4 border-t border-slate-100 flex gap-3">
              <button onClick={handleEditFile} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl">Simpan</button>
              <button onClick={()=>setModal(null)} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl">Batal</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
