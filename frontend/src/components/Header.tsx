import React, { useState, useRef, useEffect } from 'react'
import {
  PlusCircle,
  User,
  Settings,
  Radio,
  PanelLeft,
  MessageSquare,
  RefreshCw,
  LogOut,
  Lock,
  MoreVertical,
  Palette,
  Shield,
  Activity,
  Music,
  Disc,
  Square,
  Mic
} from 'lucide-react'

interface HeaderProps {
  online: boolean
  activeProfile: string
  isSidebarOpen: boolean
  onToggleSidebar: () => void
  onNewChat: () => void
  onOpenSettings: (tab?: 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor') => void
  onOpenLiveVoice: () => void
  onOpenMusicPlayer?: () => void
  onOpenVoiceStudio?: () => void
  onLogout: () => void
  onLockScreen?: () => void
  isAdmin?: boolean
  isGenerating: boolean
  activeViewTitle?: string
  assistantEmoji?: string
  assistantName?: string
}

export const Header: React.FC<HeaderProps> = ({
  online,
  activeProfile,
  isSidebarOpen,
  onToggleSidebar,
  onNewChat,
  onOpenSettings,
  onOpenLiveVoice,
  onOpenMusicPlayer,
  onOpenVoiceStudio,
  onLogout,
  onLockScreen,
  isAdmin = false,
  isGenerating,
  activeViewTitle,
  assistantEmoji = '🦖',
  assistantName = 'Doshie',
}) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [activeMusic, setActiveMusic] = useState<{ state: string; title?: string; artist?: string } | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  // Poll music player state every 2.5s for instant Now Playing & Stop display
  useEffect(() => {
    let active = true
    const checkMusic = async () => {
      try {
        const res = await fetch('/music/api/status')
        if (res.ok && active) {
          const data = await res.json()
          if (data && data.state === 'PLAYING' && data.current_track) {
            setActiveMusic({
              state: 'PLAYING',
              title: data.current_track.title,
              artist: data.current_track.artist,
            })
          } else {
            setActiveMusic(null)
          }
        }
      } catch (e) {}
    }
    checkMusic()
    const timer = setInterval(checkMusic, 2500)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  // Auto-close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsMobileMenuOpen(false)
      }
    }

