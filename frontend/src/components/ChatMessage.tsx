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
  Calculator,
  BookOpen,
  Search,
  Cpu,
  Database,
  Bot,
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

// Standalone Syntax-Highlighted Code Block with Antigravity Approval Flow
const CodeBlock: React.FC<{
  language?: string
  children: string
  activeProfile?: string
}> = ({ language, children, activeProfile = 'Hermes' }) => {
  const [copied, setCopied] = useState(false)
  const [wrap, setWrap] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [isDeclined, setIsDeclined] = useState(false)
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
  const isPython = ['python', 'py', 'python3'].includes(lang)
  const isExecutable = isShellCommand || isPython

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
    setIsDeclined(false)
    setExecResult(null)
    setShowOutput(true)
    try {
      let commandToRun = children.trim()
      if (isPython) {
        commandToRun = `python3 -c ${JSON.stringify(children.trim())}`
      }
      const res = await fetch('/api/execute-command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command: commandToRun,
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
    <div className="relative my-3 rounded-xl overflow-hidden bg-[#09090b] border border-[#27272a] shadow-lg shadow-black/60 group/code">
      {/* Title Bar */}
      <div className="flex items-center justify-between px-3.5 py-2 bg-[#121215] border-b border-[#27272a] text-[11px] select-none">
        <div className="flex items-center gap-2">
          {/* Terminal / Code Icon & Language Badge */}
          <Terminal className="w-3.5 h-3.5 text-neutral-400 flex-none" />
          <span className="font-mono font-semibold text-white px-2 py-0.5 rounded bg-white/10 border border-white/10 uppercase text-[10px] tracking-wider">
            {displayLang}
          </span>

          {isExecutable && (
            <span className="font-medium text-neutral-300 text-[11px]">
              {isShellCommand ? 'Shell Command' : 'Python Script'}
            </span>
          )}

          {lineCount > 1 && (
            <span className="hidden sm:inline-block text-[10px] text-neutral-500 font-mono">
              {lineCount} lines
            </span>
          )}
        </div>

        {/* Status Pill & Actions */}
        <div className="flex items-center gap-2">
          {/* Status Badge */}
          {isRunning ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-sky-400 bg-sky-950/40 border border-sky-500/30 px-2 py-0.5 rounded">
              <Loader2 className="w-2.5 h-2.5 animate-spin text-sky-400" />
              <span>Running...</span>
            </span>
          ) : execResult ? (
            execResult.ok ? (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-500/30 px-2 py-0.5 rounded">
                <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                <span>exit 0</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-rose-400 bg-rose-950/40 border border-rose-500/30 px-2 py-0.5 rounded">
                <AlertTriangle className="w-2.5 h-2.5 text-rose-400" />
                <span>exit {execResult.exit_code ?? 1}</span>
              </span>
            )
          ) : isDeclined ? (
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/5 border border-white/10 text-neutral-400">
              Declined
            </span>
          ) : isExecutable ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-amber-300 bg-amber-950/40 border border-amber-500/30 px-2 py-0.5 rounded">
              Awaiting Approval
            </span>
          ) : null}

          {/* Wrap Toggle */}
          <button
            onClick={() => setWrap(!wrap)}
            type="button"
            className={`p-1 rounded border text-[11px] transition-all cursor-pointer ${
              wrap
                ? 'bg-white/20 border-white/30 text-white'
                : 'bg-white/5 hover:bg-white/10 border-white/10 text-neutral-400 hover:text-white'
            }`}
            title={wrap ? 'Disable wrap' : 'Enable wrap'}
          >
            <WrapText className="w-3 h-3" />
          </button>

          {/* Copy */}
          <button
            onClick={handleCopy}
            type="button"
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium text-neutral-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all cursor-pointer active:scale-95"
            title="Copy code"
          >
            {copied ? (
              <>
                <Check className="w-3 h-3 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3 text-neutral-400" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Code Text Area */}
      <pre
        className={`p-3.5 text-[12.5px] sm:text-[13px] font-mono leading-relaxed text-neutral-100 bg-[#09090b] ${
          wrap ? 'whitespace-pre-wrap break-words' : 'overflow-x-auto whitespace-pre'
        }`}
      >
        <code
          className={`language-${displayLang}`}
          dangerouslySetInnerHTML={{ __html: highlightedHtml }}
        />
      </pre>

      {/* Antigravity Approval Bar (Interactive Host Execution) */}
      {isExecutable && (
        <div className="flex items-center justify-between px-3.5 py-2 bg-[#0e1015] border-t border-[#27272a] text-xs select-none">
          {!execResult && !isDeclined ? (
            <>
              <div className="flex items-center gap-2 text-neutral-400 font-mono text-[11px]">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse inline-block" />
                <span>Workstation: <strong className="text-neutral-200">acer-nitro</strong></span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsDeclined(true)}
                  disabled={isRunning}
                  className="px-2.5 py-1 rounded text-xs font-medium text-neutral-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors cursor-pointer"
                >
                  Decline
                </button>
                <button
                  type="button"
                  onClick={handleRunCommand}
                  disabled={isRunning}
                  className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-semibold text-emerald-950 bg-emerald-400 hover:bg-emerald-300 transition-all shadow-sm shadow-emerald-500/20 active:scale-95 cursor-pointer disabled:opacity-50"
                  title="Approve and execute on host machine"
                >
                  {isRunning ? (
                    <>
                      <Loader2 className="w-3 h-3 animate-spin text-emerald-950" />
                      <span>Executing...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3 h-3 text-emerald-950 fill-emerald-950" />
                      <span>Approve & Run</span>
                    </>
                  )}
                </button>
              </div>
            </>
          ) : isDeclined ? (
            <>
              <span className="text-[11px] text-neutral-400 font-mono">Execution declined by user</span>
              <button
                type="button"
                onClick={() => {
                  setIsDeclined(false)
                  handleRunCommand()
                }}
                className="text-[11px] text-emerald-400 hover:underline cursor-pointer font-medium"
              >
                Approve & Run anyway
              </button>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-[11px] font-mono text-neutral-400">
                <span>Executed in {execResult?.duration ?? 0}s</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowOutput(!showOutput)}
                  className="text-[11px] font-mono text-neutral-400 hover:text-white transition-colors cursor-pointer"
                >
                  {showOutput ? 'Hide Output' : 'Show Output'}
                </button>
                <button
                  type="button"
                  onClick={handleRunCommand}
                  disabled={isRunning}
                  className="flex items-center gap-1 text-[11px] font-medium text-neutral-300 hover:text-white px-2 py-0.5 rounded bg-white/5 hover:bg-white/10 border border-white/10 transition-colors cursor-pointer"
                >
                  <RotateCw className="w-3 h-3" />
                  <span>Re-run</span>
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Live Terminal Output Drawer */}
      {execResult && showOutput && (
        <div className="border-t border-[#27272a] bg-[#05070a] p-3 text-xs font-mono">
          <div className="max-h-60 overflow-y-auto whitespace-pre-wrap rounded-lg bg-black/90 p-2.5 text-neutral-200 select-text border border-white/5">
            {execResult.stdout && <div>{execResult.stdout}</div>}
            {execResult.stderr && <div className="text-rose-400">{execResult.stderr}</div>}
            {execResult.error && <div className="text-rose-400">{execResult.error}</div>}
            {!execResult.stdout && !execResult.stderr && !execResult.error && (
              <div className="text-neutral-500 italic">(Command executed successfully with no output)</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Antigravity Tool Icon Resolver
const ToolIcon: React.FC<{ tool: string }> = ({ tool }) => {
  const t = (tool || '').toLowerCase()
  if (t.includes('calc') || t.includes('math')) return <Calculator className="w-3.5 h-3.5 text-amber-400" />
  if (t.includes('wiki') || t.includes('book')) return <BookOpen className="w-3.5 h-3.5 text-sky-400" />
  if (t.includes('search') || t.includes('web')) return <Search className="w-3.5 h-3.5 text-teal-400" />
  if (t.includes('terminal') || t.includes('command') || t.includes('cli') || t.includes('diagnost')) return <Terminal className="w-3.5 h-3.5 text-emerald-400" />
  if (t.includes('code') || t.includes('file') || t.includes('edit')) return <FileCode className="w-3.5 h-3.5 text-indigo-400" />
  if (t.includes('delete') || t.includes('remove') || t.includes('trash')) return <Trash2 className="w-3.5 h-3.5 text-rose-400" />
  if (t.includes('hard') || t.includes('cpu') || t.includes('gpu') || t.includes('governor')) return <Cpu className="w-3.5 h-3.5 text-cyan-400" />
  if (t.includes('memo') || t.includes('task') || t.includes('note')) return <Database className="w-3.5 h-3.5 text-purple-400" />
  if (t.includes('agent') || t.includes('hermes')) return <Bot className="w-3.5 h-3.5 text-violet-400" />
  return <Wrench className="w-3.5 h-3.5 text-neutral-400" />
}

// Antigravity Step Card Component
const AntigravityStepCard: React.FC<{
  step: {
    tool: string
    title?: string
    arguments?: any
    result?: any
    ok?: boolean
    duration_ms?: number
    preview?: string
    thought?: string
  }
  index: number
  defaultExpanded?: boolean
}> = ({ step, index, defaultExpanded = false }) => {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [copiedInput, setCopiedInput] = useState(false)
  const [copiedOutput, setCopiedOutput] = useState(false)

  const toolName = (step.tool || '').toLowerCase()
  const title = step.title || step.tool.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())

  // Quick summary string for the header pill
  const quickParam = useMemo(() => {
    if (!step.arguments) return ''
    if (typeof step.arguments === 'string') return step.arguments.slice(0, 52)
    if (step.arguments.code) return String(step.arguments.code).slice(0, 52)
    if (step.arguments.expression) return String(step.arguments.expression).slice(0, 52)
    if (step.arguments.query) return `"${String(step.arguments.query).slice(0, 38)}"`
    if (step.arguments.command) return String(step.arguments.command).slice(0, 52)
    if (step.arguments.relative_path) return String(step.arguments.relative_path)
    if (step.arguments.fact) return `"${String(step.arguments.fact).slice(0, 38)}"`
    if (step.arguments.note) return `"${String(step.arguments.note).slice(0, 38)}"`
    if (step.arguments.component) return String(step.arguments.component)
    return ''
  }, [step.arguments])

  const formatPayload = (val: any): string => {
    if (val === null || val === undefined) return ''
    if (typeof val === 'string') return val
    try {
      return JSON.stringify(val, null, 2)
    } catch {
      return String(val)
    }
  }

  const inputStr = useMemo(() => formatPayload(step.arguments), [step.arguments])
  const outputStr = useMemo(() => {
    if (step.result && typeof step.result === 'object') {
      if (step.result.stdout !== undefined) {
        let out = step.result.stdout || ''
        if (step.result.stderr) out += (out ? '\n' : '') + '[stderr]: ' + step.result.stderr
        if (!out && step.result.result) out = String(step.result.result)
        return out || '(Execution returned empty stdout)'
      }
      if (step.result.summary !== undefined) {
        let out = ''
        if (step.result.title) out += `### ${step.result.title}\n`
        if (step.result.description) out += `*${step.result.description}*\n\n`
        out += step.result.summary
        if (step.result.url) out += `\n\nLink: ${step.result.url}`
        return out
      }
      if (step.result.error) return String(step.result.error)
    }
    return formatPayload(step.result)
  }, [step.result])

  const handleCopyInput = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(inputStr)
    setCopiedInput(true)
    setTimeout(() => setCopiedInput(false), 2000)
  }

  const handleCopyOutput = (e: React.MouseEvent) => {
    e.stopPropagation()
    navigator.clipboard.writeText(outputStr)
    setCopiedOutput(true)
    setTimeout(() => setCopiedOutput(false), 2000)
  }

  return (
    <div className="rounded-xl border border-white/10 bg-[#0f141c]/90 overflow-hidden shadow-sm shadow-black/40 mb-2 transition-all hover:border-white/20">
      {/* Step Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3 py-2 flex items-center justify-between text-xs hover:bg-white/[0.04] transition-colors cursor-pointer select-none gap-2"
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Step Number Badge */}
          <span className="w-4 h-4 rounded-full bg-white/10 text-[10px] font-mono text-neutral-300 flex items-center justify-center flex-none font-bold">
            {index + 1}
          </span>

          {/* Tool Icon */}
          <div className="p-1 rounded-md bg-black/40 border border-white/10 flex-none">
            <ToolIcon tool={toolName} />
          </div>

          {/* Action Title */}
          <span className="font-semibold text-white truncate text-[12px] tracking-wide">
            {title}
          </span>

          {/* Quick Param Preview */}
          {quickParam && (
            <span className="hidden sm:inline-block font-mono text-[10.5px] text-neutral-300 bg-black/40 px-2 py-0.5 rounded border border-white/5 truncate max-w-[280px]">
              {quickParam}
            </span>
          )}
        </div>

        {/* Right Status Badge */}
        <div className="flex items-center gap-2 flex-none">
          {step.ok !== false ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-emerald-400 bg-emerald-950/60 border border-emerald-500/30 px-2 py-0.5 rounded-full">
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
              <span>{step.duration_ms ? `${step.duration_ms}ms` : 'Done'}</span>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium text-rose-400 bg-rose-950/60 border border-rose-500/30 px-2 py-0.5 rounded-full">
              <AlertTriangle className="w-3 h-3 text-rose-400" />
              <span>Error</span>
            </span>
          )}

          {expanded ? (
            <ChevronUp className="w-3.5 h-3.5 text-neutral-400 hover:text-white transition-colors" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5 text-neutral-400 hover:text-white transition-colors" />
          )}
        </div>
      </div>

      {/* Expanded Accordion Drawer */}
      {expanded && (
        <div className="p-3 border-t border-white/10 bg-[#080c13] space-y-2.5 text-xs font-mono">
          {/* Input / Arguments */}
          {inputStr && (
            <div>
              <div className="flex items-center justify-between text-[10px] uppercase font-bold text-neutral-400 mb-1">
                <span>Input Parameters</span>
                <button
                  type="button"
                  onClick={handleCopyInput}
                  className="flex items-center gap-1 text-[10px] text-neutral-400 hover:text-white transition-colors cursor-pointer"
                >
                  {copiedInput ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedInput ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <pre className="p-2.5 rounded-lg bg-black/60 text-neutral-200 border border-white/5 overflow-x-auto whitespace-pre-wrap max-h-48 text-[11px] leading-relaxed">
                {inputStr}
              </pre>
            </div>
          )}

          {/* Result / Output */}
          {outputStr && (
            <div>
              <div className="flex items-center justify-between text-[10px] uppercase font-bold text-[var(--accent-light)] mb-1">
                <span>Execution Output</span>
                <button
                  type="button"
                  onClick={handleCopyOutput}
                  className="flex items-center gap-1 text-[10px] text-neutral-400 hover:text-white transition-colors cursor-pointer"
                >
                  {copiedOutput ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedOutput ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
              <pre className={`p-2.5 rounded-lg bg-black/60 border border-white/5 overflow-x-auto whitespace-pre-wrap max-h-60 text-[11px] leading-relaxed ${
                step.ok === false ? 'text-rose-300' : 'text-emerald-300'
              }`}>
                {outputStr}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Antigravity Multi-Step Trajectory Block
const AntigravityExecutionBlock: React.FC<{
  steps: Array<any>
}> = ({ steps }) => {
  if (!steps || steps.length === 0) return null

  const [allExpanded, setAllExpanded] = useState(false)

  return (
    <div className="my-3 rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-3 shadow-md shadow-black/30">
      <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/10 text-xs font-semibold text-neutral-300">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-white font-bold tracking-wide">Agent Execution Trajectory</span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
            {steps.length} {steps.length === 1 ? 'action' : 'actions'}
          </span>
        </div>
        <button
          type="button"
          onClick={() => setAllExpanded(!allExpanded)}
          className="text-[11px] text-[var(--accent-light)] hover:text-white transition-colors cursor-pointer font-medium"
        >
          {allExpanded ? 'Collapse All' : 'Expand All'}
        </button>
      </div>

      <div className="space-y-1.5">
        {steps.map((st, idx) => (
          <AntigravityStepCard
            key={idx}
            step={st}
            index={idx}
            defaultExpanded={allExpanded}
          />
        ))}
      </div>
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

  const { displayContent, thoughtContent, parsedInlineSteps } = useMemo(() => {
    let content = message.content || ''
    let thought = message.thinking || ''
    const inlineSteps: any[] = []

    const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/i)
    if (thinkMatch) {
      if (!thought) {
        thought = thinkMatch[1].trim()
      }
      content = content.replace(/<think>[\s\S]*?<\/think>/i, '').trim()
    }

    // Check if content contains raw tool call JSON(s) (e.g. from Ollama/local models)
    // 1. Check fenced code blocks
    const jsonBlockRegex = /```(?:json)?\s*(\{[\s\S]*?\})\s*```/gi
    let match: RegExpExecArray | null
    let hasFenced = false
    while ((match = jsonBlockRegex.exec(content)) !== null) {
      try {
        const parsed = JSON.parse(match[1])
        if (parsed.name || parsed.tool || parsed.action) {
          inlineSteps.push({
            tool: parsed.name || parsed.tool || parsed.action,
            title: parsed.title,
            arguments: parsed.arguments || parsed.parameters || parsed.args || {},
            result: parsed.result || parsed.output || '',
            ok: parsed.ok !== false,
          })
          hasFenced = true
        }
      } catch {}
    }
    if (hasFenced) {
      content = content.replace(jsonBlockRegex, '').trim()
    }

    // 2. Also check for raw unfenced JSON objects (single or multiple)
    let depth = 0
    let startIdx = -1
    let cleanedContent = ''
    let lastEnd = 0
    let foundAnyRaw = false

    for (let i = 0; i < content.length; i++) {
      const char = content[i]
      if (char === '{') {
        if (depth === 0) startIdx = i
        depth++
      } else if (char === '}') {
        depth--
        if (depth === 0 && startIdx !== -1) {
          const candidate = content.slice(startIdx, i + 1)
          try {
            const parsed = JSON.parse(candidate)
            if (parsed.name || parsed.tool || parsed.action) {
              inlineSteps.push({
                tool: parsed.name || parsed.tool || parsed.action,
                title: parsed.title,
                arguments: parsed.arguments || parsed.parameters || parsed.args || {},
                result: parsed.result || parsed.output || '',
                ok: parsed.ok !== false,
              })
              cleanedContent += content.slice(lastEnd, startIdx)
              lastEnd = i + 1
              foundAnyRaw = true
            }
          } catch {}
          startIdx = -1
        }
      }
    }
    if (foundAnyRaw) {
      cleanedContent += content.slice(lastEnd)
      content = cleanedContent.trim()
    }

    // If text has inline bullets (e.g. " • " or "• ") that didn't have newlines, normalize them so markdown renders them as proper list items
    if (content.includes('•') && !content.includes('\n•') && !content.includes('\n- ')) {
      content = content.replace(/\s*•\s*/g, '\n- ')
    }

    return { displayContent: content, thoughtContent: thought, parsedInlineSteps: inlineSteps }
  }, [message.content, message.thinking])

  const effectiveSteps = useMemo(() => {
    if (message.steps && message.steps.length > 0) {
      return message.steps
    }
    if (parsedInlineSteps && parsedInlineSteps.length > 0) {
      return parsedInlineSteps
    }
    return []
  }, [message.steps, parsedInlineSteps])

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
          <div className="hidden sm:flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 self-center mr-1 mb-1.5 flex-none select-none bg-[#18181b]/90 border border-white/10 p-1 rounded-xl shadow-xs">
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
                <Edit3 className="w-3.5 h-3.5" />
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
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
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
                {String(message.agent.name || '').toLowerCase() === 'aeriel' ? 'Master Builder' : 'Specialist Agent'}
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

          {/* Thinking / Streaming / Tool Planning Indicator */}
          {message.pending ? (
            <div className="py-2.5 px-3 rounded-xl bg-black/40 border border-[var(--accent)]/30 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 text-[var(--accent-light)] font-mono">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--accent-light)] opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--accent)]"></span>
                  </span>
                  <span className="font-semibold tracking-wide flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-[var(--accent)]" />
                    <span>Doshie is reasoning & planning tools on RTX 5070...</span>
                  </span>
                </div>
                <span className="text-[10px] text-neutral-400 font-mono px-2 py-0.5 rounded bg-white/5 border border-white/5">
                  Running
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
                      <span>Thinking Process & Reasoning</span>
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

              {/* ⚡ Antigravity Agent Execution Trajectory */}
              {effectiveSteps.length > 0 && (
                <AntigravityExecutionBlock steps={effectiveSteps} />
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

                  <div className="flex items-center gap-1.5 bg-[#18181b]/90 border border-white/10 px-1.5 py-0.5 rounded-lg ml-auto">
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
                        className="p-1 rounded-md text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
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
                        className="p-1 rounded-md text-neutral-300 hover:text-white hover:bg-white/10 transition-colors cursor-pointer active:scale-90"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
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
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
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
                    <div className="flex items-center gap-1.5 bg-[#18181b]/90 border border-white/10 px-1.5 py-0.5 rounded-lg">
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
                            ? 'text-sky-300 bg-white/10 border-sky-400/50'
                            : isPlayingAudio
                            ? 'text-sky-300 bg-sky-500/20 border-sky-400 animate-pulse'
                            : 'text-neutral-400 hover:text-white hover:bg-white/10 border-transparent hover:border-white/10'
                        }`}
                      >
                        {isSynthesizing ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-400" />
                        ) : isPlayingAudio ? (
                          <>
                            <VolumeX className="w-3.5 h-3.5" />
                            <span className="text-[10px] font-semibold text-sky-300">Playing</span>
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
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
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
