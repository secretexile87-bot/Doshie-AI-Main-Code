import React from 'react'
import { Tv, Play, Film, ExternalLink, ShieldCheck } from 'lucide-react'

export const MediaView: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto w-full px-3 sm:px-6 py-6 space-y-6">
      
      {/* Media Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl hud-panel border border-cyan-500/30">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Tv className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg sm:text-xl font-bold font-mono text-slate-100 glow-cyan">
              4K MEDIA &amp; STREAMING HUB
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 font-mono">
            Plex 4K HDR Zero-Buffering &bull; Multi-Gigabit Direct Play &bull; NVENC Accelerated
          </p>
        </div>

        <a
          href="http://192.168.1.167:32400/web"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-amber-500 text-black font-mono font-bold text-xs hover:bg-amber-400 transition-all shadow-[0_0_15px_rgba(245,158,11,0.3)]"
        >
          <Play className="w-4 h-4 fill-current" />
          <span>Launch Plex Web</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>

      {/* Stream Hub Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Plex Media Server Card */}
        <div className="p-5 rounded-2xl hud-panel border border-zinc-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Film className="w-5 h-5 text-amber-400" />
              <span className="font-mono font-bold text-sm text-slate-100">PLEX MEDIA SERVER</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
              ACTIVE (PORT 32400)
            </span>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed font-sans">
            Hardware transcoding enabled via NVIDIA NVENC. Direct Play streams up to 2.5 Gbps across your local network with zero buffering.
          </p>

          <div className="pt-2 border-t border-zinc-800/80 flex flex-col gap-1.5 text-xs font-mono text-slate-300">
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Local LAN URL:</span>
              <a href="http://192.168.1.167:32400" target="_blank" rel="noreferrer" className="text-cyan-400 hover:underline">
                192.168.1.167:32400
              </a>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500">Remote Tailscale:</span>
              <span className="text-slate-300">100.109.79.35:32400</span>
            </div>
          </div>
        </div>

        {/* Console & TV Direct Play Tips */}
        <div className="p-5 rounded-2xl hud-panel border border-zinc-800 space-y-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <span className="font-mono font-bold text-sm text-slate-100">ZERO-LAG STREAMING TIPS</span>
          </div>

          <ul className="text-xs text-slate-400 space-y-2 font-sans list-disc list-inside">
            <li>
              <strong className="text-slate-200">On Smart TV / Fire Stick:</strong> In Plex Settings &gt; Advanced &gt; Manual Connections, add <code className="text-cyan-400">192.168.1.167</code>.
            </li>
            <li>
              <strong className="text-slate-200">Original Quality:</strong> Always select <span className="text-emerald-400">Direct Play / Original Quality</span> to eliminate transcoding lag.
            </li>
            <li>
              <strong className="text-slate-200">Away From Home:</strong> Connect phone to Tailscale with Exit Node set to None for direct peer-to-peer 4K streaming.
            </li>
          </ul>
        </div>
      </div>

    </div>
  )
}
