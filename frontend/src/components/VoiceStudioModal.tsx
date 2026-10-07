import React, { useState, useEffect, useRef } from 'react'
import {
  X,
  Mic,
  RefreshCw,
  ArrowLeft,
  Play,
  Square,
  Sparkles,
  Volume2,
  Upload,
  Sliders,
  Check,
  Wand2,
  CheckCircle2,
  Layers
} from 'lucide-react'
import type { Profile } from '../types'
import { stopSpeech } from '../utils/audio'

interface VoiceStudioModalProps {
  isOpen: boolean
  onClose: () => void
  activeProfile?: string
  availableProfiles?: Profile[]
}

interface VoiceModel {
  id: string
  name: string
  desc: string
  gender: 'male' | 'female'
  badge?: string
  kokoro_voice?: string
  sampleText?: string
}

const BUILTIN_VOICES: VoiceModel[] = [
  {
    id: 'am_adam',
    name: 'Adam (Hermes Master)',
    desc: 'Natural, grounded, warm and friendly male demeanor. Master voice for Hermes.',
    gender: 'male',
    badge: 'Master Male',
    kokoro_voice: 'am_adam',
    sampleText: 'Hello Hermes! I am your local AI companion running on your RTX 5070 workstation.'
  },
  {
    id: 'af_heart',
    name: 'Heart (Aeriel Master)',
    desc: 'Gentle, compassionate, warm and calming female demeanor. Master voice for Aeriel.',
    gender: 'female',
    badge: 'Master Female',
    kokoro_voice: 'af_heart',
    sampleText: 'Hello! It is wonderful to speak with you today. How can I help you right now?'
  },
  {
    id: 'af_bella',
    name: 'Bella (Energetic)',
    desc: 'Bright, cheerful, clear and articulate female demeanor.',
    gender: 'female',
    badge: 'Upbeat',
    kokoro_voice: 'af_bella',
    sampleText: 'Hey there! Ready to build something awesome today? Let us get straight to it!'
  },
  {
    id: 'af_nicole',
    name: 'Nicole (Professional)',
    desc: 'Focused, articulate, executive cadence with crystal-clear pronunciation.',
    gender: 'female',
    badge: 'Executive',
    kokoro_voice: 'af_nicole',
    sampleText: 'All diagnostic benchmarks are optimal. System architecture is operating efficiently.'
  },
  {
    id: 'am_michael',
    name: 'Michael (Deep Resonant)',
    desc: 'Deep, authoritative, cinematic male resonance.',
    gender: 'male',
    badge: 'Deep Baritone',
    kokoro_voice: 'am_michael',
    sampleText: 'Welcome back. Neural models and acceleration pipelines are primed and ready.'
  },
  {
    id: 'bf_emma',
    name: 'Emma (British Elegance)',
    desc: 'Classical British RP cadence, refined and articulate.',
    gender: 'female',
    badge: 'British RP',
    kokoro_voice: 'bf_emma',
    sampleText: 'Delighted to make your acquaintance. Shall we proceed with your agenda today?'
  },
  {
    id: 'bm_george',
    name: 'George (British Scholar)',
    desc: 'Distinguished British scholarly cadence with measured diction.',
    gender: 'male',
    badge: 'Distinguished',
    kokoro_voice: 'bm_george',
    sampleText: 'Indeed. A most intriguing inquiry. Allow me to elaborate on the particulars.'
  },
  {
    id: 'clone_hermes',
    name: 'Hermes Zero-Shot Clone',
    desc: 'Neural cloned voice generated from your reference audio on RTX 5070.',
    gender: 'male',
    badge: 'Neural Clone',
    kokoro_voice: 'am_adam',
    sampleText: 'This is the custom cloned voice profile running locally with zero-shot neural synthesis.'
  }
]

type StudioTab = 'gallery' | 'clone' | 'tuning' | 'changer' | 'gradio'

