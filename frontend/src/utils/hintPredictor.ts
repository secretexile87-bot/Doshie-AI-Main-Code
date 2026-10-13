/**
 * Doshie Smart Typeahead & Autonomous Hint Predictor
 * 
 * Provides real-time typing guesses, inline ghost completions, and interactive
 * suggestion chips—specialized for autonomous agents, background goals, tools, and actions.
 */

export interface PredictionHint {
  id: string
  title: string
  completion: string
  ghostSuffix?: string
  category: 'autonomous' | 'goal' | 'agent' | 'action' | 'skill' | 'prompt'
  badge: string
  icon: string
  description?: string
  accentColor?: string
  priority: number
}

export interface SpecialistAgentRef {
  id: string
  name: string
  purpose: string
  accent?: string
}

// Built-in specialist agents
export const DEFAULT_AGENTS: SpecialistAgentRef[] = [
  { id: 'hermes', name: 'Hermes', purpose: 'Primary companion & versatile troubleshooter', accent: '#35f2d0' },
  { id: 'codearchitect', name: 'CodeArchitect', purpose: 'Senior software engineer, system architecture & code optimization', accent: '#06b6d4' },
  { id: 'researcher', name: 'Researcher', purpose: 'Deep retrieval, fact-checking & structured analysis', accent: '#9d4edd' },
  { id: 'tutor', name: 'Tutor', purpose: 'Patient coding mentor & math tutor', accent: '#4ea8de' },
  { id: 'home', name: 'Home', purpose: 'Home automation, device status & local weather', accent: '#52b788' },
  { id: 'media', name: 'Media', purpose: 'Entertainment, Spotify music & media controller', accent: '#ffb703' },
]

