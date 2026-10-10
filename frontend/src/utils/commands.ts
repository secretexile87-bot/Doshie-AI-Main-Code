/**
 * Doshie Voice Wake-Up & Command Execution Engine (Gemini-style actions)
 * 
 * Supports:
 * - Hands-free wake words ("Hey Doshie", "Doshie", "OK Doshie", "Wake up Doshie", etc.)
 * - Action commands:
 *   - "open <music | settings | appearance | profiles | voice studio | agent hub | live voice | chats | camera | youtube | website>"
 *   - "send [message] <prompt / text>"
 *   - "send to terminal <command>"
 *   - "lock screen", "stop", "switch to <profile>", "new chat"
 */

export interface CommandContext {
  activeProfile: string
  onOpenMusicPlayer?: () => void
  onOpenLiveVoice?: () => void
  onOpenSettings?: (tab?: 'apps' | 'settings' | 'profiles' | 'appearance' | 'maintenance' | 'oversight' | 'doctor') => void
  onOpenVoiceStudio?: () => void
  onOpenAgentHub?: () => void
  onOpenAgentConsole?: () => void
  onOpenMessenger?: () => void
  onOpenSidebar?: () => void
  onNewChat?: () => void
  onSendMessage?: (text: string) => void
  onLockAccount?: () => void
  onStopSpeech?: () => void
  onSwitchProfile?: (profileName: string) => void
  speakFeedback?: (text: string) => void
  showBanner?: (message: string, icon?: string) => void
}

export interface CommandResult {
  handled: boolean
  actionType?: 'open' | 'send' | 'system' | 'wake_only' | 'chat_query'
  feedback?: string
  cleanPrompt?: string
}

// Regex to capture wake words with phonetic variants (Doshie, Doshi, Dashie, Dashi, Yoshi, Joshy)
const WAKE_WORD_REGEX = /^(?:(?:hey|ok|okay|hi|hello|wake\s+up|yo)\s+)?(?:doshie|doshi|dashie|dashi|yoshi|joshy|doji)\b[,!\s]*/i

/**
 * Detects if a spoken phrase starts with a wake word and extracts the payload.
 */
export function detectWakeWord(transcript: string, customWakeName?: string): {
  hasWakeWord: boolean
  wakeWordMatched?: string
  remainder: string
} {
  const trimmed = transcript.trim()
  if (!trimmed) return { hasWakeWord: false, remainder: '' }

  // Check custom wake name if provided (e.g. "Hey Doshie")
  if (customWakeName && customWakeName.trim()) {
    const customEscaped = customWakeName.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const customRegex = new RegExp(`^(?:(?:hey|ok|okay|hi|hello)\\s+)?${customEscaped}\\b[,!\\s]*`, 'i')
    const matchCustom = trimmed.match(customRegex)
    if (matchCustom) {
      return {
        hasWakeWord: true,
        wakeWordMatched: matchCustom[0].trim(),
        remainder: trimmed.slice(matchCustom[0].length).trim(),
      }
    }
  }

  // Check default wake word variants
  const match = trimmed.match(WAKE_WORD_REGEX)
  if (match) {
    return {
      hasWakeWord: true,
      wakeWordMatched: match[0].trim(),
      remainder: trimmed.slice(match[0].length).trim(),
    }
  }

  return { hasWakeWord: false, remainder: trimmed }
}

/**
 * Parses and executes actions like "open", "send", "lock", "play", "stop", etc.
 */
