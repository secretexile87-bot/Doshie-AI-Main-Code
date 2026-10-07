import React, { useState, useEffect, useRef } from 'react'
import {
  X,
  Volume2,
  VolumeX,
  Sparkles,
  PhoneOff,
  Radio,
  RotateCcw,
  Sun,
  Moon,
  Square
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
  const [noSleep, setNoSleep] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('doshie_live_no_sleep')
      return saved !== null ? saved === 'true' : true
    } catch {
      return true
    }
  })
  const isCancelledRef = useRef(false)
  const isContinuousRef = useRef(true)
  const isMutedRef = useRef(false)
  const isInterruptedRef = useRef(false)
  const bargeInCleanupRef = useRef<(() => void) | null>(null)
  const recognitionRef = useRef<any>(null)
  const silenceTimerRef = useRef<any>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const activeRecorderRef = useRef<MediaRecorder | null>(null)
  const lastRecognizedRef = useRef<string>('')
  const webSpeechSupportedRef = useRef<boolean | null>(null)
  const emptyTurnCountRef = useRef(0)
  const wakeLockRef = useRef<any>(null)
  const turnRunningRef = useRef(false)

  useEffect(() => {
    isMutedRef.current = isMuted
  }, [isMuted])

  // Screen Wake Lock API management (Keep screen awake in Live Voice mode)
  const requestWakeLock = async () => {
    if (typeof navigator === 'undefined' || !('wakeLock' in navigator)) return
    try {
      if (wakeLockRef.current && !wakeLockRef.current.released) {
        return
      }
      const sentinel = await (navigator as any).wakeLock.request('screen')
      wakeLockRef.current = sentinel
      sentinel.addEventListener('release', () => {
        wakeLockRef.current = null
      })
    } catch (err: any) {
      console.debug('Wake lock request prevented or unsupported:', err?.message || err)
    }
  }

  const releaseWakeLock = async () => {
    try {
      if (wakeLockRef.current && !wakeLockRef.current.released) {
        await wakeLockRef.current.release()
      }
    } catch {}
    wakeLockRef.current = null
  }

  const toggleNoSleep = () => {
    setNoSleep((prev) => {
      const next = !prev
      try {
        localStorage.setItem('doshie_live_no_sleep', String(next))
      } catch {}
      return next
    })
  }

  useEffect(() => {
    if (!isOpen) {
      releaseWakeLock()
      return
    }

    if (noSleep) {
      requestWakeLock()
    } else {
      releaseWakeLock()
    }

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isOpen && noSleep) {
        requestWakeLock()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      releaseWakeLock()
    }
  }, [isOpen, noSleep])

  const unlockAudioContext = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
      if (AudioCtx) {
        const ctx = new AudioCtx()
        if (ctx.state === 'suspended') {
          ctx.resume().catch(() => {})
        }
        setTimeout(() => {
          try { ctx.close().catch(() => {}) } catch {}
        }, 1000)
      }
      const audio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA')
      audio.play().catch(() => {})
    } catch {}
  }

  const ensureMicrophonePermission = async (): Promise<boolean> => {
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

  const handleInterrupt = (initialSpokenText?: string) => {
    isInterruptedRef.current = true
    if (bargeInCleanupRef.current) {
      try { bargeInCleanupRef.current() } catch {}
      bargeInCleanupRef.current = null
    }
    stopSpeech()
    setVoiceState('listening')
    if (initialSpokenText && initialSpokenText.trim()) {
      const clean = initialSpokenText.trim()
      setTranscript(clean)
      lastRecognizedRef.current = clean
      setAssistantText('I hear you! Go ahead...')
    } else {
      setTranscript('')
      setAssistantText('Listening to you...')
    }
    if (voiceState !== 'speaking' && !turnRunningRef.current) {
      runVoiceTurn()
    }
  }

  // Start background microphone listener specifically during assistant speech for voice barge-in interruption
  const startBargeInListener = (onUserSpoke: (initialSpokenText?: string) => void) => {
    let cleanedUp = false
    let rec: any = null
    let stream: MediaStream | null = null
    let audioCtx: AudioContext | null = null
    let animId: number | null = null

    const cleanup = () => {
      if (cleanedUp) return
      cleanedUp = true
      if (animId) cancelAnimationFrame(animId)
      if (audioCtx) {
        audioCtx.close().catch(() => {})
        audioCtx = null
      }
      if (stream) {
        stream.getTracks().forEach((t) => t.stop())
        stream = null
      }
      if (rec) {
        try {
          rec.abort()
        } catch {}
        rec = null
      }
    }

    // Method 1: Web Speech API interim transcript detection
    const isElectron = !!(window as any).process?.versions?.electron || navigator.userAgent.includes('Electron')
    const SpeechRec = (webSpeechSupportedRef.current !== false) && !isElectron &&
      ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)

    if (SpeechRec) {
      try {
        rec = new SpeechRec()
        rec.continuous = true
        rec.interimResults = true
        rec.lang = navigator.language || 'en-US'

        rec.onresult = (e: any) => {
          if (cleanedUp || isMutedRef.current || isCancelledRef.current) return
          let heard = ''
          for (let i = 0; i < e.results.length; i++) {
            heard += (heard ? ' ' : '') + (e.results[i][0]?.transcript || '')
          }
          if (heard.trim().length > 1) {
            console.log('Voice Barge-In triggered via speech recognition:', heard)
            cleanup()
            onUserSpoke(heard.trim())
          }
        }
        rec.onerror = () => {}
        rec.start()
      } catch (e) {
        rec = null
      }
    }

    // Method 2: Microphone energy VAD with browser echo-cancellation
    if (navigator.mediaDevices?.getUserMedia) {
      navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      }).then((s) => {
        if (cleanedUp) {
          s.getTracks().forEach(t => t.stop())
          return
        }
        stream = s
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
        if (AudioCtx) {
          try {
            audioCtx = new AudioCtx()
            const source = audioCtx.createMediaStreamSource(stream)
            const analyser = audioCtx.createAnalyser()
            analyser.fftSize = 512
            analyser.smoothingTimeConstant = 0.2
            source.connect(analyser)

            const dataArray = new Uint8Array(analyser.frequencyBinCount)
            let speechFrames = 0
            let noiseFloor = 14
            let frames = 0

            const monitorAudio = () => {
              if (cleanedUp || isCancelledRef.current || isMutedRef.current) return
              analyser.getByteFrequencyData(dataArray)
              let sum = 0
              for (let i = 0; i < dataArray.length; i++) sum += dataArray[i]
              const avg = sum / dataArray.length
              frames++
              if (frames < 15) {
                noiseFloor = Math.max(6, Math.min(noiseFloor, avg))
              }
              const threshold = Math.max(22, noiseFloor + 14)
              if (avg > threshold) {
                speechFrames++
                if (speechFrames >= 3) {
                  console.log('Voice Barge-In triggered via audio energy!')
                  cleanup()
                  onUserSpoke()
                  return
                }
              } else {
                speechFrames = Math.max(0, speechFrames - 1)
              }
              animId = requestAnimationFrame(monitorAudio)
            }
            animId = requestAnimationFrame(monitorAudio)
          } catch {}
        }
      }).catch(() => {})
    }

    return cleanup
  }

  // Play assistant voice using fast neural Kokoro / multi-engine TTS (~200ms latency) with voice barge-in
  const playSpeech = async (text: string): Promise<boolean> => {
    if (isCancelledRef.current || isMutedRef.current) return false

    setVoiceState('speaking')
    isInterruptedRef.current = false

    // Start background barge-in listener so the user can interrupt by speaking
    bargeInCleanupRef.current = startBargeInListener((initialSpokenText) => {
      handleInterrupt(initialSpokenText)
    })

    try {
      await playNeuralSpeech(text, {
        profile: activeProfile,
        engine: 'auto',
        onStart: () => {
          if (!isCancelledRef.current && !isInterruptedRef.current) {
            setVoiceState('speaking')
          }
        },
      })
    } catch (err) {
      console.warn('Voice playback fallback', err)
    } finally {
      if (bargeInCleanupRef.current) {
        try { bargeInCleanupRef.current() } catch {}
        bargeInCleanupRef.current = null
      }
    }

    return isInterruptedRef.current
  }

  // Continuous Web Speech listener with natural speech cadence debounce
  const listenWithWebSpeech = (SpeechRec: any): Promise<string> => {
    return new Promise<string>((resolve) => {
      let isResolved = false
      let recognizedText = ''
      lastRecognizedRef.current = ''

      const finish = (finalText: string) => {
        if (isResolved) return
        isResolved = true
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current)
          silenceTimerRef.current = null
        }
        try {
          if (recognitionRef.current) {
            recognitionRef.current.abort()
          }
        } catch {}
        recognitionRef.current = null
        resolve(finalText.trim())
      }

      try {
        const rec = new SpeechRec()
        recognitionRef.current = rec
        rec.continuous = true
        rec.interimResults = true
        rec.lang = navigator.language || 'en-US'

        rec.onresult = (e: any) => {
          if (isCancelledRef.current || isMutedRef.current) {
            finish('')
            return
          }

          let fullText = ''
          for (let i = 0; i < e.results.length; i++) {
            const piece = e.results[i][0]?.transcript || ''
            fullText += (fullText ? ' ' : '') + piece
          }

          if (fullText.trim()) {
            recognizedText = fullText.trim()
            lastRecognizedRef.current = recognizedText
            setTranscript(recognizedText)

            // User is speaking! Allow a comfortable 1.3s pause before finalizing turn
            if (silenceTimerRef.current) {
              clearTimeout(silenceTimerRef.current)
            }
            silenceTimerRef.current = setTimeout(() => {
              finish(recognizedText)
            }, 1300)
          }
        }

        rec.onerror = (err: any) => {
          const errType = err?.error || ''
          console.warn('Web speech recognition event:', errType)

          if (errType === 'no-speech') {
            // Normal silence timeout: If speech was already received, submit it; otherwise resolve empty to keep listening smoothly
            if (recognizedText) {
              finish(recognizedText)
            } else {
              finish('')
            }
            return
          }

          if (errType === 'network' || errType === 'service-not-allowed') {
            // Network speech service offline or blocked; fall back to server Whisper STT
            webSpeechSupportedRef.current = false
            finish(recognizedText)
            return
          }

          if (errType === 'not-allowed') {
            finish('')
            return
          }

          finish(recognizedText)
        }

        rec.onend = () => {
          recognitionRef.current = null
          finish(recognizedText)
        }

        rec.start()
      } catch (err) {
        console.warn('Recognition start failed:', err)
        finish('')
      }
    })
  }

  // Audio recorder & server transcription fallback (for Electron and browsers without Google Speech)
  const recordAndTranscribe = async (): Promise<string> => {
    if (!navigator.mediaDevices?.getUserMedia) return ''

    let stream: MediaStream | null = null
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      mediaStreamRef.current = stream
    } catch (err) {
      console.warn('Microphone stream access error:', err)
      return ''
    }

    return new Promise<string>((resolve) => {
      let cleanupDone = false
      let mediaRecorder: MediaRecorder | null = null
      let audioCtx: AudioContext | null = null
      let analyser: AnalyserNode | null = null
      let animFrameId: number | null = null

      const cleanup = () => {
        if (cleanupDone) return
        cleanupDone = true
        if (animFrameId) cancelAnimationFrame(animFrameId)
        if (audioCtx) {
          audioCtx.close().catch(() => {})
          audioCtx = null
        }
        if (stream) {
          stream.getTracks().forEach((track) => track.stop())
          stream = null
          mediaStreamRef.current = null
        }
        activeRecorderRef.current = null
      }

      try {
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : MediaRecorder.isTypeSupported('audio/webm')
          ? 'audio/webm'
          : MediaRecorder.isTypeSupported('audio/ogg')
          ? 'audio/ogg'
          : ''

        const activeStream = stream!
        mediaRecorder = mimeType ? new MediaRecorder(activeStream, { mimeType }) : new MediaRecorder(activeStream)
        activeRecorderRef.current = mediaRecorder
        const chunks: Blob[] = []
        let finished = false
        let hasSpoken = false

        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext
        if (AudioCtx) {
          try {
            audioCtx = new AudioCtx()
            const source = audioCtx.createMediaStreamSource(activeStream)
            analyser = audioCtx.createAnalyser()
            analyser.fftSize = 512
            analyser.smoothingTimeConstant = 0.3
            source.connect(analyser)
          } catch {}
        }

        const finishRecording = (sendToServer: boolean) => {
          if (finished) return
          finished = true
          cleanup()
          if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            try {
              mediaRecorder.stop()
            } catch {}
          }
          if (!sendToServer) {
            resolve('')
          }
        }

        mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) {
            chunks.push(e.data)
          }
        }

        mediaRecorder.onstop = async () => {
          cleanup()
          if (!hasSpoken || chunks.length === 0) {
            resolve('')
            return
          }
          const audioBlob = new Blob(chunks, { type: mediaRecorder?.mimeType || 'audio/webm' })
          if (audioBlob.size < 2000) {
            resolve('')
            return
          }

          setVoiceState('thinking')
          setAssistantText('Transcribing speech...')
          try {
            const formData = new FormData()
            formData.append('audio', audioBlob, 'live_turn.webm')
            const res = await fetch('/transcribe', {
              method: 'POST',
              body: formData,
            })
            if (res.ok) {
              const data = await res.json()
              resolve(String(data.text || '').trim())
            } else {
              resolve('')
            }
          } catch (err) {
            console.warn('Transcription fetch failed:', err)
            resolve('')
          }
        }

        mediaRecorder.start(200)

        if (analyser) {
          const dataArray = new Uint8Array(analyser.frequencyBinCount)
          let silenceStart = 0
          let noiseFloor = 10
          let frameCount = 0
          let speechFrameCount = 0
          const recordStart = Date.now()

          const checkAudio = () => {
            if (finished || isCancelledRef.current) return
            analyser!.getByteFrequencyData(dataArray)
            let sum = 0
            for (let i = 0; i < dataArray.length; i++) {
              sum += dataArray[i]
            }
            const avg = sum / dataArray.length
            frameCount++

            if (frameCount < 20) {
              noiseFloor = Math.max(4, Math.min(noiseFloor, avg))
            }

            const speechThreshold = Math.max(12, noiseFloor + 8)
            const elapsed = Date.now() - recordStart

            if (avg > speechThreshold) {
              speechFrameCount++
              if (speechFrameCount > 3) {
                hasSpoken = true
                silenceStart = 0
              }
            } else if (hasSpoken) {
              if (silenceStart === 0) {
                silenceStart = Date.now()
              } else if (Date.now() - silenceStart > 1300) {
                // Natural 1.3s pause after speech
                finishRecording(true)
                return
              }
            } else if (elapsed > 8000) {
              // 8s ambient silence without speech - recycle loop seamlessly without server call
              finishRecording(false)
              return
            }

            if (elapsed > 18000) {
              finishRecording(hasSpoken)
              return
            }

            animFrameId = requestAnimationFrame(checkAudio)
          }
          animFrameId = requestAnimationFrame(checkAudio)
        } else {
          setTimeout(() => finishRecording(true), 6000)
        }
      } catch (err) {
        cleanup()
        resolve('')
      }
    })
  }

  // Handle a single turn of voice conversation
  const runVoiceTurn = async () => {
    if (isCancelledRef.current || isMutedRef.current) return
    turnRunningRef.current = true

    try {
      setVoiceState('listening')

      let userSpoken = ''

      // Attempt Web Speech API first (if available in Chrome desktop/mobile)
      const isElectron = !!(window as any).process?.versions?.electron || navigator.userAgent.includes('Electron')
      const SpeechRec = (webSpeechSupportedRef.current !== false) && !isElectron &&
        ((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)

      if (SpeechRec) {
        try {
          userSpoken = await listenWithWebSpeech(SpeechRec)
        } catch {
          userSpoken = ''
        }
      } else {
        webSpeechSupportedRef.current = false
      }

      // If Web Speech is unavailable (Android WebView, Capacitor, Firefox) or heard nothing, record directly and transcribe with RTX 5070 Whisper
      if (!userSpoken && !isCancelledRef.current) {
        try {
          userSpoken = await recordAndTranscribe()
        } catch (err) {
          console.warn('Whisper recording fallback error:', err)
          userSpoken = ''
        }
      }

      if (isCancelledRef.current) return

      if (!userSpoken) {
        emptyTurnCountRef.current++
        if (emptyTurnCountRef.current > 5) {
          setVoiceState('idle')
          setAssistantText('Listening paused. Tap the orb anytime to speak.')
          return
        }

        // Ambient silence - wait 400ms before next listen cycle
        if (isContinuousRef.current && !isCancelledRef.current) {
          setTimeout(() => {
            if (isContinuousRef.current && !isCancelledRef.current) {
              runVoiceTurn()
            }
          }, 400)
        }
        return
      }

      emptyTurnCountRef.current = 0

      setTranscript(userSpoken)
      setVoiceState('thinking')
      setAssistantText('Doshie is thinking...')

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
        if (data.locked || data.code === 'profile_locked') {
          setAssistantText('Account is locked. Please enter your PIN on screen to unlock Doshie.')
          setVoiceState('idle')
          return
        }

        const reply = String(data.reply || '').trim()

        if (reply) {
          setAssistantText(reply)
          onMessageCreated(userSpoken, reply)
          const wasInterrupted = await playSpeech(reply)
          if (wasInterrupted) {
            // User interrupted by voice or tap: immediately continue turn to capture full interruption
            if (isContinuousRef.current && !isCancelledRef.current) {
              setTimeout(() => {
                if (isContinuousRef.current && !isCancelledRef.current) {
                  runVoiceTurn()
                }
              }, 60)
            }
            return
          }
        } else if (data.error) {
          setAssistantText(String(data.error))
        }
      } catch (err: any) {
        console.error('Turn error', err)
        setAssistantText(`Connection issue: ${err.message || 'failed to get response'}`)
      }

      // Continue conversation loop smoothly
      if (isContinuousRef.current && !isCancelledRef.current && !isInterruptedRef.current) {
        setTimeout(() => {
          if (isContinuousRef.current && !isCancelledRef.current && !isInterruptedRef.current) {
            setTranscript('')
            runVoiceTurn()
          }
        }, 300)
      } else if (!isInterruptedRef.current) {
        setVoiceState('idle')
      }
    } finally {
      turnRunningRef.current = false
    }
  }

  const cleanupAllVoice = () => {
    isCancelledRef.current = true
    isContinuousRef.current = false
    if (bargeInCleanupRef.current) {
      try {
        bargeInCleanupRef.current()
      } catch {}
      bargeInCleanupRef.current = null
    }
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort()
      } catch {}
      recognitionRef.current = null
    }
    if (activeRecorderRef.current && activeRecorderRef.current.state !== 'inactive') {
      try {
        activeRecorderRef.current.stop()
      } catch {}
      activeRecorderRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop())
      mediaStreamRef.current = null
    }
    stopSpeech()
    releaseWakeLock()
  }

  // Start live session when modal opens
  useEffect(() => {
    if (isOpen) {
      isCancelledRef.current = false
      isContinuousRef.current = true
      isInterruptedRef.current = false
      emptyTurnCountRef.current = 0
      setAssistantText('I’m listening. Talk to me anytime!')
      setTranscript('')
      unlockAudioContext()
      ensureMicrophonePermission().then(() => {
        if (!isCancelledRef.current) {
          runVoiceTurn()
        }
      })
    } else {
      cleanupAllVoice()
    }

    return () => {
      cleanupAllVoice()
    }
  }, [isOpen])

  const handleToggleMute = () => {
    const nextMuted = !isMuted
    setIsMuted(nextMuted)
    isMutedRef.current = nextMuted
    if (nextMuted) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch {}
      }
      setVoiceState('idle')
    } else {
      emptyTurnCountRef.current = 0
      runVoiceTurn()
    }
  }

  const handleOrbClick = () => {
    if (voiceState === 'speaking') {
      handleInterrupt()
    } else if (voiceState === 'listening') {
      if (recognitionRef.current && lastRecognizedRef.current) {
        // Immediately finalize speech when user taps the orb
        try {
          recognitionRef.current.stop()
        } catch {}
      }
    } else if (voiceState === 'idle') {
      emptyTurnCountRef.current = 0
      runVoiceTurn()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-between bg-[var(--bg-dark)]/95 backdrop-blur-2xl p-6 sm:p-8 animate-in fade-in duration-300 select-none text-neutral-100">
      {/* Top Controls */}
      <div className="w-full max-w-xl flex items-center justify-between z-10 pt-[max(env(safe-area-inset-top,0px),var(--native-safe-top,0px),12px)]">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2.5 bg-[var(--card-dark)] border border-[var(--border-dark)] px-3.5 py-1.5 rounded-full shadow-lg">
            <Radio className="w-4 h-4 text-[var(--accent)] animate-pulse" />
            <span className="text-xs font-semibold tracking-wider text-[var(--accent-light)] uppercase">Live Voice Mode</span>
          </div>

          {/* No Sleep / Keep Awake Toggle */}
          <button
            onClick={toggleNoSleep}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all cursor-pointer shadow-md active:scale-95 ${
              noSleep
                ? 'bg-amber-500/15 border-amber-500/40 text-amber-300 hover:bg-amber-500/25'
                : 'bg-[var(--card-dark)] border-[var(--border-dark)] text-neutral-400 hover:text-neutral-200 hover:bg-[var(--card-hover)]'
            }`}
            title={noSleep ? 'No Sleep is ON: Device screen stays awake' : 'No Sleep is OFF: Device may sleep normally'}
          >
            {noSleep ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
            <span className="hidden sm:inline">{noSleep ? 'No Sleep: ON' : 'No Sleep: OFF'}</span>
            <span className="sm:hidden">{noSleep ? 'Awake' : 'Sleep'}</span>
          </button>
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
            onClick={handleOrbClick}
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

        {/* Dedicated One-Tap Interrupt Button below Orb when Speaking */}
        {voiceState === 'speaking' && (
          <div className="my-2 flex flex-col items-center gap-1 animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => handleInterrupt()}
              type="button"
              className="px-6 py-2.5 rounded-full bg-gradient-to-r from-rose-600 via-rose-500 to-red-500 hover:from-rose-500 hover:to-red-400 text-white font-bold text-xs sm:text-sm shadow-xl shadow-rose-950/80 border border-rose-300/40 flex items-center gap-2 animate-bounce cursor-pointer active:scale-95 transition-all"
              title="Tap or speak out loud to interrupt Doshie immediately"
            >
              <Square className="w-3.5 h-3.5 fill-white" />
              <span>Tap to Interrupt (or Speak)</span>
            </button>
            <span className="text-[10px] text-rose-300/75 font-medium tracking-wide">
              Voice Barge-In active · Speak out loud anytime to interrupt
            </span>
          </div>
        )}

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
            <div className="space-y-1.5 w-full">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-semibold uppercase tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping" />
                <span>Speaking · Say "Stop" or tap to interrupt</span>
              </div>
              <p className="text-xs sm:text-sm text-neutral-100 font-normal line-clamp-3 leading-relaxed">
                {assistantText}
              </p>
            </div>
          )}

          {voiceState === 'idle' && (
            <p className="text-xs sm:text-sm text-[var(--accent-light)]/80">
              {assistantText || 'Tap the microphone or say something to start.'}
            </p>
          )}
        </div>
      </div>

      {/* Bottom Action Dock */}
      <div className="w-full max-w-md flex items-center justify-center gap-4 sm:gap-5 z-10 pb-[max(env(safe-area-inset-bottom,0px),var(--native-safe-bottom,0px),16px)]">
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

        {/* Interrupt / Next Turn */}
        {voiceState === 'speaking' ? (
          <button
            onClick={() => handleInterrupt()}
            type="button"
            className="flex items-center gap-2 px-5 py-3.5 rounded-full bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs shadow-xl shadow-rose-950/80 border border-rose-400 animate-pulse active:scale-95 transition-all cursor-pointer"
            title="Stop speaking and listen now"
          >
            <Square className="w-4 h-4 fill-white" />
            <span>Interrupt</span>
          </button>
        ) : (
          <button
            onClick={() => handleInterrupt()}
            type="button"
            className="p-3.5 rounded-full bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] text-[var(--accent-light)] hover:text-white transition-all active:scale-95 shadow-lg cursor-pointer"
            title="Next Turn / Reset"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  )
}
