import React from 'react'
import { X, ExternalLink, Mic, RefreshCw } from 'lucide-react'

interface VoiceStudioModalProps {
  isOpen: boolean
  onClose: () => void
}

export const VoiceStudioModal: React.FC<VoiceStudioModalProps> = ({ isOpen, onClose }) => {
  const [iframeKey, setIframeKey] = React.useState(0)

  if (!isOpen) return null

  // Embedded Studio URL proxied through Doshie backend for full HTTPS/LAN/Tailscale support
  const studioUrl = '/voice-studio/'

  const handleRefresh = () => {
    setIframeKey((prev) => prev + 1)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-150"
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), 38px)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), 8px)',
      }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-6xl h-full sm:h-[92vh] sm:max-h-[860px] bg-[var(--bg-dark)] border-0 sm:border border-[var(--border-dark)] rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden text-neutral-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 sm:py-3 bg-[var(--card-dark)]/95 border-b border-[var(--border-dark)] shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-500 flex items-center justify-center shadow-sm shrink-0">
              <Mic className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs sm:text-sm font-bold text-white tracking-wide truncate">Voice Studio & Changer</h3>
                <span className="text-[9px] font-semibold uppercase tracking-wider px-1 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shrink-0">
                  RTX 5070
                </span>
              </div>
              <p className="hidden sm:block text-[11px] text-[var(--accent-light)]/80">
                Zero-Shot Voice Cloning · Voice Conversion · Realtime Kokoro Neural TTS
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={handleRefresh}
              title="Reload Studio"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--accent)]/30 border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs font-medium"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Reload</span>
            </button>

            <a
              href={studioUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                if ((window as any).electron?.shell?.openExternal) {
                  e.preventDefault()
                  ;(window as any).electron.shell.openExternal(window.location.origin + studioUrl)
                }
              }}
              title="Open studio in separate browser tab"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--accent)]/30 border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs font-medium"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden md:inline">New Tab</span>
            </a>

            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-rose-500/20 border border-[var(--border-dark)] hover:border-rose-500/40 text-neutral-400 hover:text-rose-300 transition-all cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Embedded Iframe */}
        <div className="flex-1 w-full bg-[#0b0f19] relative overflow-hidden">
          <iframe
            key={iframeKey}
            src={studioUrl}
            title="Doshie Voice Studio"
            className="w-full h-full border-0"
            allow="microphone; camera; clipboard-write;"
          />
        </div>
      </div>
    </div>
  )
}
