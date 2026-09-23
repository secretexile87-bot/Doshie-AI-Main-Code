import React, { useState, useEffect, useRef, useTransition } from 'react'
import { Header } from './components/Header'
import { Sidebar } from './components/Sidebar'
import { ChatMessage } from './components/ChatMessage'
import { ChatComposer } from './components/ChatComposer'
import { EmptyState } from './components/EmptyState'
import { SettingsModal } from './components/SettingsModal'
import { LiveVoiceModal } from './components/LiveVoiceModal'
import { TranscriptViewer } from './components/TranscriptViewer'
import { LockScreen } from './components/LockScreen'
import { MusicPlayerModal } from './components/MusicPlayerModal'
import { VoiceStudioModal } from './components/VoiceStudioModal'
import { stopSpeech } from './utils/audio'
import type { Message, ChatSession, AntigravitySummary, GuiCustomization, Profile, ChatAttachment } from './types'

const getSessionsStorageKey = (profile: string) =>
  `Doshie_chat_sessions_${profile.toLowerCase().replace(/\s+/g, '_')}`

const DEFAULT_CUSTOMIZATION: GuiCustomization = {
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
  lockScreenWallpaper: 'glow',
  lockScreenClockFormat: '12h',
  lockScreenAutoLockMinutes: 5,
}

const getCustomizationStorageKey = (profile: string) =>
  `Doshie_gui_customization_${profile.toLowerCase().replace(/\s+/g, '_')}`

const loadInitialCustomization = (profile: string): GuiCustomization => {
  try {
    const profileSaved = localStorage.getItem(getCustomizationStorageKey(profile))
    if (profileSaved) return { ...DEFAULT_CUSTOMIZATION, ...JSON.parse(profileSaved) }
    const globalSaved = localStorage.getItem('Doshie_gui_customization')
    if (globalSaved) return { ...DEFAULT_CUSTOMIZATION, ...JSON.parse(globalSaved) }
  } catch {}
  return DEFAULT_CUSTOMIZATION
}

