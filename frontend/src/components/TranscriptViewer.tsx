import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Terminal,
  Download,
  RefreshCw,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  Brain,
  Wrench,
  User,
  ArrowLeft,
  FileCode,
  CheckCircle2,
  Clock,
} from 'lucide-react'
import type { AntigravityDetail, AntigravityTurn } from '../types'

interface TranscriptViewerProps {
  conversationId: string
  onBackToChat: () => void
}

export const TranscriptViewer: React.FC<TranscriptViewerProps> = ({
  conversationId,
  onBackToChat,
}) => {
  const [data, setData] = useState<AntigravityDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copiedId, setCopiedId] = useState(false)
  const [expandedThoughts, setExpandedThoughts] = useState<Record<number, boolean>>({})
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>({})

  const fetchTranscript = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/antigravity/conversations/${conversationId}`)
      if (!res.ok) throw new Error(`HTTP error ${res.status}`)
      const json = await res.json()
      if (json.ok) {
        setData(json)
      } else {
        setError(json.error || 'Failed to load transcript')
      }
    } catch (e: any) {
      setError(e.message || 'Error fetching transcript')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTranscript()
  }, [conversationId])

  const handleCopyId = () => {
    navigator.clipboard.writeText(conversationId)
    setCopiedId(true)
    setTimeout(() => setCopiedId(false), 2000)
  }

  const toggleThought = (idx: number) => {
    setExpandedThoughts(prev => ({ ...prev, [idx]: !prev[idx] }))
  }

  const toggleTool = (toolKey: string) => {
    setExpandedTools(prev => ({ ...prev, [toolKey]: !prev[toolKey] }))
  }

  const handleExport = (format: 'md' | 'json') => {
    window.open(`/api/antigravity/conversations/${conversationId}/export?format=${format}`, '_blank')
  }

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-emerald-400">
        <RefreshCw className="w-8 h-8 animate-spin mb-3 text-emerald-400/80" />
        <p className="text-sm font-medium">Loading Antigravity session...</p>
        <p className="text-xs text-emerald-500/60 mt-1 font-mono">{conversationId}</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-rose-300">
        <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/80 max-w-md text-center">
          <p className="text-sm font-semibold mb-1">Failed to load conversation</p>
          <p className="text-xs text-rose-300/70 mb-4">{error || 'Unknown error'}</p>
          <div className="flex justify-center gap-2">
            <button
              onClick={fetchTranscript}
              className="px-3 py-1.5 rounded-xl bg-emerald-800 hover:bg-emerald-700 text-xs font-medium text-white transition-colors cursor-pointer"
            >
              Retry
            </button>
            <button
              onClick={onBackToChat}
              className="px-3 py-1.5 rounded-xl bg-neutral-800 hover:bg-neutral-700 text-xs font-medium text-white transition-colors cursor-pointer"
            >
              Back to Chat
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col bg-[var(--bg-dark)] text-neutral-100 select-text">
      {/* Top Banner / Details Header */}
      <div className="sticky top-0 z-20 bg-[var(--card-dark)]/95 backdrop-blur-md border-b border-[var(--border-dark)] px-4 py-3 flex flex-wrap items-center justify-between gap-3 shadow-md shadow-black/40">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBackToChat}
            title="Back to live chat"
            className="p-1.5 rounded-xl bg-[var(--card-hover)] hover:bg-[var(--accent)] hover:text-white text-[var(--accent-light)] transition-colors cursor-pointer flex items-center gap-1.5 text-xs font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="hidden sm:inline">Back</span>
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-bold text-white truncate">{data.title}</h1>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-[var(--bg-dark)] border border-[var(--border-dark)] text-[var(--accent-light)]">
                Antigravity
              </span>
            </div>

            <div className="flex items-center gap-3 text-[11px] text-neutral-400 mt-0.5">
              <button
                onClick={handleCopyId}
                title="Click to copy Conversation ID"
                className="font-mono hover:text-white transition-colors flex items-center gap-1 cursor-pointer"
              >
                <span>{conversationId.slice(0, 8)}...</span>
                {copiedId ? <Check className="w-3 h-3 text-[var(--accent-light)]" /> : <Copy className="w-3 h-3 opacity-60" />}
              </button>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {new Date(data.updated_at).toLocaleDateString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </span>
            </div>
          </div>
        </div>

        {/* Header Action Tools */}
        <div className="flex items-center gap-2">
          {/* Summary Pills */}
          <div className="hidden md:flex items-center gap-2 text-[11px] mr-2">
            <span className="px-2 py-0.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] text-[var(--accent-light)] font-medium">
              {data.turn_count} turns
            </span>
            <span className="px-2 py-0.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] text-[var(--accent-light)] font-medium">
              {data.tool_call_count} tool calls
            </span>
          </div>

          <button
            onClick={() => handleExport('md')}
            title="Export full transcript as Markdown"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-xs font-medium text-[var(--accent-light)] hover:text-white transition-all cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden xs:inline">Markdown</span>
          </button>

          <button
            onClick={() => handleExport('json')}
            title="Export raw JSON transcript"
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-xs font-medium text-[var(--accent-light)] hover:text-white transition-all cursor-pointer"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span className="hidden xs:inline">JSON</span>
          </button>

          <button
            onClick={fetchTranscript}
            title="Refresh transcript"
            className="p-1.5 rounded-xl bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-[var(--accent-light)] hover:text-white transition-all cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Main Conversation Feed */}
      <div className="w-full max-w-4xl mx-auto py-6 px-3 sm:px-6 space-y-6">
        {data.turns.length === 0 ? (
          <div className="text-center py-12 text-neutral-400">
            <Terminal className="w-12 h-12 mx-auto mb-3 opacity-30" />
            <p>No turns recorded in this session yet.</p>
          </div>
        ) : (
          data.turns.map((turn: AntigravityTurn, tIdx: number) => {
            const hasThoughts = turn.thoughts && turn.thoughts.length > 0
            const hasTools = turn.tool_calls && turn.tool_calls.length > 0
            const isThoughtExpanded = expandedThoughts[tIdx] ?? false

            return (
              <div
                key={tIdx}
                className="space-y-4 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] p-4 sm:p-5 shadow-sm shadow-black/30"
              >
                {/* Turn Header / Index Pill */}
                <div className="flex items-center justify-between pb-2 border-b border-[var(--border-dark)] text-[11px] text-neutral-400">
                  <span className="font-semibold text-[var(--accent-light)] flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
                    Turn #{turn.turn_index || tIdx + 1}
                  </span>
                  {turn.created_at && (
                    <span>
                      {new Date(turn.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                  )}
                </div>

                {/* 👤 User Message */}
                <div className="flex items-start gap-3">
                  <div className="flex-none w-7 h-7 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] border border-[var(--accent-light)]/40 flex items-center justify-center text-xs font-semibold text-white mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                  <div className="flex-1 rounded-2xl bg-[var(--card-hover)] border border-[var(--border-dark)] px-4 py-3 text-sm text-white shadow-sm">
                    <div className="font-medium whitespace-pre-wrap leading-relaxed">
                      {turn.user.text}
                    </div>
                  </div>
                </div>

                {/* 🧠 Thinking / Chain of Thought Accordion */}
                {hasThoughts && (
                  <div className="pl-10">
                    <div className="rounded-xl border border-indigo-900/60 bg-[#0d1624]/80 overflow-hidden">
                      <button
                        onClick={() => toggleThought(tIdx)}
                        className="w-full px-3 py-2 flex items-center justify-between text-xs font-medium text-indigo-300 hover:text-indigo-100 hover:bg-indigo-950/40 transition-colors cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          <Brain className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Thought Process & Reasoning</span>
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 font-mono">
                            {turn.thoughts.length} steps
                          </span>
                        </div>
                        {isThoughtExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>

                      {isThoughtExpanded && (
                        <div className="p-3 pt-1 border-t border-indigo-950/80 space-y-2 text-xs font-mono text-indigo-200/90 leading-relaxed bg-[#080d16]">
                          {turn.thoughts.map((th, thIdx) => (
                            <div key={thIdx} className="whitespace-pre-wrap opacity-90">
                              {th.text}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* ⚡ Tool Execution Badges */}
                {hasTools && (
                  <div className="pl-10 space-y-2">
                    <div className="text-[11px] font-semibold text-[var(--accent-light)] flex items-center gap-1.5">
                      <Wrench className="w-3 h-3 text-[var(--accent)]" />
                      <span>Tool Calls ({turn.tool_calls.length})</span>
                    </div>

                    <div className="space-y-2">
                      {turn.tool_calls.map((tool, tcIdx) => {
                        const toolKey = `${tIdx}-${tcIdx}`
                        const isExpanded = expandedTools[toolKey] ?? false
                        const hasResult = tool.result !== null && tool.result !== undefined

                        return (
                          <div
                            key={tcIdx}
                            className="rounded-xl border border-[var(--border-dark)] bg-[var(--card-hover)] overflow-hidden text-xs"
                          >
                            <button
                              onClick={() => toggleTool(toolKey)}
                              className="w-full px-3 py-2 flex items-center justify-between hover:bg-[var(--card-dark)] transition-colors cursor-pointer text-left select-none"
                            >
                              <div className="flex items-center gap-2 flex-wrap min-w-0">
                                <span className="font-mono font-bold text-[var(--accent-light)]">{tool.name}</span>
                                {tool.summary && (
                                  <span className="text-[11px] text-neutral-300 truncate">
                                    {tool.summary.replace(/^"|"$/g, '')}
                                  </span>
                                )}
                              </div>

                              <div className="flex items-center gap-2 flex-none ml-2">
                                {hasResult && (
                                  <span className="text-[10px] text-[var(--accent-light)] flex items-center gap-1 font-medium">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Done
                                  </span>
                                )}
                                {isExpanded ? <ChevronUp className="w-3.5 h-3.5 text-[var(--accent-light)]" /> : <ChevronDown className="w-3.5 h-3.5 text-[var(--accent-light)]" />}
                              </div>
                            </button>

                            {isExpanded && (
                              <div className="p-3 border-t border-[var(--border-dark)] bg-[var(--bg-dark)] space-y-2 font-mono text-[11px]">
                                {tool.args && (
                                  <div>
                                    <div className="text-[10px] uppercase font-bold text-neutral-400 mb-1">
                                      Arguments
                                    </div>
                                    <pre className="p-2 rounded bg-black/40 text-neutral-200 overflow-x-auto border border-[var(--border-dark)]">
                                      {typeof tool.args === 'string'
                                        ? tool.args
                                        : JSON.stringify(tool.args, null, 2)}
                                    </pre>
                                  </div>
                                )}

                                {hasResult && (
                                  <div>
                                    <div className="text-[10px] uppercase font-bold text-[var(--accent-light)]/80 mb-1">
                                      Result Output
                                    </div>
                                    <pre className="p-2 rounded bg-black/40 text-neutral-200 overflow-x-auto max-h-60 border border-[var(--border-dark)] whitespace-pre-wrap">
                                      {String(tool.result)}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* 🤖 Assistant Response */}
                {turn.assistant_replies && turn.assistant_replies.length > 0 && (
                  <div className="flex items-start gap-3">
                    <div className="flex-none w-7 h-7 sm:w-8 sm:h-8 rounded-xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-hover)] flex items-center justify-center text-sm sm:text-base shadow-sm mt-0.5">
                      🦖
                    </div>
                    <div className="flex-1 rounded-2xl bg-[var(--card-dark)] border border-[var(--border-dark)] px-4 py-3.5 text-sm text-neutral-100 shadow-sm">
                      {turn.assistant_replies.map((reply, rIdx) => (
                        <div key={rIdx} className="prose prose-invert max-w-none break-words text-[13.5px] sm:text-sm leading-relaxed">
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
                              ul: ({ children }) => <ul className="my-2 space-y-1 list-disc list-inside">{children}</ul>,
                              ol: ({ children }) => <ol className="my-2 space-y-1 list-decimal list-inside">{children}</ol>,
                              pre({ children }) {
                                return <>{children}</>
                              },
                              code({ className, children, ...props }: any) {
                                const match = /language-(\w+)/.exec(className || '')
                                const rawString = String(children).replace(/\n$/, '')
                                const isBlock = Boolean(match) || rawString.includes('\n')

                                if (isBlock) {
                                  return (
                                    <div className="relative my-2.5 rounded-xl overflow-hidden bg-[var(--bg-dark)] border border-[var(--border-dark)] shadow-md shadow-black/40">
                                      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[var(--card-dark)] border-b border-[var(--border-dark)] text-[11px] select-none">
                                        <span className="font-mono font-semibold text-[var(--accent-light)] lowercase">
                                          {match ? match[1] : 'code'}
                                        </span>
                                        <button
                                          onClick={() => {
                                            navigator.clipboard.writeText(rawString)
                                          }}
                                          type="button"
                                          className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-semibold text-white bg-[var(--card-hover)] hover:bg-[var(--accent)] border border-[var(--border-dark)] transition-all cursor-pointer active:scale-95 shadow-xs"
                                          title="Copy code"
                                        >
                                          <Copy className="w-3 h-3 text-[var(--accent-light)]/80" />
                                          <span>Copy</span>
                                        </button>
                                      </div>
                                      <pre className="p-3.5 text-[12px] sm:text-[12.5px] overflow-x-auto font-mono text-neutral-100 leading-relaxed whitespace-pre">
                                        <code>{rawString}</code>
                                      </pre>
                                    </div>
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
                            {reply.text}
                          </ReactMarkdown>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