    if (isMobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isMobileMenuOpen])

  return (
    <header
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 40px)',
      }}
      className="relative flex-none bg-[var(--bg-dark)] border-b border-[var(--border-dark)] px-2.5 sm:px-4 pb-2.5 sm:pb-3 flex items-center justify-between z-30 shadow-sm shadow-black/40"
    >
      {/* Left: Sidebar Toggle & Brand */}
      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0 flex-1 max-w-[50%] sm:max-w-none">
        <button
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Collapse chat sidebar' : 'Open past chats & transcripts'}
          className={`p-1.5 sm:px-2.5 sm:py-1.5 rounded-xl border transition-all cursor-pointer flex items-center gap-1.5 text-xs font-semibold flex-none ${
            isSidebarOpen
              ? 'bg-[var(--accent)]/30 border-[var(--accent)] text-white'
              : 'bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border-[var(--border-dark)] hover:border-[var(--accent)]/40 text-[var(--accent-light)]'
          }`}
        >
          <PanelLeft className="w-4 h-4 text-[var(--accent-light)]" />
          <span className="hidden sm:inline">Chats</span>
        </button>

        <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 truncate">
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-sm sm:text-base shadow-sm flex-none">
            {assistantEmoji}
          </div>
          <div className="min-w-0 truncate">
            <div className="flex items-center gap-1 leading-tight truncate">
              <span className="font-semibold text-white text-xs sm:text-sm tracking-wide truncate">{assistantName}</span>
              <span className="text-[9px] sm:text-[10px] uppercase font-bold tracking-wider px-1 py-0.2 sm:px-1.5 sm:py-0.5 rounded bg-[var(--card-dark)] border border-[var(--border-dark)] text-[var(--accent-light)] flex-none">
                AI
              </span>
            </div>
            <div className="flex items-center gap-1 text-[10px] sm:text-[11px] text-[var(--accent-light)]/80 truncate">
              {online ? (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse flex-none" />
                  <span className="truncate">Ready · RTX 5070</span>
                </>
              ) : (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-none" />
                  <span className="truncate">Connecting...</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Center: Title (if viewing transcript or active conversation) - Hidden on medium/mobile screens */}
      {activeViewTitle && (
        <div className="hidden xl:flex items-center gap-1.5 text-xs text-[var(--accent-light)]/90 bg-[var(--card-dark)] px-3 py-1 rounded-full border border-[var(--border-dark)] max-w-xs truncate mx-2">
          <MessageSquare className="w-3 h-3 text-[var(--accent)] flex-none" />
          <span className="truncate">{activeViewTitle}</span>
        </div>
      )}

      {/* Right Actions: Responsive Desktop Toolbar vs Collapsible Mobile Menu */}
      <div className="flex items-center gap-1 sm:gap-1.5 flex-none" ref={menuRef}>
        {/* Live Voice Mode Button - always quick accessible */}
        <button
          onClick={onOpenLiveVoice}
          title="Start Live Voice conversation"
          className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] border border-[var(--accent-light)]/40 text-xs font-semibold text-white transition-all shadow-md shadow-black/40 cursor-pointer active:scale-95 animate-pulse"
        >
          <Radio className="w-3.5 h-3.5 text-white" />
          <span className="hidden sm:inline">Live Talk</span>
        </button>

        {/* Music Player Button & Live Playing Bar */}
        {onOpenMusicPlayer && (
          activeMusic?.state === 'PLAYING' ? (
            <div className="flex items-center gap-1.5 bg-gradient-to-r from-sky-950/90 to-indigo-950/90 border border-sky-500/50 rounded-xl px-2 py-1 shadow-md shadow-sky-950/50 animate-in fade-in duration-200">
              <button
                onClick={onOpenMusicPlayer}
                className="flex items-center gap-1.5 text-xs font-semibold text-sky-200 hover:text-white cursor-pointer"
                title={`Now Playing: ${activeMusic.title || 'Music'} - Click to open player`}
              >
                <Disc className="w-3.5 h-3.5 text-sky-400 animate-spin [animation-duration:3s] flex-none" />
                <span className="max-w-[85px] sm:max-w-[130px] truncate text-[11px] font-medium text-sky-100">
                  {activeMusic.title || 'Playing'}
                </span>
              </button>
              <button
                onClick={async (e) => {
                  e.stopPropagation()
                  try {
                    await fetch('/music/api/stop', { method: 'POST' })
                    setActiveMusic(null)
                  } catch (e) {}
                }}
                title="Stop Music immediately"
                className="p-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/40 text-rose-300 border border-rose-500/40 transition-all cursor-pointer active:scale-90 flex-none"
              >
                <Square className="w-2.5 h-2.5 fill-rose-400 text-rose-400" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenMusicPlayer}
              title="Open Universal Music Player (Spotify, YouTube, SoundCloud, Radio)"
              className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-sky-500/50 text-xs font-semibold text-white transition-all shadow-sm cursor-pointer active:scale-95"
            >
              <Music className="w-3.5 h-3.5 text-sky-400" />
              <span className="hidden sm:inline">Music</span>
            </button>
          )
        )}

        {/* Voice Studio & Voice Changer Button */}
        {onOpenVoiceStudio && (
          <button
            onClick={onOpenVoiceStudio}
            title="Open Voice Studio & Voice Changer"
            className="flex items-center gap-1 sm:gap-1.5 px-2 sm:px-2.5 py-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-emerald-500/50 text-xs font-semibold text-white transition-all shadow-sm cursor-pointer active:scale-95"
          >
            <Mic className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Voice Studio</span>
          </button>
        )}

        {/* New Chat Button - always quick accessible */}
        <button
          onClick={onNewChat}
          disabled={isGenerating}
          title="Start new conversation"
          className="p-1.5 sm:px-3 sm:py-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/50 active:scale-95 text-white text-xs font-medium transition duration-150 disabled:opacity-50 disabled:pointer-events-none shadow-sm cursor-pointer flex items-center"
        >
          <PlusCircle className="w-4 h-4 text-[var(--accent-light)]" />
          <span className="hidden lg:inline ml-1.5">New Chat</span>
        </button>

        {/* Desktop-only Direct Action Buttons (md: and up) */}
        <div className="hidden md:flex items-center gap-1 sm:gap-1.5">
          {/* Profile Pill Button */}
          <button
            onClick={() => onOpenSettings('profiles')}
            title="Switch or add profile"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/40 text-xs font-medium text-white transition-all cursor-pointer active:scale-95"
          >
            <User className="w-3.5 h-3.5 text-[var(--accent-light)]" />
            <span className="max-w-[75px] truncate">{activeProfile}</span>
          </button>

          {/* Quick Refresh Button */}
          <button
            onClick={() => window.location.reload()}
            title="Quick Refresh Interface"
            className="p-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/40 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer active:scale-95 group"
          >
            <RefreshCw className="w-4 h-4 group-hover:rotate-180 transition-transform duration-500" />
          </button>

          {/* Lock Screen Button */}
          {onLockScreen && (
            <button
              onClick={onLockScreen}
              title="Lock Workstation & Interface"
              className="p-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-amber-950/60 border border-[var(--border-dark)] hover:border-amber-500/50 text-amber-400/80 hover:text-amber-300 transition-all cursor-pointer active:scale-95"
            >
              <Lock className="w-4 h-4" />
            </button>
          )}

          {/* Doctor AI Quick Button */}
          <button
            onClick={() => onOpenSettings('doctor')}
            title="Doshie Doctor AI & System Health"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-emerald-950/70 hover:bg-emerald-900/90 border border-emerald-700/60 hover:border-emerald-500 text-emerald-300 text-xs font-semibold transition-all shadow-sm cursor-pointer active:scale-95"
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
            <span className="hidden sm:inline">Doctor AI</span>
          </button>

          {/* Settings Gear Button */}
          <button
            onClick={() => onOpenSettings('settings')}
            title="App Settings & Customization"
            className="p-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/40 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer active:scale-95"
          >
            <Settings className="w-4 h-4" />
          </button>

          {/* Logout Button */}
          <button
            onClick={onLogout}
            title={`Log out / Switch account (${activeProfile})`}
            className="p-1.5 rounded-xl bg-[var(--card-dark)] hover:bg-rose-950/60 border border-[var(--border-dark)] hover:border-rose-500/50 text-[var(--accent-light)]/80 hover:text-rose-300 transition-all cursor-pointer active:scale-95"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>

        {/* Mobile / Fold Compact Menu Toggle Button (Visible on narrow screens) */}
        <div className="relative md:hidden">
          <button
            onClick={() => setIsMobileMenuOpen(prev => !prev)}
            title="Open Quick Actions Menu"
            className={`p-1.5 rounded-xl border transition-all cursor-pointer flex items-center justify-center active:scale-95 ${
              isMobileMenuOpen
                ? 'bg-[var(--accent)] text-white border-[var(--accent-light)] shadow-md ring-2 ring-[var(--accent)]/30'
                : 'bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border-[var(--border-dark)] text-[var(--accent-light)]'
            }`}
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {/* Collapsible Mobile Dropdown Menu */}
          {isMobileMenuOpen && (
            <div className="absolute right-0 top-full mt-2 w-64 max-h-[calc(100vh-80px)] overflow-y-auto overscroll-contain bg-[var(--card-dark)]/95 backdrop-blur-2xl border border-[var(--border-dark)] rounded-2xl shadow-2xl shadow-black/80 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150 text-neutral-100">
              {/* Profile Card Header */}
              <div className="px-3.5 py-2.5 border-b border-[var(--border-dark)] mb-1 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center font-bold text-xs text-white">
                    {activeProfile.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <div className="font-bold text-xs text-white truncate max-w-[120px]">{activeProfile}</div>
                    <div className="text-[10px] text-[var(--accent-light)]/80">Active Session</div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false)
                    onOpenSettings('profiles')
                  }}
                  className="text-[10px] px-2 py-0.5 rounded-lg bg-[var(--card-hover)] border border-[var(--border-dark)] text-[var(--accent-light)] font-semibold cursor-pointer hover:bg-[var(--accent)] hover:text-white"
                >
                  Switch
                </button>
              </div>

              {/* Menu Navigation Items */}
              <div className="space-y-0.5 px-1.5">
                {onOpenMusicPlayer && (
                  activeMusic?.state === 'PLAYING' ? (
                    <div className="w-full px-2.5 py-2 rounded-xl bg-sky-950/60 border border-sky-500/40 flex items-center justify-between gap-2">
                      <button
                        onClick={() => {
                          setIsMobileMenuOpen(false)
                          onOpenMusicPlayer()
                        }}
                        className="flex items-center gap-2 text-left min-w-0 flex-1 cursor-pointer"
                      >
                        <Disc className="w-4 h-4 text-sky-400 animate-spin [animation-duration:3s] flex-none" />
                        <div className="truncate">
                          <div className="text-xs font-bold text-sky-200 truncate">{activeMusic.title || 'Playing Music'}</div>
                          <div className="text-[10px] text-sky-400/80 truncate">{activeMusic.artist || 'Now Playing'}</div>
                        </div>
                      </button>
                      <button
                        onClick={async (e) => {
                          e.stopPropagation()
                          try {
                            await fetch('/music/api/stop', { method: 'POST' })
                            setActiveMusic(null)
                          } catch (e) {}
                        }}
                        title="Stop Music"
                        className="px-2 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/40 text-rose-300 border border-rose-500/30 text-[11px] font-bold flex items-center gap-1 cursor-pointer"
                      >
                        <Square className="w-2.5 h-2.5 fill-rose-400 text-rose-400" />
                        <span>Stop</span>
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        setIsMobileMenuOpen(false)
                        onOpenMusicPlayer()
                      }}
                      className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-semibold text-sky-400 hover:text-sky-300 hover:bg-sky-950/40 flex items-center gap-2.5 transition-colors cursor-pointer"
                    >
                      <Music className="w-4 h-4 text-sky-400" />
                      <span>🎵 Universal Music Player</span>
                    </button>
                  )
                )}

                {onOpenVoiceStudio && (
                  <button
                    onClick={() => {
                      setIsMobileMenuOpen(false)
                      onOpenVoiceStudio()
                    }}
                    className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-semibold text-emerald-400 hover:text-emerald-300 hover:bg-emerald-950/40 flex items-center gap-2.5 transition-colors cursor-pointer"
                  >
                    <Mic className="w-4 h-4 text-emerald-400" />
                    <span>🎙️ Voice Studio & Voice Changer</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false)
                    onOpenSettings('settings')
                  }}
                  className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-neutral-200 hover:text-white hover:bg-[var(--card-hover)] flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <Settings className="w-4 h-4 text-[var(--accent-light)]" />
                  <span>Voice & Persona Settings</span>
                </button>

                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false)
                    onOpenSettings('doctor')
                  }}
                  className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-emerald-300 hover:text-emerald-100 hover:bg-emerald-950/60 flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <span>🩺 Doshie Doctor AI</span>
                </button>

                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false)
                    onOpenSettings('appearance')
                  }}
                  className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-neutral-200 hover:text-white hover:bg-[var(--card-hover)] flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <Palette className="w-4 h-4 text-[var(--accent-light)]" />
                  <span>Appearance & Lock Screen</span>
                </button>

                {isAdmin && (
                  <button
                    onClick={() => {
                      setIsMobileMenuOpen(false)
                      onOpenSettings('oversight')
                    }}
                    className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-amber-300 hover:text-amber-100 hover:bg-amber-950/60 flex items-center gap-2.5 transition-colors cursor-pointer"
                  >
                    <Shield className="w-4 h-4 text-amber-400" />
                    <span>👑 Guest Oversight Center</span>
                  </button>
                )}

                {onLockScreen && (
                  <button
                    onClick={() => {
                      setIsMobileMenuOpen(false)
                      onLockScreen()
                    }}
                    className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-amber-300 hover:text-amber-100 hover:bg-amber-950/60 flex items-center gap-2.5 transition-colors cursor-pointer"
                  >
                    <Lock className="w-4 h-4 text-amber-400" />
                    <span>Lock Screen Now</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false)
                    onOpenSettings('maintenance')
                  }}
                  className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-neutral-200 hover:text-white hover:bg-[var(--card-hover)] flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4 text-cyan-400" />
                  <span>Reset & System Cache</span>
                </button>

                <button
                  onClick={() => {
                    setIsMobileMenuOpen(false)
                    window.location.reload()
                  }}
                  className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-medium text-neutral-200 hover:text-white hover:bg-[var(--card-hover)] flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4 text-[var(--accent-light)]" />
                  <span>Quick Reload App</span>
                </button>

                <div className="pt-1 mt-1 border-t border-[var(--border-dark)]">
                  <button
                    onClick={() => {
                      setIsMobileMenuOpen(false)
                      onLogout()
                    }}
                    className="w-full px-2.5 py-2 rounded-xl text-left text-xs font-semibold text-rose-300 hover:text-rose-100 hover:bg-rose-950/60 flex items-center gap-2.5 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-4 h-4 text-rose-400" />
                    <span>Log Out of {activeProfile}</span>
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
