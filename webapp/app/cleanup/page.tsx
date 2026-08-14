"use client";

import { useState, useEffect, useRef } from "react";
import { Trash2, CheckCircle2, XCircle, FolderTree, Loader2, ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function CleanupPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [progress, setProgress] = useState(0);
  const [stats, setStats] = useState({
    checked: 0,
    total: 0,
    valid: 0,
    dead: 0,
  });
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const startCleanup = async () => {
    try {
      setError("");
      setResult(null);
      setProgress(0);
      setStats({ checked: 0, total: 0, valid: 0, dead: 0 });

      const response = await fetch("http://localhost:8001/api/cleanup", {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to start cleanup");
      }

      const data = await response.json();
      const newSessionId = data.session_id;

      setSessionId(newSessionId);
      setIsRunning(true);
      setStats((prev) => ({ ...prev, total: data.total_cookies }));

      // Connect WebSocket
      const ws = new WebSocket(`ws://localhost:8001/ws/${newSessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected for cleanup");
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === "progress") {
          const pdata = message.data;
          setProgress(pdata.percentage);
          setStats({
            checked: pdata.checked,
            total: pdata.total,
            valid: pdata.valid,
            dead: pdata.dead,
          });
        } else if (message.type === "complete") {
          setResult(message.data);
          setIsRunning(false);
          setProgress(100);
          ws.close();
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setError("WebSocket connection error");
        setIsRunning(false);
      };

      ws.onclose = () => {
        console.log("WebSocket closed");
        setIsRunning(false);
      };
    } catch (err: any) {
      setError(err.message || "Failed to start cleanup");
      setIsRunning(false);
    }
  };

  const stopCleanup = async () => {
    if (!sessionId) return;

    try {
      await fetch(`http://localhost:8001/api/session/${sessionId}/stop`, {
        method: "POST",
      });

      if (wsRef.current) {
        wsRef.current.close();
      }

      setIsRunning(false);
    } catch (err: any) {
      setError(err.message || "Failed to stop cleanup");
    }
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Link href="/" className="p-2 hover:bg-slate-200 rounded-lg transition-colors">
            <ArrowLeft size={20} className="text-slate-600" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Cookie Cleanup</h1>
            <p className="text-sm text-slate-500">Validate dan organisir cookies Netflix</p>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <XCircle size={20} className="text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-900">Error</p>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-6">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-slate-900 mb-2">Cleanup Process</h2>
            <p className="text-sm text-slate-600">
              Cookies yang valid akan diorganisir ke: <code className="bg-slate-100 px-2 py-1 rounded text-xs">stok/netflix/{"{Country}/{Plan}/"}</code>
              <br />
              Cookies yang mati akan dihapus otomatis
            </p>
          </div>

          {!isRunning && !result && (
            <button
              onClick={startCleanup}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <Trash2 size={20} />
              Start Cleanup
            </button>
          )}

          {isRunning && (
            <div className="space-y-6">
              {/* Progress Bar */}
              <div>
                <div className="flex justify-between text-sm font-medium text-slate-700 mb-2">
                  <span>Progress</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-full transition-all duration-300 ease-out"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>

              {/* Stats Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <div className="text-sm text-slate-600 mb-1">Checked</div>
                  <div className="text-2xl font-bold text-slate-900">
                    {stats.checked}/{stats.total}
                  </div>
                </div>
                <div className="bg-green-50 rounded-xl p-4">
                  <div className="text-sm text-green-700 mb-1">Valid</div>
                  <div className="text-2xl font-bold text-green-600">{stats.valid}</div>
                </div>
                <div className="bg-red-50 rounded-xl p-4">
                  <div className="text-sm text-red-700 mb-1">Dead</div>
                  <div className="text-2xl font-bold text-red-600">{stats.dead}</div>
                </div>
                <div className="bg-slate-50 rounded-xl p-4">
                  <div className="text-sm text-slate-600 mb-1">Remaining</div>
                  <div className="text-2xl font-bold text-slate-900">{stats.total - stats.checked}</div>
                </div>
              </div>

              {/* Stop Button */}
              <button
                onClick={stopCleanup}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2"
              >
                <XCircle size={20} />
                Stop Cleanup
              </button>
            </div>
          )}

          {result && (
            <div className="space-y-6">
              {/* Success Alert */}
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-start gap-3">
                <CheckCircle2 size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-green-900">Cleanup selesai!</p>
                  <p className="text-sm text-green-700">Cookies berhasil divalidasi dan diorganisir</p>
                </div>
              </div>

              {/* Result Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-xl p-4">
                  <div className="text-sm text-slate-600 mb-1">Total Checked</div>
                  <div className="text-2xl font-bold text-slate-900">{result.total}</div>
                </div>
                <div className="bg-green-50 rounded-xl p-4">
                  <div className="text-sm text-green-700 mb-1">Valid (Organized)</div>
                  <div className="text-2xl font-bold text-green-600">{result.valid}</div>
                </div>
                <div className="bg-red-50 rounded-xl p-4">
                  <div className="text-sm text-red-700 mb-1">Dead (Deleted)</div>
                  <div className="text-2xl font-bold text-red-600">{result.dead}</div>
                </div>
                <div className="bg-blue-50 rounded-xl p-4">
                  <div className="text-sm text-blue-700 mb-1">Files Organized</div>
                  <div className="text-2xl font-bold text-blue-600">{result.organized}</div>
                </div>
              </div>

              {/* Folder Info */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-start gap-3">
                <FolderTree size={20} className="text-blue-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-blue-900">Cookies valid telah diorganisir ke:</p>
                  <code className="text-xs text-blue-700 bg-blue-100 px-2 py-1 rounded mt-1 inline-block">
                    stok/netflix/{"{Country}/{Plan}/"}
                  </code>
                </div>
              </div>

              {/* Run Again Button */}
              <button
                onClick={() => {
                  setResult(null);
                  setProgress(0);
                  setStats({ checked: 0, total: 0, valid: 0, dead: 0 });
                }}
                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-3 px-4 rounded-xl transition-colors"
              >
                Run Cleanup Again
              </button>
            </div>
          )}
        </div>

        {/* How It Works */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <h2 className="text-lg font-semibold text-slate-900 mb-4">How It Works</h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-indigo-600">1</span>
              </div>
              <p className="text-sm text-slate-700">Scan semua cookie files di <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">stok/netflix/</code></p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-indigo-600">2</span>
              </div>
              <p className="text-sm text-slate-700">Validate setiap cookie dengan Netflix API</p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-indigo-600">3</span>
              </div>
              <p className="text-sm text-slate-700">Extract Country dan Plan dari cookies yang valid</p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-indigo-600">4</span>
              </div>
              <p className="text-sm text-slate-700">Organisir ke folder: <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">stok/netflix/{"{Country}/{Plan}/"}</code></p>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-indigo-600">5</span>
              </div>
              <p className="text-sm text-slate-700">Hapus cookies yang mati dari folder input</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