export async function parseAndExecuteCommand(
  rawInput: string,
  context: CommandContext
): Promise<CommandResult> {
  const input = rawInput.trim()
  if (!input) return { handled: false }

  const lower = input.toLowerCase()

  // Helper to trigger voice confirmation & banner
  const confirmAction = (feedback: string, icon: string = '⚡') => {
    context.showBanner?.(feedback, icon)
    if (context.speakFeedback) {
      context.speakFeedback(feedback)
    }
  }

  // Helper to open URLs securely
  const openUrl = (url: string, name: string) => {
    confirmAction(`Opening ${name}...`, '🌐')
    try {
      const isCapacitor = Boolean((window as any).Capacitor?.isNativePlatform?.())
      if (isCapacitor && (window as any).Capacitor?.Plugins?.Browser) {
        ;(window as any).Capacitor.Plugins.Browser.open({ url })
      } else {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
    } catch {
      window.open(url, '_blank')
    }
  }

  // ==========================================
  // 1. OPEN COMMANDS
  // ==========================================

  // Open Music Player
  if (/\b(?:open|launch|play|show)\s+(?:music|music\s*player|songs?|audio\s*player|retro\s*player)\b/i.test(lower)) {
    context.onOpenMusicPlayer?.()
    confirmAction('Opening Music Player', '🎵')
    return { handled: true, actionType: 'open', feedback: 'Opening Music Player' }
  }

  // Open Live Voice
  if (/\b(?:open|launch|start)\s+(?:live\s*voice|voice\s*mode|talk\s*mode)\b/i.test(lower) || /\btalk\s+to\s+doshie\b/i.test(lower)) {
    context.onOpenLiveVoice?.()
    confirmAction('Starting Live Voice mode', '🎙️')
    return { handled: true, actionType: 'open', feedback: 'Starting Live Voice mode' }
  }

  // Open Appearance / Themes
  if (/\b(?:open|show|change)\s+(?:appearance|themes?|seasonal\s*themes?|styling|colors?)\b/i.test(lower)) {
    context.onOpenSettings?.('appearance')
    confirmAction('Opening Appearance & Themes', '🎨')
    return { handled: true, actionType: 'open', feedback: 'Opening Appearance & Themes' }
  }

  // Open Profiles
  if (/\b(?:open|show|switch)\s+(?:profiles?|family\s*accounts?|users?)\b/i.test(lower)) {
    context.onOpenSettings?.('profiles')
    confirmAction('Opening Profiles', '👤')
    return { handled: true, actionType: 'open', feedback: 'Opening Profiles' }
  }

  // Open Voice Studio
  if (/\b(?:open|launch|show)\s+(?:voice\s*studio|custom\s*voices?|voice\s*cloning)\b/i.test(lower)) {
    context.onOpenVoiceStudio?.()
    confirmAction('Opening Voice Studio', '🎙️')
    return { handled: true, actionType: 'open', feedback: 'Opening Voice Studio' }
  }

  // Open Agent Console / Terminal / CLI
  if (/\b(?:open|launch|show)\s+(?:console|terminal|cli|bash|agent\s*cli|agent\s*console)\b/i.test(lower)) {
    context.onOpenAgentConsole?.()
    confirmAction('Opening Terminal & Agent Console', '💻')
    return { handled: true, actionType: 'open', feedback: 'Opening Terminal & Agent Console' }
  }

  // Open Agent Hub
  if (/\b(?:open|launch|show)\s+(?:agent\s*hub|agents?|specialists?)\b/i.test(lower)) {
    context.onOpenAgentHub?.()
    confirmAction('Opening Agent Hub', '🤖')
    return { handled: true, actionType: 'open', feedback: 'Opening Agent Hub' }
  }

  // Open Settings / Control Center
  if (/\b(?:open|launch|show|go\s+to)\s+(?:settings|preferences|options|control\s*center)\b/i.test(lower)) {
    context.onOpenSettings?.('apps')
    confirmAction('Opening Settings', '⚙️')
    return { handled: true, actionType: 'open', feedback: 'Opening Settings' }
  }

  // Open Chats / History / Sidebar
  if (/\b(?:open|show|view)\s+(?:chats?|chat\s*explorer|history|sidebar|transcripts?)\b/i.test(lower)) {
    context.onOpenSidebar?.()
    confirmAction('Opening Chat Explorer', '💬')
    return { handled: true, actionType: 'open', feedback: 'Opening Chat Explorer' }
  }

  // Open Doshie Messenger / DMs / Family Chat
  if (
    /\b(?:open|launch|show|go\s+to)\s+(?:messenger|messages?|inbox|dms?|family\s*chat)\b/i.test(lower) ||
    /^\/(?:message|messages|messenger|inbox|dm)\b/i.test(lower)
  ) {
    context.onOpenMessenger?.()
    confirmAction('Opening Doshie Messenger', '💬')
    return { handled: true, actionType: 'open', feedback: 'Opening Doshie Messenger' }
  }

  // New Chat / Fresh Conversation
  if (/\b(?:start|create|open)?\s*(?:new\s*chat|fresh\s*chat|clear\s*chat)\b/i.test(lower)) {
    context.onNewChat?.()
    confirmAction('Starting a new chat', '✨')
    return { handled: true, actionType: 'open', feedback: 'Starting a new chat' }
  }

  // Camera / Take photo
  if (/\b(?:open|take|launch)\s*(?:camera|photos?|pictures?)\b/i.test(lower)) {
    const fileInput = document.createElement('input')
    fileInput.type = 'file'
    fileInput.accept = 'image/*'
    fileInput.capture = 'environment'
    fileInput.click()
    confirmAction('Opening camera', '📷')
    return { handled: true, actionType: 'open', feedback: 'Opening camera' }
  }

  // Popular Websites (Gemini-style URL / app opening)
  if (/\b(?:open|launch|go\s+to)\s+youtube\b/i.test(lower)) {
    openUrl('https://youtube.com', 'YouTube')
    return { handled: true, actionType: 'open', feedback: 'Opening YouTube' }
  }
  if (/\b(?:open|launch|go\s+to)\s+google\b/i.test(lower)) {
    openUrl('https://google.com', 'Google')
    return { handled: true, actionType: 'open', feedback: 'Opening Google' }
  }
  if (/\b(?:open|launch|go\s+to)\s+github\b/i.test(lower)) {
    openUrl('https://github.com', 'GitHub')
    return { handled: true, actionType: 'open', feedback: 'Opening GitHub' }
  }
  if (/\b(?:open|launch|go\s+to)\s+spotify\b/i.test(lower)) {
    openUrl('https://open.spotify.com', 'Spotify')
    return { handled: true, actionType: 'open', feedback: 'Opening Spotify' }
  }
  if (/\b(?:open|launch|go\s+to)\s+reddit\b/i.test(lower)) {
    openUrl('https://reddit.com', 'Reddit')
    return { handled: true, actionType: 'open', feedback: 'Opening Reddit' }
  }
  if (/\b(?:open|launch|go\s+to)\s+netflix\b/i.test(lower)) {
    openUrl('https://netflix.com', 'Netflix')
    return { handled: true, actionType: 'open', feedback: 'Opening Netflix' }
  }

  // Generic URL or domain open (e.g. "open wikipedia.org" or "open https://example.com")
  const urlMatch = input.match(/\b(?:open|launch|go\s+to)\s+(https?:\/\/[^\s]+|[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\/[^\s]*)?)\b/i)
  if (urlMatch) {
    let target = urlMatch[1]
    if (!target.startsWith('http')) {
      target = `https://${target}`
    }
    openUrl(target, target.replace(/^https?:\/\//, ''))
    return { handled: true, actionType: 'open', feedback: `Opening ${target}` }
  }

  // ==========================================
  // 2. SEND COMMANDS
  // ==========================================

  // Send to Terminal / CLI
  const terminalMatch = input.match(/\b(?:send\s+to\s+(?:terminal|cli|bash)|run\s+command)\s+(.+)$/i)
  if (terminalMatch) {
    const cmd = terminalMatch[1].trim()
    confirmAction(`Executing terminal command: ${cmd}`, '💻')
    fetch('/api/execute-command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        command: cmd,
        profile: context.activeProfile,
      }),
    }).catch(err => console.error('Terminal command failed:', err))
    return { handled: true, actionType: 'send', feedback: `Running command: ${cmd}` }
  }

  // Send Message / Prompt into Active Chat
  const sendMatch = input.match(/^send\s+(?:message|prompt|text|to\s+chat)?\s*(.+)$/i)
  if (sendMatch) {
    const messageToSend = sendMatch[1].trim()
    // If user says "send me a recipe" or "send me 5 tips", treat as chat prompt, not command
    if (/^me\b/i.test(messageToSend)) {
      return { handled: false, cleanPrompt: input }
    }
    if (messageToSend && context.onSendMessage) {
      confirmAction(`Sending: "${messageToSend}"`, '🚀')
      context.onSendMessage(messageToSend)
      return { handled: true, actionType: 'send', feedback: `Sending: ${messageToSend}` }
    }
  }

  // ==========================================
  // 3. SYSTEM & CONTROL COMMANDS
  // ==========================================

  // Lock Screen
  if (/\b(?:lock\s*(?:screen|account|app|doshie)?|log\s*out)\b/i.test(lower)) {
    confirmAction('Locking Doshie', '🔒')
    context.onLockAccount?.()
    return { handled: true, actionType: 'system', feedback: 'Locking screen' }
  }

  // Stop Speech / Generation
  if (/^(?:stop|pause|shut\s*up|be\s*quiet|silence)$/i.test(lower)) {
    context.onStopSpeech?.()
    confirmAction('Stopped', '⏹️')
    return { handled: true, actionType: 'system', feedback: 'Stopped' }
  }

  // Switch Profile
  const switchMatch = input.match(/\b(?:switch|change)\s*(?:to\s*)?(?:profile|user|account)?\s*([a-zA-Z0-9_-]+)\b/i)
  if (switchMatch) {
    const targetProfile = switchMatch[1].trim()
    if (targetProfile && context.onSwitchProfile) {
      confirmAction(`Switching profile to ${targetProfile}`, '👤')
      context.onSwitchProfile(targetProfile)
      return { handled: true, actionType: 'system', feedback: `Switched profile to ${targetProfile}` }
    }
  }

  return { handled: false, cleanPrompt: input }
}
