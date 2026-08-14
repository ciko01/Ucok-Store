"use client"

import { useEffect, useState } from "react"
import { apiFetch } from "@/lib/api"
import { Crown, Pencil, Check, X, UserCheck, UserPlus } from "lucide-react"
import Modal from "@/components/Modal"

interface Tier {
  tier_id: number
  name: string
  duration_days: number
  discount_percent: number
  bonus_multiplier: number
  skip_queue: boolean
  badge: string
}

interface UserMembership {
  user_id: number
  full_name: string
  username: string | null
  tier_name: string
  badge: string
  discount_percent: number
  bonus_multiplier: number
  skip_queue: boolean
  activated_at: string
  expires_at: string | null
  is_active: boolean
}

interface User {
  user_id: number
  full_name: string
  username: string | null
}

const TIER_COLORS: Record<string, string> = {
  Free:   "bg-slate-100 text-slate-600",
  Bronze: "bg-orange-100 text-orange-700",
  Silver: "bg-slate-100 text-slate-700",
  Gold:   "bg-amber-100 text-amber-700",
  Admin:  "bg-purple-100 text-purple-700",
}

export default function MembershipPage() {
  const [tiers, setTiers] = useState<Tier[]>([])
  const [members, setMembers] = useState<UserMembership[]>([])
  const [allUsers, setAllUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [editTier, setEditTier] = useState<Tier | null>(null)
  const [tierForm, setTierForm] = useState({ duration_days: 0, discount_percent: 0, bonus_multiplier: 1, skip_queue: false, badge: "" })
  const [saving, setSaving] = useState(false)
  const [setMemberModal, setSetMemberModal] = useState<{ user_id: number; full_name: string } | null>(null)
  const [addMemberModal, setAddMemberModal] = useState(false)
  const [selectedTier, setSelectedTier] = useState("Bronze")
  const [searchUser, setSearchUser] = useState("")
  const [searchNewUser, setSearchNewUser] = useState("")
  const [selectedNewUser, setSelectedNewUser] = useState<User | null>(null)

  const load = () => {
    setLoading(true)
    Promise.all([
      apiFetch<Tier[]>("/membership/tiers"),
      apiFetch<UserMembership[]>("/membership/users"),
      apiFetch<User[]>("/users?limit=500"),
    ])
      .then(([t, m, u]) => { setTiers(t); setMembers(m); setAllUsers(u) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const openEditTier = (t: Tier) => {
    setEditTier(t)
    setTierForm({ duration_days: t.duration_days, discount_percent: t.discount_percent, bonus_multiplier: t.bonus_multiplier, skip_queue: t.skip_queue, badge: t.badge })
  }

  const saveTier = async () => {
    if (!editTier) return
    setSaving(true)
    try {
      await apiFetch(`/membership/tiers/${editTier.tier_id}`, { method: "PATCH", body: JSON.stringify(tierForm) })
      setEditTier(null)
      load()
    } finally { setSaving(false) }
  }

  const activateMembership = async () => {
    if (!setMemberModal) return
    setSaving(true)
    try {
      await apiFetch(`/membership/users/${setMemberModal.user_id}`, { method: "POST", body: JSON.stringify({ tier_name: selectedTier }) })
      setSetMemberModal(null)
      load()
    } finally { setSaving(false) }
  }

  const activateNewMember = async () => {
    if (!selectedNewUser) return
    setSaving(true)
    try {
      await apiFetch(`/membership/users/${selectedNewUser.user_id}`, { method: "POST", body: JSON.stringify({ tier_name: selectedTier }) })
      setAddMemberModal(false)
      setSelectedNewUser(null)
      setSearchNewUser("")
      load()
    } finally { setSaving(false) }
  }

  const filteredMembers = members.filter(m =>
    m.full_name.toLowerCase().includes(searchUser.toLowerCase()) ||
    (m.username || "").toLowerCase().includes(searchUser.toLowerCase()) ||
    String(m.user_id).includes(searchUser)
  )

  if (error) return <div className="bg-red-50 border border-red-100 text-red-600 rounded-2xl p-4 text-sm">{error}</div>

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Membership</h1>
        <p className="text-sm text-slate-500 mt-0.5">Kelola tier membership dan aktifkan untuk pengguna</p>
      </div>

      {/* Tabel tier */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Crown size={16} className="text-amber-500" />
            <h2 className="font-semibold text-slate-800">Konfigurasi Tier</h2>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Tier</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Durasi</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Diskon</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Bonus ×</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Skip Queue</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Edit</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {tiers.map((t) => (
              <tr key={t.tier_id} className="hover:bg-slate-50/50">
                <td className="px-5 py-3.5">
                  <span className={`inline-flex items-center gap-1.5 text-sm font-semibold px-3 py-1 rounded-full ${TIER_COLORS[t.name] || "bg-slate-100 text-slate-600"}`}>
                    {t.badge} {t.name}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-center text-slate-600">
                  {t.duration_days === 0 ? "Selamanya" : `${t.duration_days} hari`}
                </td>
                <td className="px-5 py-3.5 text-center font-medium text-emerald-600">
                  {t.discount_percent > 0 ? `${t.discount_percent}%` : "—"}
                </td>
                <td className="px-5 py-3.5 text-center font-medium text-indigo-600">
                  {t.bonus_multiplier > 1 ? `×${t.bonus_multiplier}` : "—"}
                </td>
                <td className="px-5 py-3.5 text-center">
                  {t.skip_queue ? <Check size={16} className="text-emerald-500 mx-auto" /> : <X size={16} className="text-slate-300 mx-auto" />}
                </td>
                <td className="px-5 py-3.5 text-center">
                  <button onClick={() => openEditTier(t)} className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors">
                    <Pencil size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Member aktif */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <UserCheck size={16} className="text-indigo-500" />
            <h2 className="font-semibold text-slate-800">Member Aktif</h2>
            <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">{members.length}</span>
          </div>
          <div className="flex items-center gap-2">
            <input
              value={searchUser}
              onChange={(e) => setSearchUser(e.target.value)}
              placeholder="Cari nama / username / ID..."
              className="border border-slate-200 rounded-xl px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-48"
            />
            <button
              onClick={() => { setAddMemberModal(true); setSelectedTier("Bronze"); setSearchNewUser(""); setSelectedNewUser(null) }}
              className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-3 py-2 rounded-xl transition-colors flex-shrink-0"
            >
              <UserPlus size={13} /> Tambah Member
            </button>
          </div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">User</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Tier</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Berlaku Hingga</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Status</th>
              <th className="px-5 py-3 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Ubah Tier</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {loading ? (
              <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-400 text-sm">Memuat...</td></tr>
            ) : filteredMembers.length === 0 ? (
              <tr><td colSpan={5} className="px-5 py-8 text-center text-slate-400 text-sm">Belum ada member</td></tr>
            ) : filteredMembers.map((m) => (
              <tr key={m.user_id} className="hover:bg-slate-50/50">
                <td className="px-5 py-3.5">
                  <p className="font-medium text-slate-800">{m.full_name}</p>
                  <p className="text-xs text-slate-400">{m.username ? `@${m.username}` : `ID: ${m.user_id}`}</p>
                </td>
                <td className="px-5 py-3.5 text-center">
                  <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${TIER_COLORS[m.tier_name] || "bg-slate-100 text-slate-600"}`}>
                    {m.badge} {m.tier_name}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-slate-600 text-xs">
                  {m.expires_at ? m.expires_at.slice(0, 10) : "Selamanya"}
                </td>
                <td className="px-5 py-3.5 text-center">
                  {m.is_active
                    ? <span className="text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Aktif</span>
                    : <span className="text-xs font-medium text-red-500 bg-red-50 px-2 py-0.5 rounded-full">Expired</span>}
                </td>
                <td className="px-5 py-3.5 text-center">
                  <button
                    onClick={() => { setSetMemberModal({ user_id: m.user_id, full_name: m.full_name }); setSelectedTier(m.tier_name) }}
                    className="text-xs font-medium text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
                  >
                    Ubah
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Edit tier modal */}
      {editTier && (
        <Modal title={`Edit Tier — ${editTier.badge} ${editTier.name}`} onClose={() => setEditTier(null)}>
          <div className="space-y-4">
            <p className="text-xs text-slate-400 bg-slate-50 rounded-xl px-3 py-2">
              Perubahan durasi berlaku untuk aktivasi berikutnya. Perubahan benefit berlaku untuk semua member tier ini.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Durasi (hari) <span className="text-slate-400 font-normal">— 0 = Selamanya</span></label>
                <input type="number" min="0"
                  value={tierForm.duration_days}
                  onChange={(e) => setTierForm({ ...tierForm, duration_days: parseInt(e.target.value) || 0 })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Diskon (%)</label>
                <input type="number" min="0" max="100"
                  value={tierForm.discount_percent}
                  onChange={(e) => setTierForm({ ...tierForm, discount_percent: parseInt(e.target.value) || 0 })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Multiplier Bonus (×)</label>
                <input type="number" min="1" max="10" step="0.5"
                  value={tierForm.bonus_multiplier}
                  onChange={(e) => setTierForm({ ...tierForm, bonus_multiplier: parseFloat(e.target.value) || 1 })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center font-semibold focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Badge (emoji)</label>
                <input
                  value={tierForm.badge}
                  onChange={(e) => setTierForm({ ...tierForm, badge: e.target.value })}
                  className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm text-center text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex flex-col justify-center">
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Skip Queue</label>
                <button
                  type="button"
                  onClick={() => setTierForm({ ...tierForm, skip_queue: !tierForm.skip_queue })}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${tierForm.skip_queue ? "bg-indigo-600" : "bg-slate-200"}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${tierForm.skip_queue ? "translate-x-6" : "translate-x-1"}`} />
                </button>
              </div>
            </div>
            <div className="flex gap-3 pt-1">
              <button onClick={saveTier} disabled={saving} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl disabled:opacity-60">
                {saving ? "Menyimpan..." : "Simpan"}
              </button>
              <button onClick={() => setEditTier(null)} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl">
                Batal
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Set member modal */}
      {setMemberModal && (
        <Modal title={`Aktifkan Membership — ${setMemberModal.full_name}`} onClose={() => setSetMemberModal(null)}>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-2">Pilih Tier</label>
              <div className="grid grid-cols-2 gap-2">
                {tiers.map((t) => (
                  <button
                    key={t.tier_id}
                    type="button"
                    onClick={() => setSelectedTier(t.name)}
                    className={`flex flex-col items-center gap-1 p-3 rounded-xl border transition-all ${
                      selectedTier === t.name
                        ? "border-indigo-500 bg-indigo-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <span className="text-xl">{t.badge}</span>
                    <span className="text-sm font-semibold text-slate-800">{t.name}</span>
                    <span className="text-xs text-slate-400">{t.duration_days === 0 ? "Selamanya" : `${t.duration_days} hari`}</span>
                    {t.discount_percent > 0 && <span className="text-xs text-emerald-600">Diskon {t.discount_percent}%</span>}
                  </button>
                ))}
              </div>
            </div>
            <p className="text-xs text-slate-400 bg-slate-50 rounded-xl px-3 py-2">
              User akan mendapat notifikasi Telegram saat membership diaktifkan.
            </p>
            <div className="flex gap-3">
              <button onClick={activateMembership} disabled={saving} className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl disabled:opacity-60">
                {saving ? "Mengaktifkan..." : "Aktifkan"}
              </button>
              <button onClick={() => setSetMemberModal(null)} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl">
                Batal
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Tambah Member Modal */}
      {addMemberModal && (
        <Modal title="Tambah Member Baru" onClose={() => setAddMemberModal(false)}>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Cari Pengguna</label>
              <input
                value={searchNewUser}
                onChange={(e) => setSearchNewUser(e.target.value)}
                placeholder="Nama, username, atau ID..."
                className="w-full border border-slate-200 rounded-xl px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                autoFocus
              />
              {searchNewUser.length > 1 && (
                <div className="mt-2 max-h-40 overflow-y-auto border border-slate-200 rounded-xl divide-y divide-slate-50">
                  {allUsers
                    .filter(u =>
                      u.full_name.toLowerCase().includes(searchNewUser.toLowerCase()) ||
                      (u.username || "").toLowerCase().includes(searchNewUser.toLowerCase()) ||
                      String(u.user_id).includes(searchNewUser)
                    )
                    .slice(0, 10)
                    .map(u => (
                      <button
                        key={u.user_id}
                        onClick={() => { setSelectedNewUser(u); setSearchNewUser(u.full_name) }}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-slate-50 transition-colors ${selectedNewUser?.user_id === u.user_id ? "bg-indigo-50" : ""}`}
                      >
                        <div className="w-7 h-7 bg-indigo-50 rounded-lg flex items-center justify-center flex-shrink-0">
                          <span className="text-xs font-bold text-indigo-600">{u.full_name[0]}</span>
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{u.full_name}</p>
                          <p className="text-xs text-slate-400">{u.username ? `@${u.username}` : `ID: ${u.user_id}`}</p>
                        </div>
                      </button>
                    ))}
                </div>
              )}
              {selectedNewUser && (
                <div className="mt-2 flex items-center gap-2 bg-indigo-50 rounded-xl px-3 py-2">
                  <Check size={14} className="text-indigo-600" />
                  <span className="text-sm text-indigo-700 font-medium">Dipilih: {selectedNewUser.full_name}</span>
                  <button onClick={() => { setSelectedNewUser(null); setSearchNewUser("") }} className="ml-auto text-indigo-400 hover:text-indigo-600">
                    <X size={13} />
                  </button>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-2">Pilih Tier</label>
              <div className="grid grid-cols-2 gap-2">
                {tiers.map((t) => (
                  <button key={t.tier_id} type="button" onClick={() => setSelectedTier(t.name)}
                    className={`flex flex-col items-center gap-1 p-3 rounded-xl border transition-all ${selectedTier === t.name ? "border-indigo-500 bg-indigo-50" : "border-slate-200 hover:border-slate-300"}`}
                  >
                    <span className="text-xl">{t.badge}</span>
                    <span className="text-sm font-semibold text-slate-800">{t.name}</span>
                    <span className="text-xs text-slate-400">{t.duration_days === 0 ? "Selamanya" : `${t.duration_days} hari`}</span>
                    {t.discount_percent > 0 && <span className="text-xs text-emerald-600">Diskon {t.discount_percent}%</span>}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-xs text-slate-400 bg-slate-50 rounded-xl px-3 py-2">
              User akan mendapat notifikasi Telegram saat membership diaktifkan.
            </p>
            <div className="flex gap-3">
              <button onClick={activateNewMember} disabled={saving || !selectedNewUser}
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium py-2.5 rounded-xl disabled:opacity-60">
                {saving ? "Mengaktifkan..." : "Aktifkan Membership"}
              </button>
              <button onClick={() => setAddMemberModal(false)} className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2.5 rounded-xl">
                Batal
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
