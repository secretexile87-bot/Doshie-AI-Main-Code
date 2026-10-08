import React, { useState, useRef, useEffect } from 'react'
import { Mic, Music, Terminal, Lock, Plus, X } from 'lucide-react'
import { playWakeChime } from '../utils/audio'
import type { GuiCustomization } from '../types'

interface QuickWakeWidgetProps {
  customization: GuiCustomization
  onQuickWake: () => void
  onOpenMusicPlayer?: () => void
  onOpenAgentConsole?: () => void
  onNewChat?: () => void
  onLockAccount?: () => void
  isLocked?: boolean
}

export const QuickWakeWidget: React.FC<QuickWakeWidgetProps> = ({
  customization,
  onQuickWake,
  onOpenMusicPlayer,
  onOpenAgentConsole,
  onNewChat,
  onLockAccount,
  isLocked = false,
}) => {
  // If explicitly disabled in customization, don't render
  if (customization.quickWakeWidgetEnabled === false) {
    return null
  }

  // If locked and not configured to show on lock screen, don't render
  if (isLocked && customization.quickWakeWidgetShowOnLock === false) {
    return null
  }

  const [isOpenMenu, setIsOpenMenu] = useState(false)
  const [isPressed, setIsPressed] = useState(false)
  const [position, setPosition] = useState<{ x: number; y: number }>(() => {
    try {
      const saved = localStorage.getItem('doshie_quick_wake_pos')
      if (saved) return JSON.parse(saved)
    } catch {}
    // Default: bottom right floating dock
    return { x: window.innerWidth - 76, y: window.innerHeight - 150 }
  })

  const isDraggingRef = useRef(false)
  const dragStartPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 })
  const widgetStartPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 })
  const hasMovedRef = useRef(false)

  // Clamp within viewport on resize
  useEffect(() => {
    const handleResize = () => {
      setPosition(prev => ({
        x: Math.min(Math.max(16, prev.x), window.innerWidth - 68),
        y: Math.min(Math.max(16, prev.y), window.innerHeight - 78),
      }))
    }
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Drag handlers
  const handlePointerDown = (e: React.PointerEvent) => {
    isDraggingRef.current = true
    hasMovedRef.current = false
    dragStartPosRef.current = { x: e.clientX, y: e.clientY }
    widgetStartPosRef.current = { ...position }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!isDraggingRef.current) return
    const dx = e.clientX - dragStartPosRef.current.x
    const dy = e.clientY - dragStartPosRef.current.y
    if (Math.abs(dx) > 5 || Math.abs(dy) > 5) {
      hasMovedRef.current = true
    }
    const newX = Math.min(Math.max(16, widgetStartPosRef.current.x + dx), window.innerWidth - 68)
    const newY = Math.min(Math.max(16, widgetStartPosRef.current.y + dy), window.innerHeight - 78)
    setPosition({ x: newX, y: newY })
  }

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!isDraggingRef.current) return
    isDraggingRef.current = false
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId)
      localStorage.setItem('doshie_quick_wake_pos', JSON.stringify(position))
    } catch {}
  }

  const handleWidgetClick = () => {
    if (hasMovedRef.current) return
    // Play Wake Chime with user's configured sound & volume
    playWakeChime(
      customization.wakeSoundType,
      customization.wakeSoundVolume,
      customization.wakeSoundCustomUrl
    )
    setIsPressed(true)
    setTimeout(() => setIsPressed(false), 300)
    onQuickWake()
  }

  const assistantEmoji = customization.assistantEmoji || '🦖'

  return (
    <div
      style={{
        transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        touchAction: 'none',
      }}
      className="fixed top-0 left-0 z-[9990] select-none pointer-events-auto"
    >
      {/* Quick Action Dial Popover Menu */}
      {isOpenMenu && (
        <div className="absolute bottom-16 right-0 mb-2 p-2 bg-[#0c1a11]/95 backdrop-blur-xl border border-emerald-500/40 rounded-2xl shadow-2xl shadow-emerald-950/80 flex flex-col gap-2 min-w-[160px] animate-in fade-in slide-in-from-bottom-2 duration-150">
          <div className="flex items-center justify-between pb-1 px-1 border-b border-emerald-500/20 text-[10px] text-emerald-400 font-semibold tracking-wider uppercase">
            <span>Quick Actions</span>
            <button
              onClick={() => setIsOpenMenu(false)}
              className="text-neutral-400 hover:text-white p-0.5 rounded"
            >
              <X className="w-3 h-3" />
            </button>
          </div>

          <button
            onClick={() => {
              setIsOpenMenu(false)
              handleWidgetClick()
            }}
            className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-200 text-xs font-medium transition-all text-left"
          >
            <Mic className="w-4 h-4 text-emerald-400" />
            <span>Live Voice Talk</span>
          </button>

          {onOpenMusicPlayer && (
            <button
              onClick={() => {
                setIsOpenMenu(false)
                onOpenMusicPlayer()
              }}
              className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-white/10 text-neutral-200 text-xs transition-all text-left"
            >
              <Music className="w-4 h-4 text-amber-400" />
              <span>Music Player</span>
            </button>
          )}

          {onNewChat && (
            <button
              onClick={() => {
                setIsOpenMenu(false)
                onNewChat()
              }}
              className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-white/10 text-neutral-200 text-xs transition-all text-left"
            >
              <Plus className="w-4 h-4 text-cyan-400" />
              <span>New Chat</span>
            </button>
          )}

          {onOpenAgentConsole && (
            <button
              onClick={() => {
                setIsOpenMenu(false)
                onOpenAgentConsole()
              }}
              className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-white/10 text-neutral-200 text-xs transition-all text-left"
            >
              <Terminal className="w-4 h-4 text-indigo-400" />
              <span>Terminal CLI</span>
            </button>
          )}

          {onLockAccount && (
            <button
              onClick={() => {
                setIsOpenMenu(false)
                onLockAccount()
              }}
              className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-xl hover:bg-rose-950/40 text-rose-300 text-xs transition-all text-left"
            >
              <Lock className="w-4 h-4 text-rose-400" />
              <span>Lock Screen</span>
            </button>
          )}
        </div>
      )}

      {/* Floating Main Quick-Click Bubble */}
      <div className="relative group">
        {/* Pulsing Aura */}
        <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-emerald-500/40 via-amber-500/40 to-teal-500/40 blur-xs opacity-70 group-hover:opacity-100 animate-pulse pointer-events-none" />

        <button
          type="button"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onClick={handleWidgetClick}
          onContextMenu={(e) => {
            e.preventDefault()
            setIsOpenMenu(prev => !prev)
          }}
          title="Quick Wake Doshie (Tap to speak / wake up, right-click/long-tap for menu)"
          className={`relative flex items-center justify-center w-14 h-14 rounded-full bg-[#0a180f]/95 border-2 border-emerald-400/80 shadow-2xl shadow-emerald-950 text-white transition-all duration-200 cursor-grab active:cursor-grabbing seasonal-action-pill ${
            isPressed ? 'scale-90 ring-4 ring-emerald-400/60' : 'hover:scale-105 active:scale-95'
          }`}
        >
          <span className="text-2xl filter drop-shadow select-none">{assistantEmoji}</span>
          
          {/* Glowing Mic Badge on bottom corner */}
          <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500 border border-[#0a180f] flex items-center justify-center text-black shadow-md">
            <Mic className="w-3 h-3 text-black stroke-[2.5]" />
          </div>
        </button>

        {/* Small quick menu dots button next to widget */}
        <button
          onClick={(e) => {
            e.stopPropagation()
            setIsOpenMenu(prev => !prev)
          }}
          title="Quick Menu"
          className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-[#132c1b] border border-emerald-500/40 hover:bg-emerald-600 hover:text-black flex items-center justify-center text-[10px] text-emerald-300 transition-colors cursor-pointer shadow"
        >
          {isOpenMenu ? '✕' : '⋮'}
        </button>
      </div>
    </div>
  )
}
