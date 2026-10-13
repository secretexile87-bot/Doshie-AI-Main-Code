import React, { useMemo } from 'react'
import {
  Settings,
  PanelLeft,
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
  messengerUnreadCount?: number
  activeViewTitle?: string
  assistantEmoji?: string
  assistantName?: string
  seasonalCountdownVisible?: boolean
}

export const Header: React.FC<HeaderProps> = ({
  online,
  isSidebarOpen,
  onToggleSidebar,
  onOpenSettings,
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
      {/* Left: Sidebar Toggle & Clean Brand */}
      <div className="flex items-center gap-2.5 min-w-0">
        <button
          onClick={onToggleSidebar}
          title={isSidebarOpen ? 'Collapse sidebar' : 'Open past chats'}
          className="px-2.5 py-1 rounded bg-[#18181b] hover:bg-[#27272a] border border-[#27272a] text-xs font-mono text-neutral-300 hover:text-white transition-all cursor-pointer flex items-center gap-1.5 active:scale-95"
        >
          <PanelLeft className="w-3.5 h-3.5" />
          <span>chats</span>
        </button>

        <div className="flex items-center gap-1.5 font-mono text-xs">
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

      {/* Right: Clean Settings Access */}
      <div className="flex items-center gap-2 flex-none">
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