// Curated autonomous prompts, goals, and actions
const AUTONOMOUS_HINTS: Array<Omit<PredictionHint, 'id' | 'ghostSuffix'>> = [
  // Autonomous Goals & Background Agent Tasks
  {
    title: '/goal Dispatch autonomous background task',
    completion: '/goal ',
    category: 'goal',
    badge: 'Autonomous Goal',
    icon: '🎯',
    description: 'Assign a multi-step objective to run in the background with tool execution',
    accentColor: '#38bdf8',
    priority: 100,
  },
  {
    title: 'Autonomous task: Analyze codebase and refactor',
    completion: 'Autonomous task: Analyze the codebase and suggest performance optimizations',
    category: 'autonomous',
    badge: 'Autonomous',
    icon: '🤖',
    description: 'Dispatch an autonomous agent to inspect and optimize code files',
    accentColor: '#06b6d4',
    priority: 95,
  },
  {
    title: 'Autonomous task: Deep research on topic',
    completion: 'Autonomous task: Research the latest developments in ',
    category: 'autonomous',
    badge: 'Autonomous',
    icon: '🔬',
    description: 'Multi-step web search and source synthesis',
    accentColor: '#a855f7',
    priority: 92,
  },
  {
    title: 'Autonomously monitor route and network health',
    completion: 'Autonomously monitor the system network route, NAT masquerading, and service health',
    category: 'autonomous',
    badge: 'Autonomous',
    icon: '🛡️',
    description: 'Background watchdog for local network & Tailscale routing',
    accentColor: '#10b981',
    priority: 90,
  },
  {
    title: 'Autonomous multi-step reasoning for',
    completion: 'Execute autonomous multi-step reasoning to solve: ',
    category: 'autonomous',
    badge: 'Autonomous',
    icon: '🧠',
    description: 'Step-by-step problem breakdown and automated solution verification',
    accentColor: '#f59e0b',
    priority: 88,
  },
  {
    title: 'Run autonomous agent in background',
    completion: 'Run an autonomous background agent to complete ',
    category: 'autonomous',
    badge: 'Autonomous',
    icon: '⚡',
    description: 'Launch an asynchronous task with live progress reporting',
    accentColor: '#ec4899',
    priority: 87,
  },
  {
    title: 'Dispatch background goal for',
    completion: 'Dispatch an autonomous background goal for ',
    category: 'goal',
    badge: 'Autonomous Goal',
    icon: '🚀',
    description: 'Run long-running autonomous workflow until finished',
    accentColor: '#6366f1',
    priority: 85,
  },

  // Slash Commands
  {
    title: '/console Open Autonomous Terminal & CLI',
    completion: '/console',
    category: 'action',
    badge: 'Console',
    icon: '💻',
    description: 'Open the autonomous agent console with terminal execution & code diffs',
    accentColor: '#10b981',
    priority: 82,
  },
  {
    title: '/tasks View running background tasks',
    completion: '/tasks',
    category: 'action',
    badge: 'Tasks',
    icon: '📋',
    description: 'Inspect live autonomous task status, steps, and tool calls',
    accentColor: '#3b82f6',
    priority: 80,
  },
  {
    title: '/skills Browse Antigravity agent skills',
    completion: '/skills',
    category: 'skill',
    badge: 'Skills',
    icon: '🛠️',
    description: 'Explore specialized Antigravity autonomous capabilities',
    accentColor: '#8b5cf6',
    priority: 78,
  },
  {
    title: '/agent Assign to specialist agent',
    completion: '/agent @',
    category: 'agent',
    badge: 'Agent',
    icon: '👤',
    description: 'Direct prompt to Hermes, CodeArchitect, Researcher, Tutor, etc.',
    accentColor: '#14b8a6',
    priority: 76,
  },
  {
    title: '/model Switch AI model brain',
    completion: '/model ',
    category: 'action',
    badge: 'Model',
    icon: '🧠',
    description: 'Choose auto, fast (9B), coding (7B), advanced (14B), or cloud',
    accentColor: '#f97316',
    priority: 70,
  },
  {
    title: '/clear Start a new conversation',
    completion: '/clear',
    category: 'action',
    badge: 'Action',
    icon: '✨',
    description: 'Clear chat messages and begin a fresh session',
    accentColor: '#64748b',
    priority: 65,
  },
  {
    title: '/weather Check current local weather',
    completion: '/weather',
    category: 'action',
    badge: 'Action',
    icon: '⛅',
    description: 'Fetch current weather and forecast for detected location',
    accentColor: '#0ea5e9',
    priority: 64,
  },
  {
    title: '/lock Lock current profile',
    completion: '/lock',
    category: 'action',
    badge: 'Security',
    icon: '🔒',
    description: 'Lock screen with PIN or biometric authentication',
    accentColor: '#ef4444',
    priority: 62,
  },

  // Interactive Tools & Autonomous Creative Features
  {
    title: 'Create a 3D model of a puppy',
    completion: 'Create a 3D model of a playful golden retriever puppy with a tennis ball',
    category: 'prompt',
    badge: '3D Creation',
    icon: '🐶',
    description: 'Generate an interactive animated 3D puppy model in Three.js',
    accentColor: '#f59e0b',
    priority: 75,
  },
  {
    title: 'Create a 3D model of a cat',
    completion: 'Create a 3D model of a sleeping orange tabby cat',
    category: 'prompt',
    badge: '3D Creation',
    icon: '🐱',
    description: 'Generate an interactive 3D cat model in Three.js',
    accentColor: '#f97316',
    priority: 74,
  },
  {
    title: 'Create a 3D model of a sports car',
    completion: 'Create a 3D model of a futuristic sports car with glowing wheels',
    category: 'prompt',
    badge: '3D Creation',
    icon: '🏎️',
    description: 'Generate a procedural 3D vehicle model with headlights',
    accentColor: '#ef4444',
    priority: 73,
  },
  {
    title: 'Create a 3D model of a modern house',
    completion: 'Create a 3D model of a cozy modern glass house with warm interior lights',
    category: 'prompt',
    badge: '3D Creation',
    icon: '🏠',
    description: 'Generate an architectural 3D building model',
    accentColor: '#10b981',
    priority: 72,
  },
  {
    title: 'Search the web for',
    completion: 'Search the web for ',
    category: 'prompt',
    badge: 'Web Tool',
    icon: '🌐',
    description: 'Perform real-time live search with verified source citations',
    accentColor: '#3b82f6',
    priority: 68,
  },
  {
    title: 'Check system health and diagnostics',
    completion: 'Check host system health, CPU, memory, and service status',
    category: 'prompt',
    badge: 'System Tool',
    icon: '📊',
    description: 'Inspect Ollama GPU, Tailscale, RAM, and disk utilization',
    accentColor: '#06b6d4',
    priority: 66,
  },
  {
    title: 'Calculate exact math expression',
    completion: 'Calculate using python_calculator: ',
    category: 'prompt',
    badge: 'Math Tool',
    icon: '🧮',
    description: 'Execute verified Python code for precise arithmetic and statistics',
    accentColor: '#8b5cf6',
    priority: 60,
  },
  {
    title: 'Wikipedia search for',
    completion: 'Wikipedia search for ',
    category: 'prompt',
    badge: 'Encyclopedia',
    icon: '📚',
    description: 'Retrieve verified summaries from Wikipedia articles',
    accentColor: '#6366f1',
    priority: 58,
  },

  // Gemini-style Voice/Text Action Commands
  {
    title: 'Open Settings',
    completion: 'open settings',
    category: 'action',
    badge: 'Action',
    icon: '⚙️',
    description: 'Navigate to app preferences, security & themes',
    accentColor: '#94a3b8',
    priority: 55,
  },
  {
    title: 'Open Agent Hub',
    completion: 'open agent hub',
    category: 'action',
    badge: 'Action',
    icon: '🤖',
    description: 'View specialists, autonomous tasks, and Antigravity skills',
    accentColor: '#38bdf8',
    priority: 54,
  },
  {
    title: 'Open Live Voice',
    completion: 'open live voice',
    category: 'action',
    badge: 'Action',
    icon: '🎙️',
    description: 'Launch real-time hands-free voice dialogue',
    accentColor: '#ec4899',
    priority: 52,
  },
  {
    title: 'Open Appearance & Themes',
    completion: 'open appearance',
    category: 'action',
    badge: 'Action',
    icon: '🎨',
    description: 'Customize colors, seasonal lighting, and LED glows',
    accentColor: '#f43f5e',
    priority: 50,
  },
  {
    title: 'Open dchats explorer',
    completion: 'open dchats',
    category: 'action',
    badge: 'Action',
    icon: '💬',
    description: 'Browse chat sessions and saved conversations',
    accentColor: '#10b981',
    priority: 48,
  },
]

