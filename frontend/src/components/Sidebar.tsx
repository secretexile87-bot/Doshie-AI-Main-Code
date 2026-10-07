import React, { useState, useMemo } from 'react'
import {
  Plus,
  MessageSquare,
  Sparkles,
  Terminal,
  Search,
  Trash2,
  Edit2,
  Download,
  X,
  Clock,
  Check,
  PanelLeftClose,
  Wrench,
  Shield,
  Eye,
} from 'lucide-react'
import type { ChatSession, AntigravitySummary, Profile } from '../types'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  activeTab: 'doshie' | 'antigravity'
  onTabChange: (tab: 'doshie' | 'antigravity') => void
  sessions: ChatSession[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onNewChat: () => void
  onDeleteSession: (id: string) => void
  onRenameSession: (id: string, newTitle: string) => void
  onExportSession: (session: ChatSession) => void
  antigravityList: AntigravitySummary[]
  activeAntigravityId: string | null
  onSelectAntigravity: (id: string) => void
  activeProfile: string
  isAdmin?: boolean
  oversightProfile?: string
  onSelectOversightProfile?: (profile: string) => void
  availableProfiles?: Profile[]
}

function formatRelativeTime(dateInput: number | string): string {
  const ts = typeof dateInput === 'string' ? new Date(dateInput).getTime() : dateInput
  const diffSec = Math.floor((Date.now() - ts) / 1000)
  if (diffSec < 60) return 'Just now'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`
  return new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function getTimeCategory(dateInput: number | string): 'Today' | 'Yesterday' | 'Previous 7 Days' | 'Older' {
  const ts = typeof dateInput === 'string' ? new Date(dateInput).getTime() : dateInput
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterday = today - 86400000
  const sevenDays = today - 7 * 86400000

  if (ts >= today) return 'Today'
  if (ts >= yesterday) return 'Yesterday'
  if (ts >= sevenDays) return 'Previous 7 Days'
  return 'Older'
}



const toggleDesktopSite = () => {
  const meta = document.querySelector('meta[name="viewport"]');
  if (!meta) return;
  const current = meta.getAttribute('content') || '';
  if (current.includes('width=1200')) {
    meta.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover, interactive-widget=resizes-content');
    document.body.style.minWidth = 'auto';
    document.body.style.overflowX = 'hidden';
    document.getElementById('root')!.style.minWidth = 'auto';
    alert("Mobile Site Restored.");
  } else {
    meta.setAttribute('content', 'width=1200, user-scalable=yes, viewport-fit=cover');
    document.body.style.minWidth = '1200px';
    document.body.style.overflowX = 'auto';
    document.getElementById('root')!.style.minWidth = '1200px';
    alert("Desktop Site Enabled! If it doesn't zoom automatically, you can pinch-to-zoom or scroll sideways.");
  }
}


export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  activeTab,
  onTabChange,
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  onRenameSession,
  onExportSession,
  antigravityList,
  activeAntigravityId,
  onSelectAntigravity,
  activeProfile,
  isAdmin = false,
  oversightProfile,
  onSelectOversightProfile,
  availableProfiles = [],
}) => {
  const [searchQuery, setSearchQuery] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editTitle, setEditTitle] = useState('')

  // Filter and group Doshie sessions
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions
    const q = searchQuery.toLowerCase()
    return sessions.filter(
      s =>
        s.title.toLowerCase().includes(q) ||
        s.messages.some(m => m.content.toLowerCase().includes(q))
    )
  }, [sessions, searchQuery])

  const groupedSessions = useMemo(() => {
    const groups: Record<string, ChatSession[]> = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    }
    filteredSessions.forEach(s => {
      const cat = getTimeCategory(s.updated_at || s.created_at)
      groups[cat].push(s)
    })
    return groups
  }, [filteredSessions])

  // Filter and group Antigravity sessions
  const filteredAntigravity = useMemo(() => {
    if (!searchQuery.trim()) return antigravityList
    const q = searchQuery.toLowerCase()
    return antigravityList.filter(
      a =>
        a.title.toLowerCase().includes(q) ||
        a.preview.toLowerCase().includes(q) ||
        a.id.toLowerCase().includes(q)
    )
  }, [antigravityList, searchQuery])

  const groupedAntigravity = useMemo(() => {
    const groups: Record<string, AntigravitySummary[]> = {
      Today: [],
      Yesterday: [],
      'Previous 7 Days': [],
      Older: [],
    }
    filteredAntigravity.forEach(a => {
      const cat = getTimeCategory(a.updated_at || a.created_at)
      groups[cat].push(a)
    })
    return groups
  }, [filteredAntigravity])

  const handleStartRename = (s: ChatSession, e: React.MouseEvent) => {
    e.stopPropagation()
    setEditingId(s.id)
    setEditTitle(s.title)
  }

  const handleSaveRename = (id: string, e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (editTitle.trim()) {
      onRenameSession(id, editTitle.trim())
    }
    setEditingId(null)
  }

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-40 md:hidden transition-opacity"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed md:relative inset-y-0 left-0 z-50 flex flex-col w-[290px] sm:w-[320px] bg-black/85 md:bg-black/60 backdrop-blur-2xl border-r border-white/10 transition-transform duration-200 ease-in-out select-none shadow-2xl md:shadow-none ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:-translate-x-full md:hidden'
        }`}
      >
        {/* Header with Title and Close Button */}
        <div
          style={{
            paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 16px)',
          }}
          className="flex items-center justify-between px-4 pb-3 border-b border-white/10"
        >
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-sm shadow-sm">
              🦖
            </div>
            <span className="font-bold text-white text-sm tracking-wide">
              Chat Explorer
            </span>
          </div>

          <button
            onClick={onClose}
            title="Collapse sidebar"
            className="p-1.5 rounded-xl text-neutral-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* Action: New Chat Button */}
        <div className="p-3 pb-2">
          <button
            onClick={() => {
              onNewChat()
              if (window.innerWidth < 768) onClose()
            }}
            className="w-full py-2.5 px-3.5 rounded-2xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] hover:opacity-95 active:scale-[0.98] text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-[var(--accent)]/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Admin Guest Oversight Selector (Visible ONLY to Admin) */}
        {isAdmin && availableProfiles && availableProfiles.length > 1 && (
          <div className="px-3 pb-2">
            <div className="p-2 rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)] space-y-1.5 shadow-sm">
              <div className="flex items-center justify-between text-[10px] uppercase font-bold text-amber-400">
                <span className="flex items-center gap-1.5">
                  <Shield className="w-3 h-3 text-amber-400" />
                  <span>Admin Guest Oversight</span>
                </span>
                {oversightProfile && oversightProfile.toLowerCase() !== activeProfile.toLowerCase() ? (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-950/90 text-amber-300 border border-amber-800 flex items-center gap-0.5">
                    <Eye className="w-2.5 h-2.5" /> Inspecting
                  </span>
                ) : (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--card-hover)] text-[var(--accent-light)] border border-[var(--border-dark)]">
                    My Account
                  </span>
                )}
              </div>
              <select
                value={oversightProfile || activeProfile}
                onChange={e => onSelectOversightProfile && onSelectOversightProfile(e.target.value)}
                className="w-full py-1.5 px-2 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] text-xs font-medium text-white focus:outline-none focus:border-amber-400 cursor-pointer"
              >
                {availableProfiles.map(p => {
                  const isSelf = p.name.toLowerCase() === activeProfile.toLowerCase()
                  return (
                    <option key={p.id} value={p.name}>
                      {isSelf
                        ? `👑 ${p.name} (My Admin Chats)`
                        : `👤 ${p.name} (${p.role || 'Guest'})`}
                    </option>
                  )
                })}
              </select>
            </div>
          </div>
        )}

        {/* Tab Switcher: Doshie vs Antigravity */}
        <div className="px-3 pb-2">
          <div className="grid grid-cols-2 p-0.5 rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)]">
            <button
              onClick={() => onTabChange('doshie')}
              className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                activeTab === 'doshie'
                  ? 'bg-[var(--accent)] text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Doshie ({sessions.length})</span>
            </button>

            <button
              onClick={() => onTabChange('antigravity')}
              className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                activeTab === 'antigravity'
                  ? 'bg-[var(--accent)] text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Antigravity ({antigravityList.length})</span>
            </button>
          </div>
        </div>

        {/* Search Filter */}
        <div className="px-3 pb-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--accent-light)]/60" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={activeTab === 'doshie' ? 'Search Doshie chats...' : 'Search agent transcripts...'}
              className="w-full pl-8 pr-7 py-1.5 bg-[var(--card-dark)] border border-[var(--border-dark)] rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-hidden focus:border-[var(--accent)] transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Sessions / Transcripts List Scroll Area */}
        <div className="flex-1 overflow-y-auto px-2 space-y-4 py-1 text-xs">
          {activeTab === 'doshie' ? (
            <>
              {/* Oversight Guest Inspection Banner */}
              {oversightProfile && oversightProfile.toLowerCase() !== activeProfile.toLowerCase() && (
                <div className="mx-1 p-2 rounded-xl bg-amber-950/40 border border-amber-800/60 flex items-center justify-between text-[11px] text-amber-200 shadow-xs">
                  <span className="flex items-center gap-1.5 truncate">
                    <Eye className="w-3 h-3 text-amber-400 flex-none" />
                    <span className="truncate">Inspecting <strong>{oversightProfile}</strong></span>
                  </span>
                  <button
                    onClick={() => onSelectOversightProfile && onSelectOversightProfile(activeProfile)}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-amber-900/80 hover:bg-amber-800 text-white font-medium flex-none ml-1 cursor-pointer active:scale-95"
                  >
                    My Chats
                  </button>
                </div>
              )}

              {/* Doshie Chats List */}
              {filteredSessions.length === 0 ? (
                <div className="text-center py-8 px-4 text-neutral-400">
                  <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  <p>{searchQuery ? 'No chats match your search.' : `No conversations saved for ${oversightProfile || activeProfile}.`}</p>
                  <p className="text-[10px] mt-1 text-[var(--accent-light)]/80">Start a new chat to begin!</p>
                </div>
              ) : (
              Object.entries(groupedSessions).map(([category, items]) => {
                if (items.length === 0) return null
                return (
                  <div key={category} className="space-y-1">
                    <div className="px-2 py-1 text-[10px] font-bold tracking-wider uppercase text-[var(--accent-light)]/70">
                      {category}
                    </div>
                    {items.map(s => {
                      const isActive = activeSessionId === s.id
                      const isEditing = editingId === s.id

                      return (
                        <div
                          key={s.id}
                          onClick={() => {
                            onSelectSession(s.id)
                            if (window.innerWidth < 768) onClose()
                          }}
                          className={`group relative flex items-center justify-between px-2.5 py-2 rounded-xl transition-all cursor-pointer ${
                            isActive
                              ? 'bg-[var(--card-hover)] border border-[var(--accent)]/50 text-white shadow-sm'
                              : 'text-neutral-300 hover:text-white hover:bg-[var(--card-dark)] border border-transparent'
                          }`}
                        >
                          <div className="flex items-center gap-2 overflow-hidden flex-1 mr-1">
                            <MessageSquare
                              className={`w-3.5 h-3.5 flex-none ${
                                isActive ? 'text-[var(--accent-light)]' : 'text-neutral-500'
                              }`}
                            />
                            {isEditing ? (
                              <form
                                onSubmit={e => handleSaveRename(s.id, e)}
                                onClick={e => e.stopPropagation()}
                                className="flex-1 flex items-center gap-1"
                              >
                                <input
                                  type="text"
                                  value={editTitle}
                                  onChange={e => setEditTitle(e.target.value)}
                                  autoFocus
                                  onBlur={() => handleSaveRename(s.id)}
                                  className="w-full bg-[var(--bg-dark)] text-white text-xs px-1.5 py-0.5 rounded border border-[var(--accent)] outline-none"
                                />
                                <button type="submit" className="p-0.5 text-[var(--accent-light)] hover:text-white">
                                  <Check className="w-3 h-3" />
                                </button>
                              </form>
                            ) : (
                              <div className="truncate flex-1">
                                <span className="block truncate font-medium text-[12.5px]">{s.title}</span>
                                <span className="text-[10px] text-neutral-400 flex items-center gap-1 mt-0.5">
                                  <Clock className="w-2.5 h-2.5" />
                                  {formatRelativeTime(s.updated_at || s.created_at)} · {s.messages.length} msgs
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Action Hover Buttons */}
                          {!isEditing && (
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex-none">
                              <button
                                onClick={e => handleStartRename(s, e)}
                                title="Rename chat"
                                className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]"
                              >
                                <Edit2 className="w-3 h-3" />
                              </button>
                              <button
                                onClick={e => {
                                  e.stopPropagation()
                                  onExportSession(s)
                                }}
                                title="Export Markdown"
                                className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]"
                              >
                                <Download className="w-3 h-3" />
                              </button>
                              <button
                                onClick={e => {
                                  e.stopPropagation()
                                  onDeleteSession(s.id)
                                }}
                                title="Delete chat"
                                className="p-1 rounded text-rose-400 hover:text-rose-200 hover:bg-rose-950/60"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )
              })
            )}
            </>
          ) : (
            /* Antigravity Transcripts List */
            filteredAntigravity.length === 0 ? (
              <div className="text-center py-8 px-4 text-neutral-400">
                <Terminal className="w-8 h-8 mx-auto mb-2 opacity-40" />
                <p>{searchQuery ? 'No transcripts match your search.' : 'No Antigravity logs found.'}</p>
              </div>
            ) : (
              Object.entries(groupedAntigravity).map(([category, items]) => {
                if (items.length === 0) return null
                return (
                  <div key={category} className="space-y-1">
                    <div className="px-2 py-1 text-[10px] font-bold tracking-wider uppercase text-[var(--accent-light)]/70">
                      {category}
                    </div>
                    {items.map(a => {
                      const isActive = activeAntigravityId === a.id

                      return (
                        <div
                          key={a.id}
                          onClick={() => {
                            onSelectAntigravity(a.id)
                            if (window.innerWidth < 768) onClose()
                          }}
                          className={`group relative flex flex-col px-2.5 py-2 rounded-xl transition-all cursor-pointer ${
                            isActive
                              ? 'bg-[var(--card-hover)] border border-[var(--accent)]/60 text-white shadow-sm'
                              : 'text-neutral-300 hover:text-white hover:bg-[var(--card-dark)] border border-transparent'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-1 mb-1">
                            <span className="font-medium text-[12.5px] truncate flex-1">{a.title}</span>
                            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-[var(--card-dark)] border border-[var(--border-dark)] text-[var(--accent-light)] flex-none">
                              {a.id.slice(0, 6)}
                            </span>
                          </div>

                          <p className="text-[11px] text-neutral-400 truncate line-clamp-1 mb-1">
                            {a.preview || 'No prompt preview available.'}
                          </p>

                          <div className="flex items-center justify-between text-[10px] text-neutral-400">
                            <span className="flex items-center gap-1">
                              <Clock className="w-2.5 h-2.5" />
                              {formatRelativeTime(a.updated_at || a.created_at)}
                            </span>
                            <span className="flex items-center gap-1 text-[var(--accent-light)]/80">
                              <Wrench className="w-2.5 h-2.5" />
                              Agent Session
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )
              })
            )
          )}
        </div>

                {/* Desktop Site Toggle Button */}
        <div className="px-3 pb-3">
          <button
            onClick={toggleDesktopSite}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl border border-sky-500/40 bg-sky-950/40 hover:bg-sky-900/60 text-sky-300 text-xs font-semibold cursor-pointer transition-colors"
          >
            🖥️ Desktop Site Mode
          </button>
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-[var(--border-dark)] flex items-center justify-between text-[11px] text-neutral-400 bg-[var(--card-dark)]">
          <span className="truncate">Profile: <strong className="text-white font-semibold">{activeProfile}</strong></span>
          <span className="text-[10px] text-neutral-500 font-mono">v1.2</span>
        </div>
      </aside>
    </>
  )
}
