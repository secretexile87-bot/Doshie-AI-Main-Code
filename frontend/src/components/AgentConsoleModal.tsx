import React, { useState, useEffect } from 'react'
import { X, ExternalLink, Bot, Minus, ShieldCheck, ArrowLeft } from 'lucide-react'

interface AgentConsoleModalProps {
  isOpen: boolean
  onClose: () => void
}

export const AgentConsoleModal: React.FC<AgentConsoleModalProps> = ({ isOpen, onClose }) => {
  // Remember if modal was ever opened so we don't load the iframe until first use
  const [hasEverOpened, setHasEverOpened] = useState(isOpen)

  useEffect(() => {
    if (isOpen && !hasEverOpened) {
      setHasEverOpened(true)
    }
  }, [isOpen, hasEverOpened])

  // Listen for close message from embedded iframe
  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && e.data.type === 'close_agent_console') {
        onClose()
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [onClose])

  const handleOpenExternal = async (e: React.MouseEvent) => {
    e.preventDefault()
    const fullUrl = window.location.origin + '/agent-console/'
    if ((window as any).Capacitor?.Plugins?.Browser?.open) {
      try {
        await (window as any).Capacitor.Plugins.Browser.open({ url: fullUrl })
        return
      } catch (err) {
        console.warn('Capacitor browser open failed', err)
      }
    }
    if ((window as any).electron?.shell?.openExternal) {
      try {
        ;(window as any).electron.shell.openExternal(fullUrl)
        return
      } catch (err) {}
    }
    window.open(fullUrl, '_blank')
  }

  // Embedded agent console URL proxied through Doshie backend for full HTTPS/Tailscale support
  const consoleUrl = '/agent-console/'

  if (!hasEverOpened) return null

  return (
    <div
      className={`fixed inset-0 flex items-center justify-center p-0 sm:p-4 bg-black/85 backdrop-blur-md transition-all duration-200 ${
        isOpen
          ? 'z-50 opacity-100 pointer-events-auto'
          : 'z-[-50] opacity-0 pointer-events-none'
      }`}
      style={{
        transform: isOpen ? 'scale(1)' : 'scale(0.96)',
        transition: 'opacity 0.18s ease, transform 0.18s ease, z-index 0.18s ease',
      }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-6xl h-full sm:h-[92vh] sm:max-h-[920px] bg-[var(--bg-dark)] border-0 sm:border border-[var(--border-dark)] rounded-none sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden text-neutral-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div
          className="flex items-center justify-between px-3 sm:px-4 py-2.5 bg-[var(--card-dark)]/90 border-b border-[var(--border-dark)] flex-wrap gap-2"
          style={{
            paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 10px)',
          }}
        >
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-[var(--card-hover)] hover:bg-[var(--bg-dark)] border border-[var(--border-dark)] text-neutral-300 hover:text-white transition-colors cursor-pointer flex items-center gap-1 text-xs font-semibold sm:hidden"
              title="Back to chat"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-500 flex items-center justify-center shadow-sm flex-none">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">Agent Console</h3>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-emerald-400" />
                  Approval Controlled
                </span>
              </div>
              <p className="text-[11px] text-[var(--accent-light)]/80 hidden sm:block">
                Autonomous pairing agent · Run commands · Code edits · File system
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Minimize Button */}
            <button
              onClick={onClose}
              title="Minimize console to background"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--card-dark)] border border-[var(--border-dark)] hover:border-neutral-500 text-neutral-300 hover:text-white transition-all cursor-pointer"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>

            {/* Pop Out Button */}
            <button
              onClick={handleOpenExternal}
              title="Open Agent Console in separate window"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--accent)]/30 border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs font-medium"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Pop Out</span>
            </button>

            {/* Close Button ("X") */}
            <button
              onClick={onClose}
              title="Close window"
              className="px-2.5 py-1.5 rounded-xl bg-rose-950/60 hover:bg-rose-900/80 border border-rose-500/50 hover:border-rose-400 text-rose-200 hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs font-semibold shadow-sm"
            >
              <X className="w-4 h-4" />
              <span>Close</span>
            </button>
          </div>
        </div>

        {/* Embedded Agent Console Iframe */}
        <div className="flex-1 w-full h-full bg-[#0c0f17] relative">
          <iframe
            src={consoleUrl}
            title="Doshie Agent Console"
            className="w-full h-full border-0"
            allow="clipboard-read; clipboard-write"
          />
        </div>
      </div>
    </div>
  )
}
