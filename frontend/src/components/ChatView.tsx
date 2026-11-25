import { useState, useRef, useEffect } from 'react'
import type { FormEvent } from 'react'
import type { ChatMessage } from '../types'
import { Send, Zap, Volume2, VolumeX, Terminal, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ChatViewProps {
  messages: ChatMessage[]
  onSendMessage: (text: string) => void
  loading: boolean
}

export const ChatView = ({
  messages,
  onSendMessage,
  loading
}: ChatViewProps) => {
  const [input, setInput] = useState('')
  const [ttsEnabled, setTtsEnabled] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const isNearBottomRef = useRef(true)

  const handleScroll = () => {
    const el = scrollContainerRef.current
    if (!el) return
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    isNearBottomRef.current = distanceToBottom < 100
  }

  const scrollToBottom = (force = false) => {
    if (force || isNearBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    onSendMessage(input.trim())
    setInput('')
    setTimeout(() => scrollToBottom(true), 50)
  }

  const handleQuickCommand = (cmd: string) => {
    onSendMessage(cmd)
    setTimeout(() => scrollToBottom(true), 50)
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col max-w-4xl mx-auto w-full px-3 sm:px-6 py-2 overflow-hidden">
      
      {/* Quick Action Suggestion Chips */}
      <div className="flex-shrink-0 flex items-center gap-2 overflow-x-auto pb-2 mb-2 text-xs font-mono no-scrollbar touch-pan-x">
        <button
          onClick={() => handleQuickCommand("Hey Doshie, how's everything going with you today? Let's catch up.")}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-400/50 text-cyan-300 hover:bg-cyan-900/50 transition-all cursor-pointer font-sans"
        >
          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          <span>💬 Let's Chat</span>
        </button>

        <button
          onClick={() => handleQuickCommand('Report system status and GPU telemetry.')}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-900/90 border border-cyan-500/30 text-cyan-400 hover:bg-cyan-950/50 transition-all cursor-pointer"
        >
          <Zap className="w-3.5 h-3.5 text-cyan-400" />
          <span>Status Report</span>
        </button>

        <button
          onClick={() => handleQuickCommand('Optimize network routes for low-latency gaming.')}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-900/90 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-950/50 transition-all cursor-pointer"
        >
          <Zap className="w-3.5 h-3.5 text-emerald-400" />
          <span>Optimize Routes</span>
        </button>

        <button
          onClick={() => handleQuickCommand('What is the status of Plex media server?')}
          className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-900/90 border border-zinc-700 text-slate-300 hover:bg-zinc-800 transition-all cursor-pointer"
        >
          <Terminal className="w-3.5 h-3.5 text-slate-400" />
          <span>Check Plex</span>
        </button>
      </div>

      {/* Message History Feed */}
      <div 
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 min-h-0 overflow-y-auto space-y-4 pr-1 overscroll-contain scroll-touch"
        style={{
          WebkitOverflowScrolling: 'touch',
          touchAction: 'pan-y'
        }}
      >
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4">
            <div className="w-14 h-14 rounded-2xl bg-cyan-950/40 border border-cyan-500/30 flex items-center justify-center mb-4 arc-pulse">
              <Zap className="w-7 h-7 text-cyan-400" />
            </div>
            <h2 className="text-lg sm:text-xl font-bold font-mono tracking-wide text-slate-100 glow-cyan mb-1">
              DOSHIE // EXECUTIVE &amp; COMPANION
            </h2>
            <p className="text-xs sm:text-sm text-slate-400 max-w-md font-sans mb-6">
              Always here for open conversation, everyday thoughts, and top-tier technical operations. Communication is key.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex flex-col ${
                msg.role === 'user' ? 'items-end' : 'items-start'
              }`}
            >
              <div
                className={`max-w-[90%] sm:max-w-[80%] rounded-2xl px-4 py-3 text-sm font-sans leading-relaxed transition-all ${
                  msg.role === 'user'
                    ? 'bg-zinc-900/90 text-cyan-200 border border-cyan-500/40 shadow-[0_0_15px_rgba(56,189,248,0.15)] rounded-br-sm'
                    : 'hud-panel text-slate-100 border border-zinc-800 rounded-bl-sm'
                }`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-cyan-400 mb-1.5 font-bold tracking-wider">
                    <Zap className="w-3 h-3 text-cyan-400" />
                    <span>DOSHIE // EXECUTIVE</span>
                  </div>
                )}

                <div className="prose prose-invert prose-sm max-w-none break-words font-sans">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>

                <div className="text-[10px] text-slate-500 font-mono mt-1 text-right">
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-zinc-900/50 border border-cyan-500/20 w-fit text-xs font-mono text-cyan-400 animate-pulse">
            <Zap className="w-3.5 h-3.5 animate-spin" />
            <span>Formulating executive response...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer */}
      <form onSubmit={handleSubmit} className="flex-shrink-0 mt-2 mb-[max(env(safe-area-inset-bottom,0px),8px)] relative">
        <div className="flex items-center gap-2 p-1.5 rounded-2xl bg-zinc-950 border border-zinc-800 focus-within:border-cyan-500/60 shadow-[0_4px_20px_rgba(0,0,0,0.6)] transition-all">
          
          <button
            type="button"
            onClick={() => setTtsEnabled(!ttsEnabled)}
            className={`p-2 rounded-xl transition-all ${
              ttsEnabled ? 'text-cyan-400 bg-cyan-950/60' : 'text-slate-500 hover:text-slate-300'
            }`}
            title={ttsEnabled ? 'Speech Output Enabled' : 'Speech Output Muted'}
          >
            {ttsEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Chat with Doshie, ask anything, or issue a command..."
            className="flex-1 bg-transparent px-2 py-1 text-sm text-slate-100 placeholder-slate-500 focus:outline-none font-sans"
            disabled={loading}
          />

          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="flex items-center justify-center w-9 h-9 rounded-xl bg-cyan-500 text-black hover:bg-cyan-400 disabled:opacity-40 disabled:hover:bg-cyan-500 transition-all font-semibold shadow-[0_0_12px_rgba(56,189,248,0.4)]"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  )
}
