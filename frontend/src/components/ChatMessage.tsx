import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
} from 'lucide-react'
import type { Message, ChatAttachment } from '../types'
import { playNeuralSpeech, stopSpeech } from '../utils/audio'
import { FileEditorModal } from './FileEditorModal'

interface ChatMessageProps {
  message: Message
  assistantEmoji?: string
  activeProfile?: string
}

// Standalone clean Code Block with dedicated Copy button
const CodeBlock: React.FC<{
  language?: string
  children: string
}> = ({ language, children }) => {
  const [copied, setCopied] = useState(false)

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative my-2.5 rounded-xl overflow-hidden bg-[var(--bg-dark)] border border-[var(--border-dark)] shadow-md shadow-black/40">
      {/* Code Header Bar */}
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[var(--card-dark)] border-b border-[var(--border-dark)] text-[11px] select-none">
        <span className="font-mono font-semibold text-[var(--accent-light)] lowercase tracking-wide">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          type="button"
          className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold text-white bg-[var(--card-hover)] hover:bg-[var(--accent)] border border-[var(--border-dark)] transition-all cursor-pointer active:scale-95 shadow-xs"
          title="Copy code to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-[var(--accent-light)]" />
              <span className="text-[var(--accent-light)] font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 text-[var(--accent-light)]/80" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Text */}
      <pre className="p-3.5 text-[12px] sm:text-[12.5px] overflow-x-auto font-mono text-neutral-100 leading-relaxed whitespace-pre">
        <code>{children}</code>
      </pre>
    </div>
  )
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  assistantEmoji = '🦖',
  activeProfile = 'Hermes',
}) => {
  const isAssistant = message.role === 'assistant'
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [lightboxImage, setLightboxImage] = useState<ChatAttachment | null>(null)
  const [editingFile, setEditingFile] = useState<ChatAttachment | null>(null)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content)
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

    if (!message.content.trim()) return

    setIsSynthesizing(true)
    try {
      await playNeuralSpeech(message.content, {
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
      return download ? `${att.url}&download=1` : att.url
    }
    return `/chat-attachment/${att.id}?profile=${encodeURIComponent(activeProfile)}${download ? '&download=1' : ''}`
  }

  const images = message.attachments?.filter(a => a.kind === 'image') || []
  const files = message.attachments?.filter(a => a.kind !== 'image') || []

  return (
    <>
      <div
        className={`group w-full py-1.5 px-3 sm:px-4 flex gap-2.5 sm:gap-3 transition-colors ${
          isUser ? 'justify-end' : 'justify-start'
        }`}
      >
        {/* Assistant Avatar */}
        {isAssistant && (
          <div className="flex-none w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] flex items-center justify-center text-sm sm:text-base shadow-sm mt-0.5">
            {assistantEmoji}
          </div>
        )}

        {/* Message Bubble */}
        <div
          style={{
            borderRadius: 'var(--bubble-radius, 1.25rem)',
            fontSize: 'var(--chat-font-size, 14.5px)',
            background: isUser ? 'var(--user-bubble)' : message.error ? undefined : 'var(--bot-bubble)',
            borderColor: isUser ? undefined : message.error ? undefined : 'var(--bot-border)',
          }}
          className={`relative max-w-[92%] sm:max-w-[85%] px-4 py-3 leading-relaxed ${
            isUser
              ? 'text-white shadow-md'
              : message.error
              ? 'bg-rose-950/50 border border-rose-800 text-rose-200'
              : 'border text-white shadow-sm'
          }`}
        >
          {/* Attached Images Grid */}
          {images.length > 0 && (
            <div
              className={`mb-2.5 gap-2 grid ${
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
                    className="group/img relative rounded-xl overflow-hidden bg-black/40 border border-white/10 hover:border-[var(--accent)] cursor-pointer transition-all shadow-sm max-h-[260px] flex items-center justify-center"
                  >
                    <img
                      src={src}
                      alt={img.name}
                      loading="lazy"
                      className="w-full h-full object-cover group-hover/img:scale-105 transition-transform duration-200"
                    />
                    <div className="absolute inset-0 bg-black/30 opacity-0 group-hover/img:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <span className="p-1.5 rounded-lg bg-black/60 text-white shadow backdrop-blur-xs">
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
            <div className="mb-2.5 flex flex-col gap-1.5">
              {files.map(f => (
                <div
                  key={f.id}
                  className="flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-[var(--bg-dark)]/60 border border-[var(--border-dark)] hover:border-[var(--accent)]/50 transition-all text-xs"
                >
                  <div
                    onClick={() => setEditingFile(f)}
                    className="flex items-center gap-2.5 min-w-0 cursor-pointer hover:opacity-90"
                  >
                    <div className="p-1.5 rounded-lg bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent-light)] flex-none">
                      {f.name.endsWith('.py') || f.name.endsWith('.js') || f.name.endsWith('.json') || f.name.endsWith('.html') ? (
                        <FileCode className="w-4 h-4" />
                      ) : (
                        <FileText className="w-4 h-4" />
                      )}
                    </div>
                    <div className="flex flex-col min-w-0">
                      <span className="font-medium text-white truncate max-w-[180px] sm:max-w-[280px]">
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
                      className="p-1.5 rounded-lg bg-[var(--card-hover)] hover:bg-[var(--accent)] text-neutral-300 hover:text-white transition-all flex-none cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <a
                      href={getAttachmentUrl(f, true)}
                      download={f.name}
                      title="Download file"
                      className="p-1.5 rounded-lg bg-[var(--card-hover)] hover:bg-[var(--accent)] text-neutral-300 hover:text-white transition-all flex-none"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Message Content */}
          {message.pending ? (
            <div className="flex items-center gap-2 text-[var(--accent-light)] py-1">
              <span className="w-2 h-2 rounded-full bg-[var(--accent)] animate-ping" />
              <span className="text-xs font-medium">Doshie is thinking...</span>
            </div>
          ) : (
            message.content && (
              <div className="prose prose-invert max-w-none break-words text-[13.5px] sm:text-sm leading-relaxed">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
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
                          className="inline-flex items-baseline gap-1 text-[var(--accent-light)] hover:text-white underline underline-offset-2 decoration-[var(--accent)]/50 hover:decoration-[var(--accent-light)] font-medium transition-colors cursor-pointer"
                        >
                          <span>{children}</span>
                          <span className="text-[10px] opacity-70">↗</span>
                        </a>
                      )
                    },
                    ul: ({ children }) => (
                      <ul className="my-2 space-y-1.5 list-disc list-inside text-neutral-100">{children}</ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="my-2 space-y-2 list-decimal list-inside text-neutral-100">{children}</ol>
                    ),
                    li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                    strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                    blockquote: ({ children }) => (
                      <blockquote className="border-l-2 border-[var(--accent)] pl-3 my-2 text-[var(--accent-light)] italic bg-[var(--card-dark)]/40 py-1 rounded-r">
                        {children}
                      </blockquote>
                    ),
                    h1: ({ children }) => <h1 className="text-base font-bold text-white mt-3 mb-1.5 first:mt-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-sm font-bold text-white mt-2.5 mb-1 first:mt-0">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-xs font-semibold text-[var(--accent-light)] mt-2 mb-1 first:mt-0">{children}</h3>,
                    pre({ children }) {
                      return <>{children}</>
                    },
                    code({ className, children, ...props }: any) {
                      const match = /language-(\w+)/.exec(className || '')
                      const rawString = String(children).replace(/\n$/, '')
                      const isBlock = Boolean(match) || rawString.includes('\n')

                      if (isBlock) {
                        return (
                          <CodeBlock language={match ? match[1] : undefined}>
                            {rawString}
                          </CodeBlock>
                        )
                      }

                      return (
                        <code
                          className="inline-block px-1.5 py-0.5 mx-0.5 rounded bg-[var(--card-dark)] text-[var(--accent-light)] font-mono text-[12px] border border-[var(--border-dark)] align-baseline font-medium"
                          {...props}
                        >
                          {children}
                        </code>
                      )
                    },
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )
          )}

          {/* Footer info, Listen & Copy buttons */}
          {!message.pending && (
            <div
              className={`mt-2 pt-1 border-t border-[var(--border-dark)]/50 flex items-center gap-2 text-[10px] ${
                isUser ? 'text-white/80 justify-end' : 'text-neutral-400 justify-between'
              }`}
            >
              <span>{formatTime(message.timestamp)}</span>

              {isAssistant && message.content && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={handleToggleSpeak}
                    title={
                      isSynthesizing
                        ? 'Generating cloned voice...'
                        : isPlayingAudio
                        ? 'Stop reading'
                        : 'Read aloud with cloned voice'
                    }
                    className={`p-1 rounded transition-all cursor-pointer flex items-center gap-1 ${
                      isSynthesizing
                        ? 'text-[var(--accent-light)] bg-[var(--card-hover)]'
                        : isPlayingAudio
                        ? 'text-[var(--accent-light)] bg-[var(--card-dark)] animate-pulse'
                        : 'text-neutral-400 hover:text-[var(--accent-light)] hover:bg-[var(--card-hover)]'
                    }`}
                  >
                    {isSynthesizing ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--accent)]" />
                    ) : isPlayingAudio ? (
                      <VolumeX className="w-3.5 h-3.5" />
                    ) : (
                      <Volume2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                  <button
                    onClick={handleCopy}
                    title="Copy full response"
                    className="p-1 rounded text-neutral-400 hover:text-white hover:bg-[var(--card-hover)] transition-colors cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-[var(--accent-light)]" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User Avatar */}
        {isUser && (
          <div className="flex-none w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] border border-[var(--accent-light)]/40 flex items-center justify-center text-xs font-semibold text-white shadow-sm mt-0.5">
            <User className="w-4 h-4" />
          </div>
        )}
      </div>

      {/* Fullscreen Image Lightbox Modal */}
      {lightboxImage && (
        <div
          onClick={() => setLightboxImage(null)}
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex flex-col items-center justify-center p-4 animate-fadeIn"
        >
          <div className="absolute top-4 right-4 flex items-center gap-3">
            <a
              href={getAttachmentUrl(lightboxImage, true)}
              download={lightboxImage.name}
              onClick={e => e.stopPropagation()}
              className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors flex items-center gap-1.5 text-xs font-medium"
              title="Download image"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </a>
            <button
              onClick={() => setLightboxImage(null)}
              className="p-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors cursor-pointer"
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
              className="max-w-full max-h-[78vh] object-contain rounded-2xl shadow-2xl border border-white/10"
            />
            <div className="mt-3 text-center">
              <p className="text-sm font-medium text-white">{lightboxImage.name}</p>
              <p className="text-xs text-neutral-400">{formatFileSize(lightboxImage.size)}</p>
            </div>
          </div>
        </div>
      )}

      {/* File Editor / Viewer Modal for attachments */}
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
