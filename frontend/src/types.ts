export interface ChatAttachment {
  id: string
  name: string
  size: number
  mime_type: string
  kind: 'image' | 'file'
  url?: string
  previewUrl?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  error?: boolean
  pending?: boolean
  space?: string
  attachments?: ChatAttachment[]
  agent?: {
    id: string
    name: string
    accent: string
  }
  thinking?: string
  steps?: Array<{
    tool: string
    arguments?: any
    preview?: string
    thought?: string
  }>
}

export interface SpecialistAgent {
  id: string
  name: string
  purpose: string
  model_mode: string
  memory_scope: string
  instructions?: string
  accent: string
  capabilities: string[]
  enabled: boolean
}

export interface AgentTaskStep {
  step: number
  type: string
  thought?: string
  output?: string
  tool_calls?: Array<{
    tool: string
    arguments: any
    result?: any
    error?: string
    ok: boolean
  }>
  timestamp: string
}

export interface AgentTask {
  id: string
  agent_id: string
  agent_name: string
  agent_accent: string
  agent_purpose: string
  goal: string
  profile: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  steps: AgentTaskStep[]
  result?: string | null
  error?: string | null
}

export interface AntigravitySkill {
  name: string
  description: string
  path: string
  category: string
}


export interface GuiCustomization {
  // Theme & Colors
  theme: 'antigravity' | 'emerald' | 'cyberpunk' | 'oled' | 'amber' | 'crimson' | 'terminal' | 'nord' | 'dracula' | 'seasonal'
  seasonalThemeEnabled?: boolean
  seasonalCountdownVisible?: boolean
  backgroundStyle: 'solid' | 'glow' | 'grid' | 'stars'
  customWallpaperUrl?: string
  glassEffect: boolean

  // Typography & Density
  fontSize: 'compact' | 'comfortable' | 'large'
  chatDensity: 'compact' | 'comfortable' | 'spacious'
  bubbleStyle: 'rounded' | 'modern' | 'terminal' | 'glow_card'
  
  // Assistant Persona & Identity
  assistantEmoji: string
  assistantName: string
  greetingTitle: string
  greetingSubtitle: string
  
  // Chat & Code Features
  showTimestamp: boolean
  showAvatars: boolean
  codeTheme: 'matrix' | 'dracula' | 'monokai' | 'high_contrast'
  soundEffects: boolean
  soundVolume: number
  smoothScroll: boolean

  // Lock Screen Customization
  lockScreenTitle?: string
  lockScreenSubtitle?: string
  lockScreenWallpaper?: 'matrix' | 'glow' | 'stars' | 'cyberpunk' | 'oled' | 'aurora' | 'seasonal'
  lockScreenClockFormat?: '12h' | '24h'
  lockScreenAutoLockMinutes?: number
  lockScreenCustomNote?: string
  lockScreenShowWeather?: boolean
  lockScreenShowQuickProfiles?: boolean
  lockScreenShowSeasonCountdown?: boolean

  // MySpace Studio & Custom Code
  myspaceCustomCss?: string
  myspacePreset?: string
  myspaceBackgroundRepeat?: 'cover' | 'tile' | 'repeat-x'
  myspaceSparkleCursor?: boolean
  myspaceMarqueeText?: string
  myspaceSongUrl?: string
  myspaceSongTitle?: string
  myspaceHeadline?: string
  myspaceTop8Visible?: boolean
}

export interface Profile {
  id: string
  name: string
  color?: string
  role?: string
  avatar?: string
  is_admin?: boolean
  is_child?: boolean
  locked?: boolean
  unlocked?: boolean
  auth_type?: string
  has_biometrics?: boolean
  biometrics_count?: number
  mfa_enabled?: boolean
  biometrics_quick_unlock?: boolean
}

export interface AdminGuestMemory {
  id: number
  memory: string
  category: string
  importance: string
  created_at: string
  updated_at?: string
  active?: boolean
  profile?: string
  scope?: string
}

export interface AdminProfileOversight {
  name: string
  role: string
  is_admin: boolean
  is_child: boolean
  chat_count: number
  memory_count: number
  last_active: number
  recent_memories: AdminGuestMemory[]
}

export interface ChatSession {
  id: string
  title: string
  messages: Message[]
  created_at: number
  updated_at: number
  is_voice?: boolean
}

export interface AntigravitySummary {
  id: string
  title: string
  preview: string
  updated_at: string
  created_at: string
  file_size?: number
}

export interface AntigravityTurn {
  turn_index: number
  user: {
    text: string
    raw?: string
    created_at: string
  }
  thoughts: Array<{
    text: string
    created_at?: string
  }>
  tool_calls: Array<{
    name: string
    args?: any
    action?: string
    summary?: string
    result?: string | null
    created_at?: string
  }>
  assistant_replies: Array<{
    text: string
    created_at?: string
  }>
  created_at?: string
}

export interface AntigravityDetail {
  id: string
  title: string
  turns: AntigravityTurn[]
  turn_count: number
  step_count: number
  tool_call_count: number
  updated_at: string
}