/**
 * Normalizes string for prefix & substring comparisons
 */
function clean(str: string): string {
  return str.toLowerCase().trim()
}

/**
 * Returns a list of predictive hints matching the current input.
 * When the input is empty or very short, returns top autonomous starter hints.
 */
export function getPredictiveHints(
  rawInput: string,
  options?: {
    customAgents?: SpecialistAgentRef[]
    limit?: number
  }
): PredictionHint[] {
  const input = rawInput.trim()
  const lower = rawInput.toLowerCase()
  const agents = options?.customAgents && options.customAgents.length > 0 ? options.customAgents : DEFAULT_AGENTS
  const limit = options?.limit || 6

  // 1. User typed '@' -> Agent Mention Palette
  if (lower.startsWith('@') || /\s@([a-zA-Z0-9_-]*)$/.test(rawInput)) {
    const match = lower.match(/(?:^|\s)@([a-zA-Z0-9_-]*)$/)
    const query = match ? match[1].toLowerCase() : ''
    const filteredAgents = agents.filter(a => a.name.toLowerCase().includes(query) || clean(a.purpose).includes(query))

    return filteredAgents.slice(0, limit).map((a, idx) => {
      const completionText = `@${a.name} `
      let ghostSuffix: string | undefined
      if (lower.startsWith('@')) {
        const typedName = lower.slice(1)
        if (a.name.toLowerCase().startsWith(typedName)) {
          ghostSuffix = a.name.slice(typedName.length) + ' '
        }
      }
      return {
        id: `agent-${a.id}-${idx}`,
        title: `@${a.name}`,
        completion: completionText,
        ghostSuffix,
        category: 'agent',
        badge: 'Specialist Agent',
        icon: '👤',
        description: a.purpose,
        accentColor: a.accent || '#38bdf8',
        priority: 100 - idx,
      }
    })
  }

  // 2. User typed '/' -> Slash Commands Palette
  if (lower.startsWith('/')) {
    const query = lower.slice(1).trim()
    const slashCandidates = AUTONOMOUS_HINTS.filter(h => h.completion.startsWith('/'))

    const matched = slashCandidates
      .filter(h => {
        const cmd = h.completion.slice(1).toLowerCase().trim()
        return !query || cmd.includes(query) || clean(h.title).includes(query)
      })
      .map((h, idx) => {
        let ghostSuffix: string | undefined
        const cmdOnly = h.completion.toLowerCase().trim()
        if (cmdOnly.startsWith(lower)) {
          ghostSuffix = h.completion.slice(rawInput.length)
        }
        return {
          ...h,
          id: `slash-${idx}`,
          ghostSuffix,
          priority: h.priority + 10,
        }
      })

    return matched.slice(0, limit)
  }

  // 3. User hasn't typed anything or just whitespace -> Top Autonomous Starter Hints
  if (!input) {
    return [
      AUTONOMOUS_HINTS[0], // /goal Dispatch autonomous background task
      AUTONOMOUS_HINTS[1], // Autonomous task: Analyze codebase and refactor
      AUTONOMOUS_HINTS[7], // /console Open Autonomous Terminal & CLI
      AUTONOMOUS_HINTS[10], // /agent Assign to specialist agent
      AUTONOMOUS_HINTS[15], // Create a 3D model of a puppy
      AUTONOMOUS_HINTS[19], // Search the web for
    ].map((h, idx) => ({
      ...h,
      id: `default-${idx}`,
      ghostSuffix: undefined,
    }))
  }

  // 4. User typed text -> Predictive Scoring with Heavy Weighting on Autonomous tasks
  const isAutonomousQuery = /^(?:auto|goal|run|task|disp|exec|agent|build|resear)/i.test(lower)

  const scored: Array<PredictionHint & { score: number }> = []

  for (let i = 0; i < AUTONOMOUS_HINTS.length; i++) {
    const hint = AUTONOMOUS_HINTS[i]
    const completionLower = hint.completion.toLowerCase()
    const titleLower = hint.title.toLowerCase()
    const descLower = (hint.description || '').toLowerCase()

    let score = 0
    let ghostSuffix: string | undefined

    // Direct prefix match on completion text (Highest quality for ghost text)
    if (completionLower.startsWith(lower)) {
      score += 150
      ghostSuffix = hint.completion.slice(rawInput.length)
    } else if (titleLower.startsWith(lower)) {
      score += 120
      if (!ghostSuffix && hint.completion.toLowerCase().startsWith(lower)) {
        ghostSuffix = hint.completion.slice(rawInput.length)
      }
    } else if (completionLower.includes(lower)) {
      score += 80
    } else if (titleLower.includes(lower)) {
      score += 60
    } else if (descLower.includes(lower)) {
      score += 30
    }

    // Boost autonomous items when typing autonomous keywords
    if (isAutonomousQuery && (hint.category === 'autonomous' || hint.category === 'goal')) {
      score += 80
    }

    // Base priority boost
    score += hint.priority * 0.5

    if (score > 40) {
      scored.push({
        ...hint,
        id: `hint-${i}`,
        ghostSuffix,
        score,
      })
    }
  }

  // Also check if user is typing an agent name directly (e.g. "Hermes", "CodeArch")
  agents.forEach((a, idx) => {
    const aName = a.name.toLowerCase()
    if (aName.startsWith(lower) || a.purpose.toLowerCase().includes(lower)) {
      let ghostSuffix: string | undefined
      if (aName.startsWith(lower)) {
        ghostSuffix = a.name.slice(lower.length) + ': '
      }
      scored.push({
        id: `agent-direct-${a.id}-${idx}`,
        title: `@${a.name}`,
        completion: `@${a.name} `,
        ghostSuffix,
        category: 'agent',
        badge: 'Specialist Agent',
        icon: '👤',
        description: a.purpose,
        accentColor: a.accent || '#38bdf8',
        priority: 90,
        score: (aName.startsWith(lower) ? 140 : 50) + (isAutonomousQuery ? 20 : 0),
      })
    }
  })

  scored.sort((a, b) => b.score - a.score)
  return scored.slice(0, limit)
}

/**
 * Returns the single best ghost suffix string for the current input, if any.
 */
export function getTopGhostSuffix(input: string, hints: PredictionHint[]): string | null {
  if (!input || input.length < 1) return null
  const match = hints.find(h => h.ghostSuffix && h.ghostSuffix.length > 0)
  return match?.ghostSuffix || null
}
