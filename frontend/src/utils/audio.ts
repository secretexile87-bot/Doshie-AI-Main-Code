/**
 * High-performance pipelined audio & neural speech synthesis utility with client-side caching
 * and instant sentence streaming.
 */

// In-memory cache for audio object URLs to allow instant replay (0ms latency)
const audioCache = new Map<string, string>()
const MAX_CACHE_SIZE = 100

let currentAudio: HTMLAudioElement | null = null
let cancelCurrentPlayback: (() => void) | null = null

/**
 * Strips markdown, emojis, code blocks, and URLs for crisp, fast neural TTS synthesis.
 */
export function cleanSpeakableText(rawText: string): string {
  if (!rawText) return ''

  return rawText
    // Remove fenced code blocks completely
    .replace(/```[\s\S]*?```/g, '')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove markdown links [text](url) -> text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove URLs
    .replace(/https?:\/\/\S+/g, '')
    // Remove markdown symbols #, *, _, ~, >, |, +, -
    .replace(/[#*_~>|+]/g, ' ')
    // Replace multiple spaces/newlines with single space
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
 * Stops any currently playing speech and cancels pending pipelined chunks.
 */
export function stopSpeech() {
  if (cancelCurrentPlayback) {
    cancelCurrentPlayback()
    cancelCurrentPlayback = null
  }
  if (currentAudio) {
    try {
      currentAudio.pause()
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
 * Plays a single audio URL returning a Promise that resolves when finished.
 */
function playAudioChunk(audioUrl: string, onStarted?: () => void): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const audio = new Audio(audioUrl)
    currentAudio = audio

    audio.onplay = () => {
      onStarted?.()
    }

    const handleEnd = () => {
      if (currentAudio === audio) {
        currentAudio = null
      }
      resolve()
    }

    audio.onended = handleEnd
    audio.onerror = (e) => {
      if (currentAudio === audio) {
        currentAudio = null
      }
      reject(e)
    }

    audio.play().catch((err) => {
      console.warn('Audio play prevented or interrupted:', err)
      handleEnd()
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
    options.onEnded?.()
    return
  }

  // Stop any active speech first
  stopSpeech()

  let isCancelled = false
  cancelCurrentPlayback = () => {
    isCancelled = true
  }

  const profile = options.profile || 'Hermes'
  const sentences = splitSentences(clean)

  if (sentences.length === 0) {
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
          options.onStart?.()
        }
      })
    }

    if (!isCancelled) {
      options.onEnded?.()
    }
  } catch (error) {
    console.warn('Neural pipelined TTS error, falling back to Web Speech API:', error)
    if (isCancelled) return

    if ('speechSynthesis' in window) {
      return new Promise<void>((resolve) => {
        const utterance = new SpeechSynthesisUtterance(clean.slice(0, 300))
        utterance.rate = 1.0

        utterance.onstart = () => {
          options.onStart?.()
        }
        utterance.onend = () => {
          options.onEnded?.()
          resolve()
        }
        utterance.onerror = (e) => {
          options.onError?.(e)
          options.onEnded?.()
          resolve()
        }
        window.speechSynthesis.speak(utterance)
      })
    } else {
      options.onError?.(error)
      options.onEnded?.()
    }
  }
}
