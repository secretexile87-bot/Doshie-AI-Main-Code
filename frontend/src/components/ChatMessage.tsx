import React, { useState, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import Prism from 'prismjs'
import 'prismjs/components/prism-javascript'
import 'prismjs/components/prism-typescript'
import 'prismjs/components/prism-python'
import 'prismjs/components/prism-bash'
import 'prismjs/components/prism-json'
import 'prismjs/components/prism-css'
import 'prismjs/components/prism-markup'
import 'prismjs/components/prism-sql'
import 'prismjs/components/prism-yaml'
import 'prismjs/components/prism-markdown'
import {
  Copy,
  Check,
  User,
  Volume2,
  VolumeX,
  Loader2,
  FileText,
  FileCode,
  Download,
  X,
  Maximize2,
  Edit3,
  WrapText,
  Sparkles,
  ExternalLink,
  Brain,
  Wrench,
  ChevronDown,
  ChevronUp,
  Play,
  Terminal,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Repeat,
  Trash2,
} from 'lucide-react'
import type { Message, ChatAttachment } from '../types'
import { playNeuralSpeech, stopSpeech } from '../utils/audio'
import { FileEditorModal } from './FileEditorModal'
import { ModelViewer3D } from './ModelViewer3D'

interface ChatMessageProps {
  message: Message
  assistantEmoji?: string
  activeProfile?: string
  onRetry?: (message: Message) => void
  onResend?: (message: Message) => void
  onEditPrompt?: (content: string) => void
  onDeleteMessage?: (messageId: string) => void
  isGenerating?: boolean
}

// Standalone Syntax-Highlighted Code Block with Terminal Controls
const CodeBlock: React.FC<{
  language?: string
  children: string
  activeProfile?: string
}> = ({ language, children, activeProfile = 'Hermes' }) => {
  const [copied, setCopied] = useState(false)
  const [wrap, setWrap] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [execResult, setExecResult] = useState<{
    ok: boolean
    exit_code?: number
    stdout?: string
    stderr?: string
    duration?: number
    error?: string
  } | null>(null)
  const [showOutput, setShowOutput] = useState(true)

  const lang = (language || '').toLowerCase().trim()
  const displayLang = lang || 'code'
  const isShellCommand = ['bash', 'sh', 'shell', 'zsh', 'terminal', 'cmd'].includes(lang)

  const highlightedHtml = useMemo(() => {
    try {
      const grammar = Prism.languages[lang]
      if (grammar) {
        return Prism.highlight(children, grammar, lang)
      }
      return Prism.highlight(children, Prism.languages.clike || Prism.languages.plain, 'plain')
    } catch {
      return children
    }
  }, [children, lang])

  const lineCount = useMemo(() => {
    return children.split('\n').length
  }, [children])

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRunCommand = async () => {
    if (isRunning) return
    setIsRunning(true)
    setExecResult(null)
    setShowOutput(true)
    try {
      const res = await fetch('/api/execute-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: children.trim(),
          profile: activeProfile,
        })
      })
      const data = await res.json()
      setExecResult(data)
    } catch (err: any) {
      setExecResult({
        ok: false,
        error: err?.message || 'Network error executing command'
      })
    } finally {
      setIsRunning(false)
    }
  }

  return (
    <div className="relative my-3 rounded-2xl overflow-hidden bg-black/60 border border-white/10 shadow-xl shadow-black/50 backdrop-blur-md group/code">
      {/* Terminal Title Bar */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-white/[0.04] border-b border-white/10 text-[11px] select-none">
        <div className="flex items-center gap-2">
          {/* Terminal Controls */}
          <div className="flex items-center gap-1.5 opacity-80 group-hover/code:opacity-100 transition-opacity">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block shadow-xs" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block shadow-xs" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block shadow-xs" />
          </div>

          {/* Language Badge */}
          <span className="ml-1.5 font-mono font-semibold text-[var(--accent-light)] px-2 py-0.5 rounded-md bg-[var(--card-dark)]/80 border border-[var(--border-dark)] uppercase text-[10px] tracking-wider">
            {displayLang}
          </span>

          {lineCount > 1 && (
            <span className="hidden sm:inline-block text-[10px] text-neutral-400 font-mono">
              {lineCount} lines
            </span>
          )}
        </div>

        {/* Code Actions: Run Command, Wrap & Copy */}
        <div className="flex items-center gap-1.5">
          {isShellCommand && (
            <button
              onClick={handleRunCommand}
              disabled={isRunning}
              type="button"
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-emerald-300 bg-emerald-950/60 hover:bg-emerald-900/80 border border-emerald-500/40 hover:border-emerald-400 transition-all cursor-pointer active:scale-95 shadow-xs disabled:opacity-50"
              title="Run command on host PC (acer-nitro)"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin text-emerald-400" />
                  <span>Running...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 text-emerald-400 fill-emerald-400" />
                  <span>Run</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={() => setWrap(!wrap)}
            type="button"
            className={`p-1.5 rounded-lg border text-[11px] transition-all cursor-pointer ${
              wrap
                ? 'bg-[var(--accent)]/30 border-[var(--accent)] text-white'
                : 'bg-white/5 hover:bg-white/10 border-white/10 text-neutral-400 hover:text-white'
            }`}
            title={wrap ? 'Disable text wrap' : 'Enable text wrap'}
          >
            <WrapText className="w-3 h-3" />
          </button>

          <button
            onClick={handleCopy}
            type="button"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-white bg-white/10 hover:bg-[var(--accent)] border border-white/10 hover:border-[var(--accent)] transition-all cursor-pointer active:scale-95 shadow-xs"
            title="Copy code to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-[var(--accent-light)]" />
                <span className="text-[var(--accent-light)] font-medium">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 text-neutral-300" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Highlighted Code Text */}
      <pre
        className={`p-4 text-[12.5px] sm:text-[13px] font-mono leading-relaxed text-neutral-100 ${
          wrap ? 'whitespace-pre-wrap break-words' : 'overflow-x-auto whitespace-pre'
        }`}
      >
        <code
          className={`language-${displayLang}`}
          dangerouslySetInnerHTML={{ __html: highlightedHtml }}
        />
      </pre>

      {/* Live Command Execution Output Drawer */}
      {execResult && (
        <div className="border-t border-white/10 bg-[#090d14] p-3 text-xs font-mono">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10 text-[11px]">
            <div className="flex items-center gap-2">
              <Terminal className="w-3.5 h-3.5 text-[var(--accent-light)]" />
              <span className="font-semibold text-white">Terminal Output</span>
              {execResult.ok ? (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  <CheckCircle2 className="w-2.5 h-2.5" /> exit 0
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  <AlertTriangle className="w-2.5 h-2.5" /> exit {execResult.exit_code ?? 1}
                </span>
              )}
              {execResult.duration !== undefined && (
                <span className="text-neutral-400 text-[10px]">({execResult.duration}s)</span>
              )}
            </div>

            <button
              onClick={() => setShowOutput(!showOutput)}
              className="text-[10px] text-neutral-400 hover:text-white transition-colors cursor-pointer"
            >
              {showOutput ? 'Hide' : 'Show'}
            </button>
          </div>

          {showOutput && (
            <div className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-lg bg-black/80 p-2.5 text-neutral-200 select-text">
              {execResult.stdout && <div>{execResult.stdout}</div>}
              {execResult.stderr && <div className="text-rose-400">{execResult.stderr}</div>}
              {execResult.error && <div className="text-rose-400">{execResult.error}</div>}
              {!execResult.stdout && !execResult.stderr && !execResult.error && (
                <div className="text-neutral-500 italic">(Command executed with no output)</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  assistantEmoji = '🦖',
  activeProfile = 'Hermes',
  onRetry,
  onResend,
  onEditPrompt,
  onDeleteMessage,
  isGenerating,
}) => {
  const isAssistant = message.role === 'assistant'
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [isThoughtExpanded, setIsThoughtExpanded] = useState(false)
  const [lightboxImage, setLightboxImage] = useState<ChatAttachment | null>(null)
  const [editingFile, setEditingFile] = useState<ChatAttachment | null>(null)

  const { displayContent, thoughtContent } = useMemo(() => {
    let content = message.content || ''
    let thought = message.thinking || ''

    const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/i)
    if (thinkMatch) {
      if (!thought) {
        thought = thinkMatch[1].trim()
      }
      content = content.replace(/<think>[\s\S]*?<\/think>/i, '').trim()
    }

    return { displayContent: content, thoughtContent: thought }
  }, [message.content, message.thinking])

  const handleCopy = () => {
    navigator.clipboard.writeText(displayContent || message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleToggleSpeak = async () => {
    if (isPlayingAudio || isSynthesizing) {
      stopSpeech()
      setIsPlayingAudio(false)
      setIsSynthesizing(false)
      return
    }

    const textToSpeak = displayContent || message.content
    if (!textToSpeak.trim()) return

    setIsSynthesizing(true)
    try {
      await playNeuralSpeech(textToSpeak, {
        profile: activeProfile,
        engine: 'auto',
        onStart: () => {
          setIsSynthesizing(false)
          setIsPlayingAudio(true)
        },
        onEnded: () => {
          setIsSynthesizing(false)
          setIsPlayingAudio(false)
        },
        onError: () => {
          setIsSynthesizing(false)
          setIsPlayingAudio(false)
        },
      })
    } catch {
      setIsSynthesizing(false)
      setIsPlayingAudio(false)
    }
  }

  const formatTime = (ts: number) => {
    return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatFileSize = (bytes: number) => {
    if (!bytes) return ''
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getAttachmentUrl = (att: ChatAttachment, download = false) => {
    if (att.url) {
      if (!download) return att.url
      const sep = att.url.includes('?') ? '&' : '?'
      return `${att.url}${sep}download=1`
    }
    return `/chat-attachment/${att.id}?profile=${encodeURIComponent(activeProfile)}${download ? '&download=1' : ''}`
  }

  const images = message.attachments?.filter(a => a.kind === 'image') || []
  const files = message.attachments?.filter(a => a.kind !== 'image') || []

  return (
    <>
      <div
        className={`group w-full py-2 px-2.5 sm:px-4 flex gap-2.5 sm:gap-3 transition-colors animate-message-enter ${
          isUser ? 'justify-end' : 'justify-start'
        }`}
      >
        {/* Assistant Avatar */}
        {isAssistant && (
          <div
            style={
              message.agent?.accent
                ? { background: `linear-gradient(135deg, ${message.agent.accent}, #111827)` }
                : undefined
            }
            className={`flex-none w-8 h-8 sm:w-9 sm:h-9 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] flex items-center justify-center text-sm sm:text-base font-bold shadow-md shadow-black/40 mt-0.5 border border-white/10 ${
              message.pending ? 'animate-pulse ring-2 ring-[var(--accent)]/50' : ''
            }`}
          >
            {message.agent?.name ? message.agent.name.charAt(0) : assistantEmoji}
          </div>
        )}

        {/* Quick action buttons next to user bubble (visible on desktop hover & active) */}
        {isUser && !message.pending && (
          <div className="hidden sm:flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 self-center mr-1 mb-1.5 flex-none select-none seasonal-action-pill p-1 rounded-xl">
            {onRetry && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onRetry(message)
                }}
                disabled={isGenerating}
                title="Retry / Regenerate response"
                className="p-1 rounded-lg hover:bg-white/15 text-neutral-300 hover:text-white transition-all cursor-pointer disabled:opacity-40 active:scale-90"
              >
                <RotateCw className="w-3.5 h-3.5" />
              </button>
            )}
            {onResend && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onResend(message)
                }}
                disabled={isGenerating}
                title="Resend prompt as new message"
                className="p-1 rounded-lg hover:bg-white/15 text-neutral-300 hover:text-white transition-all cursor-pointer disabled:opacity-40 active:scale-90"
              >
                <Repeat className="w-3.5 h-3.5" />
              </button>
            )}
            {onEditPrompt && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onEditPrompt(message.content)
                }}
                title="Edit prompt in input composer"
                className="p-1 rounded-lg hover:bg-white/15 text-neutral-300 hover:text-white transition-all cursor-pointer active:scale-90"
              >
                <Edit3 className="w-3.5 h-3.5 seasonal-glow-icon" />
              </button>
            )}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                handleCopy()
              }}
              title="Copy text"
              className="p-1 rounded-lg hover:bg-white/15 text-neutral-300 hover:text-white transition-all cursor-pointer active:scale-90"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 seasonal-glow-icon" />}
            </button>
            {onDeleteMessage && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteMessage(message.id)
                }}
                title="Delete message"
                className="p-1 rounded-lg hover:bg-rose-950/60 text-rose-400 hover:text-rose-200 transition-all cursor-pointer active:scale-90"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )}

        {/* Message Bubble Card */}
        <div
          style={{
            borderRadius: isUser ? '1.25rem 1.25rem 0.35rem 1.25rem' : 'var(--bubble-radius, 1.25rem)',
            fontSize: 'var(--chat-font-size, 14.5px)',
            background: isUser ? 'var(--user-bubble)' : message.error ? undefined : 'var(--bot-bubble)',
            borderColor: isUser ? 'rgba(255, 255, 255, 0.12)' : message.error ? undefined : 'var(--bot-border)',
          }}
          className={`relative max-w-[94%] sm:max-w-[85%] px-4 sm:px-5 py-3.5 leading-relaxed transition-all ${
            isUser
              ? 'text-white shadow-lg shadow-black/40 border'
              : message.error
              ? 'bg-rose-950/60 border border-rose-800 text-rose-200 shadow-md backdrop-blur-md'
              : 'border text-neutral-100 shadow-md shadow-black/40 backdrop-blur-md'
          }`}
        >
          {/* Specialist Agent Badge */}
          {isAssistant && message.agent && (
            <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-white/10 text-[11px] font-bold">
              <span
                style={{ color: message.agent.accent || 'var(--accent-light)' }}
                className="flex items-center gap-1"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {message.agent.name}
              </span>
              <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-white/10 text-neutral-300 border border-white/10">
                Specialist Agent
              </span>
            </div>
          )}

          {/* Attached Images Grid */}
          {images.length > 0 && (
            <div
              className={`mb-3 gap-2.5 grid ${
                images.length === 1
                  ? 'grid-cols-1'
                  : images.length === 2
                  ? 'grid-cols-2'
                  : 'grid-cols-2 sm:grid-cols-3'
              }`}
            >
              {images.map(img => {
                const src = img.previewUrl || getAttachmentUrl(img)
                return (
                  <div
                    key={img.id}
                    onClick={() => setLightboxImage(img)}
                    className="group/img relative rounded-2xl overflow-hidden bg-black/50 border border-white/10 hover:border-[var(--accent)] cursor-pointer transition-all shadow-md max-h-[280px] flex items-center justify-center"
                  >
                    <img
                      src={src}
                      alt={img.name}
                      loading="lazy"
                      className="w-full h-full object-cover group-hover/img:scale-105 transition-transform duration-300"
                    />
                    <div className="absolute inset-0 bg-black/40 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <span className="p-2 rounded-xl bg-black/70 text-white shadow-lg backdrop-blur-md border border-white/20">
                        <Maximize2 className="w-4 h-4" />
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Attached Files List */}
          {files.length > 0 && (
            <div className="mb-3 flex flex-col gap-2">
              {files.map(f => (
                <div
                  key={f.id}
                  className="flex items-center justify-between gap-3 px-3.5 py-2.5 rounded-2xl bg-black/40 border border-white/10 hover:border-[var(--accent)]/60 transition-all text-xs backdrop-blur-sm"
                >
                  <div
                    onClick={() => setEditingFile(f)}
                    className="flex items-center gap-3 min-w-0 cursor-pointer hover:opacity-90"
                  >
                    <div className="p-2 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent-light)] flex-none shadow-xs">
                      {f.name.endsWith('.py') || f.name.endsWith('.js') || f.name.endsWith('.json') || f.name.endsWith('.html') ? (
                        <FileCode className="w-4 h-4" />
                      ) : (
                        <FileText className="w-4 h-4" />
                      )}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-semibold text-white truncate max-w-[180px] sm:max-w-[280px]">
                        {f.name}
                      </span>
                      <span className="text-[10px] text-neutral-400">{formatFileSize(f.size)}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 flex-none">
                    <button
                      type="button"
                      onClick={() => setEditingFile(f)}
                      title="View & Edit File Content"
                      className="p-1.5 rounded-xl bg-white/5 hover:bg-[var(--accent)] text-neutral-300 hover:text-white transition-all flex-none cursor-pointer border border-white/10"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <a
                      href={getAttachmentUrl(f, true)}
                      download={f.name}
                      title="Download file"
                      className="p-1.5 rounded-xl bg-white/5 hover:bg-[var(--accent)] text-neutral-300 hover:text-white transition-all flex-none border border-white/10"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Thinking / Streaming Indicator */}
          {message.pending ? (
            <div className="py-2 space-y-2">
              <div className="flex items-center gap-2 text-[var(--accent-light)]">
                <span className="flex gap-1 items-center">
                  <span className="w-2 h-2 rounded-full bg-[var(--accent)] animate-wave-1" />
                  <span className="w-2 h-2 rounded-full bg-[var(--accent)] animate-wave-2" />
                  <span className="w-2 h-2 rounded-full bg-[var(--accent)] animate-wave-3" />
                </span>
                <span className="text-xs font-semibold tracking-wide">
                  Doshie is synthesizing response...
                </span>
              </div>
              <div className="w-full h-1 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent w-full animate-pulse" />
              </div>
            </div>
          ) : (
            <>
              {/* 🧠 Thinking / Chain of Thought Accordion */}
              {thoughtContent && (
                <div className="mb-3 rounded-xl border border-indigo-900/60 bg-[#0d1624]/80 overflow-hidden shadow-sm">
                  <button
                    type="button"
                    onClick={() => setIsThoughtExpanded(prev => !prev)}
                    className="w-full px-3 py-2 flex items-center justify-between text-xs font-medium text-indigo-300 hover:text-indigo-100 hover:bg-indigo-950/40 transition-colors cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-2">
                      <Brain className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Thought Process & Reasoning</span>
                    </div>
                    {isThoughtExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>

                  {isThoughtExpanded && (
                    <div className="p-3 pt-2 border-t border-indigo-950/80 space-y-2 text-xs font-mono text-indigo-200/90 leading-relaxed bg-[#080d16] whitespace-pre-wrap max-h-96 overflow-y-auto">
                      {thoughtContent}
                    </div>
                  )}
                </div>
              )}

              {/* ⚡ Multi-Step Tool Execution Badges */}
              {message.steps && message.steps.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {message.steps.map((st, sIdx) => (
                    <span
                      key={sIdx}
                      title={st.preview || st.thought || ''}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/60 border border-emerald-500/30 text-[11px] font-mono text-emerald-300 shadow-sm"
                    >
                      <Wrench className="w-3 h-3 text-emerald-400" />
                      <span>{st.tool ? `Step ${sIdx + 1}: ${st.tool}` : `Step ${sIdx + 1}`}</span>
                    </span>
                  ))}
                </div>
              )}

              {(displayContent || message.content) && (
                <div className="prose prose-invert max-w-none break-words text-[13.5px] sm:text-[14px] leading-relaxed">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                  components={{
                    p: ({ children }) => <p className="mb-2.5 last:mb-0 leading-relaxed text-neutral-200">{children}</p>,
                    a: ({ href, children }) => {
                      let validHref = String(href || '').trim()
                      if (
                        validHref &&
                        !validHref.startsWith('http://') &&
                        !validHref.startsWith('https://') &&
                        !validHref.startsWith('/') &&
                        !validHref.startsWith('#') &&
                        !validHref.startsWith('mailto:')
                      ) {
                        validHref = 'https://' + validHref
                      }
                      return (
                        <a
                          href={validHref}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => {
                            if ((window as any).electron?.shell?.openExternal) {
                              e.preventDefault()
                              ;(window as any).electron.shell.openExternal(validHref)
                            }
                          }}
                          className="inline-flex items-baseline gap-1 text-[var(--accent-light)] hover:text-white underline underline-offset-4 decoration-[var(--accent)]/60 hover:decoration-[var(--accent-light)] font-medium transition-colors cursor-pointer"
                        >
                          <span>{children}</span>
                          <ExternalLink className="w-3 h-3 opacity-70" />
                        </a>
                      )
                    },
                    img: ({ src, alt }: any) => {
                      const imageSrc = String(src || '')
                      return (
                        <div className="my-3 rounded-2xl overflow-hidden border border-white/10 bg-black/40 shadow-xl max-w-xl group relative">
                          <img
                            src={imageSrc}
                            alt={alt || 'Image'}
                            loading="lazy"
                            className="w-full h-auto max-h-[440px] object-cover rounded-xl transition-transform duration-300 group-hover:scale-[1.01] cursor-pointer"
                            onClick={() => window.open(imageSrc, '_blank')}
                          />
                          {alt && (
                            <div className="px-3.5 py-2 text-xs text-neutral-300 bg-black/70 border-t border-white/10 flex items-center justify-between">
                              <span className="font-medium truncate mr-2">{alt}</span>
                              <span className="text-[10px] text-[var(--accent-light)] flex-none uppercase tracking-wider">Click to view full</span>
                            </div>
                          )}
                        </div>
                      )
                    },
                    ul: ({ children }) => (
                      <ul className="my-2.5 space-y-1.5 list-disc list-inside text-neutral-200 pl-1">{children}</ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="my-2.5 space-y-2 list-decimal list-inside text-neutral-200 pl-1">{children}</ol>
                    ),
                    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                    strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-3 border-[var(--accent)] pl-3.5 my-3 text-neutral-200 bg-white/[0.03] py-2 px-3.5 rounded-r-xl border border-white/5">
                        {children}
                      </blockquote>
                    ),
                    table: ({ children }) => (
                      <div className="my-3 overflow-x-auto rounded-xl border border-white/10 shadow-md">
                        <table className="w-full text-left border-collapse text-xs sm:text-sm">{children}</table>
                      </div>
                    ),
                    th: ({ children }) => (
                      <th className="bg-white/5 px-3 py-2 font-semibold text-white border-b border-white/10 text-xs uppercase tracking-wider">{children}</th>
                    ),
                    td: ({ children }) => (
                      <td className="px-3 py-2 border-b border-white/5 text-neutral-300">{children}</td>
                    ),
                    h1: ({ children }) => <h1 className="text-base font-bold text-white mt-4 mb-2 first:mt-0 pb-1 border-b border-white/10">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-sm font-bold text-white mt-3.5 mb-1.5 first:mt-0">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-xs font-semibold text-[var(--accent-light)] mt-3 mb-1 first:mt-0 uppercase tracking-wider">{children}</h3>,
                    pre({ children }) {
                      return <>{children}</>
                    },
                    code({ className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '')
                      const rawString = String(children).replace(/\n$/, '')
                      const isBlock = Boolean(match) || rawString.includes('\n')

                      if (isBlock) {
                        const lang = (match ? match[1] : '').toLowerCase().trim()
                        if (['3d', 'threejs', 'three', 'gltf', 'stl', 'obj', 'model3d'].includes(lang)) {
                          return <ModelViewer3D code={rawString} />
                        }
                        return (
                          <CodeBlock language={match ? match[1] : undefined} activeProfile={activeProfile}>
                            {rawString}
                          </CodeBlock>
                        )
                      }

                      return (
                        <code
                          className="inline-block px-1.5 py-0.5 mx-0.5 rounded-md bg-black/40 text-[var(--accent-light)] font-mono text-[12px] border border-white/10 align-baseline font-medium"
                          {...props}
                        >
                          {children}
                        </code>
                      )
                    },
                  }}
                >
                  {displayContent || message.content}
                </ReactMarkdown>
              </div>
            )}
          </>
        )}

          {/* Footer info: Actions, Listen, Copy, Timestamp */}
          {!message.pending && (
            <div
              className={`mt-2.5 pt-1.5 border-t border-white/10 flex items-center gap-2 text-[10px] ${
                isUser ? 'text-white/80 justify-between' : 'text-neutral-400 justify-between'
              }`}
            >
              {isUser ? (
                <>
                  <span className="font-mono text-[10px] text-white/60">{formatTime(message.timestamp)}</span>

                  <div className="flex items-center gap-1.5 seasonal-action-pill px-1.5 py-0.5 rounded-lg ml-auto">
                    {onRetry && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onRetry(message)
                        }}
                        disabled={isGenerating}
                        title="Retry / Regenerate response"
                        className="p-1 rounded-md text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                      >
                        <RotateCw className="w-3.5 h-3.5 seasonal-glow-icon" />
                      </button>
                    )}

                    {onResend && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onResend(message)
                        }}
                        disabled={isGenerating}
                        title="Resend prompt as new message"
                        className="p-1 rounded-md text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                      >
                        <Repeat className="w-3.5 h-3.5 seasonal-glow-icon" />
                      </button>
                    )}

                    {onEditPrompt && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onEditPrompt(message.content)
                        }}
                        title="Edit prompt in input composer"
                        className="p-1 rounded-md text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                      >
                        <Edit3 className="w-3.5 h-3.5 seasonal-glow-icon" />
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleCopy()
                      }}
                      title="Copy message"
                      className="p-1 rounded-md text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 seasonal-glow-icon" />}
                    </button>

                    {onDeleteMessage && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation()
                          onDeleteMessage(message.id)
                        }}
                        title="Delete message"
                        className="p-1 rounded-md text-rose-400 hover:text-rose-200 hover:bg-rose-950/60 transition-colors cursor-pointer active:scale-90"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  <span className="font-mono">{formatTime(message.timestamp)}</span>

                  {isAssistant && message.content && (
                    <div className="flex items-center gap-1.5 seasonal-action-pill px-1.5 py-0.5 rounded-lg">
                      <button
                        onClick={handleToggleSpeak}
                        title={
                          isSynthesizing
                            ? 'Generating neural voice...'
                            : isPlayingAudio
                            ? 'Stop reading'
                            : 'Read aloud with neural voice'
                        }
                        className={`px-2 py-1 rounded-lg transition-all cursor-pointer flex items-center gap-1 border ${
                          isSynthesizing
                            ? 'text-[var(--accent-light)] bg-white/10 border-[var(--accent)]/50'
                            : isPlayingAudio
                            ? 'text-[var(--accent-light)] bg-[var(--accent)]/20 border-[var(--accent)] animate-pulse'
                            : 'text-neutral-400 hover:text-white hover:bg-white/10 border-transparent hover:border-white/10'
                        }`}
                      >
                        {isSynthesizing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--accent)]" />
                        ) : isPlayingAudio ? (
                          <>
                            <VolumeX className="w-3.5 h-3.5" />
                            <span className="text-[10px] font-semibold text-[var(--accent-light)]">Playing</span>
                          </>
                        ) : (
                          <Volume2 className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {onRetry && (
                        <button
                          onClick={() => onRetry(message)}
                          title="Retry (regenerate response)"
                          className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                        >
                          <RotateCw className="w-3.5 h-3.5" />
                        </button>
                      )}

                      <button
                        onClick={handleCopy}
                        title="Copy full response"
                        className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 seasonal-glow-icon" />}
                      </button>

                      {onDeleteMessage && (
                        <button
                          onClick={() => onDeleteMessage(message.id)}
                          title="Delete message"
                          className="p-1 rounded-md text-rose-400 hover:text-rose-200 hover:bg-rose-950/60 transition-colors cursor-pointer active:scale-90"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>

        {/* User Avatar */}
        {isUser && (
          <div className="flex-none w-8 h-8 sm:w-9 sm:h-9 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] border border-white/20 flex items-center justify-center text-xs font-semibold text-white shadow-md shadow-black/30 mt-0.5">
            <User className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Fullscreen Image Lightbox Modal */}
      {lightboxImage && (
        <div
          onClick={() => setLightboxImage(null)}
          className="fixed inset-0 z-50 bg-black/92 backdrop-blur-xl flex flex-col items-center justify-center p-4 animate-fadeIn"
        >
          <div className="absolute top-4 right-4 flex items-center gap-3">
            <a
              href={getAttachmentUrl(lightboxImage, true)}
              download={lightboxImage.name}
              onClick={e => e.stopPropagation()}
              className="px-3 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors flex items-center gap-2 text-xs font-semibold backdrop-blur-md border border-white/10"
              title="Download image"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </a>
            <button
              onClick={() => setLightboxImage(null)}
              className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors cursor-pointer border border-white/10"
              title="Close viewer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div
            onClick={e => e.stopPropagation()}
            className="max-w-4xl max-h-[85vh] flex flex-col items-center"
          >
            <img
              src={lightboxImage.previewUrl || getAttachmentUrl(lightboxImage)}
              alt={lightboxImage.name}
              className="max-w-full max-h-[78vh] object-contain rounded-2xl shadow-2xl border border-white/15"
            />
            <div className="mt-3 text-center">
              <p className="text-sm font-semibold text-white">{lightboxImage.name}</p>
              <p className="text-xs text-neutral-400">{formatFileSize(lightboxImage.size)}</p>
            </div>
          </div>
        </div>
      )}

      {/* File Editor / Viewer Modal */}
      <FileEditorModal
        isOpen={Boolean(editingFile)}
        attachment={editingFile}
        activeProfile={activeProfile}
        onClose={() => setEditingFile(null)}
        onSave={() => setEditingFile(null)}
      />
    </>
  )
}
export default ChatMessage
