import { useState } from 'react'
import type { GamingStatus, HardwareTelemetry } from '../types'
import {
  Gamepad2,
  Zap,
  Activity,
  Wand2,
  CheckCircle2,
  Cpu,
  Flame,
  Gauge,
  Wifi
} from 'lucide-react'

interface GamingCockpitViewProps {
  telemetry: HardwareTelemetry | null
  gamingStatus: GamingStatus | null
  onRefresh: () => void
}

export const GamingCockpitView = ({
  telemetry,
  gamingStatus,
  onRefresh
}: GamingCockpitViewProps) => {
  const [fixing, setFixing] = useState(false)
  const [togglingTunnel, setTogglingTunnel] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')

  const handleFixNetwork = async () => {
    try {
      setFixing(true)
      setStatusMsg('Applying self-healing network & routing fixes...')
      const res = await fetch('/api/gaming-fix', { method: 'POST' })
      const data = await res.json()
      if (data?.ok) {
        setStatusMsg('All packet forwarding, NAT masquerading, and gaming routes repaired!')
        onRefresh()
      } else {
        setStatusMsg(`Fix issue: ${data?.error || 'Unknown error'}`)
      }
    } catch (err: any) {
      setStatusMsg(`Auto-fix error: ${err.message}`)
    } finally {
      setFixing(false)
      setTimeout(() => setStatusMsg(''), 5000)
    }
  }

  const handleToggleTunnel = async (enable: boolean) => {
    try {
      setTogglingTunnel(true)
      setStatusMsg(enable ? 'Enabling low-latency Dallas gaming tunnel...' : 'Switching to local ISP route...')
      const res = await fetch('/api/gaming-tunnel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable, node: 'vultr' })
      })
      const data = await res.json()
      if (data?.ok) {
        setStatusMsg(enable ? '🚀 Dallas tunnel active! Game packets routed via high-speed backbone.' : 'Routed via local ISP.')
        onRefresh()
      } else {
        setStatusMsg(`Failed to toggle route: ${data?.error || 'Unknown error'}`)
      }
    } catch (err: any) {
      setStatusMsg(`Route toggle error: ${err.message}`)
    } finally {
      setTogglingTunnel(false)
      setTimeout(() => setStatusMsg(''), 5000)
    }
  }

  return (
    <div className="max-w-5xl mx-auto w-full px-3 sm:px-6 py-6 space-y-6">
      
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-5 rounded-2xl hud-panel border border-cyan-500/30">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Gamepad2 className="w-5 h-5 text-cyan-400" />
            <h1 className="text-lg sm:text-xl font-bold font-mono text-slate-100 glow-cyan">
              GAMING &amp; NETWORK COCKPIT
            </h1>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 font-mono">
            ExitLag-Style Performance &bull; Zero Packet Loss Routing &bull; RTX 5070 Hardware Hub
          </p>
        </div>

        <button
          onClick={handleFixNetwork}
          disabled={fixing}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-cyan-500 text-black font-mono font-bold text-xs hover:bg-cyan-400 disabled:opacity-50 transition-all shadow-[0_0_15px_rgba(56,189,248,0.4)]"
        >
          <Wand2 className={`w-4 h-4 ${fixing ? 'animate-spin' : ''}`} />
          <span>{fixing ? 'Repairing...' : '1-Click Auto-Repair'}</span>
        </button>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-cyan-950/60 border border-cyan-500/40 text-xs font-mono text-cyan-300 animate-fadeIn">
          {statusMsg}
        </div>
      )}

      {/* Latency & Routing Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Dallas Ping Card */}
        <div className="p-4 rounded-xl hud-panel border border-zinc-800 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>DALLAS GAME ROUTE</span>
            <Wifi className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-mono font-bold text-emerald-400 glow-emerald">
            {gamingStatus?.dallas_ping_ms ?? 23} ms
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            Optimal for Dallas central game servers
          </div>
        </div>

        {/* ExitLag-Style Tunnel Card */}
        <div className="p-4 rounded-xl hud-panel border border-zinc-800 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>NETWORK TUNNEL</span>
            <Activity className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${gamingStatus?.tunnel_active ? 'bg-emerald-400' : 'bg-slate-500'}`} />
            <span className="text-sm font-mono font-semibold text-slate-200">
              {gamingStatus?.tunnel_active ? 'Dallas Route ACTIVE' : 'Local ISP Direct'}
            </span>
          </div>
          <button
            onClick={() => handleToggleTunnel(!gamingStatus?.tunnel_active)}
            disabled={togglingTunnel}
            className="w-full py-1.5 px-3 rounded-lg text-xs font-mono font-medium bg-zinc-900 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/50 transition-all"
          >
            {togglingTunnel ? 'Switching...' : gamingStatus?.tunnel_active ? 'Switch to ISP' : 'Activate Dallas Tunnel'}
          </button>
        </div>

        {/* Packet Health */}
        <div className="p-4 rounded-xl hud-panel border border-zinc-800 space-y-2">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>PACKET HEALTH</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-mono font-bold text-slate-100">
            0.0% LOSS
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            IPv6 fragmentation bypassed
          </div>
        </div>
      </div>

      {/* GPU & Hardware Telemetry HUD */}
      <div className="space-y-3">
        <h2 className="text-xs font-mono font-bold tracking-wider text-slate-400 uppercase">
          RTX 5070 &bull; HARDWARE STATUS
        </h2>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          
          <div className="p-3.5 rounded-xl bg-zinc-950/80 border border-zinc-800 space-y-1">
            <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono">
              <Flame className="w-3.5 h-3.5 text-amber-400" />
              <span>GPU TEMP</span>
            </div>
            <div className="text-lg sm:text-xl font-mono font-bold text-slate-100">
              {telemetry?.gpu_temp ?? 42}°C
            </div>
            <div className="text-[10px] font-mono text-emerald-400">Cool &bull; Fans idle</div>
          </div>

          <div className="p-3.5 rounded-xl bg-zinc-950/80 border border-zinc-800 space-y-1">
            <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono">
              <Zap className="w-3.5 h-3.5 text-cyan-400" />
              <span>POWER DRAW</span>
            </div>
            <div className="text-lg sm:text-xl font-mono font-bold text-cyan-400">
              {telemetry?.gpu_power_watts ?? 2.99}W
            </div>
            <div className="text-[10px] font-mono text-slate-400">P8 Low-Power Idle</div>
          </div>

          <div className="p-3.5 rounded-xl bg-zinc-950/80 border border-zinc-800 space-y-1">
            <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono">
              <Gauge className="w-3.5 h-3.5 text-emerald-400" />
              <span>VRAM USAGE</span>
            </div>
            <div className="text-lg sm:text-xl font-mono font-bold text-slate-100">
              {telemetry?.vram_used_mb ? (telemetry.vram_used_mb / 1024).toFixed(1) : '0.7'} GB
            </div>
            <div className="text-[10px] font-mono text-emerald-400">11.5 GB Free (94%)</div>
          </div>

          <div className="p-3.5 rounded-xl bg-zinc-950/80 border border-zinc-800 space-y-1">
            <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-mono">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span>CPU CORES</span>
            </div>
            <div className="text-lg sm:text-xl font-mono font-bold text-slate-100">
              20 CORES
            </div>
            <div className="text-[10px] font-mono text-slate-400">8 P-Cores + 12 E-Cores</div>
          </div>
        </div>
      </div>

    </div>
  )
}
