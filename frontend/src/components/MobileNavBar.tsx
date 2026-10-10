import React from 'react'
import { Home, PanelLeft, Radio, MessageSquare, Settings } from 'lucide-react'

interface MobileNavBarProps {
  onGoHome: () => void
  onToggleSidebar: () => void
  onOpenLiveVoice: () => void
  onOpenChat: () => void
  onOpenSettings: () => void
  isSidebarOpen?: boolean
  isChatActive?: boolean
  messengerUnreadCount?: number
  selectedAgentName?: string
}

export const MobileNavBar: React.FC<MobileNavBarProps> = ({
  onGoHome,
  onToggleSidebar,
  onOpenLiveVoice,
  onOpenChat,
  onOpenSettings,
  isSidebarOpen = false,
  isChatActive = false,
  messengerUnreadCount = 0,
  selectedAgentName,
}) => {
  return (
    <nav
      style={{
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 8px)',
      }}
      className="lg:hidden flex-none z-30 bg-black/80 backdrop-blur-2xl border-t border-white/10 px-2 pt-1.5 shadow-2xl select-none"
    >
      <div className="flex items-center justify-around max-w-md mx-auto">
        {/* 1. Home Screen Button */}
        <button
          onClick={onGoHome}
          type="button"
          title="Home Screen"
          className="flex flex-col items-center justify-center py-1 px-2.5 rounded-xl text-neutral-400 hover:text-emerald-300 transition-all cursor-pointer active:scale-90"
        >
          <Home className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-medium tracking-tight">Home</span>
        </button>

        {/* 2. dchats / Sidebar Drawer */}
        <button
          onClick={onToggleSidebar}
          type="button"
          title="Past dchats & Transcripts"
          className={`flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition-all cursor-pointer active:scale-90 ${
            isSidebarOpen ? 'text-[var(--accent-light)] font-semibold' : 'text-neutral-400 hover:text-white'
          }`}
        >
          <PanelLeft className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-medium tracking-tight">dchats</span>
        </button>

        {/* 3. Center Jewel: Live Talk */}
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

        {/* 4. Chat Interface & Messenger Button (Replaced Music Player) */}
        <button
          onClick={onOpenChat}
          type="button"
          title={selectedAgentName ? `Chat with ${selectedAgentName}` : "Open Chat & Messenger Interface"}
          className={`relative flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition-all cursor-pointer active:scale-90 ${
            isChatActive ? 'text-emerald-400 font-semibold' : 'text-neutral-400 hover:text-emerald-300'
          }`}
        >
          <MessageSquare className="w-5 h-5 mb-0.5" />
          <span className="text-[10px] font-medium tracking-tight truncate max-w-[50px]">
            {selectedAgentName || 'Chat'}
          </span>
          {messengerUnreadCount > 0 && (
            <span className="absolute top-0.5 right-1.5 px-1 py-0.2 rounded-full bg-emerald-500 text-neutral-950 text-[9px] font-black leading-none shadow-xs">
              {messengerUnreadCount}
            </span>
          )}
        </button>

        {/* 5. Settings */}
        <button
          onClick={onOpenSettings}
          type="button"
          title="Settings & Appearance"
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
