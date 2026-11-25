import { useState, useRef, useEffect } from 'react'
import type { FormEvent } from 'react'
import { ShieldCheck, Lock, AlertCircle, X, Loader2 } from 'lucide-react'

interface UnlockModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  profileName?: string
}

export const UnlockModal = ({
  isOpen,
  onClose,
  onSuccess,
  profileName = 'Hermes'
}: UnlockModalProps) => {
  const [pin, setPin] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (isOpen) {
      setPin('')
      setError(null)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleUnlock = async (e?: FormEvent) => {
    if (e) e.preventDefault()
    if (!pin.trim() || loading) return

    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/profile-lock/unlock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: profileName,
          pin: pin.trim(),
          credential: pin.trim()
        })
      })

      const data = await res.json()

      if (res.ok && data?.unlocked) {
        onSuccess()
        onClose()
      } else {
        setError(data?.error || 'Authorization failed. Incorrect PIN code.')
      }
    } catch (err: any) {
      setError(`Connection failure: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      <div 
        className="relative w-full max-w-sm rounded-2xl bg-zinc-950 border border-cyan-500/40 p-6 shadow-[0_0_40px_rgba(6,182,212,0.25)] flex flex-col items-center text-center animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-zinc-900 transition-colors cursor-pointer"
          aria-label="Close modal"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Lock Graphic */}
        <div className="relative flex items-center justify-center w-14 h-14 rounded-full bg-cyan-950/80 border border-cyan-400/60 mb-4 shadow-[0_0_20px_rgba(6,182,212,0.3)]">
          <Lock className="w-6 h-6 text-cyan-400 animate-pulse" />
        </div>

        {/* Header */}
        <div className="font-mono text-xs uppercase tracking-widest text-cyan-400 mb-1">
          {profileName} // Clearance
        </div>
        <h2 className="text-lg font-bold text-slate-100 mb-2">
          Profile Session Locked
        </h2>
        <p className="text-xs text-slate-400 mb-6 max-w-xs">
          Enter your security PIN or password to authorize this device and converse with Doshie.
        </p>

        {/* Error Alert */}
        {error && (
          <div className="w-full flex items-center gap-2 p-2.5 mb-4 rounded-lg bg-rose-950/60 border border-rose-500/40 text-rose-300 text-xs text-left">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
            <span className="flex-1">{error}</span>
          </div>
        )}

        {/* PIN Form */}
        <form onSubmit={handleUnlock} className="w-full flex flex-col gap-4">
          <div className="relative w-full">
            <input
              ref={inputRef}
              type="password"
              inputMode="numeric"
              maxLength={16}
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              placeholder="••••"
              className="w-full text-center text-2xl tracking-[0.5em] font-mono py-3 px-4 rounded-xl bg-zinc-900/90 border border-zinc-700 focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 text-cyan-200 outline-none transition-all placeholder:text-zinc-600 placeholder:tracking-normal placeholder:text-sm"
              disabled={loading}
              autoComplete="current-password"
            />
          </div>

          <div className="flex items-center gap-2 w-full pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 py-2.5 px-4 rounded-xl border border-zinc-800 bg-zinc-900/80 text-xs font-mono text-slate-300 hover:bg-zinc-850 hover:text-white transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!pin.trim() || loading}
              className="flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-cyan-400/50 bg-cyan-500/20 text-xs font-mono font-semibold text-cyan-300 hover:bg-cyan-500/30 transition-all shadow-[0_0_15px_rgba(6,182,212,0.25)] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
                  <span>Verifying...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Authorize</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
