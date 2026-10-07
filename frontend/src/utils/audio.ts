/**
 * High-performance pipelined audio & neural speech synthesis utility with client-side caching
 * and instant sentence streaming.
 */

// In-memory cache for audio object URLs to allow instant replay (0ms latency)
const audioCache = new Map<string, string>()
const MAX_CACHE_SIZE = 100

let currentAudio: HTMLAudioElement | null = null
let cancelCurrentPlayback: (() => void) | null = null
let activeChunkResolver: (() => void) | null = null

const speechListeners = new Set<(speaking: boolean) => void>()
let currentSpeechActive = false

function notifySpeechState(speaking: boolean) {
  if (currentSpeechActive !== speaking) {
    currentSpeechActive = speaking
    speechListeners.forEach((fn) => {
      try {
        fn(speaking)
      } catch (e) {
        console.warn('Speech listener error:', e)
      }
    })
  }
}

export function isSpeaking(): boolean {
  return currentSpeechActive
}

export function subscribeSpeechState(callback: (speaking: boolean) => void): () => void {
  speechListeners.add(callback)
  callback(currentSpeechActive)
  return () => {
    speechListeners.delete(callback)
  }
}

/**
 * Strips markdown, emojis, code blocks, URLs, thinking tags, and symbols for crisp, natural speech synthesis.
 * Ensures Doshie speaks only the actual conversational words.
 */
export function cleanSpeakableText(rawText: string): string {
  if (!rawText) return ''

  let text = rawText

  // 1. Strip reasoning / thinking tags completely (e.g., DeepSeek R1 <think>...</think>)
  text = text
    .replace(/<think>[\s\S]*?<\/think>/gi, ' ')
    .replace(/<thought>[\s\S]*?<\/thought>/gi, ' ')
    .replace(/<reasoning>[\s\S]*?<\/reasoning>/gi, ' ')
    .replace(/<system>[\s\S]*?<\/system>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')

  // 2. Remove fenced code blocks completely
  text = text.replace(/```[\s\S]*?```/g, ' ')

  // 3. Remove inline code backticks, keeping the word/identifier
  text = text.replace(/`([^`]+)`/g, '$1')

  // 4. Remove LaTeX / Math blocks
  text = text
    .replace(/\$\$[\s\S]*?\$\$/g, ' ')
    .replace(/\$[^\$]+\$/g, ' ')
    .replace(/\\\[[\s\S]*?\\\]/g, ' ')
    .replace(/\\\(.*?\\\)/g, ' ')

  // 5. Remove markdown links [title](url) -> keep title, discard url
  text = text.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')

  // 6. Remove raw URLs completely
  text = text.replace(/https?:\/\/\S+/gi, ' ').replace(/www\.\S+/gi, ' ')

  // 7. Remove bracketed citations like [1], [2], [note]
  text = text.replace(/\[\d+\]/g, ' ')

  // 8. Remove roleplay / action narrations like *smiles*, *sighs*, *chuckles*, (sighs), etc.
  text = text
    .replace(/\*(?:smiles|chuckles|laughs|giggles|sighs|winks|nods|pauses|clears throat|whispers|gasps|shrugs|waves|blushes|grins|beams)[^*]*\*/gi, ' ')
    .replace(/\((?:smiles|chuckles|laughs|giggles|sighs|winks|nods|pauses|clears throat|whispers|gasps|shrugs|waves|blushes|grins|beams)[^)]*\)/gi, ' ')

  // 9. Remove all Emojis & Pictographs
  text = text.replace(
    /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2300}-\u{23FF}\u{2B50}\u{200D}\u{FE0F}]/gu,
    ' '
  )

  // 10. Remove text emoticons like :) :( :D xD <3 :P
  text = text.replace(/(?:\s|^)(?::[-~]?[)DPOpP\(/\\|]|;[-~]?[)DPOpP]|<3|xD|XD)(?:\s|$)/g, ' ')

  // 11. Remove markdown structure markers: headers (#), bullet lists (*, -, +), numbered prefixes (1. , 2. )
  text = text
    .replace(/^[ \t]*[#>*•\-+][ \t]+/gm, '')
    .replace(/^[ \t]*\d+\.[ \t]+/gm, '')
    .replace(/[#*_~>|\\^`]/g, ' ')

  // 12. Normalize punctuation artifacts (multiple dashes, arrows, stray slashes)
  text = text
    .replace(/-{2,}|—+|–+/g, ', ')
    .replace(/->|=>|<-|<=/g, ' ')
    .replace(/[/\\~@#$%^&*+=]/g, ' ')
    .replace(/!{2,}/g, '!')
    .replace(/\?{2,}/g, '?')

  // 13. Collapse multiple spaces and trim to speakable length
  return text
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 1000)
}

/**
 * Splits clean text into natural speakable sentence chunks for pipelined low-latency streaming.
 */
export function splitSentences(text: string): string[] {
  if (!text) return []

  // Split on sentence terminators followed by whitespace or linebreaks
  const rawChunks = text
    .split(/(?<=[.!?])\s+|\n+/)
    .map((s) => s.trim())
    .filter(Boolean)

  if (rawChunks.length === 0) return [text]

  const merged: string[] = []
  let buffer = ''

  for (const chunk of rawChunks) {
    if (!buffer) {
      buffer = chunk
    } else if (buffer.length + chunk.length < 50) {
      // Merge very short fragments so sentences are natural
      buffer = `${buffer} ${chunk}`
    } else {
      merged.push(buffer)
      buffer = chunk
    }
  }
  if (buffer) {
    merged.push(buffer)
  }

  return merged.length > 0 ? merged : [text]
}

/**
 * Stops any currently playing speech and cancels pending pipelined chunks instantly.
 */
