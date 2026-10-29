import React, { useMemo } from 'react'
import {
  Settings,
  PanelLeft,
  Radio,
  Gamepad2,
  Bot,
  Terminal,
  Wrench,
} from 'lucide-react'
import { getSeasonalInfo } from '../utils/seasonal'

interface HeaderProps {
  online: boolean
  activeProfile?: string
  isSidebarOpen: boolean
  onToggleSidebar: () => void
  onOpenSettings: (tab?: 'apps' | 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor') => void
  onGoHome?: () => void
  onOpenLiveVoice?: () => void
  onOpenAgentHub?: () => void
  onOpenAgentConsole?: () => void
  onOpenMessenger?: () => void
  onOpenGaming?: () => void
  messengerUnreadCount?: number
  activeViewTitle?: string
  assistantEmoji?: string
  assistantName?: string
  seasonalCountdownVisible?: boolean
  speakReplies?: boolean
  onToggleSpeakReplies?: () => void
}

export const Header: React.FC<HeaderProps> = ({
  online,
  isSidebarOpen,
  onToggleSidebar,
  onOpenSettings,
  onOpenLiveVoice,
  onOpenGaming,
  onOpenAgentHub,
  onOpenAgentConsole,
  activeViewTitle,
  seasonalCountdownVisible = false,
}) => {
  const seasonal = useMemo(() => getSeasonalInfo(), [])

  return (
    <header
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 8px)',
      }}
      className="relative flex-none bg-black border-b border-[#27272a] px-3 sm:px-4 py-2 flex items-center justify-between z-30 select-none"
    >
      {/* Left: Sidebar Toggle, Agents, Agent CLI & Clean Brand */}
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Collapse sidebar' : 'Open past chats'}
          className="px-2.5 py-1 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-xs font-mono text-neutral-300 hover:text-white transition-all cursor-pointer flex items-center gap-1.5 active:scale-95 flex-none"
        >
          <PanelLeft className="w-3.5 h-3.5" />
          <span>chats</span>
        </button>

        {onOpenAgentHub && (
          <button
            onClick={onOpenAgentHub}
            title="Open Specialist Agents Hub"
            className="px-2.5 py-1 rounded bg-[#18181b] hover:bg-purple-950/50 border border-[#27272a] hover:border-purple-500/60 text-xs font-mono text-purple-300 hover:text-white transition-all cursor-pointer flex items-center gap-1.5 active:scale-95 flex-none shadow-xs"
          >
            <Bot className="w-3.5 h-3.5 text-purple-400" />
            <span>agents</span>
          </button>
        )}

        {onOpenAgentConsole && (
          <button
            onClick={onOpenAgentConsole}
            title="Autonomous Agent Console (CLI & Terminal)"
            className="hidden sm:flex px-2.5 py-1 rounded bg-[#18181b] hover:bg-teal-950/50 border border-[#27272a] hover:border-teal-500/60 text-xs font-mono text-teal-300 hover:text-white transition-all cursor-pointer items-center gap-1.5 active:scale-95 flex-none shadow-xs"
          >
            <Terminal className="w-3.5 h-3.5 text-teal-400" />
            <span>cli</span>
          </button>
        )}

        <a
          href="/tech"
          title="Hermes Tech Solutions Command Center"
          className="px-2.5 py-1 rounded bg-[#18181b] hover:bg-blue-950/50 border border-[#27272a] hover:border-blue-500/60 text-xs font-mono text-blue-300 hover:text-white transition-all cursor-pointer flex items-center gap-1.5 active:scale-95 flex-none shadow-xs"
        >
          <Wrench className="w-3.5 h-3.5 text-blue-400" />
          <span>tech</span>
        </a>

        <div className="flex items-center gap-1.5 font-mono text-xs ml-0.5">
          <span className="font-semibold text-white tracking-wide">doshie</span>
          <span
            className={`inline-block w-1.5 h-1.5 rounded-full ${
              online ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'
            }`}
            title={online ? 'Online · Workstation' : 'Connecting...'}
          />
        </div>
      </div>

      {/* Center: Seasonal Countdown Badge & Active Title */}
      <div className="flex items-center justify-center min-w-0 truncate mx-2 gap-2">
        {seasonalCountdownVisible && (
          <button
            onClick={() => onOpenSettings('appearance')}
            title={`Current Season: ${seasonal.seasonName} (${seasonal.daysUntilNext} days until ${seasonal.nextSeasonName}). Click to customize appearance.`}
            className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono text-[var(--accent-light)] transition-all cursor-pointer active:scale-95 flex-none"
          >
            <span>{seasonal.icon}</span>
            <span className="font-semibold text-white">{seasonal.seasonName}</span>
            <span className="text-white/40">•</span>
            <span>{seasonal.daysUntilNext}d</span>
          </button>
        )}
        {activeViewTitle && (
          <span className="text-xs font-mono text-neutral-400 truncate max-w-[160px] sm:max-w-xs">
            {activeViewTitle}
          </span>
        )}
      </div>

      {/* Right: Voice Toggle & Settings Access */}
      <div className="flex items-center gap-2 flex-none">
        {/* Live Voice mode is the dedicated voice interaction */}

        {onOpenLiveVoice && (
          <button
            onClick={onOpenLiveVoice}
            title="Start Live Voice Talk"
            className="p-1.5 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-neutral-300 hover:text-white transition-all cursor-pointer active:scale-95"
          >
            <Radio className="w-3.5 h-3.5 text-[var(--accent-light)]" />
          </button>
        )}

        {onOpenGaming && (
          <button
            onClick={onOpenGaming}
            title="Doshie Gaming & Low-Latency VoIP Gateway"
            className="p-1.5 rounded bg-[#18181b] hover:bg-cyan-950/60 border border-[#27272a] hover:border-cyan-600/60 text-cyan-400 hover:text-cyan-300 transition-all cursor-pointer active:scale-95"
          >
            <Gamepad2 className="w-3.5 h-3.5" />
          </button>
        )}

        <button
          onClick={() => onOpenSettings('apps')}
          title="Settings"
          className="p-1.5 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-neutral-300 hover:text-white transition-all cursor-pointer active:scale-95"
        >
          <Settings className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  )
}
export default Header
