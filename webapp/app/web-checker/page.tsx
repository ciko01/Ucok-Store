"use client"

import { useState } from "react"
import { ArrowLeft, Upload, Play, Download, AlertCircle } from "lucide-react"
import Link from "next/link"

interface CheckingResult {
  premium?: number
  premium_extra?: number
  standard?: number
  standard_with_ads?: number
  basic?: number
  mobile?: number
  free?: number
  broken?: number
  duplicate?: number
  invalid?: number
  checked?: number
  valid?: number
  on_hold?: number
  accounts?: ValidAccount[]
}

interface ValidAccount {
  plan: string
  category: string
  formatted: string
  cookie: string
  cookie_content: string
  info: {
    email?: string
    plan?: string
    country?: string
    member_since?: string
    next_billing?: string
    payment_method?: string
    card?: string
    phone?: string
    quality?: string
    max_streams?: number
    plan_price?: string
    extra_members?: number
    profiles?: number
  }
  nftoken?: {
    pc?: string
    mobile?: string
  }
}

export default function WebCheckerPage() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [isChecking, setIsChecking] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState<CheckingResult | null>(null)
  const [error, setError] = useState("")
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null)
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [sessionId, setSessionId] = useState<string>("")

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files
    if (files) {
      setUploadedFiles(Array.from(files))
      setError("")
    }
  }

  const handleStartChecking = async () => {
    if (uploadedFiles.length === 0) {
      setError("Silakan upload file cookie terlebih dahulu")
      return
    }

    setIsChecking(true)
    setProgress(0)
    setError("")

    try {
      const formData = new FormData()
      uploadedFiles.forEach(file => formData.append("files", file))

      // Call Web Checker service on port 8001
      const response = await fetch("http://localhost:8001/api/check", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Failed to upload file: ${response.statusText}`)
      }

      const data = await response.json()
      const newSessionId = data.session_id

      if (!newSessionId) {
        throw new Error("No session ID returned")
      }

      // Save session ID to state so handleStopChecking can use it
      setSessionId(newSessionId)

      // Connect to WebSocket on Web Checker service (port 8001)
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
      const websocket = new WebSocket(`${protocol}//localhost:8001/ws/${newSessionId}`)
      setWs(websocket)

      websocket.onopen = () => {
        console.log("WebSocket connected")
      }

      websocket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          console.log("WS Message:", message) // Debug log

          if (message.type === "progress") {
            const progressData = message.data
            const progressValue = progressData.percentage || 0  // Backend sends 'percentage' not 'progress'
            console.log("Progress update:", progressValue, progressData) // Debug log
            setProgress(progressValue)
            setResults((prev: CheckingResult | null) => ({
              ...prev,
              checked: progressData.checked,
              valid: progressData.valid,
              invalid: progressData.invalid,
              broken: progressData.broken,
              duplicate: progressData.duplicate,
            }))
          } else if (message.type === "valid_account") {
            // Handle valid account update - add to accounts array
            const account = message.data.account
            const category = message.data.category
            setResults((prev: CheckingResult | null) => {
              const accounts = prev?.accounts || []
              return {
                ...prev,
                [category]: ((prev?.[category as keyof CheckingResult] as number) || 0) + 1,
                accounts: [...accounts, { ...account, category }],
              }
            })
          } else if (message.type === "complete") {
            setProgress(100)
            setIsChecking(false)
            websocket.close()
            setWs(null)
          }
        } catch (e) {
          console.error("Failed to parse message:", e)
        }
      }

      websocket.onerror = (error) => {
        console.error("WebSocket error:", error)
        setError("Error connecting to WebSocket")
        setIsChecking(false)
      }

      websocket.onclose = () => {
        console.log("WebSocket closed")
        setWs(null)
      }
    } catch (err) {
      setError("Error checking cookies: " + (err as Error).message)
      setIsChecking(false)
    }
  }

  const handleStopChecking = async () => {
    console.log("🛑 Stop button clicked")
    console.log("Current sessionId:", sessionId)
    
    if (!sessionId) {
      console.error("❌ No sessionId available! Cannot stop.")
      setError("Cannot stop: No active session found")
      return
    }
    
    try {
      console.log(`Sending stop request to: http://localhost:8001/api/session/${sessionId}/stop`)
      
      // Call backend API to stop the checking session
      const response = await fetch(`http://localhost:8001/api/session/${sessionId}/stop`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      })
      
      console.log("Stop response status:", response.status)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error("Stop request failed:", errorText)
        throw new Error(`Failed to stop checking: ${response.statusText}`)
      }
      
      const result = await response.json()
      console.log("✅ Stop request successful:", result)
      console.log("Backend should stop processing now - check terminal logs")
    } catch (err) {
      console.error("❌ Error stopping checking:", err)
      setError("Failed to stop checking: " + (err as Error).message)
    }
    
    // Close WebSocket and update UI state
    if (ws) {
      ws.close()
      setWs(null)
    }
    setIsChecking(false)
    setError("Checking stopped by user")
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Link href="/" className="p-2 hover:bg-slate-200 rounded-lg transition-colors">
            <ArrowLeft size={20} className="text-slate-600" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Web Checker</h1>
            <p className="text-sm text-slate-500">Netflix Cookie Validator</p>
          </div>
        </div>

        {/* Main Content */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* Upload Section */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">1. Upload Cookie File</h2>
            <div className="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center hover:border-indigo-400 transition-colors cursor-pointer group">
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload size={40} className="mx-auto text-slate-400 group-hover:text-indigo-500 transition-colors mb-3" />
                <p className="text-sm font-medium text-slate-700 mb-1">
                  Drag & drop multiple cookie files atau klik untuk browse
                </p>
                <p className="text-xs text-slate-500">Format: .txt (Netscape), .json, atau .zip</p>
                <input
                  id="file-upload"
                  type="file"
                  onChange={handleFileUpload}
                  accept=".txt,.json,.zip"
                  multiple
                  className="hidden"
                />
              </label>
            </div>
            {uploadedFiles.length > 0 && (
              <div className="mt-3 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                <p className="text-sm text-indigo-900">✓ {uploadedFiles.length} file(s) uploaded</p>
                {uploadedFiles.map((file, idx) => (
                  <p key={idx} className="text-xs text-indigo-700 ml-2">• {file.name}</p>
                ))}
              </div>
            )}
          </div>

          {/* Start Checking */}
          <div className="mb-8">
            <h2 className="text-lg font-semibold text-slate-900 mb-4">2. Start Checking</h2>
            <div className="flex items-center gap-3">
              <button
                onClick={handleStartChecking}
                disabled={uploadedFiles.length === 0 || isChecking}
                className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition-colors"
              >
                <Play size={18} />
                {isChecking ? "Checking..." : "Start Checking"}
              </button>
              {isChecking && (
                <button
                  onClick={handleStopChecking}
                  className="flex items-center gap-2 px-6 py-3 bg-red-600 text-white font-medium rounded-xl hover:bg-red-700 transition-colors"
                >
                  <AlertCircle size={18} />
                  Stop Checking
                </button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          {isChecking && (
            <div className="mb-8">
              <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 to-indigo-600 transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Progress: {Math.round(progress)}%
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mb-8 p-4 bg-red-50 border border-red-200 rounded-xl flex items-start gap-3">
              <AlertCircle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Results */}
          {results && (
            <div className="mb-8">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">3. Results</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                <button
                  onClick={() => setExpandedCategory(expandedCategory === 'premium' ? null : 'premium')}
                  className={`bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-4 border border-purple-200 hover:shadow-md transition-all cursor-pointer text-left ${
                    expandedCategory === 'premium' ? 'ring-2 ring-purple-500' : ''
                  }`}
                >
                  <p className="text-xs text-purple-600 font-medium">Premium</p>
                  <p className="text-2xl font-bold text-purple-900">{results.premium || 0}</p>
                </button>
                <button
                  onClick={() => setExpandedCategory(expandedCategory === 'standard' ? null : 'standard')}
                  className={`bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-4 border border-blue-200 hover:shadow-md transition-all cursor-pointer text-left ${
                    expandedCategory === 'standard' ? 'ring-2 ring-blue-500' : ''
                  }`}
                >
                  <p className="text-xs text-blue-600 font-medium">Standard</p>
                  <p className="text-2xl font-bold text-blue-900">{results.standard || 0}</p>
                </button>
                <button
                  onClick={() => setExpandedCategory(expandedCategory === 'basic' ? null : 'basic')}
                  className={`bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-4 border border-green-200 hover:shadow-md transition-all cursor-pointer text-left ${
                    expandedCategory === 'basic' ? 'ring-2 ring-green-500' : ''
                  }`}
                >
                  <p className="text-xs text-green-600 font-medium">Basic</p>
                  <p className="text-2xl font-bold text-green-900">{results.basic || 0}</p>
                </button>
                <button
                  onClick={() => setExpandedCategory(expandedCategory === 'free' ? null : 'free')}
                  className={`bg-gradient-to-br from-amber-50 to-amber-100 rounded-lg p-4 border border-amber-200 hover:shadow-md transition-all cursor-pointer text-left ${
                    expandedCategory === 'free' ? 'ring-2 ring-amber-500' : ''
                  }`}
                >
                  <p className="text-xs text-amber-600 font-medium">Free</p>
                  <p className="text-2xl font-bold text-amber-900">{results.free || 0}</p>
                </button>
                <button
                  onClick={() => setExpandedCategory(expandedCategory === 'broken' ? null : 'broken')}
                  className={`bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-4 border border-red-200 hover:shadow-md transition-all cursor-pointer text-left ${
                    expandedCategory === 'broken' ? 'ring-2 ring-red-500' : ''
                  }`}
                >
                  <p className="text-xs text-red-600 font-medium">Broken</p>
                  <p className="text-2xl font-bold text-red-900">{results.broken || 0}</p>
                </button>
              </div>

              {/* Valid Accounts Detail */}
              {expandedCategory && results.accounts && results.accounts.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-md font-semibold text-slate-900 mb-3">
                    {expandedCategory.charAt(0).toUpperCase() + expandedCategory.slice(1)} Accounts (
                    {results.accounts.filter(acc => acc.category === expandedCategory || acc.category === `${expandedCategory}_extra`).length})
                  </h3>
                  <div className="space-y-4">
                    {results.accounts
                      .filter(acc => acc.category === expandedCategory || acc.category === `${expandedCategory}_extra`)
                      .map((account, idx) => (
                      <div key={idx} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <span className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                              account.category === 'premium' || account.category === 'premium_extra' ? 'bg-purple-100 text-purple-700' :
                              account.category === 'standard' ? 'bg-blue-100 text-blue-700' :
                              account.category === 'basic' ? 'bg-green-100 text-green-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {account.plan}
                            </span>
                          </div>
                          <span className="text-xs text-slate-500">Account #{idx + 1}</span>
                        </div>

                        {/* Account Details */}
                        <div className="mb-3">
                          <h4 className="text-sm font-semibold text-slate-700 mb-2">Account Details</h4>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            {account.info.email && (
                              <div className="col-span-2">
                                <span className="text-slate-500">Email:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.email}</span>
                              </div>
                            )}
                            {account.info.country && (
                              <div>
                                <span className="text-slate-500">Country:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.country}</span>
                              </div>
                            )}
                            {account.info.quality && (
                              <div>
                                <span className="text-slate-500">Quality:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.quality}</span>
                              </div>
                            )}
                            {account.info.max_streams && (
                              <div>
                                <span className="text-slate-500">Max Streams:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.max_streams}</span>
                              </div>
                            )}
                            {account.info.plan_price && (
                              <div>
                                <span className="text-slate-500">Price:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.plan_price}</span>
                              </div>
                            )}
                            {account.info.next_billing && (
                              <div className="col-span-2">
                                <span className="text-slate-500">Next Billing:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.next_billing}</span>
                              </div>
                            )}
                            {account.info.payment_method && (
                              <div className="col-span-2">
                                <span className="text-slate-500">Payment:</span>
                                <span className="ml-2 font-medium text-slate-900">{account.info.payment_method}</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Cookie */}
                        <div className="mb-3">
                          <h4 className="text-sm font-semibold text-slate-700 mb-2">Cookie</h4>
                          <div className="bg-slate-50 rounded p-2 border border-slate-200">
                            <pre className="text-xs text-slate-700 whitespace-pre-wrap break-all font-mono">
                              {account.cookie_content || account.cookie}
                            </pre>
                          </div>
                        </div>

                        {/* NFToken if available */}
                        {account.nftoken && (
                          <div>
                            <h4 className="text-sm font-semibold text-slate-700 mb-2">NFToken Login Links</h4>
                            <div className="space-y-2">
                              {account.nftoken.pc && (
                                <div className="flex items-center gap-2">
                                  <span className="text-slate-500 min-w-[80px]">🖥️ PC Login:</span>
                                  <a 
                                    href={account.nftoken.pc} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="flex-1 px-3 py-2 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-600 hover:bg-indigo-100 hover:text-indigo-800 transition-colors text-sm font-medium"
                                  >
                                    Open PC Login →
                                  </a>
                                </div>
                              )}
                              {account.nftoken.mobile && (
                                <div className="flex items-center gap-2">
                                  <span className="text-slate-500 min-w-[80px]">📱 Mobile Login:</span>
                                  <a 
                                    href={account.nftoken.mobile} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="flex-1 px-3 py-2 bg-indigo-50 border border-indigo-200 rounded-lg text-indigo-600 hover:bg-indigo-100 hover:text-indigo-800 transition-colors text-sm font-medium"
                                  >
                                    Open Mobile Login →
                                  </a>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Info Section */}
          <div className="mt-8 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <h3 className="font-medium text-slate-900 mb-2">Tentang Web Checker</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Web Checker adalah tool untuk memvalidasi dan mengklasifikasikan cookies Netflix secara batch. Upload file cookie Anda (format Netscape .txt atau JSON), dan sistem akan mengecek status setiap akun, kemudian mengelompokkan berdasarkan tipe subscription (Premium, Standard, Basic, Free, atau Broken).
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