export const VoiceStudioModal: React.FC<VoiceStudioModalProps> = ({
  isOpen,
  onClose,
  activeProfile = 'Hermes',
  availableProfiles = [],
}) => {
  const [activeTab, setActiveTab] = useState<StudioTab>('gallery')
  const [iframeKey, setIframeKey] = useState(0)

  // Voice audition state
  const [selectedVoiceId, setSelectedVoiceId] = useState('am_adam')
  const [customPhrase, setCustomPhrase] = useState(
    'Greetings! Doshie neural voice engine is online and running directly on your RTX 5070 workstation.'
  )
  const [isPlayingAudition, setIsPlayingAudition] = useState(false)
  const [isSynthesizingAudition, setIsSynthesizingAudition] = useState(false)
  const [auditionAudio, setAuditionAudio] = useState<HTMLAudioElement | null>(null)
  const [auditionError, setAuditionError] = useState<string | null>(null)
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null)

  // Cloner / Recorder state
  const [isRecording, setIsRecording] = useState(false)
  const [recordSeconds, setRecordSeconds] = useState(0)
  const [recordedAudioBlob, setRecordedAudioBlob] = useState<Blob | null>(null)
  const [recordedAudioUrl, setRecordedAudioUrl] = useState<string | null>(null)
  const [cloneVoiceName, setCloneVoiceName] = useState('')
  const [cloneTargetProfile, setCloneTargetProfile] = useState(activeProfile)
  const [isUploadingClone, setIsUploadingClone] = useState(false)
  const [cloneStatusMsg, setCloneStatusMsg] = useState<string | null>(null)

  // Tuning state
  const [speed, setSpeed] = useState(1.0)
  const [pitch, setPitch] = useState(1.0)
  const [bargeInEnabled, setBargeInEnabled] = useState(true)
  const [tuningSaved, setTuningSaved] = useState(false)

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const recordingTimerRef = useRef<any>(null)
  const audioChunksRef = useRef<Blob[]>([])

  useEffect(() => {
    if (isOpen) {
      // Sync initial profile tuning from localStorage or backend
      try {
        const savedPrefs = localStorage.getItem(`Doshie_preferences_${activeProfile.toLowerCase()}`)
        if (savedPrefs) {
          const parsed = JSON.parse(savedPrefs)
          if (parsed.voice_rate) setSpeed(parsed.voice_rate)
          if (parsed.voice_pitch) setPitch(parsed.voice_pitch)
          if (parsed.voice_identity) setSelectedVoiceId(parsed.voice_identity)
        }
      } catch {}
    } else {
      // Stop audition playback on modal close
      if (auditionAudio) {
        auditionAudio.pause()
        auditionAudio.src = ''
        setAuditionAudio(null)
      }
      stopSpeech()
      setIsPlayingAudition(false)
      setIsRecording(false)
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current)
    }
  }, [isOpen, activeProfile])

  if (!isOpen) return null

  // Audition voice playback via /speak endpoint
  const handleAuditionVoice = async (voiceId: string, textToSpeak?: string) => {
    if (isPlayingAudition || isSynthesizingAudition) {
      if (auditionAudio) {
        auditionAudio.pause()
        auditionAudio.src = ''
        setAuditionAudio(null)
      }
      stopSpeech()
      setIsPlayingAudition(false)
      setIsSynthesizingAudition(false)
      return
    }

    const text = textToSpeak || customPhrase
    if (!text.trim()) return

    setIsSynthesizingAudition(true)
    setAuditionError(null)

    try {
      const isClone = voiceId.includes('clone')
      const engine = isClone ? 'clone' : 'kokoro'

      const res = await fetch('/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.trim(),
          voice: voiceId,
          engine: engine,
          profile: activeProfile,
        }),
      })

      if (!res.ok) {
        throw new Error(`TTS server responded with status ${res.status}`)
      }

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      setAuditionAudio(audio)

      audio.onplay = () => {
        setIsSynthesizingAudition(false)
        setIsPlayingAudition(true)
      }
      audio.onended = () => {
        setIsPlayingAudition(false)
        setAuditionAudio(null)
      }
      audio.onerror = () => {
        setIsPlayingAudition(false)
        setIsSynthesizingAudition(false)
        setAuditionAudio(null)
        setAuditionError('Audio playback failed.')
      }

      await audio.play()
    } catch (err: any) {
      console.warn('Audition error:', err)
      setIsSynthesizingAudition(false)
      setIsPlayingAudition(false)
      setAuditionError(err?.message || 'Failed to synthesize voice sample.')
    }
  }

  // Assign voice to active profile
  const handleAssignVoice = async (voiceId: string, profileName: string) => {
    try {
      const isClone = voiceId.includes('clone')
      const engine = isClone ? 'clone' : 'kokoro'

      // Update server preferences
      await fetch('/profile-preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: profileName,
          preferences: {
            voice_identity: voiceId,
            voice_engine: engine,
            voice_rate: speed,
            voice_pitch: pitch,
          },
        }),
      })

      // Also persist to settings
      await fetch('/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voice_identity: voiceId,
          voice_engine: engine,
          voice_rate: speed,
          voice_pitch: pitch,
        }),
      }).catch(() => {})

      setAssignSuccess(`Set "${voiceId}" as the voice for ${profileName}!`)
      setTimeout(() => setAssignSuccess(null), 3500)
    } catch (err: any) {
      setAuditionError(`Failed to save voice profile: ${err.message}`)
    }
  }

  // Voice Recording for Cloner
  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setCloneStatusMsg('Microphone not supported on this browser.')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      })
      audioChunksRef.current = []

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'

      const recorder = new MediaRecorder(stream, { mimeType })
      mediaRecorderRef.current = recorder

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data)
        }
      }

      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        setRecordedAudioBlob(blob)
        setRecordedAudioUrl(URL.createObjectURL(blob))
      }

      recorder.start(250)
      setIsRecording(true)
      setRecordSeconds(0)

      recordingTimerRef.current = setInterval(() => {
        setRecordSeconds((s) => {
          if (s >= 14) {
            stopRecording()
            return 15
          }
          return s + 1
        })
      }, 1000)
    } catch (err: any) {
      setCloneStatusMsg(`Microphone error: ${err.message}`)
    }
  }

  const stopRecording = () => {
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current)
      recordingTimerRef.current = null
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop()
      } catch {}
    }
    setIsRecording(false)
  }

  // Upload and Save Cloned Voice
  const handleSaveClonedVoice = async () => {
    if (!recordedAudioBlob) {
      setCloneStatusMsg('Please record or upload a voice sample first.')
      return
    }

    const name = cloneVoiceName.trim() || `Voice_${Date.now()}`
    setIsUploadingClone(true)
    setCloneStatusMsg('Uploading and registering voice model on RTX 5070...')

    try {
      // Convert blob to Base64
      const reader = new FileReader()
      reader.readAsDataURL(recordedAudioBlob)
      reader.onloadend = async () => {
        const base64Audio = reader.result as string
        const res = await fetch('/api/voices/upload', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile: name,
            audio: base64Audio,
            verify: true,
          }),
        })

        if (!res.ok) {
          throw new Error(`Upload failed with status ${res.status}`)
        }

        const data = await res.json()
        if (data.ok) {
          setCloneStatusMsg(`✅ Voice "${name}" registered successfully!`)
          // Link to chosen profile
          if (cloneTargetProfile) {
            await handleAssignVoice(name.toLowerCase(), cloneTargetProfile)
          }
        } else {
          setCloneStatusMsg(`Error: ${data.error || 'Failed to save voice'}`)
        }
        setIsUploadingClone(false)
      }
    } catch (err: any) {
      setCloneStatusMsg(`Upload Error: ${err.message}`)
      setIsUploadingClone(false)
    }
  }

  // Tuning Preset handler
  const applyPreset = (presetSpeed: number, presetPitch: number, _presetName: string) => {
    setSpeed(presetSpeed)
    setPitch(presetPitch)
    setTuningSaved(true)
    setTimeout(() => setTuningSaved(false), 2500)
    handleAssignVoice(selectedVoiceId, activeProfile)
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4 bg-black/85 backdrop-blur-md animate-in fade-in duration-150"
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 12px)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 8px)',
      }}
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-5xl h-full sm:h-[92vh] sm:max-h-[860px] bg-[var(--bg-dark)] border-0 sm:border border-[var(--border-dark)] rounded-t-2xl sm:rounded-2xl shadow-2xl flex flex-col overflow-hidden text-neutral-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-3 sm:px-5 py-2 sm:py-2.5 bg-[var(--card-dark)]/95 border-b border-[var(--border-dark)] shrink-0 gap-2">
          {/* Left: Back & Title */}
          <div className="flex items-center gap-2.5 min-w-0">
            <button
              type="button"
              onClick={onClose}
              title="Back to Chat"
              className="px-2.5 py-1.5 rounded-xl bg-white/10 hover:bg-rose-500/20 border border-white/20 text-white flex items-center gap-1.5 text-xs font-bold active:scale-95 transition-all cursor-pointer shrink-0"
            >
              <ArrowLeft className="w-4 h-4 text-[var(--accent-light)]" />
              <span>Back</span>
            </button>

            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-500 flex items-center justify-center shadow-sm shrink-0">
              <Mic className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs sm:text-sm font-bold text-white tracking-wide truncate">
                  Neural Voice Studio
                </h3>
                <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shrink-0">
                  RTX 5070
                </span>
              </div>
              <p className="hidden sm:block text-[11px] text-[var(--accent-light)]/80">
                Zero-Shot Neural Cloning · Voice Auditions · Realtime Kokoro TTS (~150ms)
              </p>
            </div>
          </div>

          {/* Right: Studio Mode Switcher & Exit */}
          <div className="flex items-center gap-1.5 shrink-0">
            {activeTab === 'gradio' && (
              <button
                type="button"
                onClick={() => setIframeKey((k) => k + 1)}
                title="Reload Lab"
                className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--accent)]/30 border border-[var(--border-dark)] text-[var(--accent-light)] hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs font-medium"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Reload</span>
              </button>
            )}

            <button
              type="button"
              onClick={onClose}
              title="Close Voice Studio"
              className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-rose-500/20 border border-[var(--border-dark)] hover:border-rose-500/40 text-neutral-400 hover:text-rose-300 transition-all cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Studio Navigation Tabs */}
        <div className="flex items-center px-3 sm:px-5 py-1.5 bg-[#080d16] border-b border-[var(--border-dark)] gap-1.5 overflow-x-auto shrink-0 select-none">
          <button
            type="button"
            onClick={() => setActiveTab('gallery')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shrink-0 ${
              activeTab === 'gallery'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-neutral-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>Voice Gallery & Audition</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('clone')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shrink-0 ${
              activeTab === 'clone'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-neutral-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Voice Cloner & Recorder</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('tuning')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shrink-0 ${
              activeTab === 'tuning'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'text-neutral-400 hover:text-white hover:bg-white/5'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Acoustics & Tuning</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('gradio')}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shrink-0 ${
              activeTab === 'gradio'
                ? 'bg-purple-600 text-white shadow-sm'
                : 'text-purple-300 hover:text-white hover:bg-purple-950/40 border border-purple-500/30'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>🎛️ Advanced Modular Lab (Gradio)</span>
          </button>
        </div>

        {/* Notification Toast */}
        {assignSuccess && (
          <div className="px-4 py-2 bg-emerald-950/90 border-b border-emerald-500/50 text-emerald-200 text-xs flex items-center gap-2 animate-in fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{assignSuccess}</span>
          </div>
        )}
        {auditionError && (
          <div className="px-4 py-2 bg-rose-950/90 border-b border-rose-500/50 text-rose-200 text-xs flex items-center justify-between animate-in fade-in">
            <span>{auditionError}</span>
            <button onClick={() => setAuditionError(null)} className="text-rose-400 hover:text-white">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Body Area */}
        <div className="flex-1 overflow-y-auto bg-[#070b12] p-3 sm:p-5">
          {/* TAB 1: Voice Gallery & Audition */}
          {activeTab === 'gallery' && (
            <div className="space-y-4 max-w-4xl mx-auto">
              <div>
                <h4 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                  <Volume2 className="w-4 h-4 text-emerald-400" />
                  <span>Audition & Select Neural Voices</span>
                </h4>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Audition each model running locally on your RTX 5070 GPU. Assign your favorite voice to Hermes or any family profile with one tap.
                </p>
              </div>

              {/* Grid of Voice Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {BUILTIN_VOICES.map((v) => {
                  const isSelected = selectedVoiceId === v.id
                  return (
                    <div
                      key={v.id}
                      onClick={() => setSelectedVoiceId(v.id)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between gap-2.5 ${
                        isSelected
                          ? 'bg-emerald-950/40 border-emerald-400 ring-1 ring-emerald-400/50 shadow-lg shadow-emerald-950/50'
                          : 'bg-[var(--card-dark)]/80 border-[var(--border-dark)] hover:border-emerald-500/40 hover:bg-[var(--card-hover)]'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-xs font-bold text-white">{v.name}</span>
                            {v.badge && (
                              <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                {v.badge}
                              </span>
                            )}
                          </div>
                          <p className="text-[11px] text-neutral-400 mt-1 leading-relaxed">{v.desc}</p>
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t border-white/5">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedVoiceId(v.id)
                            handleAuditionVoice(v.id, v.sampleText)
                          }}
                          className={`flex-1 py-1.5 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-95 ${
                            isSelected && isPlayingAudition
                              ? 'bg-rose-600 hover:bg-rose-500 text-white'
                              : 'bg-white/10 hover:bg-emerald-600 text-white border border-white/10'
                          }`}
                        >
                          {isSelected && isPlayingAudition ? (
                            <>
                              <Square className="w-3.5 h-3.5 fill-white" />
                              <span>Stop</span>
                            </>
                          ) : (
                            <>
                              <Play className="w-3.5 h-3.5 fill-white" />
                              <span>Audition Voice</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedVoiceId(v.id)
                            handleAssignVoice(v.id, activeProfile)
                          }}
                          title={`Assign to ${activeProfile}`}
                          className="py-1.5 px-3 rounded-xl bg-emerald-700/80 hover:bg-emerald-600 text-white text-xs font-semibold flex items-center gap-1 transition-all cursor-pointer active:scale-95 shadow-sm"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Use for {activeProfile}</span>
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Custom Audition Box */}
              <div className="p-4 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Test Any Custom Phrase</span>
                  </span>
                  <span className="text-[10px] text-neutral-400 font-mono">
                    Active: {selectedVoiceId}
                  </span>
                </div>

                <textarea
                  rows={2}
                  value={customPhrase}
                  onChange={(e) => setCustomPhrase(e.target.value)}
                  placeholder="Type any phrase you want Doshie to speak..."
                  className="w-full px-3 py-2 rounded-xl bg-black/40 border border-white/10 focus:border-emerald-400 focus:outline-none text-xs text-white resize-none"
                />

                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 overflow-x-auto text-[11px] text-neutral-400">
                    <span className="shrink-0 text-[10px] uppercase tracking-wider font-semibold">Try:</span>
                    <button
                      type="button"
                      onClick={() => setCustomPhrase('How may I assist you with your project today, Hermes?')}
                      className="px-2 py-0.5 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 truncate max-w-[140px]"
                    >
                      "How may I assist..."
                    </button>
                    <button
                      type="button"
                      onClick={() => setCustomPhrase('RTX 5070 running cool at 42 degrees with 12GB VRAM active.')}
                      className="px-2 py-0.5 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 truncate max-w-[140px]"
                    >
                      "RTX 5070 running cool..."
                    </button>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleAuditionVoice(selectedVoiceId)}
                    disabled={isSynthesizingAudition}
                    className="py-1.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer active:scale-95 shrink-0"
                  >
                    {isSynthesizingAudition ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Synthesizing...</span>
                      </>
                    ) : isPlayingAudition ? (
                      <>
                        <Square className="w-3.5 h-3.5 fill-white" />
                        <span>Stop</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 fill-white" />
                        <span>Speak Phrase</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: Voice Cloner & Recorder */}
          {activeTab === 'clone' && (
            <div className="space-y-4 max-w-2xl mx-auto">
              <div>
                <h4 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                  <Mic className="w-4 h-4 text-emerald-400" />
                  <span>Zero-Shot Voice Cloner & In-App Recorder</span>
                </h4>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Record a 5-15 second voice sample using your microphone, or upload any reference WAV file. Doshie will clone the vocal characteristics to speak with that voice.
                </p>
              </div>

              {/* Recorder Box */}
              <div className="p-5 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] flex flex-col items-center justify-center text-center space-y-4 shadow-xl">
                <div className="relative">
                  <div
                    className={`w-20 h-20 rounded-full flex items-center justify-center transition-all ${
                      isRecording
                        ? 'bg-rose-600 text-white ring-4 ring-rose-500/40 animate-pulse scale-110'
                        : 'bg-emerald-600/20 text-emerald-300 border border-emerald-500/40'
                    }`}
                  >
                    <Mic className="w-8 h-8" />
                  </div>
                </div>

                <div>
                  <div className="text-sm font-bold text-white">
                    {isRecording ? `Recording Sample... (${recordSeconds}s / 15s)` : 'Record Your Reference Voice'}
                  </div>
                  <p className="text-xs text-neutral-400 mt-1 max-w-sm">
                    {isRecording
                      ? 'Speak clearly in a natural conversational tone. Read any sentence out loud.'
                      : 'Tap record and speak for at least 5 to 10 seconds to capture vocal timbre.'}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  {isRecording ? (
                    <button
                      type="button"
                      onClick={stopRecording}
                      className="px-6 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-rose-950/60 active:scale-95 transition-all cursor-pointer"
                    >
                      <Square className="w-4 h-4 fill-white" />
                      <span>Stop Recording ({recordSeconds}s)</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={startRecording}
                      className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-emerald-950/60 active:scale-95 transition-all cursor-pointer"
                    >
                      <Mic className="w-4 h-4" />
                      <span>Start Voice Recording</span>
                    </button>
                  )}
                </div>

                {/* Audio preview if recorded */}
                {recordedAudioUrl && (
                  <div className="w-full pt-3 border-t border-white/10 space-y-2">
                    <span className="text-[11px] text-emerald-300 font-semibold block">
                      Preview Recorded Sample:
                    </span>
                    <audio src={recordedAudioUrl} controls className="w-full h-8" />
                  </div>
                )}
              </div>

              {/* Upload Alternative */}
              <div className="p-4 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Upload className="w-3.5 h-3.5 text-[var(--accent-light)]" />
                    <span>Or Upload Audio File (.wav, .mp3)</span>
                  </span>
                </div>
                <input
                  type="file"
                  accept="audio/*,.wav,.mp3,.m4a,.ogg"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) {
                      setRecordedAudioBlob(file)
                      setRecordedAudioUrl(URL.createObjectURL(file))
                      setCloneVoiceName(file.name.replace(/\.[^/.]+$/, ''))
                    }
                  }}
                  className="block w-full text-xs text-neutral-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-white/10 file:text-white hover:file:bg-white/20 cursor-pointer"
                />
              </div>

              {/* Name & Save Cloned Profile */}
              <div className="p-4 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] space-y-3">
                <span className="text-xs font-bold text-white block">Save & Assign Cloned Voice</span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] text-neutral-400 mb-1">Voice Profile Name</label>
                    <input
                      type="text"
                      value={cloneVoiceName}
                      onChange={(e) => setCloneVoiceName(e.target.value)}
                      placeholder="e.g. Master_Hermes_Clean"
                      className="w-full px-3 py-1.5 rounded-xl bg-black/40 border border-white/10 focus:border-emerald-400 focus:outline-none text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] text-neutral-400 mb-1">Assign to Doshie Profile</label>
                    <select
                      value={cloneTargetProfile}
                      onChange={(e) => setCloneTargetProfile(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-xl bg-black/40 border border-white/10 focus:border-emerald-400 focus:outline-none text-xs text-white"
                    >
                      <option value={activeProfile}>{activeProfile} (Active)</option>
                      {availableProfiles
                        .filter((p) => p.name.toLowerCase() !== activeProfile.toLowerCase())
                        .map((p) => (
                          <option key={p.id} value={p.name}>
                            {p.name}
                          </option>
                        ))}
                    </select>
                  </div>
                </div>

                {cloneStatusMsg && (
                  <p className="text-xs text-emerald-300 font-medium">{cloneStatusMsg}</p>
                )}

                <button
                  type="button"
                  onClick={handleSaveClonedVoice}
                  disabled={isUploadingClone || !recordedAudioBlob}
                  className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/60 active:scale-98 transition-all cursor-pointer"
                >
                  {isUploadingClone ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Saving Voice Model...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-3.5 h-3.5" />
                      <span>Save & Activate Cloned Voice</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: Acoustics & Tuning */}
          {activeTab === 'tuning' && (
            <div className="space-y-4 max-w-2xl mx-auto">
              <div>
                <h4 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-emerald-400" />
                  <span>Acoustics, Speed, Pitch & Demeanor Tuning</span>
                </h4>
                <p className="text-xs text-neutral-400 mt-0.5">
                  Customize speech rate, pitch, and interruption sensitivity for {activeProfile}.
                </p>
              </div>

              {/* 1-Click Acoustic Presets */}
              <div className="p-4 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] space-y-2.5">
                <span className="text-xs font-bold text-white block">1-Click Demeanor Presets</span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <button
                    type="button"
                    onClick={() => applyPreset(0.95, 0.95, 'Warm & Humble')}
                    className="p-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-emerald-950/50 hover:border-emerald-500/40 text-left cursor-pointer transition-all active:scale-95"
                  >
                    <div className="text-xs font-bold text-white">Warm & Gentle</div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">0.95x speed · 0.95x pitch</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset(1.05, 1.0, 'Crisp Tech')}
                    className="p-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-emerald-950/50 hover:border-emerald-500/40 text-left cursor-pointer transition-all active:scale-95"
                  >
                    <div className="text-xs font-bold text-white">Crisp Tech</div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">1.05x speed · 1.0x pitch</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset(1.25, 1.05, 'Rapid Concise')}
                    className="p-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-emerald-950/50 hover:border-emerald-500/40 text-left cursor-pointer transition-all active:scale-95"
                  >
                    <div className="text-xs font-bold text-white">Rapid Fire</div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">1.25x speed · 1.05x pitch</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset(0.9, 0.9, 'Storyteller')}
                    className="p-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-emerald-950/50 hover:border-emerald-500/40 text-left cursor-pointer transition-all active:scale-95"
                  >
                    <div className="text-xs font-bold text-white">Storyteller</div>
                    <div className="text-[10px] text-neutral-400 mt-0.5">0.9x speed · 0.9x pitch</div>
                  </button>
                </div>
              </div>

              {/* Sliders */}
              <div className="p-4 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] space-y-4">
                <div>
                  <div className="flex items-center justify-between text-xs text-neutral-300 mb-1.5">
                    <span className="font-semibold text-white">Speech Speed / Cadence</span>
                    <span className="font-mono text-emerald-400 font-bold">{speed.toFixed(2)}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.6"
                    max="1.5"
                    step="0.05"
                    value={speed}
                    onChange={(e) => setSpeed(parseFloat(e.target.value))}
                    className="w-full accent-emerald-500 bg-white/10 h-1.5 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-neutral-500 mt-1">
                    <span>0.6x (Slow & Deliberate)</span>
                    <span>1.0x (Normal)</span>
                    <span>1.5x (Fast)</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-white/10">
                  <div className="flex items-center justify-between text-xs text-neutral-300 mb-1.5">
                    <span className="font-semibold text-white">Voice Pitch</span>
                    <span className="font-mono text-emerald-400 font-bold">{pitch.toFixed(2)}x</span>
                  </div>
                  <input
                    type="range"
                    min="0.7"
                    max="1.3"
                    step="0.05"
                    value={pitch}
                    onChange={(e) => setPitch(parseFloat(e.target.value))}
                    className="w-full accent-emerald-500 bg-white/10 h-1.5 rounded-lg cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-neutral-500 mt-1">
                    <span>0.7x (Deeper)</span>
                    <span>1.0x (Original)</span>
                    <span>1.3x (Higher)</span>
                  </div>
                </div>

                <div className="pt-3 border-t border-white/10 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-semibold text-white">Voice Barge-In Interruption</div>
                    <div className="text-[10px] text-neutral-400">
                      Instantly silence Doshie when you speak out loud
                    </div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={bargeInEnabled}
                      onChange={(e) => setBargeInEnabled(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600" />
                  </label>
                </div>

                {tuningSaved && (
                  <p className="text-xs text-emerald-300 font-medium animate-in fade-in">
                    ✅ Acoustics applied to {activeProfile}!
                  </p>
                )}

                <button
                  type="button"
                  onClick={() => {
                    handleAssignVoice(selectedVoiceId, activeProfile)
                    setTuningSaved(true)
                    setTimeout(() => setTuningSaved(false), 3000)
                  }}
                  className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-all cursor-pointer active:scale-95 shadow-md"
                >
                  Save Acoustics to {activeProfile}
                </button>
              </div>
            </div>
          )}

          {/* TAB 4: Embedded Modular Lab (Gradio) */}
          {activeTab === 'gradio' && (
            <div className="w-full h-full min-h-[500px] relative rounded-xl overflow-hidden border border-white/10">
              <iframe
                key={iframeKey}
                src="/voice-studio/"
                title="Doshie Advanced Modular Voice Lab"
                className="w-full h-full border-0 absolute inset-0"
                allow="microphone; camera; clipboard-write;"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
