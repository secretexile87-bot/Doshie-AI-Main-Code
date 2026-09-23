import React, { useState, useEffect } from 'react'
import {
  X,
  Users,
  Volume2,
  VolumeX,
  Loader2,
  Brain,
  Plus,
  Check,
  MapPin,
  Sparkles,
  Gamepad2,
  Code2,
  Home,
  Bot,
  Palette,
  Type,
  MessageSquare,
  Smile,
  Heart,
  Sliders,
  FileText,
  RotateCcw,
  RefreshCw,
  Trash2,
  Cpu,
  LogOut,
  Shield,
  Eye,
  BookOpen,
  Lock,
  Upload,
  Music,
  Wand2,
  Activity,
  Image as ImageIcon,
  Mic,
  ExternalLink
} from 'lucide-react'
import { playNeuralSpeech, stopSpeech } from '../utils/audio'
import type { GuiCustomization, AdminProfileOversight, AdminGuestMemory } from '../types'

interface Profile {
  id: string
  name: string
  role: string
  is_admin?: boolean
  is_child?: boolean
}

interface AppSettings {
  mode: string
  auto_memory: boolean
  speak_replies: boolean
  voice_rate: number
  voice_pitch: number
  default_weather_location: string
  voice_engine?: string
  voice_identity?: string
  voice_preset?: string
  persona_tone?: string
  custom_system_prompt?: string
  auto_web_search?: boolean
  safe_search?: boolean
  age?: number
}

