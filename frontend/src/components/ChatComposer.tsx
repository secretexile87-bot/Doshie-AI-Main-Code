import React, { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { Send, Square, Mic, MicOff, X, FileText, FileCode, Loader2, ChevronUp, Plus, Edit3 } from 'lucide-react'
import type { ChatAttachment, SpecialistAgent } from '../types'
import { FileEditorModal } from './FileEditorModal'

interface ChatComposerProps {
  onSend: (text: string, attachments?: ChatAttachment[], brainMode?: string, agentId?: string) => void
  onStop: () => void
  isGenerating: boolean
  placeholder?: string
  activeProfile?: string
  selectedAgent?: SpecialistAgent | null
  onClearSelectedAgent?: () => void
  onOpenAgentHub?: () => void
  isKeyboardOpen?: boolean
  onKeyboardStateChange?: (open: boolean) => void
  draftText?: string
  onClearDraftText?: () => void
}

interface UploadingFile {
  id: string
  name: string
  progress?: number
  previewUrl?: string
  kind: 'image' | 'file'
}

export const ChatComposer: React.FC<ChatComposerProps> = ({
  onSend,
  onStop,
  isGenerating,
  placeholder = "Ask anything, @ to mention, / for actions...",
  activeProfile = "Hermes",
  selectedAgent,
  onClearSelectedAgent,
  onOpenAgentHub,
  isKeyboardOpen = false,
  onKeyboardStateChange,
  draftText,
  onClearDraftText,
}) => {
  const [input, setInput] = useState('')

  useEffect(() => {
    if (draftText !== undefined && draftText !== '') {
      setInput(draftText)
      if (textareaRef.current) {
        textareaRef.current.focus()
        textareaRef.current.setSelectionRange(draftText.length, draftText.length)
      }
      onClearDraftText?.()
    }
  }, [draftText, onClearDraftText])
  const [isListening, setIsListening] = useState(false)
  const [attachments, setAttachments] = useState<ChatAttachment[]>([])
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([])
  const [isDragging, setIsDragging] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [editingAttachment, setEditingAttachment] = useState<ChatAttachment | null>(null)
  const [selectedBrain, setSelectedBrain] = useState<string>(() => {
    return localStorage.getItem('Doshie_brain_mode') || 'auto'
  })

  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<any>(null)

  const handleBrainChange = (newBrain: string) => {
    setSelectedBrain(newBrain)
    localStorage.setItem('Doshie_brain_mode', newBrain)
  }

  const getNativeSpeech = () => {
    const capacitor = (window as any).Capacitor
    if (!capacitor) return null
    if (capacitor.Plugins?.DiYoshiSpeech) {
      return capacitor.Plugins.DiYoshiSpeech
    }
    if (capacitor.Plugins?.DoshieSpeech) {
      return capacitor.Plugins.DoshieSpeech
    }
    return typeof capacitor.registerPlugin === 'function'
      ? (capacitor.registerPlugin('DiYoshiSpeech') || capacitor.registerPlugin('DoshieSpeech'))
      : null
  }

  // Auto-resize textarea based on content
  useLayoutEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const scrollHeight = textareaRef.current.scrollHeight
      const newHeight = Math.min(Math.max(scrollHeight, 24), 160)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [input])

  useEffect(() => {
    // Focus on mount (desktop/tablet)
    if (window.innerWidth > 768) {
      textareaRef.current?.focus()
    }

    // Initialize Web Speech API if supported as fallback
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition()
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript
        setInput(prev => (prev ? `${prev} ${transcript}` : transcript))
        setIsListening(false)
      }

      recognition.onerror = () => {
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognition
    }
  }, [])

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Upload handler for files
  const uploadFile = async (file: File) => {
    if (file.size > 8 * 1024 * 1024) {
      setUploadError(`"${file.name}" exceeds maximum size (8 MB).`)
      setTimeout(() => setUploadError(null), 4000)
      return
    }

    if (attachments.length + uploadingFiles.length >= 5) {
      setUploadError('You can attach up to 5 files or photos per message.')
      setTimeout(() => setUploadError(null), 4000)
      return
    }

    const tempId = `temp-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const isImage = file.type.startsWith('image/')
    const previewUrl = isImage ? URL.createObjectURL(file) : undefined

    setUploadingFiles(prev => [
      ...prev,
      { id: tempId, name: file.name, previewUrl, kind: isImage ? 'image' : 'file' },
    ])

    const formData = new FormData()
    formData.append('profile', activeProfile)
    formData.append('attachment', file)

    try {
      const res = await fetch(`/chat-attachment?profile=${encodeURIComponent(activeProfile)}`, {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      if (!res.ok || data.error) {
        throw new Error(data.error || 'Upload failed')
      }

      if (data.attachment) {
        const uploaded: ChatAttachment = {
          id: data.attachment.id,
          name: data.attachment.name,
          size: data.attachment.size,
          mime_type: data.attachment.mime || data.attachment.mime_type || file.type,
          kind: data.attachment.kind || (isImage ? 'image' : 'file'),
          url: data.attachment.url || `/chat-attachment/${data.attachment.id}?profile=${encodeURIComponent(activeProfile)}`,
          previewUrl: previewUrl,
        }
        setAttachments(prev => [...prev, uploaded])
      }
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload attachment.')
      setTimeout(() => setUploadError(null), 4000)
    } finally {
      setUploadingFiles(prev => prev.filter(f => f.id !== tempId))
    }
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      Array.from(e.target.files).forEach(uploadFile)
      e.target.value = ''
    }
  }

  const handlePaste = (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    if (e.clipboardData.files && e.clipboardData.files.length > 0) {
      e.preventDefault()
      Array.from(e.clipboardData.files).forEach(uploadFile)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      Array.from(e.dataTransfer.files).forEach(uploadFile)
    }
  }

  const removeAttachment = (id: string) => {
    setAttachments(prev => prev.filter(a => a.id !== id))
  }

  const handleSend = () => {
    const trimmed = input.trim()
    if ((!trimmed && attachments.length === 0) || isGenerating || uploadingFiles.length > 0) return
    onSend(trimmed, attachments.length > 0 ? attachments : undefined, selectedBrain, selectedAgent?.id)
    setInput('')
    setAttachments([])
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const toggleSpeech = async () => {
    const nativeSpeech = getNativeSpeech()
    if (nativeSpeech) {
      if (isListening) {
        setIsListening(false)
        await nativeSpeech.stopListening().catch(() => {})
        return
      }

      setIsListening(true)
      try {
        const result = await nativeSpeech.startListening({
          language: navigator.language || 'en-US',
        })
        const transcript = String(result?.text || '').trim()
        if (transcript) {
          setInput(prev => (prev ? `${prev} ${transcript}` : transcript))
        }
      } catch (err: any) {
        console.warn('Native speech error:', err)
      } finally {
        setIsListening(false)
      }
      return
    }

    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser.")
    } else {
      if (isListening) {
        recognitionRef.current.stop()
        setIsListening(false)
      } else {
        try {
          recognitionRef.current.start()
          setIsListening(true)
        } catch {
          setIsListening(false)
        }
      }
    }
  }

  const canSend = (input.trim().length > 0 || attachments.length > 0) && !isGenerating && uploadingFiles.length === 0

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      style={{
        paddingBottom: isKeyboardOpen
          ? '6px'
          : 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 12px)',
      }}
      className={`flex-none sticky bottom-0 z-30 px-2.5 pt-2 sm:px-4 sm:pt-3 bg-gradient-to-t from-[var(--bg-dark)] via-[var(--bg-dark)]/95 to-transparent backdrop-blur-lg border-t border-white/5 transition-all ${
        isDragging ? 'bg-[var(--accent)]/10 ring-2 ring-inset ring-[var(--accent)]' : ''
      }`}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        multiple
        accept="image/*,.png,.jpg,.jpeg,.webp,.gif,.pdf,.txt,.md,.csv,.json,.py,.js,.css,.html"
        className="hidden"
      />

      <div className="max-w-3xl mx-auto flex flex-col gap-2">
        {/* Active Specialist Agent Banner */}
        {selectedAgent && (
          <div className="flex items-center justify-between px-3.5 py-1.5 rounded-2xl bg-white/[0.04] backdrop-blur-md border border-white/10 text-xs shadow-md animate-fadeIn">
            <div className="flex items-center gap-2 min-w-0">
              <span
                style={{ backgroundColor: `${selectedAgent.accent || '#35f2d0'}25`, color: selectedAgent.accent || '#35f2d0', borderColor: `${selectedAgent.accent || '#35f2d0'}40` }}
                className="px-2.5 py-0.5 rounded-full font-bold text-[11px] flex items-center gap-1.5 flex-none border"
              >
                <span>🤖</span>
                <span>{selectedAgent.name}</span>
              </span>
              <span className="text-neutral-400 text-[11px] truncate hidden sm:inline">
                {selectedAgent.purpose}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-none">
              {onOpenAgentHub && (
                <button
                  type="button"
                  onClick={onOpenAgentHub}
                  className="text-[11px] font-semibold text-[var(--accent-light)] hover:underline cursor-pointer"
                >
                  Switch
                </button>
              )}
              {onClearSelectedAgent && (
                <button
                  type="button"
                  onClick={onClearSelectedAgent}
                  className="p-1 text-neutral-400 hover:text-white rounded-lg hover:bg-white/10 cursor-pointer transition-colors"
                  title="Reset to Default Doshie"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Upload Error Banner */}
        {uploadError && (
          <div className="px-3.5 py-2 rounded-2xl bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center justify-between animate-fadeIn shadow-lg">
            <span>{uploadError}</span>
            <button
              onClick={() => setUploadError(null)}
              className="text-rose-400 hover:text-white ml-2 p-0.5 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Attachment Preview Tray */}
        {(attachments.length > 0 || uploadingFiles.length > 0) && (
          <div className="flex flex-wrap items-center gap-2 px-1 py-1 max-h-[140px] overflow-y-auto">
            {attachments.map(att => (
              <div
                key={att.id}
                className="group relative flex items-center gap-2 pl-2 pr-1.5 py-1.5 rounded-2xl bg-white/[0.05] border border-white/10 hover:border-[var(--accent)]/60 text-xs text-neutral-200 shadow-md backdrop-blur-md transition-all"
              >
                {att.kind === 'image' ? (
                  <div className="w-8 h-8 rounded-xl overflow-hidden bg-black/50 flex items-center justify-center flex-none border border-white/15">
                    <img
                      src={att.previewUrl || att.url || `/chat-attachment/${att.id}?profile=${encodeURIComponent(activeProfile)}`}
                      alt={att.name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => setEditingAttachment(att)}
                    title="View & Edit File Content"
                    className="w-8 h-8 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 hover:border-[var(--accent)] flex items-center justify-center text-[var(--accent-light)] flex-none cursor-pointer transition-colors"
                  >
                    {att.name.endsWith('.py') || att.name.endsWith('.js') || att.name.endsWith('.html') || att.name.endsWith('.json') ? (
                      <FileCode className="w-4 h-4" />
                    ) : (
                      <FileText className="w-4 h-4" />
                    )}
                  </button>
                )}

                <div
                  onClick={() => att.kind !== 'image' && setEditingAttachment(att)}
                  className={`flex flex-col min-w-0 max-w-[120px] sm:max-w-[170px] ${att.kind !== 'image' ? 'cursor-pointer hover:underline' : ''}`}
                >
                  <span className="truncate font-semibold text-white text-[11.5px]">{att.name}</span>
                  <span className="text-[10px] text-neutral-400 font-mono">{formatFileSize(att.size)}</span>
                </div>

                <div className="flex items-center gap-0.5 ml-1">
                  {att.kind !== 'image' && (
                    <button
                      type="button"
                      onClick={() => setEditingAttachment(att)}
                      title="Edit file content"
                      className="p-1 rounded-lg text-neutral-400 hover:text-[var(--accent-light)] hover:bg-white/10 transition-colors cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => removeAttachment(att.id)}
                    title="Remove attachment"
                    className="p-1 rounded-lg text-neutral-400 hover:text-rose-400 hover:bg-rose-950/50 transition-colors cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}

            {uploadingFiles.map(file => (
              <div
                key={file.id}
                className="flex items-center gap-2 px-3 py-1.5 rounded-2xl bg-white/[0.04] border border-dashed border-[var(--accent)]/50 text-xs text-neutral-300 shadow-md backdrop-blur-md animate-pulse"
              >
                <Loader2 className="w-4 h-4 animate-spin text-[var(--accent)]" />
                <span className="truncate max-w-[120px] text-[11.5px] font-medium">{file.name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Integrated Composer Input Capsule */}
        <div className="relative flex flex-col px-3 sm:px-4 pt-3 pb-2 sm:pb-2.5 bg-white/[0.04] hover:bg-white/[0.05] border border-white/10 hover:border-white/20 focus-within:border-[var(--accent)] focus-within:ring-2 focus-within:ring-[var(--accent)]/25 rounded-3xl transition-all shadow-xl shadow-black/50 backdrop-blur-xl group overflow-hidden box-border w-full">
          {/* Top Row: Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={e => {
              setInput(e.target.value)
              textareaRef.current?.scrollIntoView({ block: 'nearest' })
            }}
            onFocus={() => {
              onKeyboardStateChange?.(true)
              setTimeout(() => {
                textareaRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
              }, 80)
            }}
            onBlur={() => {
              setTimeout(() => {
                const vv = window.visualViewport
                if (!vv || window.innerHeight - vv.height < 120) {
                  onKeyboardStateChange?.(false)
                }
              }, 120)
            }}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={isListening ? "Listening... speak now" : placeholder}
            disabled={isGenerating}
            enterKeyHint="send"
            autoCapitalize="sentences"
            autoCorrect="on"
            spellCheck="true"
            className="w-full min-w-0 bg-transparent text-white placeholder-neutral-400 text-[15px] sm:text-[16px] leading-relaxed outline-none resize-none px-0 py-0.5 min-h-[36px] max-h-[160px] overflow-y-auto"
          />

          {/* Bottom Bar: Attach, Model Selector, Voice & Send */}
          <div className="flex items-center justify-between gap-1.5 sm:gap-2 pt-2 sm:pt-2.5 mt-1 border-t border-white/5 w-full min-w-0">
            {/* Left Controls */}
            <div className="flex items-center gap-1.5 sm:gap-2 min-w-0 flex-1">
              {/* Attach File Button (+) */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isGenerating || attachments.length >= 5}
                title="Attach picture or file"
                className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white/5 hover:bg-white/15 border border-white/10 flex items-center justify-center text-neutral-300 hover:text-white transition-all disabled:opacity-40 disabled:pointer-events-none cursor-pointer active:scale-90 flex-none"
              >
                <Plus className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </button>

              {/* Model Selection Dropdown Pill Button */}
              <div className="relative flex items-center min-w-0 flex-1 max-w-[110px] sm:max-w-[210px] md:max-w-none">
                <select
                  value={selectedBrain}
                  onChange={(e) => handleBrainChange(e.target.value)}
                  className="appearance-none bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-[10.5px] sm:text-[11.5px] font-semibold text-neutral-200 pl-2.5 pr-6 sm:pl-3 sm:pr-7 py-1 sm:py-1.5 rounded-full cursor-pointer transition-all outline-none truncate w-full max-w-full"
                >
                  <option value="auto" className="bg-[#161b22] text-white">🧠 Auto</option>
                  <option value="fast" className="bg-[#161b22] text-white">⚡ Fast (9B)</option>
                  <option value="balanced" className="bg-[#161b22] text-white">⚖️ Balanced (9B)</option>
                  <option value="advanced" className="bg-[#161b22] text-white">🚀 Genius (14B)</option>
                  <option value="heavyweight" className="bg-[#161b22] text-white">🥊 Heavy (14B)</option>
                  <option value="coding" className="bg-[#161b22] text-white">⌨️ Coder (7B)</option>
                  <option value="vision" className="bg-[#161b22] text-white">👁 Vision (9B)</option>
                </select>
                <ChevronUp className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-neutral-400 absolute right-1.5 sm:right-2.5 pointer-events-none" />
              </div>
            </div>

            {/* Right Controls */}
            <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 flex-none">
              {/* Voice Button */}
              <button
                type="button"
                onClick={toggleSpeech}
                title={isListening ? "Stop listening" : "Voice input"}
                className={`w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition-all cursor-pointer active:scale-90 shrink-0 flex-none ${
                  isListening
                    ? 'bg-rose-600 text-white animate-pulse shadow-md shadow-rose-900/50'
                    : 'text-neutral-400 hover:text-white hover:bg-white/10 border border-white/10'
                }`}
              >
                {isListening ? <MicOff className="w-3.5 h-3.5 sm:w-4 sm:h-4" /> : <Mic className="w-3.5 h-3.5 sm:w-4 sm:h-4" />}
              </button>

              {/* Send or Stop Thinking Button */}
              {isGenerating ? (
                <button
                  type="button"
                  onClick={onStop}
                  title="Stop thinking"
                  className="h-7 sm:h-8 px-2.5 sm:px-3.5 rounded-full bg-rose-600 hover:bg-rose-500 active:scale-95 text-white flex items-center justify-center gap-1 sm:gap-1.5 text-[11px] sm:text-xs font-semibold transition-all shadow-lg shadow-rose-950/60 cursor-pointer border border-rose-400/30 shrink-0 flex-none"
                >
                  <Square className="w-3 h-3 sm:w-3.5 sm:h-3.5 fill-current" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!canSend}
                  title="Send message"
                  className="w-7 h-7 sm:w-8 sm:h-8 md:w-9 md:h-9 rounded-full bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] text-neutral-950 font-bold hover:opacity-95 active:scale-90 flex items-center justify-center transition-all disabled:opacity-30 disabled:pointer-events-none shadow-lg shadow-[var(--accent)]/20 cursor-pointer shrink-0 flex-none"
                >
                  <Send className="w-3.5 h-3.5 sm:w-4 sm:h-4 ml-0.5 text-neutral-950" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      <FileEditorModal
        isOpen={Boolean(editingAttachment)}
        attachment={editingAttachment}
        activeProfile={activeProfile}
        onClose={() => setEditingAttachment(null)}
        onSave={updated => {
          setAttachments(prev => prev.map(a => (a.id === editingAttachment?.id ? updated : a)))
          setEditingAttachment(null)
        }}
      />
    </div>
  )
}
