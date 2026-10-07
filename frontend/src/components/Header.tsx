import React from 'react'
import {
  Settings,
  PanelLeft,
  MessageSquare,
  User,
  Bot,
  Radio,
  Music,
  Terminal,
} from 'lucide-react'

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
}

export const Header: React.FC<HeaderProps> = ({
  online,
  activeProfile,
  isSidebarOpen,
  onToggleSidebar,
  onOpenSettings,
  onOpenMusicPlayer,
  onOpenLiveVoice,
  onOpenAgentHub,
  onOpenAgentConsole,
  activeViewTitle,
  assistantEmoji = '🦖',
  assistantName = 'Doshie',
}) => {
  return (
    <header
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 12px)',
      }}
      className="relative flex-none bg-black/60 backdrop-blur-xl border-b border-white/10 px-3 sm:px-5 pb-2.5 sm:pb-3 flex items-center justify-between z-30 shadow-md shadow-black/40 select-none"
    >
      {/* Left: Sidebar Toggle & Brand */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Collapse chat sidebar' : 'Open past chats & transcripts'}
          className={`p-2 sm:px-3 sm:py-2 rounded-2xl border transition-all cursor-pointer flex items-center gap-2 text-xs font-semibold flex-none active:scale-95 ${
            isSidebarOpen
              ? 'bg-[var(--accent)]/30 border-[var(--accent)] text-white shadow-sm'
              : 'bg-white/5 hover:bg-white/10 border-white/10 hover:border-white/20 text-neutral-300 hover:text-white'
          }`}
        >
          <PanelLeft className="w-4 h-4 text-[var(--accent-light)]" />
          <span className="hidden sm:inline">Chats</span>
        </button>

        <div className="flex items-center gap-2 sm:gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-2xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-sm shadow-md flex-none border border-white/20">
            {assistantEmoji}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 leading-tight truncate">
              <span className="font-bold text-white text-xs sm:text-sm tracking-wide truncate">
                {assistantName}
              </span>
              <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-full bg-white/10 border border-white/10 text-[var(--accent-light)] flex-none">
                AI
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-[10px] text-[var(--accent-light)]/80">
              {online ? (
                <>
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse flex-none" />
                  <span className="truncate font-mono">Ready · RTX 5070</span>
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

      {/* Center: Title (if viewing transcript or active conversation) */}
      {activeViewTitle && (
        <div className="hidden lg:flex items-center gap-2 text-xs text-[var(--accent-light)]/90 bg-white/5 px-3.5 py-1.5 rounded-full border border-white/10 max-w-sm truncate mx-2 shadow-xs">
          <MessageSquare className="w-3.5 h-3.5 text-[var(--accent)] flex-none" />
          <span className="truncate">{activeViewTitle}</span>
        </div>
      )}

      {/* Right: Clean Profile & Settings Hub Access */}
      <div className="flex items-center gap-1.5 sm:gap-2 flex-none">
        {/* Quick Launchers for Tablet & Desktop */}
        <div className="hidden md:flex items-center gap-1.5 mr-1">
          {onOpenAgentConsole && (
            <button
              onClick={onOpenAgentConsole}
              title="Autonomous Agent Console (CLI, App Builder, Terminal)"
              className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-2xl bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-xs font-semibold text-teal-300 hover:text-white transition-all cursor-pointer active:scale-95 shadow-xs"
            >
              <Terminal className="w-3.5 h-3.5 text-teal-400" />
              <span>Agent CLI</span>
            </button>
          )}

          {onOpenAgentHub && (
            <button
              onClick={onOpenAgentHub}
              title="Autonomous Agents & Tasks Hub"
              className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-xs font-semibold text-neutral-200 hover:text-white transition-all cursor-pointer active:scale-95 shadow-xs"
            >
              <Bot className="w-3.5 h-3.5 text-[var(--accent-light)]" />
              <span>Agents</span>
            </button>
          )}

          {onOpenLiveVoice && (
            <button
              onClick={onOpenLiveVoice}
              title="Continuous Live Voice Mode"
              className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-2xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/30 text-xs font-semibold text-emerald-300 hover:text-white transition-all cursor-pointer active:scale-95 shadow-xs"
            >
              <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>Live Voice</span>
            </button>
          )}

          {onOpenMusicPlayer && (
            <button
              onClick={onOpenMusicPlayer}
              title="Universal Music Player"
              className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-2xl bg-sky-500/15 hover:bg-sky-500/25 border border-sky-500/30 text-xs font-semibold text-sky-300 hover:text-white transition-all cursor-pointer active:scale-95 shadow-xs"
            >
              <Music className="w-3.5 h-3.5 text-sky-400" />
              <span>Music</span>
            </button>
          )}
        </div>

        {/* Mobile Agent CLI Icon Button */}
        {onOpenAgentConsole && (
          <button
            onClick={onOpenAgentConsole}
            title="Autonomous Agent Console (CLI, App Builder, Terminal)"
            className="md:hidden flex items-center justify-center p-2 rounded-2xl bg-teal-500/15 hover:bg-teal-500/25 border border-teal-500/30 text-teal-300 hover:text-white transition-all cursor-pointer active:scale-95 shadow-xs"
          >
            <Terminal className="w-4 h-4 text-teal-400" />
          </button>
        )}

        {/* Active Profile Pill (Click opens profile settings) */}
        <button
          onClick={() => onOpenSettings('profiles')}
          title={`Active Profile: ${activeProfile} (Click to switch)`}
          className="flex items-center gap-1.5 px-2.5 py-1.5 sm:px-3 sm:py-2 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-xs font-semibold text-white transition-all cursor-pointer active:scale-95 shadow-xs"
        >
          <User className="w-3.5 h-3.5 text-[var(--accent-light)]" />
          <span className="max-w-[80px] sm:max-w-[120px] truncate">{activeProfile}</span>
        </button>

        {/* Settings Hub Button */}
        <button
          onClick={() => onOpenSettings('apps')}
          title="Open Control Center, Apps & Settings"
          className="p-2 sm:px-3 sm:py-2 rounded-2xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-xs font-semibold text-white transition-all cursor-pointer active:scale-95 shadow-xs flex items-center gap-1.5"
        >
          <Settings className="w-4 h-4 text-[var(--accent-light)]" />
          <span className="hidden sm:inline">Settings</span>
        </button>
      </div>
    </header>
  )
}
export default Header
