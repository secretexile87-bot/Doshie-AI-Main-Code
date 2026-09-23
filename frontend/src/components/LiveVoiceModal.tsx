import React, { useState, useEffect, useRef } from 'react'
import {
  X,
  Mic,
  Volume2,
  VolumeX,
  Sparkles,
  PhoneOff,
  Radio,
  RotateCcw
} from 'lucide-react'
import { playNeuralSpeech, stopSpeech } from '../utils/audio'

interface LiveVoiceModalProps {
  isOpen: boolean
  onClose: () => void
  activeProfile: string
  onMessageCreated: (userText: string, assistantReply: string) => void
}

type VoiceState = 'idle' | 'listening' | 'thinking' | 'speaking'

export const LiveVoiceModal: React.FC<LiveVoiceModalProps> = ({
  isOpen,
  onClose,
  activeProfile,
  onMessageCreated,
}) => {
  const [voiceState, setVoiceState] = useState<VoiceState>('idle')
  const [transcript, setTranscript] = useState('')
  const [assistantText, setAssistantText] = useState('')
  const [isMuted, setIsMuted] = useState(false)
  const isCancelledRef = useRef(false)
  const isContinuousRef = useRef(true)

  const unlockAudioContext = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      if (AudioCtx) {
        const ctx = new AudioCtx()
        if (ctx.state === 'suspended') {
          ctx.resume()
        }
      }
      const audio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA')
      audio.play().catch(() => {})
    } catch {}
  }

  const ensureMicrophonePermission = async (): Promise<boolean> => {
    if (getNativeSpeech()) return true
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((track) => track.stop())
        return true
      }
    } catch (err) {
      console.warn('Microphone permission request failed:', err)
      return false
    }
    return true
  }

  const getNativeSpeech = () => {
    const cap = (window as any).Capacitor
    if (!cap) return null
    if (cap.Plugins?.DiYoshiSpeech) return cap.Plugins.DiYoshiSpeech
    if (cap.Plugins?.DoshieSpeech) return cap.Plugins.DoshieSpeech
    return typeof cap.registerPlugin === 'function'
      ? (cap.registerPlugin('DiYoshiSpeech') || cap.registerPlugin('DoshieSpeech'))
      : null
  }

  // Play assistant voice using neural Kokoro / cloned TTS
  const playSpeech = async (text: string): Promise<void> => {
    if (isCancelledRef.current) return

    setVoiceState('speaking')
    try {
      await playNeuralSpeech(text, {
        profile: activeProfile,
        engine: 'kokoro',
        onStart: () => {
          if (!isCancelledRef.current) setVoiceState('speaking')
        },
      })
    } catch (err) {
      console.warn('Voice playback fallback', err)
    }
  }

  // Handle a single turn of voice conversation
  const runVoiceTurn = async () => {
    if (isCancelledRef.current || isMuted) return

    setVoiceState('listening')
    setTranscript('')

    let userSpoken = ''

    const nativeSpeech = getNativeSpeech()
    if (nativeSpeech) {
      try {
        const result = await nativeSpeech.startListening({
          language: navigator.language || 'en-US',
        })
        userSpoken = String(result?.text || '').trim()
      } catch (err) {
        console.warn('Speech recognition ended/timed out', err)
      }
    } else {
      const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (!SpeechRec) {
        setVoiceState('idle')
        setAssistantText('Live speech recognition is not supported in this browser. Please use Chrome, Edge, or Android.')
        return
      }

      try {
        userSpoken = await new Promise<string>((resolve) => {
          let lastRecognized = ''
          let isResolved = false
          let recognitionInstance: any = null

          const finish = (text: string) => {
            if (isResolved) return
            isResolved = true
            try {
              if (recognitionInstance) recognitionInstance.stop()
            } catch {}
            resolve(text.trim())
          }

          try {
            const rec = new SpeechRec()
            recognitionInstance = rec
            rec.continuous = false
            rec.interimResults = true
            rec.lang = navigator.language || 'en-US'

            rec.onresult = (e: any) => {
              let currentText = ''
              for (let i = 0; i < e.results.length; i++) {
                const fragment = e.results[i][0]?.transcript || ''
                currentText += (currentText ? ' ' : '') + fragment
              }
              if (currentText) {
                lastRecognized = currentText
                setTranscript(currentText)
              }

              const lastResult = e.results[e.results.length - 1]
              if (lastResult?.isFinal) {
                setTimeout(() => finish(lastRecognized), 250)
              }
            }

            rec.onerror = (err: any) => {
              console.warn('Speech recognition error:', err?.error || err)
              if (err?.error === 'not-allowed') {
                setAssistantText('Microphone permission blocked. Please allow microphone access in your browser.')
                finish('')
                return
              }
              finish(lastRecognized)
            }

            rec.onend = () => {
              finish(lastRecognized)
            }

            rec.start()
          } catch (startErr) {
            console.warn('Recognition start failed:', startErr)
            finish('')
          }
        })
      } catch {
        userSpoken = ''
      }
    }

    if (isCancelledRef.current) return

    if (!userSpoken) {
      // If nothing heard, pause briefly and loop back to listen
      if (isContinuousRef.current && !isCancelledRef.current) {
        setVoiceState('idle')
        setTimeout(() => {
          if (isContinuousRef.current && !isCancelledRef.current) {
            runVoiceTurn()
          }
        }, 800)
      }
      return
    }

    setTranscript(userSpoken)
    setVoiceState('thinking')

    try {
      const chatRes = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userSpoken,
          profile: activeProfile,
        }),
      })

      if (!chatRes.ok) throw new Error(`Chat failed with status ${chatRes.status}`)
      const data = await chatRes.json()
      const reply = String(data.reply || '').trim()

      if (reply) {
        setAssistantText(reply)
        onMessageCreated(userSpoken, reply)
        await playSpeech(reply)
      }
    } catch (err: any) {
      console.error('Turn error', err)
      setAssistantText(`Connection issue: ${err.message || 'failed to get response'}`)
    }

    // Continue conversation loop
    if (isContinuousRef.current && !isCancelledRef.current) {
      setTimeout(() => {
        if (isContinuousRef.current && !isCancelledRef.current) {
          runVoiceTurn()
        }
      }, 400)
    } else {
      setVoiceState('idle')
    }
  }

  // Start live session when modal opens
  useEffect(() => {
    if (isOpen) {
      isCancelledRef.current = false
      isContinuousRef.current = true
      setAssistantText('I’m listening. Talk to me anytime!')
      unlockAudioContext()
      ensureMicrophonePermission().then(() => {
        if (!isCancelledRef.current) {
          runVoiceTurn()
        }
      })
    } else {
      isCancelledRef.current = true
      isContinuousRef.current = false
      stopSpeech()
      const nativeSpeech = getNativeSpeech()
      if (nativeSpeech) {
        nativeSpeech.stopListening().catch(() => {})
      }
    }

    return () => {
      isCancelledRef.current = true
      isContinuousRef.current = false
      stopSpeech()
    }
  }, [isOpen])

  const handleInterrupt = () => {
    stopSpeech()
    runVoiceTurn()
  }

  const handleToggleMute = () => {
    setIsMuted(!isMuted)
    if (isMuted) {
      runVoiceTurn()
    } else {
      setVoiceState('idle')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-between bg-[var(--bg-dark)]/95 backdrop-blur-2xl p-6 sm:p-8 animate-in fade-in duration-300 select-none text-neutral-100">
      {/* Top Controls */}
      <div className="w-full max-w-xl flex items-center justify-between z-10 pt-[max(env(safe-area-inset-top,0px),var(--native-safe-top,0px),12px)]">
        <div className="flex items-center gap-2.5 bg-[var(--card-dark)] border border-[var(--border-dark)] px-3.5 py-1.5 rounded-full shadow-lg">
          <Radio className="w-4 h-4 text-[var(--accent)] animate-pulse" />
          <span className="text-xs font-semibold tracking-wider text-[var(--accent-light)] uppercase">Live Voice Mode</span>
        </div>

        <button
          onClick={onClose}
          className="p-2 rounded-full bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] text-[var(--accent-light)] hover:text-white transition-all shadow-md active:scale-95 cursor-pointer"
          title="Exit Live Talk"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Center Interactive Orb & Visualizer */}
      <div className="flex-1 flex flex-col items-center justify-center my-auto w-full max-w-md text-center">
        <div className="relative flex items-center justify-center my-8">
          {/* Pulsing Outer Rings */}
          <div
            className={`absolute w-44 h-44 sm:w-56 sm:h-56 rounded-full transition-all duration-700 pointer-events-none ${
              voiceState === 'speaking'
                ? 'bg-gradient-to-tr from-[var(--accent)]/30 to-[var(--accent-light)]/30 animate-ping opacity-60 scale-125'
                : voiceState === 'listening'
                ? 'bg-gradient-to-tr from-[var(--accent)]/20 to-[var(--accent-light)]/20 animate-pulse scale-110'
                : voiceState === 'thinking'
                ? 'bg-amber-500/20 animate-pulse'
                : 'bg-[var(--accent)]/10'
            }`}
          />

          <div
            className={`absolute w-36 h-36 sm:w-48 sm:h-48 rounded-full blur-xl transition-all duration-500 ${
              voiceState === 'speaking'
                ? 'bg-[var(--accent)]/40'
                : voiceState === 'listening'
                ? 'bg-[var(--accent-light)]/30'
                : voiceState === 'thinking'
                ? 'bg-amber-400/30'
                : 'bg-[var(--accent)]/10'
            }`}
          />

          {/* Central Animated Orb */}
          <div
            onClick={voiceState === 'speaking' ? handleInterrupt : () => runVoiceTurn()}
            className={`relative w-28 h-28 sm:w-36 sm:h-36 rounded-full flex flex-col items-center justify-center shadow-2xl transition-all duration-500 cursor-pointer ${
              voiceState === 'speaking'
                ? 'bg-gradient-to-tr from-[var(--accent)] via-[var(--accent-hover)] to-[var(--accent-light)] shadow-[var(--accent)]/50 scale-105 ring-4 ring-[var(--accent-light)]/40'
                : voiceState === 'listening'
                ? 'bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-hover)] shadow-[var(--accent)]/40 ring-4 ring-[var(--accent-light)]/30 animate-pulse'
                : voiceState === 'thinking'
                ? 'bg-gradient-to-tr from-[var(--accent-hover)] to-amber-700 shadow-amber-500/30'
                : 'bg-gradient-to-tr from-[var(--card-dark)] to-[var(--card-hover)] border border-[var(--border-dark)]'
            }`}
          >
            <span className="text-4xl sm:text-5xl select-none">🦖</span>
            <div className="absolute -bottom-2 px-3 py-0.5 rounded-full bg-[var(--bg-dark)] border border-[var(--border-dark)] text-[10px] font-bold uppercase tracking-wider text-[var(--accent-light)] shadow-md">
              {voiceState === 'speaking'
                ? 'Speaking...'
                : voiceState === 'listening'
                ? 'Listening...'
                : voiceState === 'thinking'
                ? 'Thinking...'
                : 'Ready'}
            </div>
          </div>
        </div>

        {/* Live Subtitle Transcript */}
        <div className="w-full min-h-[90px] px-4 py-3 rounded-2xl bg-[var(--card-dark)]/80 border border-[var(--border-dark)] backdrop-blur-md flex flex-col items-center justify-center text-center shadow-inner">
          {voiceState === 'listening' && (
            <p className="text-sm sm:text-base text-white font-medium animate-pulse">
              {transcript ? `"${transcript}"` : 'Listening to you... speak freely'}
            </p>
          )}

          {voiceState === 'thinking' && (
            <div className="flex items-center gap-2 text-xs sm:text-sm text-[var(--accent-light)]">
              <Sparkles className="w-4 h-4 animate-spin text-[var(--accent)]" />
              <span>Doshie is preparing an answer...</span>
            </div>
          )}

          {voiceState === 'speaking' && (
            <p className="text-xs sm:text-sm text-neutral-100 font-normal line-clamp-3 leading-relaxed">
              {assistantText}
            </p>
          )}

          {voiceState === 'idle' && (
            <p className="text-xs sm:text-sm text-[var(--accent-light)]/80">
              {assistantText || 'Tap the microphone or say something to start.'}
            </p>
          )}
        </div>
      </div>

      {/* Bottom Action Dock */}
      <div className="w-full max-w-md flex items-center justify-center gap-5 z-10 pb-[max(env(safe-area-inset-bottom,0px),var(--native-safe-bottom,0px),16px)]">
        {/* Mute Button */}
        <button
          onClick={handleToggleMute}
          className={`p-3.5 rounded-full border transition-all active:scale-95 shadow-lg cursor-pointer ${
            isMuted
              ? 'bg-rose-950/80 border-rose-700 text-rose-300'
              : 'bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border-[var(--border-dark)] text-[var(--accent-light)] hover:text-white'
          }`}
          title={isMuted ? 'Unmute' : 'Mute'}
        >
          {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
        </button>

        {/* Big End Session Button */}
        <button
          onClick={onClose}
          className="flex items-center gap-2.5 px-6 py-3.5 rounded-full bg-rose-600 hover:bg-rose-500 active:scale-95 text-white font-semibold text-sm shadow-xl shadow-rose-950/60 transition-all cursor-pointer"
        >
          <PhoneOff className="w-5 h-5" />
          <span>End Live Talk</span>
        </button>

        {/* Interrupt / Repeat Turn */}
        <button
          onClick={handleInterrupt}
          className="p-3.5 rounded-full bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] text-[var(--accent-light)] hover:text-white transition-all active:scale-95 shadow-lg cursor-pointer"
          title="Interrupt / Next Turn"
        >
          {voiceState === 'speaking' ? <Mic className="w-5 h-5 text-[var(--accent)]" /> : <RotateCcw className="w-5 h-5" />}
        </button>
      </div>
    </div>
  )
}
