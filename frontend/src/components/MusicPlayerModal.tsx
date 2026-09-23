import React, { useState, useEffect } from 'react'
import { X, ExternalLink, Disc, Minus, Square, Check } from 'lucide-react'

interface MusicPlayerModalProps {
  isOpen: boolean
  onClose: () => void
}

export const MusicPlayerModal: React.FC<MusicPlayerModalProps> = ({ isOpen, onClose }) => {
  // Remember if modal was ever opened so we don't load the iframe until first use
  const [hasEverOpened, setHasEverOpened] = useState(isOpen)
  const [keepInBackground, setKeepInBackground] = useState<boolean>(() => {
    const saved = localStorage.getItem('doshie_music_keep_in_background')
    return saved !== null ? saved === 'true' : true // Default to true as requested
  })

  useEffect(() => {
    if (isOpen && !hasEverOpened) {
      setHasEverOpened(true)
    }
  }, [isOpen, hasEverOpened])

  useEffect(() => {
    const handleMessage = (e: MessageEvent) => {
      if (e.data && e.data.type === 'open_external_url' && e.data.url) {
        const url = e.data.url
        if ((window as any).Capacitor?.Plugins?.Browser?.open) {
          try {
            ;(window as any).Capacitor.Plugins.Browser.open({ url })
            return
          } catch (err) {}
        }
        if ((window as any).electron?.shell?.openExternal) {
          try {
            ;(window as any).electron.shell.openExternal(url)
            return
          } catch (err) {}
        }
        window.open(url, '_blank')
      }
    }
    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [])

  const handleToggleKeepInBackground = () => {
    const next = !keepInBackground
    setKeepInBackground(next)
    localStorage.setItem('doshie_music_keep_in_background', String(next))
  }

  const handleClose = async () => {
    if (!keepInBackground) {
      // If user chose NOT to keep in background, stop music on close
      try {
        await fetch('/music/api/stop', { method: 'POST' })
      } catch (e) {}
    }
    onClose()
  }

  const handleStopAndClose = async () => {
    try {
      await fetch('/music/api/stop', { method: 'POST' })
    } catch (e) {}
    onClose()
  }

  // Do not mount iframe until first opened
  if (!hasEverOpened) return null

  // Embedded player URL proxied through Doshie backend for full HTTPS/Tailscale support
  const playerUrl = '/music/'

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
      onClick={handleClose}
    >
      <div
        className="relative w-full max-w-5xl h-full sm:h-[90vh] sm:max-h-[820px] bg-[var(--bg-dark)] border-0 sm:border border-[var(--border-dark)] rounded-none sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden text-neutral-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between px-3 sm:px-4 py-2.5 bg-[var(--card-dark)]/90 border-b border-[var(--border-dark)] flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-500 flex items-center justify-center shadow-sm flex-none">
              <Disc className="w-4 h-4 text-white animate-spin [animation-duration:8s]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">Music Player</h3>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Universal Audio
                </span>
              </div>
              <p className="text-[11px] text-[var(--accent-light)]/80">
                Spotify · YouTube Music · SoundCloud · Live Radio
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Background Play Toggle Option */}
            <button
              onClick={handleToggleKeepInBackground}
              title="When enabled, music continues playing in the background when you close this window"
              className={`px-2.5 py-1.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                keepInBackground
                  ? 'bg-emerald-950/70 border-emerald-500/50 text-emerald-300 hover:bg-emerald-900/80 shadow-sm'
                  : 'bg-[var(--card-hover)] border-[var(--border-dark)] text-neutral-400 hover:text-white'
              }`}
            >
              <div
                className={`w-3.5 h-3.5 rounded-md flex items-center justify-center border text-[9px] ${
                  keepInBackground
                    ? 'bg-emerald-500 border-emerald-400 text-black'
                    : 'border-neutral-500'
                }`}
              >
                {keepInBackground && <Check className="w-2.5 h-2.5 stroke-[3]" />}
              </div>
              <span className="hidden sm:inline">Play in Background</span>
              <span className="sm:hidden">Background</span>
            </button>

            {/* Quick Stop Button */}
            <button
              onClick={handleStopAndClose}
              title="Stop playback immediately and close"
              className="p-1.5 rounded-xl bg-rose-950/40 hover:bg-rose-900/60 border border-rose-500/30 hover:border-rose-500/60 text-rose-300 transition-all cursor-pointer flex items-center gap-1 text-xs font-semibold"
            >
              <Square className="w-3.5 h-3.5 fill-rose-400 text-rose-400" />
              <span className="hidden md:inline">Stop</span>
            </button>

            {/* Minimize Button */}
            <button
              onClick={handleClose}
              title="Minimize player to background"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--card-dark)] border border-[var(--border-dark)] hover:border-neutral-500 text-neutral-300 hover:text-white transition-all cursor-pointer"
            >
              <Minus className="w-3.5 h-3.5" />
            </button>

            {/* Pop Out Button */}
            <a
              href={playerUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => {
                if ((window as any).electron?.shell?.openExternal) {
                  e.preventDefault()
                  ;(window as any).electron.shell.openExternal(window.location.origin + playerUrl)
                }
              }}
              title="Open player in separate tab"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--accent)]/30 border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs font-medium"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">Pop Out</span>
            </a>

            {/* Close Button ("X") */}
            <button
              onClick={handleClose}
              title={keepInBackground ? "Close window (keeps playing in background)" : "Close window and stop music"}
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-rose-950/60 border border-[var(--border-dark)] hover:border-rose-500/50 text-neutral-400 hover:text-rose-300 transition-all cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Embedded Universal Music Player Iframe */}
        <div className="flex-1 w-full h-full bg-[#0c0f17] relative">
          <iframe
            src={playerUrl}
            title="Antigravity Universal Music Player"
            className="w-full h-full border-0"
            allow="autoplay; encrypted-media; microphone; clipboard-read; clipboard-write"
          />
        </div>
      </div>
    </div>
  )
}