export function App() {
  const [activeProfile, setActiveProfile] = useState<string>(() => {
    return localStorage.getItem('Doshie_active_profile') || 'Hermes'
  })
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [oversightProfile, setOversightProfile] = useState<string>(() => {
    return localStorage.getItem('Doshie_active_profile') || 'Hermes'
  })
  const [isLocked, setIsLocked] = useState(false)
  const [isVoiceStudioOpen, setIsVoiceStudioOpen] = useState(false)

  const activeProfileObj = profiles.find(p => p.name.toLowerCase() === activeProfile.toLowerCase())
  const isAdmin = activeProfile.toLowerCase() === 'hermes' || activeProfileObj?.is_admin === true || activeProfileObj?.role?.toLowerCase() === 'admin'

  // GUI Customization State
  const [customization, setCustomization] = useState<GuiCustomization>(() => {
    return loadInitialCustomization(activeProfile)
  })
  const saveTimeoutRef = useRef<any>(null)

  // Sync profile customization from backend
  const syncProfilePreferences = async (profile: string) => {
    try {
      const res = await fetch(`/profile-preferences?profile=${encodeURIComponent(profile)}`, { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        const backendGui = data?.preferences?.gui_customization
        if (backendGui && typeof backendGui === 'object' && Object.keys(backendGui).length > 0) {
          setCustomization(prev => {
            const merged = { ...DEFAULT_CUSTOMIZATION, ...prev, ...backendGui }
            localStorage.setItem(getCustomizationStorageKey(profile), JSON.stringify(merged))
            localStorage.setItem('Doshie_gui_customization', JSON.stringify(merged))
            return merged
          })
        } else if (data?.preferences) {
          const legacyTheme = data.preferences.theme
          const legacyMins = data.preferences.auto_lock_minutes
          if (legacyTheme || legacyMins !== undefined) {
            setCustomization(prev => {
              const updated = {
                ...prev,
                ...(legacyTheme && ['emerald', 'cyberpunk', 'oled', 'amber', 'crimson', 'terminal', 'nord', 'dracula'].includes(legacyTheme) ? { theme: legacyTheme } : {}),
                ...(typeof legacyMins === 'number' ? { lockScreenAutoLockMinutes: legacyMins } : {}),
              }
              localStorage.setItem(getCustomizationStorageKey(profile), JSON.stringify(updated))
              localStorage.setItem('Doshie_gui_customization', JSON.stringify(updated))
              return updated
            })
          }
        }
      }
    } catch (err) {
      console.error('Failed to sync profile preferences from server:', err)
    }
  }

  // Load preferences on mount & when activeProfile changes
  useEffect(() => {
    const local = loadInitialCustomization(activeProfile)
    setCustomization(local)
    syncProfilePreferences(activeProfile)
  }, [activeProfile])

  // Apply customization attributes to html element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', customization.theme)
    document.documentElement.setAttribute('data-font-size', customization.fontSize)
    document.documentElement.setAttribute('data-density', customization.chatDensity || 'comfortable')
    document.documentElement.setAttribute('data-bubble-style', customization.bubbleStyle)
    document.documentElement.setAttribute('data-bg-style', customization.backgroundStyle || 'glow')
    localStorage.setItem(getCustomizationStorageKey(activeProfile), JSON.stringify(customization))
    localStorage.setItem('Doshie_gui_customization', JSON.stringify(customization))
  }, [customization, activeProfile])

  const handleUpdateCustomization = (updates: Partial<GuiCustomization>) => {
    setCustomization(prev => {
      const next = { ...prev, ...updates }
      localStorage.setItem(getCustomizationStorageKey(activeProfile), JSON.stringify(next))
      localStorage.setItem('Doshie_gui_customization', JSON.stringify(next))

      // Debounced save to backend /profile-preferences
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
      saveTimeoutRef.current = setTimeout(() => {
        fetch('/profile-preferences', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile: activeProfile,
            preferences: {
              gui_customization: next,
              theme: next.theme,
              auto_lock_minutes: next.lockScreenAutoLockMinutes ?? 5,
            },
          }),
        }).catch(err => console.error('Failed to save customization to server:', err))
      }, 200)

      return next
    })
  }

  // Apply MySpace custom CSS live to the document head
  useEffect(() => {
    let styleTag = document.getElementById('doshie-myspace-custom-css')
    if (!styleTag) {
      styleTag = document.createElement('style')
      styleTag.id = 'doshie-myspace-custom-css'
      document.head.appendChild(styleTag)
    }
    styleTag.textContent = customization.myspaceCustomCss || ''
  }, [customization.myspaceCustomCss])

  // MySpace Sparkle Cursor Trail
  useEffect(() => {
    if (!customization.myspaceSparkleCursor) return

    let lastTime = 0
    const handleMouseMove = (e: MouseEvent) => {
      const now = Date.now()
      if (now - lastTime < 45) return
      lastTime = now

      const star = document.createElement('div')
      const colors = ['#f472b6', '#38bdf8', '#fbbf24', '#a855f7', '#34d399', '#ff007f', '#ffffff']
      const color = colors[Math.floor(Math.random() * colors.length)]
      const size = Math.floor(Math.random() * 8) + 8
      star.style.cssText = `
        position: fixed;
        left: ${e.clientX}px;
        top: ${e.clientY}px;
        width: ${size}px;
        height: ${size}px;
        background: ${color};
        box-shadow: 0 0 8px ${color}, 0 0 14px ${color};
        border-radius: 50%;
        pointer-events: none;
        z-index: 99999;
        transform: translate(-50%, -50%) scale(1);
        transition: transform 0.6s cubic-bezier(0.25, 1, 0.5, 1), opacity 0.6s ease-out;
      `
      document.body.appendChild(star)

      requestAnimationFrame(() => {
        star.style.transform = `translate(-50%, -50%) scale(0.2) translateY(${Math.random() * 25 + 15}px)`
        star.style.opacity = '0'
      })

      setTimeout(() => {
        star.remove()
      }, 650)
    }

    window.addEventListener('mousemove', handleMouseMove)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
    }
  }, [customization.myspaceSparkleCursor])

  // MySpace Audio Player State
  const [isPlayingMySpaceSong, setIsPlayingMySpaceSong] = useState(false)
  const mySpaceAudioRef = useRef<HTMLAudioElement | null>(null)

  // Sidebar state
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(() => {
    return typeof window !== 'undefined' ? window.innerWidth >= 1024 : false
  })
  const [sidebarTab, setSidebarTab] = useState<'doshie' | 'antigravity'>('doshie')

  // Doshie Sessions State
  const [sessions, setSessions] = useState<ChatSession[]>(() => {
    try {
      const saved = localStorage.getItem(getSessionsStorageKey(activeProfile))
      return saved ? JSON.parse(saved) : []
    } catch {
      return []
    }
  })
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => {
    try {
      const saved = localStorage.getItem(getSessionsStorageKey(activeProfile))
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.length > 0) return parsed[0].id
      }
    } catch {}
    return null
  })

  // Active messages currently visible
  const [messages, setMessages] = useState<Message[]>([])

  // Antigravity Transcripts State
  const [antigravityList, setAntigravityList] = useState<AntigravitySummary[]>([])
  const [activeAntigravityId, setActiveAntigravityId] = useState<string | null>(null)

  const [isGenerating, setIsGenerating] = useState(false)
  const [online, setOnline] = useState(true)
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [settingsTab, setSettingsTab] = useState<'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor'>('appearance')
  const [isLiveVoiceOpen, setIsLiveVoiceOpen] = useState(false)
  const [isMusicPlayerOpen, setIsMusicPlayerOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [, startTransition] = useTransition()

  // Revert UI to clean Home state
  const revertToHome = () => {
    setActiveAntigravityId(null)
    setActiveSessionId(null)
    setMessages([])
    setIsSettingsOpen(false)
    setIsLiveVoiceOpen(false)
    setIsMusicPlayerOpen(false)
    setIsVoiceStudioOpen(false)
    stopSpeech()
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    setIsGenerating(false)
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setIsSidebarOpen(false)
    }
    if (typeof window !== 'undefined' && window.location.pathname !== '/' && window.location.pathname !== '') {
      window.history.pushState(null, '', '/')
    }
  }

  // Lock account: reverts to home and presents the login/lock screen
  const handleLockAccount = async (targetProfile: string = activeProfile) => {
    revertToHome()
    setIsLocked(true)
    try {
      await fetch('/profile-lock/lock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile: targetProfile }),
      })
    } catch {}
    setProfiles(prev =>
      prev.map(p =>
        p.name.toLowerCase() === targetProfile.toLowerCase()
          ? { ...p, locked: true, unlocked: false }
          : p
      )
    )
  }

  // Fetch registered profiles and enforce lock state
  const fetchProfiles = async () => {
    try {
      const res = await fetch('/profiles', { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        if (Array.isArray(data)) {
          setProfiles(data)
          // If active profile is locked and not unlocked in this session, revert to home to login!
          const current = data.find((p: Profile) => p.name.toLowerCase() === activeProfile.toLowerCase())
          if (current && current.locked && !current.unlocked) {
            revertToHome()
            setIsLocked(true)
          }
        }
      }
    } catch {}
  }

  useEffect(() => {
    fetchProfiles()
  }, [activeProfile])

  // Auto-lock inactivity listener
  useEffect(() => {
    const minutes = customization.lockScreenAutoLockMinutes ?? 15
    if (minutes <= 0) return

    let timeoutId: ReturnType<typeof setTimeout>

    const resetTimer = () => {
      clearTimeout(timeoutId)
      timeoutId = setTimeout(() => {
        handleLockAccount(activeProfile)
      }, minutes * 60 * 1000)
    }

    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll']
    events.forEach(evt => window.addEventListener(evt, resetTimer, { passive: true }))
    resetTimer()

    return () => {
      clearTimeout(timeoutId)
      events.forEach(evt => window.removeEventListener(evt, resetTimer))
    }
  }, [customization.lockScreenAutoLockMinutes, activeProfile])

  // Load sessions from Backend or LocalStorage on mount or profile change
  const loadSessionsForProfile = async (
    targetProfile: string,
    requester: string = activeProfile,
    activateFirst: boolean = true
  ) => {
    try {
      // 1. Load from backend
      const res = await fetch(`/api/chat/sessions?profile=${encodeURIComponent(targetProfile)}&requester=${encodeURIComponent(requester)}`)
      if (res.status === 423) {
        handleLockAccount(targetProfile)
        return
      }
      if (res.ok) {
        const json = await res.json()
        if (json.ok && Array.isArray(json.sessions)) {
          setSessions(json.sessions)
          if (targetProfile.toLowerCase() === activeProfile.toLowerCase()) {
            localStorage.setItem(getSessionsStorageKey(targetProfile), JSON.stringify(json.sessions))
          }
          if (activateFirst) {
            if (json.sessions.length > 0) {
              setActiveSessionId(json.sessions[0].id)
              setMessages(json.sessions[0].messages || [])
            } else {
              setActiveSessionId(null)
              setMessages([])
            }
          }
          return
        }
      }
    } catch {
      // Offline fallback
    }

    // Fallback to local storage (only when viewing own active profile)
    if (targetProfile.toLowerCase() === activeProfile.toLowerCase()) {
      try {
        const saved = localStorage.getItem(getSessionsStorageKey(targetProfile))
        if (saved) {
          const parsed = JSON.parse(saved)
          setSessions(parsed)
          if (activateFirst && parsed.length > 0) {
            setActiveSessionId(parsed[0].id)
            setMessages(parsed[0].messages || [])
            return
          }
        }
      } catch {}
    }

    // Fresh empty state
    setSessions([])
    setActiveSessionId(null)
    setMessages([])
  }

  // Fetch Antigravity conversation list
  const fetchAntigravityList = async () => {
    try {
      const res = await fetch('/api/antigravity/conversations')
      if (res.ok) {
        const json = await res.json()
        if (json.ok && Array.isArray(json.conversations)) {
          setAntigravityList(json.conversations)
        }
      }
    } catch {}
  }

  useEffect(() => {
    loadSessionsForProfile(activeProfile, activeProfile)
    fetchAntigravityList()
  }, [activeProfile])

  // Sync active session messages into session list and persistent storage
  const syncSessionMessages = (newMessages: Message[], targetSessionId?: string) => {
    const sId = targetSessionId || activeSessionId
    if (!sId) return

    setSessions(prev => {
      const updated = prev.map(s => {
        if (s.id === sId) {
          // If title was default or short, auto-name from first user prompt
          let autoTitle = s.title
          if ((!s.title || s.title === 'New Chat') && newMessages.length > 0) {
            const firstUser = newMessages.find(m => m.role === 'user')
            if (firstUser && firstUser.content) {
              autoTitle = firstUser.content.slice(0, 45).trim() + (firstUser.content.length > 45 ? '...' : '')
            }
          }
          return {
            ...s,
            title: autoTitle,
            messages: newMessages,
            updated_at: Date.now(),
          }
        }
        return s
      })

      try {
        localStorage.setItem(getSessionsStorageKey(activeProfile), JSON.stringify(updated))
      } catch {}

      // Background sync to backend
      const target = updated.find(s => s.id === sId)
      if (target) {
        const currentTargetProfile = oversightProfile || activeProfile
        fetch('/api/chat/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile: currentTargetProfile,
            requester: activeProfile,
            id: target.id,
            title: target.title,
            messages: target.messages,
          }),
        }).catch(() => {})
      }

      return updated
    })
  }

  // Handle Switching Profile
  const handleSelectProfile = (profile: string) => {
    const targetObj = profiles.find(p => p.name.toLowerCase() === profile.toLowerCase())
    if (targetObj && targetObj.locked && !targetObj.unlocked) {
      setActiveProfile(profile)
      setOversightProfile(profile)
      localStorage.setItem('Doshie_active_profile', profile)
      handleLockAccount(profile)
      return
    }
    setActiveProfile(profile)
    setOversightProfile(profile)
    localStorage.setItem('Doshie_active_profile', profile)
    const local = loadInitialCustomization(profile)
    setCustomization(local)
    setActiveAntigravityId(null)
    loadSessionsForProfile(profile, profile)
    syncProfilePreferences(profile)
    fetchProfiles()
  }

  // Handle Admin selecting a Guest profile to inspect
  const handleSelectOversightProfile = (profile: string) => {
    setOversightProfile(profile)
    setActiveAntigravityId(null)
    loadSessionsForProfile(profile, activeProfile)
  }

  // Select Doshie Session
  const handleSelectSession = (id: string) => {
    const s = sessions.find(item => item.id === id)
    if (s) {
      setActiveAntigravityId(null)
      setActiveSessionId(id)
      setMessages(s.messages || [])
    }
  }

  // Select Antigravity Transcript
  const handleSelectAntigravity = (id: string) => {
    setActiveAntigravityId(id)
  }

  // Scroll to bottom smoothly
  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior })
  }

  useEffect(() => {
    if (!activeAntigravityId) {
      scrollToBottom(messages.length <= 2 ? 'auto' : 'smooth')
    }
  }, [messages, activeAntigravityId])

  // Periodic Health Check & Antigravity poll
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health', { cache: 'no-store' })
        const data = await res.json()
        setOnline(data.online === true)
      } catch {
        setOnline(false)
      }
    }

    checkHealth()
    const interval = setInterval(() => {
      checkHealth()
      fetchAntigravityList()
    }, 12000)
    return () => clearInterval(interval)
  }, [])

  // Send message handler
  const handleSend = async (content: string, attachments?: ChatAttachment[]) => {
    const trimmed = content.trim()
    const hasAttachments = Boolean(attachments && attachments.length > 0)
    if ((!trimmed && !hasAttachments) || isGenerating) return

    // If currently inspecting a transcript, clear it to return to chat
    if (activeAntigravityId) {
      setActiveAntigravityId(null)
    }

    // If no active session or messages empty, ensure session exists
    let targetSessionId = activeSessionId
    if (!targetSessionId) {
      const newId = Date.now().toString()
      const titlePrompt = trimmed
        ? trimmed.slice(0, 45).trim() + (trimmed.length > 45 ? '...' : '')
        : (hasAttachments ? `Attached ${attachments![0].name}` : 'New Chat')
      const newSession: ChatSession = {
        id: newId,
        title: titlePrompt || 'New Chat',
        messages: [],
        created_at: Date.now(),
        updated_at: Date.now(),
      }
      targetSessionId = newId
      setActiveSessionId(newId)
      setSessions(prev => [newSession, ...prev])
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: trimmed,
      timestamp: Date.now(),
      attachments: hasAttachments ? attachments : undefined,
    }

    const pendingAssistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      pending: true,
    }

    const updatedWithUser = [...messages, userMessage, pendingAssistantMessage]
    setMessages(updatedWithUser)
    syncSessionMessages(updatedWithUser, targetSessionId)

    setIsGenerating(true)
    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: trimmed || (hasAttachments ? 'Analyze the attached file(s) or image(s).' : ''),
          profile: activeProfile,
          attachments: hasAttachments ? attachments!.map(a => a.id) : [],
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        let errDetail = ''
        try {
          const errData = await response.json()
          errDetail = errData.error || errData.message || ''
        } catch (_) {}

        if (response.status === 423) {
          handleLockAccount(activeProfile)
          return
        }
        throw new Error(errDetail || `Server returned HTTP ${response.status}`)
      }

      const data = await response.json()
      const replyText = data.reply || 'No response received from Doshie.'

      startTransition(() => {
        setMessages(prev => {
          const finished = prev.map(msg =>
            msg.id === pendingAssistantMessage.id
              ? {
                  ...msg,
                  content: replyText,
                  pending: false,
                }
              : msg
          )
          syncSessionMessages(finished, targetSessionId!)
          return finished
        })
      })
    } catch (error: any) {
      if (error.name === 'AbortError') {
        setMessages(prev => {
          const finished = prev.map(msg =>
            msg.id === pendingAssistantMessage.id
              ? {
                  ...msg,
                  content: '_Generation stopped by user._',
                  pending: false,
                }
              : msg
          )
          syncSessionMessages(finished, targetSessionId!)
          return finished
        })
      } else {
        const errorMsg = error?.message || '⚠️ Failed to get response from Doshie. Please ensure Ollama is active.'
        setMessages(prev => {
          const finished = prev.map(msg =>
            msg.id === pendingAssistantMessage.id
              ? {
                  ...msg,
                  content: errorMsg.startsWith('🔒') || errorMsg.startsWith('⚠️') ? errorMsg : `⚠️ ${errorMsg}`,
                  pending: false,
                  error: true,
                }
              : msg
          )
          syncSessionMessages(finished, targetSessionId!)
          return finished
        })
      }
    } finally {
      setIsGenerating(false)
      abortControllerRef.current = null
    }
  }

  // Handle messages created during Live Voice Talk
  const handleVoiceMessageCreated = (userText: string, assistantReply: string) => {
    let targetSessionId = activeSessionId
    if (!targetSessionId) {
      const newId = Date.now().toString()
      const newSession: ChatSession = {
        id: newId,
        title: userText.slice(0, 40) || 'Voice Conversation',
        messages: [],
        created_at: Date.now(),
        updated_at: Date.now(),
      }
      targetSessionId = newId
      setActiveSessionId(newId)
      setSessions(prev => [newSession, ...prev])
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: userText,
      timestamp: Date.now(),
    }
    const botMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: assistantReply,
      timestamp: Date.now(),
    }
    const newMsgs = [...messages, userMessage, botMessage]
    setMessages(newMsgs)
    syncSessionMessages(newMsgs, targetSessionId)
  }

  // Stop Generation
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  // New Chat Handler: Creates a clean new session without deleting old ones!
  const handleNewChat = () => {
    if (isGenerating) handleStop()
    setActiveAntigravityId(null)
    const newId = Date.now().toString()
    const newSession: ChatSession = {
      id: newId,
      title: 'New Chat',
      messages: [],
      created_at: Date.now(),
      updated_at: Date.now(),
    }
    setActiveSessionId(newId)
    setMessages([])
    setSessions(prev => [newSession, ...prev])

    // Save to storage
    try {
      localStorage.setItem(
        getSessionsStorageKey(activeProfile),
        JSON.stringify([newSession, ...sessions])
      )
    } catch {}

    // Reset backend main chat buffer
    fetch('/new-chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile: activeProfile }),
    }).catch(() => {})
  }

  // Delete Session
  const handleDeleteSession = (id: string) => {
    const targetProfile = oversightProfile || activeProfile
    setSessions(prev => {
      const filtered = prev.filter(s => s.id !== id)
      if (targetProfile.toLowerCase() === activeProfile.toLowerCase()) {
        try {
          localStorage.setItem(getSessionsStorageKey(activeProfile), JSON.stringify(filtered))
        } catch {}
      }

      if (activeSessionId === id) {
        if (filtered.length > 0) {
          setActiveSessionId(filtered[0].id)
          setMessages(filtered[0].messages || [])
        } else {
          setActiveSessionId(null)
          setMessages([])
        }
      }
      return filtered
    })

    // Notify backend
    fetch(`/api/chat/sessions/${id}?profile=${encodeURIComponent(targetProfile)}&requester=${encodeURIComponent(activeProfile)}`, {
      method: 'DELETE',
    }).catch(() => {})
  }

  // Rename Session
  const handleRenameSession = (id: string, newTitle: string) => {
    const targetProfile = oversightProfile || activeProfile
    setSessions(prev => {
      const updated = prev.map(s => (s.id === id ? { ...s, title: newTitle } : s))
      if (targetProfile.toLowerCase() === activeProfile.toLowerCase()) {
        try {
          localStorage.setItem(getSessionsStorageKey(activeProfile), JSON.stringify(updated))
        } catch {}
      }

      const s = updated.find(item => item.id === id)
      if (s) {
        fetch('/api/chat/sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile: targetProfile,
            requester: activeProfile,
            id: s.id,
            title: s.title,
            messages: s.messages,
          }),
        }).catch(() => {})
      }
      return updated
    })
  }

  // Export Session to Markdown
  const handleExportSession = (session: ChatSession) => {
    const lines = [`# ${session.title}`, `*Exported on ${new Date().toLocaleString()}*`, '']
    session.messages.forEach(m => {
      lines.push(`### ${m.role === 'user' ? '👤 User' : '🦖 Doshie'}`)
      lines.push(m.content)
      lines.push('')
    })
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${session.title.replace(/[^a-zA-Z0-9_-]/g, '_') || 'chat'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleOpenSettings = (initialTab: 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor' = 'appearance') => {
    setSettingsTab(initialTab)
    setIsSettingsOpen(true)
  }

  const handleLogout = async () => {
    if (window.confirm(`Log out of profile "${activeProfile}"?`)) {
      try {
        await fetch('/logout', { method: 'POST' })
      } catch {}
      handleLockAccount(activeProfile)
    }
  }

  // Determine active view title for header
  const currentSession = sessions.find(s => s.id === activeSessionId)
  const activeViewTitle = activeAntigravityId
    ? `Antigravity: ${antigravityList.find(a => a.id === activeAntigravityId)?.title || activeAntigravityId.slice(0, 8)}`
    : currentSession?.title || `${customization.assistantName || 'Doshie'} Chat`

  return (
    <div
      style={{
        backgroundImage: customization.customWallpaperUrl ? `url(${customization.customWallpaperUrl})` : undefined,
        backgroundRepeat: customization.myspaceBackgroundRepeat === 'tile' ? 'repeat' : customization.myspaceBackgroundRepeat === 'repeat-x' ? 'repeat-x' : 'no-repeat',
        backgroundSize: customization.myspaceBackgroundRepeat === 'tile' || customization.myspaceBackgroundRepeat === 'repeat-x' ? 'auto' : 'cover',
        backgroundPosition: 'center',
        backgroundAttachment: 'fixed',
      }}
      className="fixed inset-0 h-[100dvh] max-h-[100dvh] w-screen bg-[var(--bg-dark)] text-neutral-100 overflow-hidden font-sans select-text flex transition-colors"
    >
      {/* Sidebar (Chat Explorer / Transcripts) */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
        activeTab={sidebarTab}
        onTabChange={setSidebarTab}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
        onDeleteSession={handleDeleteSession}
        onRenameSession={handleRenameSession}
        onExportSession={handleExportSession}
        antigravityList={antigravityList}
        activeAntigravityId={activeAntigravityId}
        onSelectAntigravity={handleSelectAntigravity}
        activeProfile={activeProfile}
        isAdmin={isAdmin}
        oversightProfile={oversightProfile}
        onSelectOversightProfile={handleSelectOversightProfile}
        availableProfiles={profiles}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0 bg-[var(--bg-dark)]/90 backdrop-blur-xs">
        {/* Header Bar */}
        <Header
          online={online}
          activeProfile={activeProfile}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(prev => !prev)}
          onNewChat={handleNewChat}
          onOpenSettings={handleOpenSettings}
          onOpenLiveVoice={() => setIsLiveVoiceOpen(true)}
          onOpenMusicPlayer={() => setIsMusicPlayerOpen(true)}
          onOpenVoiceStudio={() => setIsVoiceStudioOpen(true)}
          onLogout={handleLogout}
          onLockScreen={() => handleLockAccount(activeProfile)}
          isAdmin={isAdmin}
          isGenerating={isGenerating}
          activeViewTitle={activeViewTitle}
          assistantEmoji={customization.assistantEmoji}
          assistantName={customization.assistantName}
        />

        {/* MySpace Retro Marquee Ticker */}
        {customization.myspaceMarqueeText && (
          <div className="flex-none bg-black/75 border-b border-pink-500/40 text-pink-300 py-1 px-3 text-xs font-mono overflow-hidden shadow-inner flex items-center justify-between z-20">
            <span className="mr-2 flex-none animate-pulse">✨</span>
            <div className="flex-1 overflow-hidden whitespace-nowrap">
              {React.createElement(
                'marquee',
                { className: 'w-full align-middle' },
                customization.myspaceMarqueeText
              )}
            </div>
            <span className="ml-2 flex-none animate-pulse">✨</span>
          </div>
        )}

        {/* MySpace Profile Song Player Widget */}
        {customization.myspaceSongUrl && (
          <div className="flex-none bg-[#11051e]/85 backdrop-blur-md border-b border-purple-500/40 px-3 py-1.5 flex items-center justify-between text-xs text-purple-200 shadow-sm z-20">
            <div className="flex items-center gap-2 min-w-0">
              <span className="p-1 rounded bg-purple-900/60 text-purple-300 flex-none animate-pulse">
                🎵
              </span>
              <span className="truncate font-semibold text-[11px]">
                {customization.myspaceSongTitle || 'MySpace Profile Song'}
              </span>
            </div>
            <audio
              ref={mySpaceAudioRef}
              src={customization.myspaceSongUrl}
              onEnded={() => setIsPlayingMySpaceSong(false)}
            />
            <button
              type="button"
              onClick={() => {
                if (!mySpaceAudioRef.current) return
                if (isPlayingMySpaceSong) {
                  mySpaceAudioRef.current.pause()
                  setIsPlayingMySpaceSong(false)
                } else {
                  mySpaceAudioRef.current.play().then(() => setIsPlayingMySpaceSong(true)).catch(() => {})
                }
              }}
              className="px-2.5 py-0.5 rounded-full bg-purple-600 hover:bg-purple-500 text-white font-bold text-[10px] uppercase tracking-wider flex items-center gap-1 transition-all cursor-pointer shadow-xs active:scale-95"
            >
              <span>{isPlayingMySpaceSong ? '⏸️ Pause' : '▶️ Play Song'}</span>
            </button>
          </div>
        )}

        {/* View Switcher: Antigravity Transcript Viewer vs Live Doshie Chat */}
        {activeAntigravityId ? (
          <TranscriptViewer
            conversationId={activeAntigravityId}
            onBackToChat={() => setActiveAntigravityId(null)}
          />
        ) : (
          <>
            {/* Main Chat Scroll View */}
            <main className="flex-1 min-h-0 overflow-y-auto overflow-x-hidden flex flex-col justify-between overscroll-contain">
              {messages.length === 0 ? (
                <EmptyState
                  onSelectPrompt={handleSend}
                  assistantEmoji={customization.assistantEmoji}
                  greetingTitle={customization.greetingTitle}
                  greetingSubtitle={customization.greetingSubtitle}
                />
              ) : (
                <div className="w-full max-w-3xl mx-auto py-4 px-3 sm:px-4 flex flex-col gap-2">
                  {messages.map(msg => (
                    <ChatMessage
                      key={msg.id}
                      message={msg}
                      assistantEmoji={customization.assistantEmoji}
                      activeProfile={activeProfile}
                    />
                  ))}
                  <div ref={messagesEndRef} className="h-2 flex-none" />
                </div>
              )}
            </main>

            {/* Composer Dock */}
            <ChatComposer
              onSend={handleSend}
              onStop={handleStop}
              isGenerating={isGenerating}
              activeProfile={activeProfile}
            />
          </>
        )}
      </div>

      {/* Live Voice Continuous Mode Modal */}
      <LiveVoiceModal
        isOpen={isLiveVoiceOpen}
        onClose={() => setIsLiveVoiceOpen(false)}
        activeProfile={activeProfile}
        onMessageCreated={handleVoiceMessageCreated}
      />

      {/* Universal Music Player Modal */}
      <MusicPlayerModal
        isOpen={isMusicPlayerOpen}
        onClose={() => setIsMusicPlayerOpen(false)}
      />

      {/* Voice Studio & Voice Changer Modal */}
      <VoiceStudioModal
        isOpen={isVoiceStudioOpen}
        onClose={() => setIsVoiceStudioOpen(false)}
      />

      {/* Settings & Customization Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        initialTab={settingsTab}
        onTabChange={setSettingsTab}
        onClose={() => setIsSettingsOpen(false)}
        activeProfile={activeProfile}
        onSelectProfile={handleSelectProfile}
        customization={customization}
        onUpdateCustomization={handleUpdateCustomization}
        isAdmin={isAdmin}
        onSelectOversightProfile={handleSelectOversightProfile}
        onLockScreen={() => handleLockAccount(activeProfile)}
      />

      {/* Lock Screen Security Overlay */}
      <LockScreen
        isLocked={isLocked}
        onUnlock={profileName => {
          setIsLocked(false)
          revertToHome()
          fetchProfiles()
          if (profileName.toLowerCase() !== activeProfile.toLowerCase()) {
            handleSelectProfile(profileName)
          } else {
            loadSessionsForProfile(profileName, profileName, false)
          }
        }}
        activeProfile={activeProfile}
        availableProfiles={profiles}
        customization={customization}
      />
    </div>
  )
}
export default App
