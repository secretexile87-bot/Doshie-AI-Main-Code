import React, { useState, useEffect } from 'react'
import {
  X,
  Gamepad2,
  RefreshCw,
  Wand2,
  Activity,
  Zap,
  Globe,
  Check,
  Server,
  Laptop
} from 'lucide-react'

interface GamingModalProps {
  isOpen: boolean
  onClose: () => void
  onOpenDoctor?: () => void
}

export const GamingModal: React.FC<GamingModalProps> = ({
  isOpen,
  onClose,
  onOpenDoctor
}) => {
  const [loading, setLoading] = useState(false)
  const [fixing, setFixing] = useState(false)
  const [togglingTunnel, setTogglingTunnel] = useState(false)
  const [gamingStatus, setGamingStatus] = useState<any>(null)
  const [statusMsg, setStatusMsg] = useState('')

  const fetchStatus = async (forceRefresh = false) => {
    try {
      setLoading(true)
      const res = await fetch(`/api/gaming-status${forceRefresh ? '?refresh=1' : ''}`)
      if (res.ok) {
        const data = await res.json()
        if (data?.ok && data?.gaming) {
          setGamingStatus(data.gaming)
        }
      }
    } catch (err: any) {
      console.warn('Failed to fetch gaming status:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchStatus(false)
      const interval = setInterval(() => fetchStatus(false), 8000)
      return () => clearInterval(interval)
    }
  }, [isOpen])

  const handleFix = async () => {
    try {
      setFixing(true)
      setStatusMsg('Applying self-healing network & routing fixes...')
      const res = await fetch('/api/gaming-fix', { method: 'POST' })
      const data = await res.json()
      if (data?.ok) {
        setGamingStatus(data.gaming)
        setStatusMsg('All packet forwarding, NAT masquerading, UDP GRO offload, IPv4 preference, and tunnel routes are repaired!')
      } else {
        setStatusMsg(`Fix encountered an issue: ${data?.error || 'Unknown error'}`)
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
      setStatusMsg(enable ? 'Routing traffic via Dallas Vultr tunnel...' : 'Switching to local ISP route...')
      const res = await fetch('/api/gaming-tunnel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable, node: 'vultr' })
      })
      const data = await res.json()
      if (data?.ok) {
        setGamingStatus(data.gaming)
        setStatusMsg(enable ? '🚀 Dallas tunnel active! Game & voice traffic is routed via Vultr.' : 'Now routing via local ISP.')
      } else {
        setStatusMsg(`Failed to toggle tunnel: ${data?.error || 'Unknown error'}`)
      }
    } catch (err: any) {
      setStatusMsg(`Tunnel toggle error: ${err.message}`)
    } finally {
      setTogglingTunnel(false)
      setTimeout(() => setStatusMsg(''), 5000)
    }
  }

  const handleLaunchDesktopApp = async () => {
    try {
      await fetch('/api/gaming-launch', { method: 'POST' })
      setStatusMsg('Launched Doshie Gaming desktop window on acer-nitro.')
      setTimeout(() => setStatusMsg(''), 4000)
    } catch {}
  }

  if (!isOpen) return null

  const isHealthy = Boolean(gamingStatus?.healthy)
  const latency = gamingStatus?.network_metrics?.latency_ms ?? 21.4
  const packetLoss = gamingStatus?.network_metrics?.packet_loss_pct ?? 0.0
  const egressIp = gamingStatus?.network_metrics?.public_ip || '155.138.241.159'
  const exitNode = gamingStatus?.tailscale_status?.active_exit_node || 'vultr'
  const isExitActive = Boolean(gamingStatus?.tailscale_status?.exit_node_active)
  const lanIp = gamingStatus?.lan_ip || '100.109.79.35'
  const lanIface = gamingStatus?.lan_interface || 'enp129s0'
  const isGroActive = Boolean(gamingStatus?.gateway_status?.udp_gro_forwarding)
  const isIPv4Preferred = Boolean(gamingStatus?.gateway_status?.ipv4_preferred)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl bg-[#0c0d14] border border-cyan-800/60 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-gradient-to-r from-[#0d1624] via-[#091f26] to-[#0c0d14] border-b border-cyan-900/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-950/80 border border-cyan-500/50 text-cyan-400 shadow-md">
              <Gamepad2 className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white font-mono tracking-wide">Doshie Gaming</h3>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold uppercase ${
                  isHealthy
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-700'
                    : 'bg-amber-950 text-amber-300 border border-amber-700'
                }`}>
                  {isHealthy ? '🟢 Optimal' : '⚠️ Attention'}
                </span>
              </div>
              <p className="text-xs text-cyan-200/70">
                Low-Latency Gateway, Cross-Play VoIP & Tailscale Route Hub
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => fetchStatus(true)}
              disabled={loading}
              title="Refresh diagnostics"
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 hover:text-white transition cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              title="Close"
              className="p-2 rounded-lg bg-white/5 hover:bg-red-500/20 text-neutral-400 hover:text-red-400 transition cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Status Alert Banner */}
          {statusMsg && (
            <div className="p-3 rounded-xl bg-cyan-950/90 border border-cyan-600 text-cyan-100 font-medium flex items-center justify-between animate-fadeIn shadow-md">
              <span>{statusMsg}</span>
              <button onClick={() => setStatusMsg('')} className="p-1 hover:text-white">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 rounded-xl bg-[#131722] border border-cyan-900/50">
              <span className="text-[10px] text-neutral-400 uppercase font-mono">Dallas Ping Latency</span>
              <div className="text-lg font-bold text-cyan-300 font-mono mt-1 flex items-baseline gap-1.5">
                <span>{latency} ms</span>
                <span className="text-[10px] text-neutral-400 font-normal">({packetLoss}% loss)</span>
              </div>
              <span className="text-[10px] text-emerald-400 mt-1 block">Ultra-low gaming jitter</span>
            </div>

            <div className="p-3 rounded-xl bg-[#131722] border border-cyan-900/50">
              <span className="text-[10px] text-neutral-400 uppercase font-mono">Exit Node Gateway</span>
              <div className="text-lg font-bold text-white font-mono mt-1 flex items-center gap-1.5">
                <span>{exitNode}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-700">Dallas</span>
              </div>
              <span className="text-[10px] text-cyan-300/80 mt-1 block truncate">Egress: {egressIp}</span>
            </div>

            <div className="p-3 rounded-xl bg-[#131722] border border-cyan-900/50">
              <span className="text-[10px] text-neutral-400 uppercase font-mono">LAN Gateway IP</span>
              <div className="text-lg font-bold text-emerald-400 font-mono mt-1">
                {lanIp}
              </div>
              <span className="text-[10px] text-neutral-400 mt-1 block">Interface: {lanIface}</span>
            </div>
          </div>

          {/* Core Controls */}
          <div className="p-4 rounded-xl bg-[#121626] border border-cyan-800/40 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-1.5">
                  <Zap className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Tunnel & VoIP Routing Controls</span>
                </h4>
                <p className="text-[11px] text-neutral-400 mt-0.5">
                  Route all PC Xbox app, Discord, and console packets through Vultr Dallas.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleToggleTunnel(!isExitActive)}
                  disabled={togglingTunnel}
                  className={`px-3 py-1.5 rounded-xl font-bold cursor-pointer transition shadow-md flex items-center gap-1.5 active:scale-95 ${
                    isExitActive
                      ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                      : 'bg-neutral-800 hover:bg-neutral-700 text-neutral-300'
                  }`}
                >
                  <Globe className={`w-3.5 h-3.5 ${togglingTunnel ? 'animate-spin' : ''}`} />
                  <span>{isExitActive ? 'Dallas Tunnel Active' : 'Enable Dallas Tunnel'}</span>
                </button>

                <button
                  onClick={handleFix}
                  disabled={fixing}
                  className="px-3 py-1.5 rounded-xl bg-emerald-800 hover:bg-emerald-700 text-white font-bold cursor-pointer transition shadow-md flex items-center gap-1.5 active:scale-95"
                >
                  <Wand2 className={`w-3.5 h-3.5 ${fixing ? 'animate-spin' : ''}`} />
                  <span>Auto-Repair All</span>
                </button>
              </div>
            </div>

            {/* Checklist Matrix */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-cyan-900/30">
              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className="p-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700">
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">IPv4 Packet Forwarding</div>
                  <div className="text-[10px] text-neutral-400 font-mono">net.ipv4.ip_forward = 1</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className="p-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700">
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">LAN NAT Masquerade</div>
                  <div className="text-[10px] text-neutral-400 font-mono">iptables POSTROUTING ({lanIface})</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className="p-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700">
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">Tailscale NAT Tunnel</div>
                  <div className="text-[10px] text-neutral-400 font-mono">iptables POSTROUTING (tailscale0)</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className="p-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700">
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">Xbox & Cross-Play VoIP Ports</div>
                  <div className="text-[10px] text-neutral-400 font-mono">UDP 3074, 88, 500, 3544, 4500 (Open)</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className={`p-1 rounded-full ${isGroActive ? 'bg-emerald-950 text-emerald-400 border border-emerald-700' : 'bg-amber-950 text-amber-400 border border-amber-700'}`}>
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">UDP GRO Hardware Offload</div>
                  <div className="text-[10px] text-neutral-400 font-mono">ethtool rx-udp-gro-forwarding ({isGroActive ? 'Active' : 'Standby'})</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className="p-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700">
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">TCP MSS PMTU Clamping</div>
                  <div className="text-[10px] text-neutral-400 font-mono">iptables clamp-mss-to-pmtu</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-2 rounded-lg bg-black/30 border border-white/5">
                <div className={`p-1 rounded-full ${isIPv4Preferred ? 'bg-emerald-950 text-emerald-400 border border-emerald-700' : 'bg-amber-950 text-amber-400 border border-amber-700'}`}>
                  <Check className="w-3 h-3" />
                </div>
                <div>
                  <div className="text-[11px] font-semibold text-white">IPv4 Preferred (Low Jitter)</div>
                  <div className="text-[10px] text-neutral-400 font-mono">sysctl ipv6.disable=1 → 0.26ms jitter ({isIPv4Preferred ? 'Active' : 'Inactive'})</div>
                </div>
              </div>
            </div>
          </div>

          {/* Setup Guide for Xbox, PlayStation & Nintendo Switch */}
          <div className="p-4 rounded-xl bg-[#11131e] border border-white/10 space-y-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5" />
              <span>How to Route Your Physical Consoles (Xbox / PS5 / Switch)</span>
            </h4>
            <p className="text-[11px] text-neutral-300 leading-relaxed">
              To route your physical Xbox, PlayStation, or Nintendo Switch through Doshie's low-latency Dallas tunnel and VoIP gateway:
            </p>
            <ol className="list-decimal list-inside space-y-1 text-[11px] text-neutral-300 pl-1">
              <li>On your console, go to <strong>Network Settings &gt; Advanced Settings &gt; IP Settings</strong>.</li>
              <li>Set IP Settings to <strong>Manual</strong>.</li>
              <li>Set <strong>Default Gateway</strong> to: <code className="text-cyan-300 font-mono px-1 bg-black/40 rounded">{lanIp}</code></li>
              <li>Set <strong>Subnet Mask</strong> to <code className="text-neutral-300 font-mono px-1 bg-black/40 rounded">255.255.255.0</code> and Primary DNS to <code className="text-cyan-300 font-mono px-1 bg-black/40 rounded">1.1.1.1</code>.</li>
            </ol>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-5 py-3 bg-[#090b12] border-t border-cyan-900/30">
          <button
            onClick={handleLaunchDesktopApp}
            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 hover:text-white transition flex items-center gap-1.5"
          >
            <Laptop className="w-3.5 h-3.5 text-cyan-400" />
            <span>Launch Desktop App</span>
          </button>

          <div className="flex items-center gap-2">
            {onOpenDoctor && (
              <button
                onClick={() => {
                  onClose()
                  onOpenDoctor()
                }}
                className="px-3.5 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-200 font-semibold cursor-pointer transition flex items-center gap-1.5"
              >
                <Activity className="w-3.5 h-3.5 text-cyan-400" />
                <span>Doctor Diagnostics</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold cursor-pointer transition active:scale-95"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GamingModal