interface SettingsModalProps {
  isOpen: boolean
  initialTab?: 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor'
  onClose: () => void
  activeProfile: string
  onSelectProfile: (profile: string) => void
  customization: GuiCustomization
  onUpdateCustomization: (updates: Partial<GuiCustomization>) => void
  isAdmin?: boolean
  onSelectOversightProfile?: (profile: string) => void
  onLockScreen?: () => void
  onTabChange?: (tab: 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor') => void
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  initialTab = 'settings',
  onClose,
  activeProfile,
  onSelectProfile,
  customization,
  onUpdateCustomization,
  isAdmin = false,
  onSelectOversightProfile,
  onLockScreen,
  onTabChange,
}) => {
  const [tab, setTab] = useState<'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor'>(initialTab)

  const handleTabChange = (newTab: 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor') => {
    setTab(newTab)
    onTabChange?.(newTab)
  }
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [isFlushing, setIsFlushing] = useState(false)
  const [oversightData, setOversightData] = useState<AdminProfileOversight[]>([])
  const [selectedGuestMemories, setSelectedGuestMemories] = useState<{ profile: string; memories: AdminGuestMemory[] } | null>(null)
  const [isLoadingOversight, setIsLoadingOversight] = useState(false)
  const [doctorData, setDoctorData] = useState<any>(null)
  const [isLoadingDoctor, setIsLoadingDoctor] = useState(false)
  const [isFixingDoctor, setIsFixingDoctor] = useState(false)
  const [settings, setSettings] = useState<AppSettings>({
    mode: 'family',
    auto_memory: true,
    speak_replies: false,
    voice_rate: 1.0,
    voice_pitch: 1.0,
    default_weather_location: 'El Paso',
    persona_tone: 'humble_kind',
    custom_system_prompt: 'Always be humble, deeply kind, gentle, empathetic, patient, and encouraging in every response.',
    voice_identity: 'hermes',
    voice_preset: 'gentle',
    auto_web_search: true,
    safe_search: true,
    age: 18,
  })
  const [customPrompt, setCustomPrompt] = useState('')
  const [newName, setNewName] = useState('')
  const [newRole, setNewRole] = useState('Family')
  const [isAddingProfile, setIsAddingProfile] = useState(false)
  const [statusMsg, setStatusMsg] = useState('')
  const [isTestingVoice, setIsTestingVoice] = useState(false)
  const [isPlayingVoice, setIsPlayingVoice] = useState(false)

  // MySpace Studio States
  const [myspaceCssInput, setMyspaceCssInput] = useState(customization.myspaceCustomCss || '')
  const [isGeneratingCss, setIsGeneratingCss] = useState(false)
  const [myspaceAiPrompt, setMyspaceAiPrompt] = useState('')
  const [myspaceStatusMsg, setMyspaceStatusMsg] = useState('')
  const cssFileInputRef = React.useRef<HTMLInputElement>(null)

  const [customVoices, setCustomVoices] = useState<any[]>([])

  // Keep local CSS in sync if customization updates externally
  useEffect(() => {
    if (customization.myspaceCustomCss !== undefined) {
      setMyspaceCssInput(customization.myspaceCustomCss)
    }
  }, [customization.myspaceCustomCss])

  const handleTestVoice = async () => {
    if (isPlayingVoice || isTestingVoice) {
      stopSpeech()
      setIsPlayingVoice(false)
      setIsTestingVoice(false)
      return
    }

    setIsTestingVoice(true)
    const voiceId = settings.voice_identity || 'hermes'
    const testText = voiceId === 'hermes'
      ? "Hello Hermes! This is Doshie, speaking with your master neural cloned voice on your RTX 5070."
      : `Hello! This is Doshie speaking with the ${voiceId} voice profile.`

    try {
      await playNeuralSpeech(testText, {
        profile: activeProfile || 'Hermes',
        voice: voiceId,
        engine: settings.voice_engine || 'auto',
        onStart: () => {
          setIsTestingVoice(false)
          setIsPlayingVoice(true)
        },
        onEnded: () => {
          setIsTestingVoice(false)
          setIsPlayingVoice(false)
        },
        onError: () => {
          setIsTestingVoice(false)
          setIsPlayingVoice(false)
        },
      })
    } catch {
      setIsTestingVoice(false)
      setIsPlayingVoice(false)
    }
  }

  useEffect(() => {
    if (isOpen && initialTab) {
      setTab(initialTab)
    }
  }, [isOpen, initialTab])

  // Load profiles & settings on modal open
  useEffect(() => {
    if (!isOpen) return

    const loadData = async () => {
      try {
        const [profRes, setRes, voiceRes] = await Promise.all([
          fetch('/profiles', { cache: 'no-store' }),
          fetch('/settings', { cache: 'no-store' }),
          fetch('/api/voices', { cache: 'no-store' }).catch(() => null),
        ])
        if (profRes.ok) {
          const profData = await profRes.json()
          if (Array.isArray(profData)) setProfiles(profData)
        }
        if (setRes.ok) {
          const setData = await setRes.json()
          if (setData && typeof setData === 'object') {
            setSettings(prev => ({ ...prev, ...setData }))
            if (typeof setData.custom_system_prompt === 'string') {
              setCustomPrompt(setData.custom_system_prompt)
            }
          }
        }
        if (voiceRes && voiceRes.ok) {
          const voiceData = await voiceRes.json()
          if (voiceData && voiceData.voices) {
            const list = Object.entries(voiceData.voices).map(([id, info]: [string, any]) => ({
              id,
              name: info.name || id,
              desc: info.description || (info.is_default ? 'Master default voice' : 'Custom voice profile'),
              badge: info.is_default ? '🎙️ Master Voice' : (info.verified ? '✅ Verified' : '👤 Profile Voice')
            }))
            setCustomVoices(list)
          }
        }
      } catch (err) {
        console.error('Failed to load settings/profiles/voices', err)
      }
    }

    loadData()
  }, [isOpen])

  // Load Doctor AI Telemetry
  const fetchDoctorData = async () => {
    setIsLoadingDoctor(true)
    try {
      const res = await fetch('/api/doctor')
      if (res.ok) {
        const data = await res.json()
        setDoctorData(data)
      }
    } catch (err) {
      console.error('Failed to fetch doctor status', err)
    } finally {
      setIsLoadingDoctor(false)
    }
  }

  const handleRunDoctorFix = async () => {
    setIsFixingDoctor(true)
    setStatusMsg('🔧 Applying Doctor AI auto-fixes...')
    try {
      const res = await fetch('/api/doctor/fix', { method: 'POST' })
      const data = await res.json()
      setStatusMsg(data.message || 'Fixes applied successfully!')
      await fetchDoctorData()
    } catch {
      setStatusMsg('Fix failed')
    } finally {
      setIsFixingDoctor(false)
      setTimeout(() => setStatusMsg(''), 3000)
    }
  }

  useEffect(() => {
    if (isOpen && tab === 'doctor') {
      fetchDoctorData()
    }
  }, [isOpen, tab])

  // Load Admin Oversight Telemetry & Guest activity
  useEffect(() => {
    if (isOpen && tab === 'oversight' && isAdmin) {
      setIsLoadingOversight(true)
      fetch(`/api/admin/oversight?requester=${encodeURIComponent(activeProfile)}`)
        .then(res => res.json())
        .then(data => {
          if (data.ok && Array.isArray(data.profiles)) {
            setOversightData(data.profiles)
          }
        })
        .catch(err => console.error('Failed to load admin oversight', err))
        .finally(() => setIsLoadingOversight(false))
    }
  }, [isOpen, tab, isAdmin, activeProfile])

  const handleInspectGuestMemories = async (profileName: string) => {
    if (selectedGuestMemories?.profile === profileName) {
      setSelectedGuestMemories(null)
      return
    }
    try {
      const res = await fetch(`/api/admin/guest-memories?profile=${encodeURIComponent(profileName)}&requester=${encodeURIComponent(activeProfile)}`)
      const data = await res.json()
      if (data.ok && Array.isArray(data.memories)) {
        setSelectedGuestMemories({ profile: profileName, memories: data.memories })
      }
    } catch (err) {
      console.error('Failed to load guest memories', err)
    }
  }

  if (!isOpen) return null

  const handleUpdateSettings = async (updates: Partial<AppSettings>) => {
    const newSettings = { ...settings, ...updates }
    setSettings(newSettings)
    try {
      await fetch('/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      setStatusMsg('Saved!')
      setTimeout(() => setStatusMsg(''), 1500)
    } catch (err) {
      console.error('Failed to save setting', err)
    }
  }

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return

    setIsAddingProfile(true)
    try {
      const res = await fetch('/family', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newName.trim(),
          role: newRole,
        }),
      })
      if (res.ok) {
        const profRes = await fetch('/profiles', { cache: 'no-store' })
        if (profRes.ok) {
          const profData = await profRes.json()
          if (Array.isArray(profData)) setProfiles(profData)
        }
        onSelectProfile(newName.trim())
        setNewName('')
        setStatusMsg(`Added ${newName.trim()}!`)
        setTimeout(() => setStatusMsg(''), 2000)
      }
    } catch (err) {
      console.error('Failed to create profile', err)
    } finally {
      setIsAddingProfile(false)
    }
  }

  const handleHardReload = () => {
    window.location.reload()
  }

  const handleClearAppCache = async () => {
    setStatusMsg('Clearing cache...')
    if ('caches' in window) {
      try {
        const keys = await window.caches.keys()
        await Promise.all(keys.map(k => window.caches.delete(k)))
      } catch {}
    }
    try {
      sessionStorage.clear()
    } catch {}
    setStatusMsg('Cache cleared! Reloading...')
    setTimeout(() => {
      window.location.href = window.location.pathname + '?reset-cache=1&t=' + Date.now()
    }, 500)
  }

  const handleResetCustomization = () => {
    if (window.confirm('Reset appearance and customizations back to default Emerald Matrix? (Your chat history will be kept)')) {
      onUpdateCustomization({
        theme: 'emerald',
        backgroundStyle: 'glow',
        fontSize: 'comfortable',
        chatDensity: 'comfortable',
        bubbleStyle: 'rounded',
        assistantEmoji: '🦖',
        assistantName: 'Doshie',
        greetingTitle: 'How can I help you today?',
        greetingSubtitle: 'Private local AI companion running directly on your RTX 5070 workstation.',
        glassEffect: true,
        showTimestamp: true,
        showAvatars: true,
        codeTheme: 'matrix',
        soundEffects: false,
        soundVolume: 0.8,
        smoothScroll: true,
      })
      setStatusMsg('Customizations reset to defaults!')
      setTimeout(() => setStatusMsg(''), 2500)
    }
  }

  const handleFlushServerCache = async () => {
    setIsFlushing(true)
    setStatusMsg('Flushing GPU & server cache...')
    try {
      const res = await fetch('/api/control-panel/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'flush_cache' }),
      })
      const data = await res.json()
      setStatusMsg(data.message || 'System & Model Cache Flushed!')
      setTimeout(() => setStatusMsg(''), 3000)
    } catch {
      setStatusMsg('Server cache flushed')
      setTimeout(() => setStatusMsg(''), 2000)
    } finally {
      setIsFlushing(false)
    }
  }

  const handleClearChatCache = () => {
    if (window.confirm(`Clear offline cached chats for ${activeProfile}? This will reset local conversation history for this profile on this device.`)) {
      try {
        localStorage.removeItem(`Doshie_chat_sessions_${activeProfile.toLowerCase().replace(/\s+/g, '_')}`)
        window.location.reload()
      } catch {}
    }
  }

  const handleLogout = async () => {
    if (window.confirm(`Log out of profile "${activeProfile}"?`)) {
      try {
        await fetch('/logout', { method: 'POST' })
      } catch {}
      try {
        await fetch('/profile-lock/lock', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: activeProfile }),
        })
      } catch {}
      localStorage.removeItem('Doshie_active_profile')
      onClose()
      if (onLockScreen) {
        onLockScreen()
      } else {
        window.location.reload()
      }
    }
  }

  const themes: Array<{
    id: GuiCustomization['theme']
    name: string
    accentColor: string
    bgColor: string
    desc: string
  }> = [
    {
      id: 'emerald',
      name: 'Emerald Matrix',
      accentColor: '#10b981',
      bgColor: '#08120d',
      desc: 'Classic obsidian green with vibrant mint accents',
    },
    {
      id: 'cyberpunk',
      name: 'Cyberpunk Neon',
      accentColor: '#a855f7',
      bgColor: '#090514',
      desc: 'Midnight violet with electric fuchsia & cyan glow',
    },
    {
      id: 'oled',
      name: 'OLED Midnight',
      accentColor: '#0284c7',
      bgColor: '#000000',
      desc: 'Deep pitch black with crisp icy blue highlights',
    },
    {
      id: 'amber',
      name: 'Sunset Amber',
      accentColor: '#d97706',
      bgColor: '#120d08',
      desc: 'Warm espresso charcoal with golden amber glow',
    },
    {
      id: 'crimson',
      name: 'Crimson Velvet',
      accentColor: '#e11d48',
      bgColor: '#120609',
      desc: 'Rich velvet plum with bold ruby red accents',
    },
    {
      id: 'terminal',
      name: 'Phosphor Retro',
      accentColor: '#22c55e',
      bgColor: '#020703',
      desc: 'Hacker monochrome CRT green on deep terminal black',
    },
    {
      id: 'nord',
      name: 'Nord Arctic Frost',
      accentColor: '#38bdf8',
      bgColor: '#0e141b',
      desc: 'Cool Scandinavian slate with icy arctic cyan glow',
    },
    {
      id: 'dracula',
      name: 'Dracula Vampire',
      accentColor: '#ec4899',
      bgColor: '#121018',
      desc: 'Gothic night purple with neon berry magenta accents',
    },
  ]

  const backgroundStyles: Array<{
    id: GuiCustomization['backgroundStyle']
    name: string
    desc: string
  }> = [
    { id: 'glow', name: 'Ambient Glow', desc: 'Soft luminous gradient aura' },
    { id: 'grid', name: 'Cyber Grid', desc: 'Futuristic technical matrix grid' },
    { id: 'stars', name: 'Starfield Galaxy', desc: 'Subtle twinkling cosmos stars' },
    { id: 'solid', name: 'Pure Minimalist', desc: 'Clean distraction-free dark solid' },
  ]

  const emojiOptions = ['🦖', '🦕', '🤖', '⚡', '🧠', '🐱', '🐉', '🚀', '🔮', '🛡️']

  const personaTones = [
    {
      id: 'humble_kind',
      label: 'Humble & Kind',
      icon: Heart,
      desc: 'Deeply humble, gentle, empathetic, patient, and uplifting in every response',
      color: 'from-emerald-600 to-teal-500',
    },
    {
      id: 'supportive',
      label: 'Compassionate Friend',
      icon: Sparkles,
      desc: 'Encouraging companion, validating, warm, and supportive',
      color: 'from-amber-500 to-orange-500',
    },
    {
      id: 'direct_tech',
      label: 'Precise Technician',
      icon: Code2,
      desc: 'Analytical, concise, objective, and code/technical focused',
      color: 'from-cyan-600 to-blue-500',
    },
    {
      id: 'playful',
      label: 'Witty & Cheerful',
      icon: Gamepad2,
      desc: 'Energetic, lighthearted, cheerful, and engaging',
      color: 'from-purple-600 to-pink-500',
    },
  ]

  const baseVoiceIdentities = [
    {
      id: 'hermes',
      name: 'Hermes (Master Overall Voice)',
      desc: 'Your neural cloned voice used by default across all profiles and responses',
      badge: '🎙️ Master Voice',
    },
    {
      id: 'aeriel',
      name: 'Aeriel Duran Voice',
      desc: 'Personal voice profile (falls back to Hermes Master Voice until sample is verified)',
      badge: '👤 Profile Voice',
    },
    {
      id: 'chatterbox_gentle',
      name: 'Gentle & Soft Companion',
      desc: 'Quiet, peaceful, gentle vocal delivery',
      badge: '✨ Gentle',
    },
    {
      id: 'chatterbox_warm',
      name: 'Warm Conversationalist',
      desc: 'Friendly, warm, conversational household voice',
      badge: '🏡 Warm',
    },
  ]

  const voiceIdentities = React.useMemo(() => {
    const map = new Map<string, any>()
    baseVoiceIdentities.forEach(v => map.set(v.id, v))
    customVoices.forEach(v => {
      if (map.has(v.id)) {
        map.set(v.id, { ...map.get(v.id), ...v })
      } else {
        map.set(v.id, v)
      }
    })
    return Array.from(map.values())
  }, [customVoices])

  const MYSPACE_PRESETS = [
    {
      id: 'myspace_2006',
      name: 'Classic MySpace 2006',
      desc: 'Retro cobalt blue borders, orange friend highlights, classic system font',
      badge: '🌟 2006 Retro',
      bg: 'https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1920&q=80',
      css: `/* === Classic 2006 MySpace Theme === */
:root {
  --bg-dark: #003366 !important;
  --card-dark: #ffffff !important;
  --card-hover: #e6f0fa !important;
  --border-dark: #002244 !important;
  --accent: #ff6600 !important;
  --accent-light: #ff8833 !important;
  --text: #000000 !important;
  --bubble-radius: 4px !important;
}
body {
  background: #003366 url('https://images.unsplash.com/photo-1579546929518-9e396f3cc809?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
  font-family: Arial, Helvetica, sans-serif !important;
}`,
    },
    {
      id: 'glitter_barbie',
      name: 'Glitter Queen 2000s',
      desc: 'Sparkly pink Barbiecore, glowing magenta glass cards & luminous buttons',
      badge: '💖 Glitter Glam',
      bg: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=80',
      css: `/* === 2000s Glitter Queen Barbiecore === */
:root {
  --bg-dark: #2a0824 !important;
  --card-dark: rgba(58, 12, 50, 0.85) !important;
  --card-hover: rgba(94, 20, 81, 0.95) !important;
  --border-dark: #f472b6 !important;
  --accent: #ec4899 !important;
  --accent-light: #fbcfe8 !important;
  --bubble-radius: 18px !important;
}
body {
  background: radial-gradient(circle, #581c87 0%, #1e0524 100%), url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}`,
    },
    {
      id: 'matrix_green',
      name: 'Cyberpunk Matrix Rain',
      desc: 'Deep terminal black, glowing phosphor green scanlines, hacker terminal',
      badge: '🕶️ Matrix Green',
      bg: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1920&q=80',
      css: `/* === Cyberpunk Matrix Green Terminal === */
:root {
  --bg-dark: #020b05 !important;
  --card-dark: rgba(5, 25, 12, 0.85) !important;
  --card-hover: rgba(8, 40, 20, 0.95) !important;
  --border-dark: #10b981 !important;
  --accent: #059669 !important;
  --accent-light: #6ee7b7 !important;
  --bubble-radius: 6px !important;
}
body {
  background: #020a05 url('https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}`,
    },
    {
      id: 'deep_space',
      name: 'Cosmic Deep Nebula',
      desc: 'Violet galactic aura, starry glass cards, ethereal purple nebula',
      badge: '🌌 Deep Nebula',
      bg: 'https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1920&q=80',
      css: `/* === Deep Space Cosmic Nebula === */
:root {
  --bg-dark: #070614 !important;
  --card-dark: rgba(18, 15, 45, 0.85) !important;
  --card-hover: rgba(30, 25, 75, 0.95) !important;
  --border-dark: #8b5cf6 !important;
  --accent: #7c3aed !important;
  --accent-light: #c4b5fd !important;
  --bubble-radius: 16px !important;
}
body {
  background: #060410 url('https://images.unsplash.com/photo-1506703719100-a0f3a48c0f86?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}`,
    },
    {
      id: 'vaporwave_84',
      name: 'Vaporwave Sunset 1984',
      desc: 'Sunset chill gradient, neon cyan & magenta grids, 80s synth aesthetic',
      badge: '🌇 Vaporwave 84',
      bg: 'https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=1920&q=80',
      css: `/* === Retro Vaporwave Sunset 1984 === */
:root {
  --bg-dark: #1f0b38 !important;
  --card-dark: rgba(43, 16, 77, 0.85) !important;
  --card-hover: rgba(70, 26, 125, 0.95) !important;
  --border-dark: #f43f5e !important;
  --accent: #06b6d4 !important;
  --accent-light: #fbcfe8 !important;
  --bubble-radius: 12px !important;
}
body {
  background: linear-gradient(180deg, #2b1055 0%, #7597de 100%) !important;
}`,
    },
    {
      id: 'scene_rawr',
      name: 'Scene / Emo Rawr 2007',
      desc: 'Jet black background, hot pink neon accents, edgy grunge borders',
      badge: '🖤 Scene Rawr',
      bg: 'https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1920&q=80',
      css: `/* === Emo / Scene Rawr 2007 === */
:root {
  --bg-dark: #000000 !important;
  --card-dark: #121212 !important;
  --card-hover: #1e1e1e !important;
  --border-dark: #ff007f !important;
  --accent: #ff007f !important;
  --accent-light: #ff66b2 !important;
  --bubble-radius: 2px !important;
}
body {
  background: #000000 url('https://images.unsplash.com/photo-1509198397868-475647b2a1e5?auto=format&fit=crop&w=1920&q=80') center/cover fixed !important;
}`,
    },
    {
      id: 'geocities_98',
      name: 'GeoCities Windows 98',
      desc: 'Classic Windows grey bevels, teal desktop wallpaper, pixel vibe',
      badge: '🕹️ Win 98',
      bg: '',
      css: `/* === GeoCities Retro Windows 98 === */
:root {
  --bg-dark: #008080 !important;
  --card-dark: #c0c0c0 !important;
  --card-hover: #dcdcdc !important;
  --border-dark: #808080 !important;
  --accent: #000080 !important;
  --accent-light: #0000ff !important;
  --text: #000000 !important;
  --bubble-radius: 0px !important;
}
body {
  background: #008080 !important;
  font-family: 'MS Sans Serif', Tahoma, sans-serif !important;
}`,
    },
  ]

  const handleSelectMySpacePreset = (preset: typeof MYSPACE_PRESETS[0]) => {
    setMyspaceCssInput(preset.css)
    onUpdateCustomization({
      myspacePreset: preset.id,
      myspaceCustomCss: preset.css,
      customWallpaperUrl: preset.bg || customization.customWallpaperUrl,
    })
    setMyspaceStatusMsg(`✨ Applied "${preset.name}" preset!`)
    setTimeout(() => setMyspaceStatusMsg(''), 3500)
  }

  const handleApplyMySpaceCss = () => {
    onUpdateCustomization({ myspaceCustomCss: myspaceCssInput })
    setMyspaceStatusMsg('🚀 MySpace custom CSS applied and saved!')
    setTimeout(() => setMyspaceStatusMsg(''), 3500)
  }

  const handleClearMySpaceCss = () => {
    setMyspaceCssInput('')
    onUpdateCustomization({ myspaceCustomCss: '' })
    setMyspaceStatusMsg('🔄 Custom CSS cleared.')
    setTimeout(() => setMyspaceStatusMsg(''), 3500)
  }

  const handleUploadCssFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target?.result as string
      if (text) {
        setMyspaceCssInput(text)
        onUpdateCustomization({ myspaceCustomCss: text })
        setMyspaceStatusMsg(`📁 Loaded and applied "${file.name}"!`)
        setTimeout(() => setMyspaceStatusMsg(''), 4000)
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleGenerateCssWithDoshie = async () => {
    if (!myspaceAiPrompt.trim() || isGeneratingCss) return
    setIsGeneratingCss(true)
    setMyspaceStatusMsg('🤖 Doshie is generating custom MySpace styling...')

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: `Generate custom MySpace CSS styling for my profile page with the following aesthetic: "${myspaceAiPrompt.trim()}". Return ONLY valid CSS code inside a \`\`\`css block. Target CSS variables like --bg-dark, --card-dark, --border-dark, --accent, --accent-light, --bubble-radius, body, button, etc.`,
          profile: activeProfile,
        }),
      })
      const data = await response.json()
      const reply = data.reply || ''
      const match = /```(?:css)?\s*([\s\S]*?)\s*```/.exec(reply)
      const generatedCss = match ? match[1].trim() : reply.trim()

      if (generatedCss && generatedCss.length > 10) {
        setMyspaceCssInput(generatedCss)
        onUpdateCustomization({ myspaceCustomCss: generatedCss })
        setMyspaceStatusMsg('✨ Doshie generated and applied your custom styling!')
      } else {
        setMyspaceStatusMsg('⚠️ Could not generate CSS. Please try again.')
      }
    } catch {
      setMyspaceStatusMsg('⚠️ Error communicating with Doshie.')
    } finally {
      setIsGeneratingCss(false)
      setTimeout(() => setMyspaceStatusMsg(''), 4000)
    }
  }

  const modes = [
    {
      id: 'family',
      label: 'Family Mode',
      icon: Home,
      desc: 'Household tasks, routines, reminders, homework & day-to-day planning',
      color: 'from-emerald-600 to-teal-500',
    },
    {
      id: 'tech',
      label: 'Tech & Code Mode',
      icon: Code2,
      desc: 'Coding, Python, Linux, system troubleshooting, hardware & architecture',
      color: 'from-cyan-600 to-blue-500',
    },
    {
      id: 'gaming',
      label: 'Gaming Mode',
      icon: Gamepad2,
      desc: 'PC/console performance, game settings, hardware temps & gaming tips',
      color: 'from-purple-600 to-indigo-500',
    },
    {
      id: 'normal',
      label: 'Balanced Assistant',
      icon: Bot,
      desc: 'Balanced, general-purpose personal assistant for all topics',
      color: 'from-emerald-700 to-emerald-600',
    },
  ]

  return (
    <div
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 48px)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 24px)',
        paddingLeft: 'max(env(safe-area-inset-left, 0px), 12px)',
        paddingRight: 'max(env(safe-area-inset-right, 0px), 12px)',
      }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div
        className="relative w-full max-w-3xl sm:max-w-4xl lg:max-w-5xl h-full max-h-[92vh] bg-[var(--card-dark)] border border-[var(--border-dark)] rounded-2xl sm:rounded-3xl shadow-2xl shadow-black flex flex-col overflow-hidden text-[var(--text)] transition-colors"
        onClick={e => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[var(--border-dark)] bg-[var(--bg-dark)] flex-none">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-xl sm:text-2xl flex-none">{customization.assistantEmoji || '🦖'}</span>
            <h2 className="font-semibold text-white text-sm sm:text-base truncate">
              Control & Customization Center
            </h2>
            {statusMsg && (
              <span className="text-[11px] text-emerald-400 bg-emerald-950/80 px-2 py-0.5 rounded-full border border-emerald-800 animate-pulse flex-none hidden sm:inline">
                {statusMsg}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-neutral-400 hover:text-white hover:bg-[var(--card-hover)] transition-colors cursor-pointer flex-none"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-[var(--border-dark)] bg-[var(--bg-dark)] overflow-x-auto flex-none px-3 sm:px-5 py-2.5 gap-2">
          <button
            onClick={() => handleTabChange('settings')}
            className={`flex-none px-3.5 py-2 rounded-xl flex items-center justify-center gap-1.5 text-xs font-semibold transition-all cursor-pointer ${
              tab === 'settings'
                ? 'bg-[var(--accent)] text-white shadow-sm'
                : 'bg-[var(--card-dark)] text-neutral-300 hover:text-white hover:bg-[var(--card-hover)] border border-[var(--border-dark)]'
            }`}
          >
            <Heart className="w-3.5 h-3.5" />
            <span>Voice & Persona</span>
          </button>
          <button
            onClick={() => handleTabChange('appearance')}
            className={`flex-none px-3.5 py-2 rounded-xl flex items-center justify-center gap-1.5 text-xs font-semibold transition-all cursor-pointer ${
              tab === 'appearance'
                ? 'bg-[var(--accent)] text-white shadow-sm'
                : 'bg-[var(--card-dark)] text-neutral-300 hover:text-white hover:bg-[var(--card-hover)] border border-[var(--border-dark)]'
            }`}
          >
            <Palette className="w-3.5 h-3.5" />
            <span>Appearance</span>
          </button>
          <button
            onClick={() => handleTabChange('profiles')}
            className={`flex-none px-3.5 py-2 rounded-xl flex items-center justify-center gap-1.5 text-xs font-semibold transition-all cursor-pointer ${
              tab === 'profiles'
                ? 'bg-[var(--accent)] text-white shadow-sm'
                : 'bg-[var(--card-dark)] text-neutral-300 hover:text-white hover:bg-[var(--card-hover)] border border-[var(--border-dark)]'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>Profiles</span>
          </button>
          <button
            onClick={() => handleTabChange('maintenance')}
            className={`flex-none px-3.5 py-2 rounded-xl flex items-center justify-center gap-1.5 text-xs font-semibold transition-all cursor-pointer ${
              tab === 'maintenance'
                ? 'bg-[var(--accent)] text-white shadow-sm'
                : 'bg-[var(--card-dark)] text-neutral-300 hover:text-white hover:bg-[var(--card-hover)] border border-[var(--border-dark)]'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset & Cache</span>
          </button>
          <button
            onClick={() => handleTabChange('doctor')}
            className={`flex-none px-3.5 py-2 rounded-xl flex items-center justify-center gap-1.5 text-xs font-semibold transition-all cursor-pointer ${
              tab === 'doctor'
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-[var(--card-dark)] text-emerald-300/90 hover:text-emerald-200 hover:bg-[var(--card-hover)] border border-emerald-800/50'
            }`}
          >
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>🩺 Doctor AI</span>
          </button>
          {isAdmin && (
            <button
              onClick={() => handleTabChange('oversight')}
              className={`flex-none px-3.5 py-2 rounded-xl flex items-center justify-center gap-1.5 text-xs font-semibold transition-all cursor-pointer ${
                tab === 'oversight'
                  ? 'bg-amber-600 text-white shadow-sm'
                  : 'bg-[var(--card-dark)] text-amber-300/80 hover:text-amber-200 hover:bg-[var(--card-hover)] border border-amber-800/50'
              }`}
            >
              <Shield className="w-3.5 h-3.5 text-amber-300" />
              <span>👑 Oversight</span>
            </button>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto overscroll-contain p-4 sm:p-5 space-y-6">
          {tab === 'settings' ? (
            <>
              {/* Section 1: Personality Demeanor (Humble & Kind) */}
              <div>
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Heart className="w-3.5 h-3.5 text-rose-400" />
                  <span>Doshie Persona & Demeanor</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {personaTones.map(p => {
                    const Icon = p.icon
                    const isSelected = (settings.persona_tone || 'humble_kind') === p.id
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleUpdateSettings({ persona_tone: p.id })}
                        className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-[#122e20] border-emerald-400 shadow-md ring-2 ring-emerald-400/40'
                            : 'bg-[#0e2218] border-[#1b432f] hover:bg-[#143224]'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <div className={`p-1.5 rounded-lg bg-gradient-to-br ${p.color} text-white`}>
                              <Icon className="w-3.5 h-3.5" />
                            </div>
                            <span className="font-semibold text-xs sm:text-sm text-white">{p.label}</span>
                          </div>
                          {isSelected && <Check className="w-4 h-4 text-emerald-400" />}
                        </div>
                        <p className="text-[11px] text-emerald-300/70 leading-relaxed">{p.desc}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Section 2: Custom Instructions / Prompt from Hermes */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-2">
                  <FileText className="w-3.5 h-3.5" />
                  <span>Custom Instructions for Doshie</span>
                </label>
                <div className="space-y-2 bg-[#0d2218] p-3.5 rounded-xl border border-[#1b432f]">
                  <p className="text-[11px] text-emerald-300/70">
                    Tell Doshie exactly how you want him to behave, speak, and treat you (e.g. humble, gentle, encouraging, kind):
                  </p>
                  <textarea
                    rows={3}
                    value={customPrompt}
                    onChange={e => setCustomPrompt(e.target.value)}
                    placeholder="e.g. Always be humble, patient, deeply kind, and explain things with warmth..."
                    className="w-full px-3 py-2 rounded-lg bg-[#081710] border border-[#214c36] focus:border-emerald-400 focus:outline-none text-xs sm:text-sm text-white resize-none"
                  />
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={() => handleUpdateSettings({ custom_system_prompt: customPrompt })}
                      className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold cursor-pointer shadow-sm active:scale-95"
                    >
                      Save Instructions
                    </button>
                  </div>
                </div>
              </div>

              {/* Section 3: Voice Selection & Speech Tuning */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Volume2 className="w-3.5 h-3.5" />
                  <span>Voice Engine & Different Voices</span>
                </label>
                <div className="space-y-3 bg-[#0d2218] p-3.5 rounded-xl border border-[#1b432f]">
                  {/* Voice Selector */}
                  <div>
                    <label className="block text-xs font-medium text-emerald-300 mb-1.5">Selected Voice Profile</label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {voiceIdentities.map(v => {
                        const isSelected = (settings.voice_identity || 'hermes') === v.id
                        return (
                          <button
                            key={v.id}
                            type="button"
                            onClick={() => handleUpdateSettings({ voice_identity: v.id })}
                            className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                              isSelected
                                ? 'bg-[#153826] border-emerald-400 ring-1 ring-emerald-400/40'
                                : 'bg-[#091b12] border-[#183928] hover:bg-[#0f281b]'
                            }`}
                          >
                            <div className="flex items-center justify-between gap-1">
                              <span className="text-xs font-semibold text-white truncate">{v.name}</span>
                              <div className="flex items-center gap-1 shrink-0">
                                {v.badge && (
                                  <span className="text-[9px] px-1.5 py-0.5 rounded-md bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-medium">
                                    {v.badge}
                                  </span>
                                )}
                                {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                              </div>
                            </div>
                            <p className="text-[10px] text-emerald-400/60 mt-0.5">{v.desc}</p>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Open Voice Studio & Voice Changer */}
                  <div className="pt-2 border-t border-[#163625]">
                    <a
                      href="/voice-studio"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full flex items-center justify-between p-3 rounded-xl bg-gradient-to-r from-emerald-900/60 via-teal-900/50 to-emerald-950/80 border border-emerald-500/40 hover:border-emerald-400 text-white transition-all shadow-sm group"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-300 group-hover:bg-emerald-500/30">
                          <Mic className="w-4 h-4" />
                        </div>
                        <div>
                          <div className="text-xs font-bold text-white flex items-center gap-1.5">
                            Voice Studio & Voice Changer
                            <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-mono">RTX 5070</span>
                          </div>
                          <div className="text-[10px] text-emerald-300/70">Record samples, clone new voices & convert your voice</div>
                        </div>
                      </div>
                      <ExternalLink className="w-4 h-4 text-emerald-400 group-hover:translate-x-0.5 transition-transform" />
                    </a>
                  </div>

                  {/* Speak Replies Toggle */}
                  <div className="flex items-center justify-between pt-2 border-t border-[#163625]">
                    <div>
                      <div className="text-xs sm:text-sm font-medium text-white">Speak AI Responses</div>
                      <div className="text-[11px] text-emerald-400/70">Read out answers using neural voice</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.speak_replies}
                        onChange={e => handleUpdateSettings({ speak_replies: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-[#163625] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                    </label>
                  </div>

                  {/* Speech Rate & Pitch Sliders */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-[#163625]">
                    <div>
                      <div className="flex justify-between text-xs text-emerald-300 mb-1">
                        <span>Speed: {settings.voice_rate ?? 1.0}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.6"
                        max="1.4"
                        step="0.05"
                        value={settings.voice_rate ?? 1.0}
                        onChange={e => handleUpdateSettings({ voice_rate: parseFloat(e.target.value) })}
                        className="w-full accent-emerald-500 bg-[#163625] h-1.5 rounded-lg cursor-pointer"
                      />
                    </div>
                    <div>
                      <div className="flex justify-between text-xs text-emerald-300 mb-1">
                        <span>Pitch: {settings.voice_pitch ?? 1.0}x</span>
                      </div>
                      <input
                        type="range"
                        min="0.7"
                        max="1.3"
                        step="0.05"
                        value={settings.voice_pitch ?? 1.0}
                        onChange={e => handleUpdateSettings({ voice_pitch: parseFloat(e.target.value) })}
                        className="w-full accent-emerald-500 bg-[#163625] h-1.5 rounded-lg cursor-pointer"
                      />
                    </div>
                  </div>

                  {/* Preview Voice Button */}
                  <div className="pt-2 border-t border-[#163625] flex items-center justify-between">
                    <div>
                      <div className="text-xs font-semibold text-emerald-200">Neural Cloned Voice Test</div>
                      <div className="text-[10px] text-emerald-400/60">Audio model: Chatterbox Turbo on RTX 5070</div>
                    </div>
                    <button
                      type="button"
                      onClick={handleTestVoice}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer shadow-xs active:scale-95 ${
                        isPlayingVoice
                          ? 'bg-rose-950/80 border-rose-600 text-rose-200'
                          : isTestingVoice
                          ? 'bg-emerald-950/80 border-emerald-500 text-emerald-300'
                          : 'bg-emerald-900/60 hover:bg-emerald-800/80 border-emerald-600/70 text-emerald-100'
                      }`}
                    >
                      {isTestingVoice ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                          <span>Generating...</span>
                        </>
                      ) : isPlayingVoice ? (
                        <>
                          <VolumeX className="w-3.5 h-3.5 text-rose-400" />
                          <span>Stop Test</span>
                        </>
                      ) : (
                        <>
                          <Volume2 className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Play Voice Sample</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>

              {/* Section 4: Operational Mode */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Operational Domain Mode</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {modes.map(m => {
                    const isSelected = (settings.mode || 'family').toLowerCase() === m.id
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => handleUpdateSettings({ mode: m.id })}
                        className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-[#153826] border-emerald-400 ring-1 ring-emerald-400/40'
                            : 'bg-[#091b12] border-[#183928] hover:bg-[#0f281b]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-white">{m.label}</span>
                          {isSelected && <Check className="w-3.5 h-3.5 text-emerald-400" />}
                        </div>
                        <p className="text-[10px] text-emerald-400/60 mt-0.5">{m.desc}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Section 5: Memory & Location */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Brain className="w-3.5 h-3.5" />
                  <span>Memory & Location</span>
                </label>
                <div className="space-y-3 bg-[#0d2218] p-3.5 rounded-xl border border-[#1b432f]">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs sm:text-sm font-medium text-white">Auto-Memory</div>
                      <div className="text-[11px] text-emerald-400/70">Automatically recall context and preferences</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.auto_memory}
                        onChange={e => handleUpdateSettings({ auto_memory: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-[#163625] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                    </label>
                  </div>

                  <div className="pt-2 border-t border-[#163625]">
                    <label className="block text-xs font-medium text-emerald-300 mb-1.5 flex items-center gap-1.5">
                      <MapPin className="w-3 h-3 text-emerald-400" />
                      <span>Default City (Weather & Local News)</span>
                    </label>
                    <input
                      type="text"
                      value={settings.default_weather_location || ''}
                      onChange={e => setSettings(s => ({ ...s, default_weather_location: e.target.value }))}
                      onBlur={e => handleUpdateSettings({ default_weather_location: e.target.value })}
                      placeholder="e.g. El Paso"
                      className="w-full px-3 py-1.5 rounded-lg bg-[#081710] border border-[#214c36] focus:border-emerald-400 focus:outline-none text-xs sm:text-sm text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Section 6: Web Search & Under-18 Safety Guardrails */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Web Search & Under-18 Child Safety</span>
                </label>
                <div className="space-y-3 bg-[#0d2218] p-3.5 rounded-xl border border-[#1b432f]">
                  {/* Auto Web Search Toggle */}
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs sm:text-sm font-medium text-white">Auto-Search Web for Questions</div>
                      <div className="text-[11px] text-emerald-400/70">Doshie automatically searches live web data to answer questions</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.auto_web_search !== false}
                        onChange={e => handleUpdateSettings({ auto_web_search: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-[#163625] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                    </label>
                  </div>

                  {/* SafeSearch & Content Filter Toggle */}
                  <div className="flex items-center justify-between pt-2 border-t border-[#163625]">
                    <div>
                      <div className="text-xs sm:text-sm font-medium text-white">SafeSearch Content Filtering</div>
                      <div className="text-[11px] text-emerald-400/70">Block explicit, adult, violence, or unsafe search results</div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input
                        type="checkbox"
                        checked={settings.safe_search !== false}
                        onChange={e => handleUpdateSettings({ safe_search: e.target.checked })}
                        className="sr-only peer"
                      />
                      <div className="w-11 h-6 bg-[#163625] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                    </label>
                  </div>

                  {/* Profile Age & Under-18 Guardrails */}
                  <div className="pt-2 border-t border-[#163625]">
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-medium text-emerald-300">Profile Age (Child Safety Rating)</label>
                      <span className="text-[11px] font-semibold text-emerald-400">
                        {(settings.age ?? 18) < 18 ? '🛡️ Minor Safety Active (< 18)' : 'Adult Profile (18+)'}
                      </span>
                    </div>
                    <input
                      type="number"
                      min="1"
                      max="120"
                      value={settings.age ?? 18}
                      onChange={e => {
                        const val = parseInt(e.target.value) || 18
                        setSettings(s => ({ ...s, age: val }))
                      }}
                      onBlur={e => {
                        const val = parseInt(e.target.value) || 18
                        handleUpdateSettings({ age: val })
                      }}
                      className="w-full px-3 py-1.5 rounded-lg bg-[#081710] border border-[#214c36] focus:border-emerald-400 focus:outline-none text-xs sm:text-sm text-white"
                    />
                    <p className="text-[10px] text-emerald-400/60 mt-1">
                      Profiles under 18 automatically enforce Bing SafeSearch, strict keyword filtering, and child-safe AI demeanor guardrails.
                    </p>
                  </div>
                </div>
              </div>
            </>
          ) : tab === 'appearance' ? (
            <>
              {/* Theme Selector */}
              <div>
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Palette className="w-3.5 h-3.5" />
                  <span>Color Theme & Aura</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {themes.map(t => {
                    const isSelected = customization.theme === t.id
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => onUpdateCustomization({ theme: t.id })}
                        className={`p-3 rounded-xl border text-left transition-all flex items-start gap-3 cursor-pointer ${
                          isSelected
                            ? 'border-[var(--accent)] bg-[var(--card-hover)] ring-2 ring-[var(--accent)]/40 shadow-md'
                            : 'border-[var(--border-dark)] bg-[var(--card-dark)] hover:bg-[var(--card-hover)]'
                        }`}
                      >
                        <div
                          className="w-7 h-7 rounded-lg border border-white/20 flex-none flex items-center justify-center shadow-inner mt-0.5"
                          style={{ backgroundColor: t.bgColor }}
                        >
                          <div
                            className="w-3.5 h-3.5 rounded-full"
                            style={{ backgroundColor: t.accentColor }}
                          />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-xs sm:text-sm text-white">{t.name}</span>
                            {isSelected && <Check className="w-4 h-4 text-[var(--accent)]" />}
                          </div>
                          <p className="text-[11px] text-emerald-300/70 mt-0.5 leading-snug">{t.desc}</p>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Background Style & Aura */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                  <span>Background Atmosphere & Aura</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {backgroundStyles.map(b => {
                    const isSelected = (customization.backgroundStyle || 'glow') === b.id
                    return (
                      <button
                        key={b.id}
                        type="button"
                        onClick={() => onUpdateCustomization({ backgroundStyle: b.id })}
                        className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                          isSelected
                            ? 'border-[var(--accent)] bg-[var(--card-hover)] ring-1 ring-[var(--accent)]/50'
                            : 'border-[var(--border-dark)] bg-[var(--card-dark)] hover:bg-[var(--card-hover)]'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-white">{b.name}</span>
                          {isSelected && <Check className="w-3.5 h-3.5 text-[var(--accent)]" />}
                        </div>
                        <p className="text-[10px] text-emerald-300/70 mt-0.5">{b.desc}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Font Size & Spacing Density */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-2">
                      <Type className="w-3.5 h-3.5" />
                      <span>Font Size</span>
                    </label>
                    <div className="grid grid-cols-3 gap-1.5">
                      {[
                        { id: 'compact', label: 'Compact' },
                        { id: 'comfortable', label: 'Medium' },
                        { id: 'large', label: 'Large' },
                      ].map(f => {
                        const isSelected = customization.fontSize === f.id
                        return (
                          <button
                            key={f.id}
                            type="button"
                            onClick={() => onUpdateCustomization({ fontSize: f.id as any })}
                            className={`py-2 px-1.5 rounded-lg border text-center text-xs transition-all cursor-pointer ${
                              isSelected
                                ? 'border-[var(--accent)] bg-[var(--card-hover)] text-white font-semibold'
                                : 'border-[var(--border-dark)] bg-[var(--card-dark)] text-emerald-300/80 hover:bg-[var(--card-hover)]'
                            }`}
                          >
                            {f.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  <div>
                    <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-2">
                      <Sliders className="w-3.5 h-3.5" />
                      <span>Chat Density</span>
                    </label>
                    <div className="grid grid-cols-3 gap-1.5">
                      {[
                        { id: 'compact', label: 'Tight' },
                        { id: 'comfortable', label: 'Balanced' },
                        { id: 'spacious', label: 'Airy' },
                      ].map(d => {
                        const isSelected = (customization.chatDensity || 'comfortable') === d.id
                        return (
                          <button
                            key={d.id}
                            type="button"
                            onClick={() => onUpdateCustomization({ chatDensity: d.id as any })}
                            className={`py-2 px-1.5 rounded-lg border text-center text-xs transition-all cursor-pointer ${
                              isSelected
                                ? 'border-[var(--accent)] bg-[var(--card-hover)] text-white font-semibold'
                                : 'border-[var(--border-dark)] bg-[var(--card-dark)] text-emerald-300/80 hover:bg-[var(--card-hover)]'
                            }`}
                          >
                            {d.label}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                </div>
              </div>

              {/* Message Bubble Style */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Chat Bubble Style</span>
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'rounded', label: 'Rounded Pills' },
                    { id: 'modern', label: 'Sleek Cards' },
                    { id: 'terminal', label: 'Retro Box' },
                    { id: 'glow_card', label: 'Luminous Card' },
                  ].map(b => {
                    const isSelected = customization.bubbleStyle === b.id
                    return (
                      <button
                        key={b.id}
                        type="button"
                        onClick={() => onUpdateCustomization({ bubbleStyle: b.id as any })}
                        className={`py-2 px-2 rounded-xl border text-center transition-all cursor-pointer ${
                          isSelected
                            ? 'border-[var(--accent)] bg-[var(--card-hover)] text-white ring-1 ring-[var(--accent)]/50 font-semibold'
                            : 'border-[var(--border-dark)] bg-[var(--card-dark)] text-emerald-300/80 hover:bg-[var(--card-hover)]'
                        }`}
                      >
                        <div className="text-xs">{b.label}</div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Custom Welcome Message */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-2">
                  <Smile className="w-3.5 h-3.5" />
                  <span>Custom Greeting & Subtitle</span>
                </label>
                <div className="space-y-2 bg-[var(--card-dark)] p-3 rounded-xl border border-[var(--border-dark)]">
                  <div>
                    <span className="text-[11px] text-emerald-400/80 block mb-1">Greeting Title</span>
                    <input
                      type="text"
                      value={customization.greetingTitle || 'How can I help you today?'}
                      onChange={e => onUpdateCustomization({ greetingTitle: e.target.value })}
                      placeholder="e.g. How can I serve you today?"
                      className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                    />
                  </div>
                  <div>
                    <span className="text-[11px] text-emerald-400/80 block mb-1">Greeting Subtitle</span>
                    <input
                      type="text"
                      value={customization.greetingSubtitle || 'Private local AI companion running directly on your RTX 5070 workstation.'}
                      onChange={e => onUpdateCustomization({ greetingSubtitle: e.target.value })}
                      placeholder="e.g. Humble, kind personal assistant."
                      className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                    />
                  </div>
                </div>
              </div>

              {/* Assistant Persona & Emoji */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Bot className="w-3.5 h-3.5" />
                  <span>Assistant Avatar & Name</span>
                </label>
                <div className="space-y-3 bg-[var(--card-dark)] p-3.5 rounded-xl border border-[var(--border-dark)]">
                  {/* Emoji Swatches */}
                  <div>
                    <span className="text-[11px] text-emerald-400/80 block mb-1.5">Avatar Emoji</span>
                    <div className="flex flex-wrap gap-2">
                      {emojiOptions.map(em => (
                        <button
                          key={em}
                          type="button"
                          onClick={() => onUpdateCustomization({ assistantEmoji: em })}
                          className={`w-9 h-9 rounded-xl text-lg flex items-center justify-center transition-all cursor-pointer ${
                            customization.assistantEmoji === em
                              ? 'bg-[var(--accent)]/30 border-2 border-[var(--accent)] scale-110 shadow-sm'
                              : 'bg-[var(--bg-dark)] border border-[var(--border-dark)] hover:scale-105'
                          }`}
                        >
                          {em}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Assistant Display Name */}
                  <div className="pt-2 border-t border-[var(--border-dark)]">
                    <span className="text-[11px] text-emerald-400/80 block mb-1">Display Name</span>
                    <input
                      type="text"
                      value={customization.assistantName || 'Doshie'}
                      onChange={e => onUpdateCustomization({ assistantName: e.target.value })}
                      placeholder="e.g. Doshie, Yoshi, Hermes"
                      className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                    />
                  </div>
                </div>
              </div>

              {/* MySpace Studio & Custom Code (HTML/CSS) */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <input
                  type="file"
                  ref={cssFileInputRef}
                  onChange={handleUploadCssFile}
                  accept=".css,.txt,.style,.html"
                  className="hidden"
                />

                <div className="flex items-center justify-between mb-3">
                  <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)]">
                    <Code2 className="w-3.5 h-3.5 text-pink-400" />
                    <span>MySpace Profile Studio & Custom CSS</span>
                  </label>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-pink-950/80 border border-pink-700/60 text-pink-300 font-mono">
                    2000s Webmaster Code
                  </span>
                </div>

                <div className="space-y-4 bg-[var(--card-dark)] p-3.5 sm:p-4 rounded-xl border border-[var(--border-dark)]">
                  <p className="text-xs text-neutral-300 leading-relaxed">
                    Personalize your interface with custom CSS stylesheets, retro 2000s themes, animated glitter backgrounds, profile songs, and cursor trails.
                  </p>

                  {myspaceStatusMsg && (
                    <div className="p-2.5 rounded-lg bg-emerald-950/90 border border-emerald-700 text-emerald-200 text-xs flex items-center justify-between animate-fadeIn">
                      <span>{myspaceStatusMsg}</span>
                      <button onClick={() => setMyspaceStatusMsg('')} className="text-emerald-400 hover:text-white p-0.5">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {/* Retro MySpace Presets Grid */}
                  <div>
                    <span className="text-[11px] text-emerald-400/90 font-semibold block mb-2">
                      🌟 1-Click Retro MySpace Themes
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                      {MYSPACE_PRESETS.map(preset => {
                        const isSelected = customization.myspacePreset === preset.id
                        return (
                          <button
                            key={preset.id}
                            type="button"
                            onClick={() => handleSelectMySpacePreset(preset)}
                            className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-1.5 ${
                              isSelected
                                ? 'bg-gradient-to-br from-pink-950/60 to-[var(--card-hover)] border-pink-500 shadow-md ring-1 ring-pink-400/50'
                                : 'bg-[var(--bg-dark)] border-[var(--border-dark)] hover:bg-[var(--card-hover)] hover:border-pink-500/40'
                            }`}
                          >
                            <div className="flex items-center justify-between w-full">
                              <span className="text-xs font-bold text-white truncate">{preset.name}</span>
                              <span className="text-[9px] px-1.5 py-0.5 rounded bg-black/50 text-pink-300 border border-pink-700/40">
                                {preset.badge}
                              </span>
                            </div>
                            <p className="text-[10px] text-neutral-400 line-clamp-2 leading-tight">
                              {preset.desc}
                            </p>
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Ask Doshie to Write CSS Theme */}
                  <div className="p-3 rounded-xl bg-[var(--bg-dark)] border border-[var(--border-dark)] space-y-2">
                    <span className="text-[11px] text-pink-300 font-semibold flex items-center gap-1.5">
                      <Wand2 className="w-3 h-3 text-pink-400" />
                      <span>Ask Doshie AI to Write a Custom Style</span>
                    </span>
                    <div className="flex flex-col sm:flex-row gap-2">
                      <input
                        type="text"
                        value={myspaceAiPrompt}
                        onChange={e => setMyspaceAiPrompt(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleGenerateCssWithDoshie()}
                        placeholder="e.g. Glowing vaporwave sunset with neon borders and glass bubbles..."
                        className="flex-1 px-3 py-1.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] focus:border-pink-400 focus:outline-none text-xs text-white"
                      />
                      <button
                        type="button"
                        onClick={handleGenerateCssWithDoshie}
                        disabled={!myspaceAiPrompt.trim() || isGeneratingCss}
                        className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-500 hover:to-purple-500 text-white text-xs font-semibold flex items-center justify-center gap-1.5 disabled:opacity-40 disabled:pointer-events-none cursor-pointer transition-all shadow-sm"
                      >
                        {isGeneratingCss ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
                        <span>{isGeneratingCss ? 'Generating...' : 'Generate CSS'}</span>
                      </button>
                    </div>
                  </div>

                  {/* Custom CSS Code Box & File Upload */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-emerald-400/90 font-semibold flex items-center gap-1.5">
                        <Code2 className="w-3.5 h-3.5" />
                        <span>Custom CSS Code Editor</span>
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => cssFileInputRef.current?.click()}
                          className="px-2.5 py-1 rounded-lg bg-[var(--bg-dark)] hover:bg-[var(--card-hover)] text-neutral-200 border border-[var(--border-dark)] hover:border-pink-500/50 text-[11px] font-medium flex items-center gap-1 transition-all cursor-pointer"
                        >
                          <Upload className="w-3 h-3 text-pink-400" />
                          <span>Upload File (.css)</span>
                        </button>
                        <button
                          type="button"
                          onClick={handleClearMySpaceCss}
                          className="px-2 py-1 rounded-lg bg-[var(--bg-dark)] hover:bg-rose-950/60 text-neutral-400 hover:text-rose-300 border border-[var(--border-dark)] text-[11px] transition-all cursor-pointer"
                        >
                          Clear
                        </button>
                      </div>
                    </div>

                    <div className="relative rounded-xl overflow-hidden border border-[var(--border-dark)] focus-within:border-pink-500 shadow-inner bg-[#0b0f19]">
                      <textarea
                        rows={7}
                        value={myspaceCssInput}
                        onChange={e => setMyspaceCssInput(e.target.value)}
                        placeholder="/* Paste or write your custom MySpace CSS rules here... */&#10;:root {&#10;  --bg-dark: #003366 !important;&#10;  --accent: #ff6600 !important;&#10;}"
                        className="w-full p-3 bg-transparent text-emerald-300 font-mono text-[12px] leading-relaxed resize-y outline-none"
                        spellCheck="false"
                      />
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] text-neutral-400">
                        Supports CSS variables, custom backgrounds, card borders, and keyframe animations.
                      </span>
                      <button
                        type="button"
                        onClick={handleApplyMySpaceCss}
                        className="px-4 py-1.5 rounded-lg bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] hover:opacity-90 active:scale-95 text-white text-xs font-semibold transition-all shadow-md cursor-pointer flex items-center gap-1.5"
                      >
                        <Check className="w-3.5 h-3.5" />
                        <span>Apply & Save CSS Live</span>
                      </button>
                    </div>
                  </div>

                  {/* MySpace Retro Interactive Extras */}
                  <div className="pt-3 border-t border-[var(--border-dark)] space-y-3">
                    <span className="text-[11px] text-pink-300 font-semibold block">
                      ✨ MySpace Profile Extras & Music
                    </span>

                    {/* Sparkle Cursor Toggle */}
                    <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)]">
                      <div>
                        <div className="text-xs font-semibold text-white flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                          <span>Glitter Sparkle Cursor Trail</span>
                        </div>
                        <div className="text-[10px] text-neutral-400">
                          Shimmering star sparkles follow your mouse cursor across the screen
                        </div>
                      </div>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={Boolean(customization.myspaceSparkleCursor)}
                          onChange={e => onUpdateCustomization({ myspaceSparkleCursor: e.target.checked })}
                          className="sr-only peer"
                        />
                        <div className="w-10 h-5 bg-neutral-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-pink-600"></div>
                      </label>
                    </div>

                    {/* Scrolling Marquee Ticker */}
                    <div className="p-2.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] space-y-1.5">
                      <span className="text-xs font-semibold text-white block">
                        📜 Retro Marquee Ticker Headline
                      </span>
                      <input
                        type="text"
                        value={customization.myspaceMarqueeText || ''}
                        onChange={e => onUpdateCustomization({ myspaceMarqueeText: e.target.value })}
                        placeholder="e.g. 🖤 Thanks for visiting my profile! Doshie is online on RTX 5070 🖤"
                        className="w-full px-3 py-1.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] focus:border-pink-400 focus:outline-none text-xs text-white"
                      />
                    </div>

                    {/* Profile Song / Audio URL */}
                    <div className="p-2.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] space-y-2">
                      <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                        <Music className="w-3.5 h-3.5 text-purple-400" />
                        <span>MySpace Profile Audio / Song Player</span>
                      </span>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <input
                          type="text"
                          value={customization.myspaceSongTitle || ''}
                          onChange={e => onUpdateCustomization({ myspaceSongTitle: e.target.value })}
                          placeholder="Song Title (e.g. Chemical Romance - Helena)"
                          className="w-full px-3 py-1.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] focus:border-pink-400 focus:outline-none text-xs text-white"
                        />
                        <input
                          type="text"
                          value={customization.myspaceSongUrl || ''}
                          onChange={e => onUpdateCustomization({ myspaceSongUrl: e.target.value })}
                          placeholder="MP3 or Audio Stream URL (https://...)"
                          className="w-full px-3 py-1.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] focus:border-pink-400 focus:outline-none text-xs text-white"
                        />
                      </div>
                    </div>

                    {/* Wallpaper URL & Tile Mode */}
                    <div className="p-2.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] space-y-2">
                      <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                        <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Custom Wallpaper URL & Tile Layout</span>
                      </span>
                      <div className="flex flex-col sm:flex-row gap-2">
                        <input
                          type="text"
                          value={customization.customWallpaperUrl || ''}
                          onChange={e => onUpdateCustomization({ customWallpaperUrl: e.target.value })}
                          placeholder="Paste image or animated GIF URL (https://...)"
                          className="flex-1 px-3 py-1.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] focus:border-pink-400 focus:outline-none text-xs text-white"
                        />
                        <select
                          value={customization.myspaceBackgroundRepeat || 'cover'}
                          onChange={e => onUpdateCustomization({ myspaceBackgroundRepeat: e.target.value as any })}
                          className="px-3 py-1.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] focus:border-pink-400 focus:outline-none text-xs text-white"
                        >
                          <option value="cover">Full Cover</option>
                          <option value="tile">Retro Tile (Repeat)</option>
                          <option value="repeat-x">Repeat Horizontal</option>
                        </select>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Section 6: Lock Screen Customization */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                  <Lock className="w-3.5 h-3.5 text-amber-400" />
                  <span>Lock Screen & Security Customization</span>
                </label>
                <div className="space-y-4 bg-[var(--card-dark)] p-3.5 rounded-xl border border-[var(--border-dark)]">
                  {/* Live Lock Screen Preview Card */}
                  <div className="relative p-4 rounded-2xl overflow-hidden border border-white/10 bg-black/40 text-center space-y-2">
                    <div className="text-[10px] uppercase font-mono tracking-wider text-emerald-400 font-bold">
                      Live Lock Screen Preview
                    </div>
                    <div className="text-2xl sm:text-3xl font-mono font-light text-white">
                      {customization.lockScreenClockFormat === '24h' ? '14:30:00' : '2:30:00 PM'}
                    </div>
                    <div className="text-sm font-bold text-white flex items-center justify-center gap-1.5">
                      <span>{customization.assistantEmoji || '🦖'}</span>
                      <span>{customization.lockScreenTitle || `${customization.assistantName || 'Doshie'} Workstation`}</span>
                    </div>
                    <div className="text-[11px] text-gray-300/80 max-w-xs mx-auto line-clamp-2">
                      {customization.lockScreenSubtitle || 'Private local AI companion secured.'}
                    </div>
                    <div className="pt-1">
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-950/80 border border-emerald-700/60 text-emerald-300 font-mono">
                        {customization.lockScreenCustomNote || 'Secure Workstation • RTX 5070 Local Engine'}
                      </span>
                    </div>
                  </div>

                  {/* Lock Screen Wallpaper Selection */}
                  <div>
                    <span className="text-[11px] text-emerald-400/80 block mb-1.5">Lock Screen Wallpaper & Ambient Style</span>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                      {[
                        { id: 'matrix', label: 'Emerald Matrix', desc: 'Obsidian emerald glow' },
                        { id: 'cyberpunk', label: 'Cyberpunk Neon', desc: 'Fuchsia & cyan aura' },
                        { id: 'aurora', label: 'Arctic Aurora', desc: 'Teal & indigo waves' },
                        { id: 'stars', label: 'Starfield Nebula', desc: 'Cosmic stars grid' },
                        { id: 'oled', label: 'Pure OLED Pitch', desc: 'Minimalist true black' },
                      ].map(w => (
                        <button
                          key={w.id}
                          type="button"
                          onClick={() => onUpdateCustomization({ lockScreenWallpaper: w.id as any })}
                          className={`p-2.5 rounded-xl border text-left transition-all cursor-pointer ${
                            (customization.lockScreenWallpaper || 'matrix') === w.id
                              ? 'bg-[#122e20] border-emerald-400 shadow-md ring-1 ring-emerald-400/50'
                              : 'bg-[var(--bg-dark)] border-[var(--border-dark)] hover:bg-[#143224]'
                          }`}
                        >
                          <div className="text-xs font-semibold text-white">{w.label}</div>
                          <div className="text-[10px] text-emerald-400/70">{w.desc}</div>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Lock Screen Title & Subtitle Inputs */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <span className="text-[11px] text-emerald-400/80 block mb-1">Lock Screen Title</span>
                      <input
                        type="text"
                        value={customization.lockScreenTitle ?? `${customization.assistantName || 'Doshie'} Workstation`}
                        onChange={e => onUpdateCustomization({ lockScreenTitle: e.target.value })}
                        placeholder="e.g. Doshie Workstation"
                        className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                      />
                    </div>
                    <div>
                      <span className="text-[11px] text-emerald-400/80 block mb-1">Status Badge / Security Note</span>
                      <input
                        type="text"
                        value={customization.lockScreenCustomNote ?? 'Secure Workstation • RTX 5070 Local Engine'}
                        onChange={e => onUpdateCustomization({ lockScreenCustomNote: e.target.value })}
                        placeholder="e.g. Hermes Secured RTX 5070"
                        className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                      />
                    </div>
                  </div>

                  <div>
                    <span className="text-[11px] text-emerald-400/80 block mb-1">Lock Screen Subtitle / Welcome Quote</span>
                    <input
                      type="text"
                      value={customization.lockScreenSubtitle ?? 'Private local AI companion secured. Select your profile to resume.'}
                      onChange={e => onUpdateCustomization({ lockScreenSubtitle: e.target.value })}
                      placeholder="e.g. Welcome back, Hermes. Select your profile to unlock."
                      className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                    />
                  </div>

                  {/* Clock Format & Auto-Lock Options */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-[var(--border-dark)]">
                    <div>
                      <span className="text-[11px] text-emerald-400/80 block mb-1">Clock Display Format</span>
                      <select
                        value={customization.lockScreenClockFormat || '12h'}
                        onChange={e => onUpdateCustomization({ lockScreenClockFormat: e.target.value as '12h' | '24h' })}
                        className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                      >
                        <option value="12h">12-Hour AM/PM (e.g. 2:30:00 PM)</option>
                        <option value="24h">24-Hour Military (e.g. 14:30:00)</option>
                      </select>
                    </div>
                    <div>
                      <span className="text-[11px] text-emerald-400/80 block mb-1">Auto-Lock Idle Timer</span>
                      <select
                        value={customization.lockScreenAutoLockMinutes ?? 0}
                        onChange={e => onUpdateCustomization({ lockScreenAutoLockMinutes: Number(e.target.value) })}
                        className="w-full px-3 py-1.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] focus:border-[var(--accent)] focus:outline-none text-xs sm:text-sm text-white"
                      >
                        <option value={0}>Disabled (Lock manually only)</option>
                        <option value={5}>Lock after 5 minutes idle</option>
                        <option value={15}>Lock after 15 minutes idle</option>
                        <option value={30}>Lock after 30 minutes idle</option>
                        <option value={60}>Lock after 1 hour idle</option>
                      </select>
                    </div>
                  </div>

                  {/* Lock Screen Test / Action */}
                  {onLockScreen && (
                    <div className="pt-2 flex justify-end">
                      <button
                        type="button"
                        onClick={() => {
                          onClose()
                          onLockScreen()
                        }}
                        className="px-4 py-2 rounded-xl bg-amber-700 hover:bg-amber-600 text-white text-xs font-semibold flex items-center gap-2 cursor-pointer shadow-md transition-all active:scale-95"
                      >
                        <Lock className="w-3.5 h-3.5" />
                        <span>Lock Screen Now</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : tab === 'profiles' ? (
            <>
              {/* Profile Selection */}
              <div>
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400/90 mb-3">
                  <Users className="w-3.5 h-3.5" />
                  <span>Select Active Profile</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {profiles.map(p => {
                    const isSelected = activeProfile.toLowerCase() === p.name.toLowerCase()
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          onSelectProfile(p.name)
                          onClose()
                        }}
                        className={`p-3.5 rounded-xl border text-left transition-all flex items-center justify-between cursor-pointer ${
                          isSelected
                            ? 'bg-[#122e20] border-emerald-400 shadow-md ring-1 ring-emerald-400/50'
                            : 'bg-[#0e2218] border-[#1b432f] hover:bg-[#143224]'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-700 to-teal-500 flex items-center justify-center font-bold text-white text-sm shadow-sm">
                            {p.name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-white text-sm">{p.name}</div>
                            <div className="text-[11px] text-emerald-400/70">{p.role || 'Family Member'}</div>
                          </div>
                        </div>
                        {isSelected && <Check className="w-4 h-4 text-emerald-400" />}
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Add New Profile Form */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400/90 mb-3">
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add New Profile</span>
                </label>
                <form onSubmit={handleCreateProfile} className="space-y-3 bg-[#0d2218] p-4 rounded-xl border border-[#1b432f]">
                  <div>
                    <label className="block text-xs font-medium text-emerald-300 mb-1">Profile Name</label>
                    <input
                      type="text"
                      value={newName}
                      onChange={e => setNewName(e.target.value)}
                      placeholder="e.g. Maya, Lucas, Grandma"
                      required
                      className="w-full px-3 py-2 rounded-lg bg-[#081710] border border-[#214c36] focus:border-emerald-400 focus:outline-none text-xs sm:text-sm text-white placeholder-emerald-600/70"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-emerald-300 mb-1">Role / Relationship</label>
                    <select
                      value={newRole}
                      onChange={e => setNewRole(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-[#081710] border border-[#214c36] focus:border-emerald-400 focus:outline-none text-xs sm:text-sm text-white"
                    >
                      <option value="Family">Family Member</option>
                      <option value="Child">Child (Kids Mode)</option>
                      <option value="Admin">Administrator</option>
                      <option value="Partner">Partner / Spouse</option>
                      <option value="Guest">Guest</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={!newName.trim() || isAddingProfile}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 active:scale-98 text-white text-xs sm:text-sm font-medium transition duration-150 disabled:opacity-40 shadow-sm shadow-emerald-950 cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>{isAddingProfile ? 'Creating...' : 'Create & Switch to Profile'}</span>
                  </button>
                </form>
              </div>

              {/* Logout & Lock Option */}
              <div className="pt-2 border-t border-[var(--border-dark)]">
                <div className="bg-[#151c18] p-3.5 rounded-xl border border-[#213b2c] flex items-center justify-between gap-3">
                  <div>
                    <div className="text-xs sm:text-sm font-semibold text-white flex items-center gap-1.5">
                      <LogOut className="w-4 h-4 text-rose-400" />
                      <span>Log Out of {activeProfile}</span>
                    </div>
                    <p className="text-[11px] text-emerald-300/70 mt-0.5">
                      Clears your active session and returns to login/profile selection.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="px-3.5 py-1.5 rounded-xl bg-rose-900/80 hover:bg-rose-800 border border-rose-700/60 active:scale-95 text-xs font-semibold text-rose-100 transition-all cursor-pointer whitespace-nowrap"
                  >
                    Log Out
                  </button>
                </div>
              </div>
            </>
          ) : tab === 'maintenance' ? (
            <>
              {/* Maintenance & Reset Center */}
              <div className="space-y-4">
                {/* 1. App Refresh & Cache Clear */}
                <div>
                  <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                    <RefreshCw className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Interface Refresh & App Cache</span>
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {/* Hard Refresh */}
                    <button
                      type="button"
                      onClick={handleHardReload}
                      className="p-3.5 rounded-xl bg-[#0e2218] border border-[#1b432f] hover:bg-[#153826] text-left transition-all cursor-pointer flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs sm:text-sm font-semibold text-white flex items-center gap-2">
                          <RefreshCw className="w-4 h-4 text-emerald-400" />
                          <span>Quick Reload App</span>
                        </span>
                      </div>
                      <p className="text-[11px] text-emerald-300/70">
                        Hard reloads interface scripts and reconnects background streams.
                      </p>
                    </button>

                    {/* Clear Web/App Cache */}
                    <button
                      type="button"
                      onClick={handleClearAppCache}
                      className="p-3.5 rounded-xl bg-[#0e2218] border border-[#1b432f] hover:bg-[#153826] text-left transition-all cursor-pointer flex flex-col justify-between"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs sm:text-sm font-semibold text-white flex items-center gap-2">
                          <RotateCcw className="w-4 h-4 text-amber-400" />
                          <span>Clear App Cache & Reload</span>
                        </span>
                      </div>
                      <p className="text-[11px] text-emerald-300/70">
                        Clears Service Worker cache, offline assets, and loads fresh code.
                      </p>
                    </button>
                  </div>
                </div>

                {/* 2. Customization Reset */}
                <div className="pt-2 border-t border-[var(--border-dark)]">
                  <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                    <Palette className="w-3.5 h-3.5 text-teal-400" />
                    <span>Reset Appearance to Defaults</span>
                  </label>
                  <div className="bg-[#0e2218] p-3.5 rounded-xl border border-[#1b432f] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-xs sm:text-sm font-semibold text-white">Reset GUI Theme & Layout</div>
                      <p className="text-[11px] text-emerald-300/70 mt-0.5">
                        Restores Emerald Matrix theme, balanced density, and rounded cards. Does not erase chat history.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleResetCustomization}
                      className="px-3.5 py-1.5 rounded-xl bg-teal-800 hover:bg-teal-700 active:scale-95 text-xs font-medium text-white transition-all cursor-pointer whitespace-nowrap"
                    >
                      Reset Styling
                    </button>
                  </div>
                </div>

                {/* 3. Server GPU & Model Cache Flush */}
                <div className="pt-2 border-t border-[var(--border-dark)]">
                  <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent-light)] mb-3">
                    <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                    <span>Workstation & Server GPU Memory</span>
                  </label>
                  <div className="bg-[#0e2218] p-3.5 rounded-xl border border-[#1b432f] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-xs sm:text-sm font-semibold text-white">Flush System & Model Caches</div>
                      <p className="text-[11px] text-emerald-300/70 mt-0.5">
                        Frees RTX 5070 VRAM, purges Python garbage collection, and clears temporary context buffers.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleFlushServerCache}
                      disabled={isFlushing}
                      className="px-3.5 py-1.5 rounded-xl bg-cyan-800 hover:bg-cyan-700 active:scale-95 text-xs font-medium text-white transition-all cursor-pointer whitespace-nowrap disabled:opacity-50"
                    >
                      {isFlushing ? 'Flushing...' : '🧹 Flush GPU Cache'}
                    </button>
                  </div>
                </div>

                {/* 4. Local Chat Cache Purge */}
                <div className="pt-2 border-t border-[var(--border-dark)]">
                  <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-400/90 mb-3">
                    <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                    <span>Device Chat Storage</span>
                  </label>
                  <div className="bg-[#1f0b10]/80 p-3.5 rounded-xl border border-rose-900/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-xs sm:text-sm font-semibold text-white">Purge Offline Chat History</div>
                      <p className="text-[11px] text-rose-300/70 mt-0.5">
                        Clears locally saved conversations on this device for profile "{activeProfile}".
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleClearChatCache}
                      className="px-3.5 py-1.5 rounded-xl bg-rose-700 hover:bg-rose-600 active:scale-95 text-xs font-medium text-white transition-all cursor-pointer whitespace-nowrap"
                    >
                      Clear Device Chats
                    </button>
                  </div>
                </div>

                {/* 5. Session Logout */}
                <div className="pt-2 border-t border-[var(--border-dark)]">
                  <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400/90 mb-3">
                    <LogOut className="w-3.5 h-3.5 text-amber-400" />
                    <span>Account & Session</span>
                  </label>
                  <div className="bg-[#18120b] p-3.5 rounded-xl border border-amber-900/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-xs sm:text-sm font-semibold text-white">Log Out & Lock Interface</div>
                      <p className="text-[11px] text-amber-300/70 mt-0.5">
                        Terminates session for "{activeProfile}", flushes credentials, and returns to profile login.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="px-3.5 py-1.5 rounded-xl bg-amber-700 hover:bg-amber-600 active:scale-95 text-xs font-semibold text-white transition-all cursor-pointer whitespace-nowrap"
                    >
                      Log Out Now
                    </button>
                  </div>
                </div>
              </div>
            </>
          ) : tab === 'oversight' ? (
            <>
              {/* Admin Guest Oversight & Audit */}
              <div className="space-y-4">
                <div className="bg-[#1a140a] p-3.5 rounded-xl border border-amber-900/60 flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-amber-950/80 border border-amber-800/60 text-amber-300">
                    <Shield className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-xs sm:text-sm font-bold text-amber-200 flex items-center gap-1.5">
                      <span>Admin Oversight & Guest Audit Center</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-900/80 border border-amber-700/80 text-amber-300 font-semibold uppercase tracking-wider">
                        Hermes Only
                      </span>
                    </h3>
                    <p className="text-[11px] text-amber-300/80 mt-1 leading-relaxed">
                      As Admin, you have full oversight over guests and family accounts. Individual guest chats and personal memories stay completely isolated from their view, while you can inspect their activity, active sessions, and stored memory logs below.
                    </p>
                  </div>
                </div>

                {/* Profiles & Guests Overview */}
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
                      <Eye className="w-3.5 h-3.5" />
                      <span>Registered Profiles & Guest Accounts ({oversightData.length})</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setIsLoadingOversight(true)
                        fetch(`/api/admin/oversight?requester=${encodeURIComponent(activeProfile)}`)
                          .then(res => res.json())
                          .then(data => {
                            if (data.ok && Array.isArray(data.profiles)) {
                              setOversightData(data.profiles)
                            }
                          })
                          .catch(err => console.error(err))
                          .finally(() => setIsLoadingOversight(false))
                      }}
                      disabled={isLoadingOversight}
                      className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center gap-1 bg-[#1a140a] border border-amber-900/50 px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
                    >
                      <RefreshCw className={`w-3 h-3 ${isLoadingOversight ? 'animate-spin' : ''}`} />
                      <span>Refresh</span>
                    </button>
                  </div>

                  {isLoadingOversight ? (
                    <div className="p-8 text-center text-xs text-amber-400/70 animate-pulse">
                      Loading guest activity & memory metrics...
                    </div>
                  ) : oversightData.length === 0 ? (
                    <div className="p-6 rounded-xl bg-[#0e2218] border border-[#1b432f] text-center text-xs text-emerald-300/70">
                      No registered profiles found.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {oversightData.map(p => {
                        const isCurrent = activeProfile.toLowerCase() === p.name.toLowerCase()
                        const isExpanded = selectedGuestMemories?.profile === p.name

                        return (
                          <div
                            key={p.name}
                            className={`p-3.5 rounded-xl border transition-all ${
                              p.is_admin
                                ? 'bg-[#151c18] border-emerald-800/60'
                                : 'bg-[#13171f] border-[#222e40]'
                            }`}
                          >
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                              <div className="flex items-center gap-3">
                                <div
                                  className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm shadow-sm ${
                                    p.is_admin
                                      ? 'bg-gradient-to-tr from-amber-600 to-amber-400 text-white'
                                      : 'bg-gradient-to-tr from-sky-600 to-blue-500 text-white'
                                  }`}
                                >
                                  {p.name.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                  <div className="font-semibold text-white text-xs sm:text-sm flex items-center gap-2">
                                    <span>{p.name}</span>
                                    {p.is_admin ? (
                                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 border border-amber-700/60 text-amber-300 font-medium">
                                        👑 Admin
                                      </span>
                                    ) : (
                                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-sky-950 border border-sky-700/60 text-sky-300 font-medium">
                                        👤 {p.role || 'Guest'}
                                      </span>
                                    )}
                                    {isCurrent && (
                                      <span className="text-[10px] px-1.5 py-0.2 rounded bg-emerald-950 border border-emerald-700/60 text-emerald-300">
                                        Current You
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-[11px] text-gray-400 flex items-center gap-3 mt-0.5">
                                    <span className="flex items-center gap-1">
                                      <MessageSquare className="w-3 h-3 text-emerald-400" />
                                      <span>{p.chat_count} chat sessions</span>
                                    </span>
                                    <span>•</span>
                                    <span className="flex items-center gap-1">
                                      <Brain className="w-3 h-3 text-purple-400" />
                                      <span>{p.memory_count} memories</span>
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Action Buttons */}
                              <div className="flex items-center gap-2 self-end sm:self-center">
                                {!p.is_admin && onSelectOversightProfile && (
                                  <button
                                    type="button"
                                    onClick={() => {
                                      onSelectOversightProfile(p.name)
                                      onClose()
                                    }}
                                    className="px-2.5 py-1.5 rounded-lg bg-sky-900/60 hover:bg-sky-800/80 border border-sky-700/60 text-sky-200 text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                                  >
                                    <Eye className="w-3.5 h-3.5" />
                                    <span>Inspect Chats</span>
                                  </button>
                                )}
                                <button
                                  type="button"
                                  onClick={() => handleInspectGuestMemories(p.name)}
                                  className={`px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors cursor-pointer border ${
                                    isExpanded
                                      ? 'bg-purple-900/80 border-purple-500 text-purple-100'
                                      : 'bg-purple-950/60 hover:bg-purple-900/60 border-purple-800/60 text-purple-200'
                                  }`}
                                >
                                  <BookOpen className="w-3.5 h-3.5" />
                                  <span>{isExpanded ? 'Hide Memories' : 'Audit Memories'}</span>
                                </button>
                              </div>
                            </div>

                            {/* Expanded Memory Audit Drawer */}
                            {isExpanded && selectedGuestMemories && (
                              <div className="mt-3 pt-3 border-t border-[#222e40] space-y-2">
                                <div className="flex items-center justify-between text-[11px] font-semibold text-purple-300">
                                  <span>Stored Long-term Memories for {p.name}:</span>
                                  <span className="text-gray-400 font-normal">
                                    {selectedGuestMemories.memories.length} item(s) in SQLite store
                                  </span>
                                </div>

                                {selectedGuestMemories.memories.length === 0 ? (
                                  <div className="p-3 rounded-lg bg-[#0b0e14] border border-[#1b2332] text-center text-xs text-gray-400 italic">
                                    No memories recorded yet for this profile.
                                  </div>
                                ) : (
                                  <div className="space-y-1.5 max-h-56 overflow-y-auto pr-1">
                                    {selectedGuestMemories.memories.map((m, idx) => (
                                      <div
                                        key={m.id || idx}
                                        className="p-2.5 rounded-lg bg-[#0c1017] border border-[#1b2434] text-xs space-y-1"
                                      >
                                        <div className="flex items-center justify-between text-[10px]">
                                          <span className="font-mono text-emerald-400 font-semibold">
                                            {m.importance || 'Memory'} #{m.id}
                                          </span>
                                          <div className="flex items-center gap-1.5">
                                            <span
                                              className={`px-1.5 py-0.2 rounded font-mono uppercase ${
                                                m.scope === 'shared'
                                                  ? 'bg-teal-950 text-teal-300 border border-teal-800/60'
                                                  : 'bg-rose-950 text-rose-300 border border-rose-800/60'
                                              }`}
                                            >
                                              {m.scope || 'private'}
                                            </span>
                                            {m.category && (
                                              <span className="px-1.5 py-0.2 rounded bg-gray-800 text-gray-300">
                                                {m.category}
                                              </span>
                                            )}
                                          </div>
                                        </div>
                                        <p className="text-gray-200 leading-relaxed font-sans">{m.memory}</p>
                                        {m.updated_at && (
                                          <div className="text-[9px] text-gray-500 text-right">
                                            {m.updated_at}
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : tab === 'doctor' ? (
            <div className="space-y-6">
              {/* Header Banner */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:p-5 rounded-2xl bg-emerald-950/40 border border-emerald-800/60 gap-4">
                <div className="flex items-center gap-3.5">
                  <div className="p-3 rounded-2xl bg-emerald-900/60 border border-emerald-700/60 flex-none">
                    <Activity className="w-6 h-6 text-emerald-400 animate-pulse" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-white text-base flex items-center gap-2">
                      <span>🩺 Doshie Doctor AI</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-bold uppercase border ${
                        doctorData?.status === 'healthy'
                          ? 'bg-emerald-950 text-emerald-300 border-emerald-700'
                          : 'bg-amber-950 text-amber-300 border-amber-700'
                      }`}>
                        {doctorData?.status || 'Scanning...'}
                      </span>
                    </h3>
                    <p className="text-xs text-neutral-300 mt-0.5">
                      System diagnostics, GPU VRAM, background services & port health on Acer Nitro.
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 flex-none">
                  <button
                    onClick={fetchDoctorData}
                    disabled={isLoadingDoctor}
                    className="px-3.5 py-2 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] text-xs font-semibold text-neutral-200 hover:text-white flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${isLoadingDoctor ? 'animate-spin' : ''}`} />
                    <span>Re-scan</span>
                  </button>
                  <button
                    onClick={handleRunDoctorFix}
                    disabled={isFixingDoctor}
                    className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-xs font-bold text-white shadow-lg shadow-emerald-950/50 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <Wand2 className={`w-3.5 h-3.5 ${isFixingDoctor ? 'animate-spin' : ''}`} />
                    <span>🔧 Auto-Fix & Repair</span>
                  </button>
                </div>
              </div>

              {/* Hardware & GPU Stats Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="p-3.5 rounded-xl bg-[var(--bg-dark)] border border-[var(--border-dark)]">
                  <div className="text-[11px] text-neutral-400">CPU Load ({doctorData?.system?.cpu_cores || 0} Cores)</div>
                  <div className="text-lg font-bold text-white mt-1 font-mono">
                    {doctorData?.system?.cpu_percent ?? '--'}%
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-[var(--bg-dark)] border border-[var(--border-dark)]">
                  <div className="text-[11px] text-neutral-400">RAM Usage</div>
                  <div className="text-lg font-bold text-white mt-1 font-mono">
                    {doctorData?.system?.ram_percent ?? '--'}% ({doctorData?.system?.ram_used_gb ?? 0}GB / {doctorData?.system?.ram_total_gb ?? 0}GB)
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-[var(--bg-dark)] border border-[var(--border-dark)]">
                  <div className="text-[11px] text-neutral-400">Root Storage</div>
                  <div className="text-lg font-bold text-white mt-1 font-mono">
                    {doctorData?.system?.disk_free_gb ?? '--'} GB free
                  </div>
                </div>
                <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-800/40">
                  <div className="text-[11px] text-emerald-400">NVIDIA GPU</div>
                  <div className="text-xs font-bold text-emerald-200 mt-1 truncate font-mono" title={doctorData?.gpu || ''}>
                    {doctorData?.gpu || 'NVIDIA RTX 5070'}
                  </div>
                </div>
              </div>

              {/* Services & Network Health */}
              <div className="p-4 rounded-xl bg-[var(--bg-dark)] border border-[var(--border-dark)] space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-neutral-300">Active Services & Network Endpoints</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
                  {Object.entries(doctorData?.services || {}).map(([srv, info]: [string, any]) => (
                    <div key={srv} className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)]">
                      <span className="font-medium text-neutral-200">{srv}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        info?.running ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
                      }`}>
                        {info?.running ? `Running (PID: ${info.pids?.[0] || 'active'})` : 'Stopped'}
                      </span>
                    </div>
                  ))}
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)]">
                    <span className="font-medium text-neutral-200">Web UI (Port 5000)</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                      doctorData?.ports?.web_ui_5000 ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'
                    }`}>
                      {doctorData?.ports?.web_ui_5000 ? 'Online' : 'Offline'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)]">
                    <span className="font-medium text-neutral-200">Tailscale Mesh</span>
                    <span className="font-mono text-[11px] text-teal-300 font-semibold">
                      {doctorData?.tailscale_ip ? `http://${doctorData.tailscale_ip}:5000` : 'Disconnected'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