export function stopSpeech() {
  if (cancelCurrentPlayback) {
    cancelCurrentPlayback()
    cancelCurrentPlayback = null
  }
  if (activeChunkResolver) {
    activeChunkResolver()
    activeChunkResolver = null
  }
  if (currentAudio) {
    try {
      currentAudio.pause()
      currentAudio.currentTime = 0
      currentAudio.src = ''
    } catch {
      // Ignore
    }
    currentAudio = null
  }
  if ('speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel()
    } catch {
      // Ignore
    }
  }
  notifySpeechState(false)
}

/**
 * Fetches synthesized audio for a single chunk, with in-memory caching.
 */
async function fetchChunkAudio(
  chunk: string,
  profile: string,
  engine?: string,
  voice?: string
): Promise<string> {
  const cacheKey = `${profile}:${engine || 'auto'}:${voice || 'default'}:${chunk}`
  const cachedUrl = audioCache.get(cacheKey)
  if (cachedUrl) return cachedUrl

  const response = await fetch('/speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: chunk,
      profile: profile,
      engine: engine,
      voice: voice,
    }),
  })

  if (!response.ok) {
    throw new Error(`TTS server returned ${response.status}`)
  }

  const blob = await response.blob()
  const audioUrl = URL.createObjectURL(blob)

  // Manage cache size
  if (audioCache.size >= MAX_CACHE_SIZE) {
    const oldestKey = audioCache.keys().next().value
    if (oldestKey) {
      const oldUrl = audioCache.get(oldestKey)
      if (oldUrl) URL.revokeObjectURL(oldUrl)
      audioCache.delete(oldestKey)
    }
  }
  audioCache.set(cacheKey, audioUrl)
  return audioUrl
}

/**
 * Plays a single audio URL returning a Promise that resolves when finished or interrupted.
 */
function playAudioChunk(audioUrl: string, onStarted?: () => void): Promise<void> {
  return new Promise<void>((resolve) => {
    const audio = new Audio(audioUrl)
    currentAudio = audio
    let settled = false

    const finish = () => {
      if (settled) return
      settled = true
      activeChunkResolver = null
      if (currentAudio === audio) {
        currentAudio = null
      }
      resolve()
    }

    activeChunkResolver = () => {
      try {
        audio.pause()
        audio.currentTime = 0
        audio.src = ''
      } catch {}
      finish()
    }

    audio.onplay = () => {
      onStarted?.()
    }

    audio.onended = finish
    audio.onerror = finish

    audio.play().catch((err) => {
      console.warn('Audio play prevented or interrupted:', err)
      finish()
    })
  })
}

/**
 * Synthesizes and plays text using low-latency pipelined sentence streaming.
 * Sentence 1 begins playing within ~150-200ms while subsequent sentences prefetch in the background.
 */
export async function playNeuralSpeech(
  text: string,
  options: {
    profile?: string
    engine?: string
    voice?: string
    onStart?: () => void
    onEnded?: () => void
    onError?: (err: any) => void
  } = {}
): Promise<void> {
  const clean = cleanSpeakableText(text)
  if (!clean) {
    notifySpeechState(false)
    options.onEnded?.()
    return
  }

  // Stop any active speech first
  stopSpeech()

  let isCancelled = false
  cancelCurrentPlayback = () => {
    isCancelled = true
    notifySpeechState(false)
  }

  const profile = options.profile || 'Hermes'
  const sentences = splitSentences(clean)

  if (sentences.length === 0) {
    notifySpeechState(false)
    options.onEnded?.()
    return
  }

  try {
    let hasStarted = false

    // Prefetch map to pipeline subsequent sentences in parallel
    const pendingPromises = new Map<number, Promise<string>>()

    const getOrFetchChunk = (index: number): Promise<string> => {
      if (index >= sentences.length) return Promise.reject(new Error('Out of bounds'))
      if (!pendingPromises.has(index)) {
        pendingPromises.set(
          index,
          fetchChunkAudio(sentences[index], profile, options.engine, options.voice)
        )
      }
      return pendingPromises.get(index)!
    }

    // Immediately trigger fetch for sentence 0 and sentence 1
    getOrFetchChunk(0)
    if (sentences.length > 1) {
      getOrFetchChunk(1)
    }

    for (let i = 0; i < sentences.length; i++) {
      if (isCancelled) break

      // Trigger prefetch for sentence i + 1
      if (i + 1 < sentences.length) {
        getOrFetchChunk(i + 1)
      }

      const audioUrl = await getOrFetchChunk(i)
      if (isCancelled) break

      await playAudioChunk(audioUrl, () => {
        if (!hasStarted) {
          hasStarted = true
          notifySpeechState(true)
          options.onStart?.()
        }
      })
    }

    notifySpeechState(false)
    if (!isCancelled) {
      options.onEnded?.()
    }
  } catch (error) {
    notifySpeechState(false)
    console.warn('Neural pipelined TTS error, falling back to Web Speech API:', error)
    if (isCancelled) return

    if ('speechSynthesis' in window) {
      return new Promise<void>((resolve) => {
        const utterance = new SpeechSynthesisUtterance(clean.slice(0, 300))
        utterance.rate = 1.0

        utterance.onstart = () => {
          notifySpeechState(true)
          options.onStart?.()
        }
        utterance.onend = () => {
          notifySpeechState(false)
          options.onEnded?.()
          resolve()
        }
        utterance.onerror = (e) => {
          notifySpeechState(false)
          options.onError?.(e)
          options.onEnded?.()
          resolve()
        }
        window.speechSynthesis.speak(utterance)
      })
    } else {
      notifySpeechState(false)
      options.onError?.(error)
      options.onEnded?.()
    }
  }
}
