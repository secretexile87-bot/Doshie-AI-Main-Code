import type { TabType, HardwareTelemetry } from '../types'
import { Zap, MessageSquare, Gamepad2, Tv, Cpu } from 'lucide-react'

interface HeaderProps {
  activeTab: TabType
  onSelectTab: (tab: TabType) => void
  telemetry: HardwareTelemetry | null
}

export const Header = ({
  activeTab,
  onSelectTab,
  telemetry
}: HeaderProps) => {
  return (
    <header className="sticky top-0 z-50 flex-shrink-0 w-full bg-black/90 backdrop-blur-md border-b border-cyan-500/20 pt-[env(safe-area-inset-top,0px)] px-3 sm:px-6 py-2.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2.5">
        
        {/* Brand & Live Arc Status */}
        <div className="flex items-center justify-between w-full sm:w-auto gap-3">
          <div className="flex items-center gap-2.5">
            <div className="relative flex items-center justify-center w-8 h-8 rounded-full bg-cyan-950/80 border border-cyan-400/50 arc-pulse">
              <Zap className="w-4 h-4 text-cyan-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono font-bold tracking-wider text-sm sm:text-base text-slate-100 glow-cyan">
                  DOSHIE <span className="text-cyan-400 font-light text-xs sm:text-sm">// J.A.R.V.I.S.</span>
                </span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
                  ONLINE
                </span>
              </div>
              <div className="text-[10px] text-slate-400 font-mono tracking-tight hidden xs:block">
                ACER NITRO 265F &bull; RTX 5070 12GB
              </div>
            </div>
          </div>

          {/* Quick Hardware Pill on mobile */}
          {telemetry && (
            <div className="flex sm:hidden items-center gap-2 px-2 py-1 rounded bg-zinc-900/80 border border-zinc-800 text-[10px] font-mono text-cyan-400">
              <span className="text-slate-300">{telemetry.gpu_temp ?? 42}°C</span>
              <span className="text-zinc-600">|</span>
              <span className="text-emerald-400">{telemetry.gpu_power_watts ?? 3}W</span>
            </div>
          )}
        </div>

        {/* Live Telemetry Pill on Desktop/Tablet */}
        {telemetry && (
          <div className="hidden sm:flex items-center gap-3 px-3 py-1 rounded-full bg-zinc-900/70 border border-cyan-500/20 text-xs font-mono">
            <span className="text-slate-400">GPU:</span>
            <span className="text-cyan-400 font-semibold">{telemetry.gpu_temp ?? 42}°C</span>
            <span className="text-zinc-600">&bull;</span>
            <span className="text-emerald-400 font-semibold">{telemetry.gpu_power_watts ?? 3}W</span>
            <span className="text-zinc-600">&bull;</span>
            <span className="text-slate-300">VRAM: {telemetry.vram_used_mb ? (telemetry.vram_used_mb / 1024).toFixed(1) : '0.7'} / 12GB</span>
          </div>
        )}

        {/* Tactical Navigation Tabs */}
        <nav className="flex items-center gap-1 sm:gap-2 w-full sm:w-auto justify-center bg-zinc-950/90 p-1 rounded-xl border border-zinc-800/80">
          <button
            onClick={() => onSelectTab('chat')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'chat'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(56,189,248,0.25)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-zinc-900'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Command</span>
          </button>

          <button
            onClick={() => onSelectTab('gaming')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'gaming'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(56,189,248,0.25)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-zinc-900'
            }`}
          >
            <Gamepad2 className="w-3.5 h-3.5" />
            <span>Gaming</span>
          </button>

          <button
            onClick={() => onSelectTab('media')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'media'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(56,189,248,0.25)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-zinc-900'
            }`}
          >
            <Tv className="w-3.5 h-3.5" />
            <span>Media</span>
          </button>

          <button
            onClick={() => onSelectTab('system')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
              activeTab === 'system'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_12px_rgba(56,189,248,0.25)]'
                : 'text-slate-400 hover:text-slate-200 hover:bg-zinc-900'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>System</span>
          </button>
        </nav>
      </div>
    </header>
  )
}
