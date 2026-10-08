import React, { useMemo } from 'react'
import {
  Settings,
  PanelLeft,
  MessageSquare,
  User,
} from 'lucide-react'
import { getSeasonalInfo } from '../utils/seasonal'

interface HeaderProps {
  online: boolean
  activeProfile: string
  isSidebarOpen: boolean
  onToggleSidebar: () => void
  onOpenSettings: (tab?: 'apps' | 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor') => void
  onOpenMusicPlayer?: () => void
  onOpenLiveVoice?: () => void
  onOpenAgentHub?: () => void
  onOpenAgentConsole?: () => void
  activeViewTitle?: string
  assistantEmoji?: string
  assistantName?: string
  seasonalCountdownVisible?: boolean
}

export const Header: React.FC<HeaderProps> = ({
  online,
  activeProfile,
  isSidebarOpen,
  onToggleSidebar,
  onOpenSettings,
  onOpenMusicPlayer: _onOpenMusicPlayer,
  onOpenLiveVoice: _onOpenLiveVoice,
  onOpenAgentHub: _onOpenAgentHub,
  onOpenAgentConsole: _onOpenAgentConsole,
  activeViewTitle,
  assistantEmoji = '🦖',
  assistantName = 'Doshie',
  seasonalCountdownVisible = true,
}) => {
  const seasonal = useMemo(() => getSeasonalInfo(), [])

  return (
    <header
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 12px)',
      }}
      className="relative flex-none bg-black/60 backdrop-blur-xl border-b border-white/10 px-2 sm:px-5 pb-2 sm:pb-3 flex items-center justify-between z-30 shadow-md shadow-black/40 select-none gap-1 sm:gap-2"
    >
      {/* Left: Sidebar Toggle & Brand */}
      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0 flex-shrink">
        <button
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Collapse chat sidebar' : 'Open past chats & transcripts'}
          className={`p-1.5 sm:px-3 sm:py-2 rounded-xl sm:rounded-2xl border transition-all cursor-pointer flex items-center gap-1.5 sm:gap-2 text-xs font-semibold flex-none active:scale-95 ${
            isSidebarOpen
              ? 'bg-[var(--accent)]/30 border-[var(--accent)] text-white shadow-sm'
              : 'bg-white/5 hover:bg-white/10 border-white/10 hover:border-white/20 text-neutral-300 hover:text-white'
          }`}
        >
          <PanelLeft className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--accent-light)]" />
          <span className="hidden sm:inline">Chats</span>
        </button>

        <div className="flex items-center gap-1.5 sm:gap-2.5 min-w-0">
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl sm:rounded-2xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-xs sm:text-sm shadow-md flex-none border border-white/20">
            {assistantEmoji}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1 leading-tight">
              <span className="font-bold text-white text-xs sm:text-sm tracking-wide truncate max-w-[55px] sm:max-w-none">
                {assistantName}
              </span>
              <span className="text-[8px] sm:text-[9px] uppercase font-bold tracking-wider px-1 py-0.5 rounded-full bg-white/10 border border-white/10 text-[var(--accent-light)] flex-none">
                AI
              </span>
            </div>
            <div className="flex items-center gap-1 text-[9px] sm:text-[10px] text-[var(--accent-light)]/80">
              {online ? (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse flex-none" />
                  <span className="truncate font-mono">
                    Ready<span className="hidden md:inline"> · RTX 5070</span>
                  </span>
                </>
              ) : (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 flex-none" />
                  <span className="truncate font-mono">Connecting...</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Center: Seasonal Countdown Badge & Active View Title */}
      <div className="flex items-center justify-center min-w-0 shrink-0 mx-1 sm:mx-2">
        {seasonalCountdownVisible && (
          <button
            onClick={() => onOpenSettings('appearance')}
            title={`Current Season: ${seasonal.seasonName} (${seasonal.daysUntilNext} days until ${seasonal.nextSeasonName}). Click to view Appearance & Seasonal Themes.`}
            className="flex items-center gap-1 sm:gap-1.5 text-[10px] sm:text-xs text-[var(--accent-light)] bg-white/5 hover:bg-white/10 px-2 sm:px-3 py-1 rounded-full border border-white/10 hover:border-white/20 transition-all cursor-pointer shadow-xs font-medium shrink-0 active:scale-95 whitespace-nowrap"
          >
            <span className="text-xs sm:text-sm flex-none">{seasonal.icon}</span>
            <span className="font-semibold text-white/95">{seasonal.seasonName}</span>
            <span className="text-white/40 hide-on-ultranarrow">•</span>
            {/* Shortened "74d" on mobile/fold devices, full "74d until Winter" on desktop */}
            <span className="text-[var(--accent-light)] font-mono text-[9px] sm:text-[11px] seasonal-mobile-short hide-on-ultranarrow">
              {seasonal.daysUntilNext}d
            </span>
            <span className="text-[var(--accent-light)] font-mono text-[10px] sm:text-[11px] seasonal-desktop-full">
              {seasonal.countdownText}
            </span>
          </button>
        )}

        {activeViewTitle && (
          <div className="hidden xl:flex items-center gap-2 text-xs text-[var(--accent-light)]/90 bg-white/5 px-3 py-1 rounded-full border border-white/10 max-w-[200px] truncate shadow-xs ml-2">
            <MessageSquare className="w-3.5 h-3.5 text-[var(--accent)] flex-none" />
            <span className="truncate">{activeViewTitle}</span>
          </div>
        )}
      </div>

      {/* Right: Clean Profile & Settings Hub Access */}
      <div className="flex items-center gap-1 sm:gap-2 flex-none">
        {/* Active Profile Pill (Click opens profile settings) */}
        <button
          onClick={() => onOpenSettings('profiles')}
          title={`Active Profile: ${activeProfile} (Click to switch)`}
          className="flex items-center gap-1 sm:gap-1.5 px-2 py-1 sm:px-3 sm:py-2 rounded-xl sm:rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-xs font-semibold text-white transition-all cursor-pointer active:scale-95 shadow-xs"
        >
          <User className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-[var(--accent-light)] flex-none" />
          <span className="max-w-[46px] sm:max-w-[120px] truncate">{activeProfile}</span>
        </button>

        {/* Settings Hub Button */}
        <button
          onClick={() => onOpenSettings('apps')}
          title="Open Control Center, Apps & Settings"
          className="p-1.5 sm:px-3 sm:py-2 rounded-xl sm:rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-xs font-semibold text-white transition-all cursor-pointer active:scale-95 shadow-xs flex items-center gap-1.5"
        >
          <Settings className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-[var(--accent-light)]" />
          <span className="hidden sm:inline">Settings</span>
        </button>
      </div>
    </header>
  )
}
export default Header
