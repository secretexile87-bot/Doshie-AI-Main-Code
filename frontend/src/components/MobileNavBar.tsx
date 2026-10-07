import React from 'react'
import { Bot, Radio, Music, Settings, PanelLeft } from 'lucide-react'

interface MobileNavBarProps {
  onToggleSidebar: () => void
  onOpenAgentHub: () => void
  onOpenLiveVoice: () => void
  onOpenMusicPlayer: () => void
  onOpenSettings: () => void
  isSidebarOpen?: boolean
  selectedAgentName?: string
}

export const MobileNavBar: React.FC<MobileNavBarProps> = ({
  onToggleSidebar,
  onOpenAgentHub,
  onOpenLiveVoice,
  onOpenMusicPlayer,
  onOpenSettings,
  isSidebarOpen = false,
  selectedAgentName,
}) => {
  return (
    <nav
      style={{
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 8px)',
      }}
      className="lg:hidden flex-none z-30 bg-black/75 backdrop-blur-2xl border-t border-white/10 px-2 pt-1.5 shadow-2xl select-none"
    >
      <div className="flex items-center justify-around max-w-md mx-auto">
        {/* Chats / Sidebar */}
        <button
          onClick={onToggleSidebar}
          type="button"
          className={`flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition-all cursor-pointer active:scale-90 ${
            isSidebarOpen ? 'text-[var(--accent-light)]' : 'text-neutral-400 hover:text-white'
          }`}
        >
          <PanelLeft className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-medium tracking-tight">Chats</span>
        </button>

        {/* Agents Hub */}
        <button
          onClick={onOpenAgentHub}
          type="button"
          className={`relative flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition-all cursor-pointer active:scale-90 ${
            selectedAgentName ? 'text-[var(--accent-light)] font-semibold' : 'text-neutral-400 hover:text-white'
          }`}
        >
          <Bot className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-medium tracking-tight truncate max-w-[50px]">
            {selectedAgentName || 'Agents'}
          </span>
          {selectedAgentName && (
            <span className="absolute top-1 right-2 w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-ping" />
          )}
        </button>

        {/* Center Jewel: Live Talk */}
        <button
          onClick={onOpenLiveVoice}
          type="button"
          title="Start Live Voice Talk"
          className="relative -top-3 flex flex-col items-center justify-center group cursor-pointer active:scale-95 transition-transform"
        >
          <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-neutral-950 shadow-xl shadow-[var(--accent)]/30 ring-4 ring-[var(--bg-dark)] border border-white/30 group-hover:scale-105 transition-all">
            <Radio className="w-6 h-6 animate-pulse" />
          </div>
          <span className="text-[9px] font-bold text-[var(--accent-light)] tracking-wider uppercase mt-0.5">
            Live
          </span>
        </button>

        {/* Music Player */}
        <button
          onClick={onOpenMusicPlayer}
          type="button"
          className="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl text-neutral-400 hover:text-sky-300 transition-all cursor-pointer active:scale-90"
        >
          <Music className="w-5 h-5 mb-0.5 text-neutral-400 hover:text-sky-400" />
          <span className="text-[10px] font-medium tracking-tight">Music</span>
        </button>

        {/* Settings */}
        <button
          onClick={onOpenSettings}
          type="button"
          className="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl text-neutral-400 hover:text-white transition-all cursor-pointer active:scale-90"
        >
          <Settings className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-medium tracking-tight">Settings</span>
        </button>
      </div>
    </nav>
  )
}
export default MobileNavBar
