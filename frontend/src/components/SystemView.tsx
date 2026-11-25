import React from 'react'
import type { HardwareTelemetry } from '../types'
import {
  Download,
  Smartphone,
  Package,
  HardDrive,
  Cpu,
  Shield,
  RefreshCw
} from 'lucide-react'

interface SystemViewProps {
  telemetry?: HardwareTelemetry | null
  onRefresh: () => void
}

export const SystemView: React.FC<SystemViewProps> = ({
  telemetry: _telemetry,
  onRefresh
}) => {
  return (
    <div className="max-w-4xl mx-auto w-full px-3 sm:px-6 py-6 space-y-6">
      
      {/* System Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl hud-panel border border-cyan-500/30">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg sm:text-xl font-bold font-mono text-slate-100 glow-cyan">
              SYSTEM &amp; DOWNLOADS
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 font-mono">
            Android APK Mobile Installs &bull; Turnkey Migration Backups &bull; Hardware Audit
          </p>
        </div>

        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-zinc-900 border border-zinc-700 text-xs font-mono text-slate-300 hover:text-cyan-400 hover:border-cyan-500/40 transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Audit</span>
        </button>
      </div>

      {/* Downloads Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Android APK Download Card */}
        <div className="p-5 rounded-2xl hud-panel border border-cyan-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-cyan-950/60 border border-cyan-500/40">
                <Smartphone className="w-5 h-5 text-cyan-400" />
              </div>
              <div>
                <h3 className="font-mono font-bold text-sm text-slate-100">DOSHIE ANDROID APK</h3>
                <span className="text-[11px] font-mono text-slate-400">Version 1.1.0 (Build 47) &bull; Fold Optimized</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-500/40">
              LATEST BUILD
            </span>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Directly installable standalone mobile app for your Samsung Galaxy Z Fold. Features full J.A.R.V.I.S. Command &amp; Gaming Cockpit.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row gap-2">
            <a
              href="/download/apk"
              download="Doshie-latest.apk"
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-cyan-500 text-black font-mono font-bold text-xs hover:bg-cyan-400 transition-all shadow-[0_0_12px_rgba(56,189,248,0.3)]"
            >
              <Download className="w-4 h-4" />
              <span>Download APK (Phone)</span>
            </a>

            <a
              href="/download/aab"
              download="Doshie-latest.aab"
              className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl bg-zinc-900 border border-zinc-700 text-slate-300 font-mono text-xs hover:border-cyan-500/40 hover:text-cyan-300 transition-all"
            >
              <Package className="w-4 h-4" />
              <span>AAB</span>
            </a>
          </div>
        </div>

        {/* Complete Migration Backup Card */}
        <div className="p-5 rounded-2xl hud-panel border border-emerald-500/30 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-emerald-950/60 border border-emerald-500/40">
                <HardDrive className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <h3 className="font-mono font-bold text-sm text-slate-100">MOVING DAY BACKUP</h3>
                <span className="text-[11px] font-mono text-emerald-400">1.0 GB &bull; Sealed Archive</span>
              </div>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950 text-emerald-300 border border-emerald-500/40">
              READY TO MOVE
            </span>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Turnkey portable archive containing Doshie’s entire brain, memory databases, J.A.R.V.I.S. identity, and the 1-click restore script.
          </p>

          <div className="pt-2">
            <div className="p-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-[11px] font-mono text-slate-300 flex items-center justify-between">
              <span className="truncate">Desktop/Doshie_Complete_Migration_Backup.tar.gz</span>
              <span className="text-emerald-400 font-bold ml-2">1013 MB</span>
            </div>
          </div>
        </div>
      </div>

      {/* Hardware Telemetry Audit Sheet */}
      <div className="p-5 rounded-2xl hud-panel border border-zinc-800 space-y-4">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-cyan-400" />
          <h2 className="font-mono font-bold text-sm text-slate-100">ACER NITRO HARDWARE AUDIT</h2>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-900">
            <div className="text-slate-500 text-[10px]">CPU ARCHITECTURE</div>
            <div className="text-slate-200 font-bold mt-0.5">Intel Core Ultra 7 265F</div>
            <div className="text-slate-500 text-[10px]">20 Cores &bull; 28 Threads</div>
          </div>

          <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-900">
            <div className="text-slate-500 text-[10px]">GRAPHICS PROCESSOR</div>
            <div className="text-cyan-400 font-bold mt-0.5">NVIDIA RTX 5070</div>
            <div className="text-slate-500 text-[10px]">12 GB GDDR7 VRAM</div>
          </div>

          <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-900">
            <div className="text-slate-500 text-[10px]">OPERATING SYSTEM</div>
            <div className="text-slate-200 font-bold mt-0.5">Ubuntu 26.04.1 LTS</div>
            <div className="text-slate-500 text-[10px]">Resolute Raccoon</div>
          </div>

          <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-900">
            <div className="text-slate-500 text-[10px]">PUBLIC HTTPS FUNNEL</div>
            <div className="text-emerald-400 font-bold mt-0.5 truncate">acer-nitro.tail50b4c5.ts.net</div>
            <div className="text-slate-500 text-[10px]">Encrypted Worldwide Access</div>
          </div>

          <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-900">
            <div className="text-slate-500 text-[10px]">LOCAL IP ADDRESS</div>
            <div className="text-slate-200 font-bold mt-0.5">192.168.1.167</div>
            <div className="text-slate-500 text-[10px]">2.5 Gbps Wired Ethernet</div>
          </div>

          <div className="p-3 rounded-xl bg-zinc-950 border border-zinc-900">
            <div className="text-slate-500 text-[10px]">TAILSCALE MESH IP</div>
            <div className="text-cyan-400 font-bold mt-0.5">100.109.79.35</div>
            <div className="text-slate-500 text-[10px]">Encrypted Mesh Overlay</div>
          </div>
        </div>
      </div>

    </div>
  )
}
