import React, { useState, useRef, useEffect, useLayoutEffect } from 'react'
import { Send, Square, Mic, MicOff, X, FileText, FileCode, Loader2, ChevronUp, Plus, Edit3 } from 'lucide-react'
import type { ChatAttachment } from '../types'
import { FileEditorModal } from './FileEditorModal'

interface ChatComposerProps {
  onSend: (text: string, attachments?: ChatAttachment[], brainMode?: string) => void
  onStop: () => void
  isGenerating: boolean
  placeholder?: string
  activeProfile?: string
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
}) => {
  const [input, setInput] = useState('')
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
    onSend(trimmed, attachments.length > 0 ? attachments : undefined, selectedBrain)
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
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 18px)',
      }}
      className={`flex-none px-2.5 pt-2.5 sm:px-3 sm:pt-3 bg-[var(--bg-dark)] border-t border-[var(--border-dark)] transition-all ${
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
        {/* Upload Error Banner */}
        {uploadError && (
          <div className="px-3 py-1.5 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-center justify-between animate-fadeIn">
            <span>{uploadError}</span>
            <button
              onClick={() => setUploadError(null)}
              className="text-rose-400 hover:text-white ml-2 p-0.5"
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
                className="group relative flex items-center gap-2 pl-2 pr-1.5 py-1.5 rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)] hover:border-[var(--accent)]/50 text-xs text-neutral-200 shadow-sm transition-all"
              >
                {att.kind === 'image' ? (
                  <div className="w-8 h-8 rounded-lg overflow-hidden bg-black/40 flex items-center justify-center flex-none border border-white/10">
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
                    className="w-8 h-8 rounded-lg bg-[var(--accent)]/15 border border-[var(--accent)]/30 hover:border-[var(--accent)] flex items-center justify-center text-[var(--accent-light)] flex-none cursor-pointer transition-colors"
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
                  <span className="truncate font-medium text-white text-[11.5px]">{att.name}</span>
                  <span className="text-[10px] text-neutral-400">{formatFileSize(att.size)}</span>
                </div>

                <div className="flex items-center gap-0.5 ml-1">
                  {att.kind !== 'image' && (
                    <button
                      type="button"
                      onClick={() => setEditingAttachment(att)}
                      title="Edit file content"
                      className="p-1 rounded-md text-neutral-400 hover:text-[var(--accent-light)] hover:bg-[var(--card-hover)] transition-colors cursor-pointer"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => removeAttachment(att.id)}
                    title="Remove attachment"
                    className="p-1 rounded-md text-neutral-400 hover:text-rose-400 hover:bg-rose-950/40 transition-colors cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}

            {uploadingFiles.map(file => (
              <div
                key={file.id}
                className="flex items-center gap-2 px-2.5 py-1.5 rounded-xl bg-[var(--card-dark)]/70 border border-dashed border-[var(--accent)]/40 text-xs text-neutral-300 shadow-sm animate-pulse"
              >
                <Loader2 className="w-4 h-4 animate-spin text-[var(--accent)]" />
                <span className="truncate max-w-[120px] text-[11.5px]">{file.name}</span>
              </div>
            ))}
          </div>
        )}

        {/* Integrated Composer Input Box & Bottom Control Pill */}
        <div className="relative flex flex-col px-3.5 pt-3 pb-2.5 bg-[var(--card-dark)] border border-[var(--border-dark)] focus-within:border-[var(--accent)] focus-within:ring-2 focus-within:ring-[var(--accent)]/20 rounded-3xl transition-all shadow-lg shadow-black/40">
          {/* Top Row: Textarea */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder={isListening ? "Listening... speak now" : placeholder}
            disabled={isGenerating}
            enterKeyHint="send"
            autoCapitalize="sentences"
            autoCorrect="on"
            spellCheck="true"
            className="w-full bg-transparent text-white placeholder-neutral-500 text-[15px] sm:text-[16px] leading-[1.4] outline-none resize-none px-0 py-1 min-h-[36px] max-h-[160px] overflow-y-auto"
          />

          {/* Bottom Bar inside the Input Pill (Attach + Model Selector + Voice + Send/Stop) */}
          <div className="flex items-center justify-between gap-2 pt-2.5 mt-1 border-t border-white/5">
            {/* Left Controls: Attach (+) and Model Pill Selector */}
            <div className="flex items-center gap-2">
              {/* Attach File Button (+) */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isGenerating || attachments.length >= 5}
                title="Attach picture or file"
                className="w-8 h-8 rounded-full bg-neutral-800/80 hover:bg-neutral-700/80 border border-white/10 flex items-center justify-center text-neutral-300 hover:text-white transition-all disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
              >
                <Plus className="w-4 h-4" />
              </button>

              {/* Model Selection Dropdown Pill Button */}
              <div className="relative flex items-center">
                <select
                  value={selectedBrain}
                  onChange={(e) => handleBrainChange(e.target.value)}
                  className="appearance-none bg-neutral-800/90 hover:bg-neutral-700/90 border border-white/10 hover:border-neutral-500 text-xs font-semibold text-neutral-200 pl-3 pr-7 py-1.5 rounded-full cursor-pointer transition-all outline-none"
                >
                  <option value="auto">🧠 Auto (qwen2.5:14b)</option>
                  <option value="balanced">⚖️ Balanced (qwen2.5:14b)</option>
                  <option value="advanced">🚀 Genius (deepseek-r1:14b)</option>
                  <option value="heavyweight">🥊 Heavyweight (deepseek-r1:32b)</option>
                  <option value="coding">⌨️ Coder (qwen2.5-coder:7b)</option>
                  <option value="fast">⚡ Fast (qwen3.5:4b)</option>
                  <option value="vision">👁 Vision (moondream)</option>
                </select>
                <ChevronUp className="w-3.5 h-3.5 text-neutral-400 absolute right-2.5 pointer-events-none" />
              </div>
            </div>

            {/* Right Controls: Voice Input & Send / Stop Thinking */}
            <div className="flex items-center gap-2">
              {/* Voice Button */}
              <button
                type="button"
                onClick={toggleSpeech}
                title={isListening ? "Stop listening" : "Voice input"}
                className={`w-8 h-8 rounded-full flex items-center justify-center transition-all cursor-pointer ${
                  isListening
                    ? 'bg-rose-600 text-white animate-pulse'
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-800/80 border border-white/10'
                }`}
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Send or Stop Thinking Button */}
              {isGenerating ? (
                <button
                  type="button"
                  onClick={onStop}
                  title="Stop thinking"
                  className="h-9 px-3.5 rounded-full bg-rose-600 hover:bg-rose-500 active:scale-95 text-white flex items-center justify-center gap-1.5 text-xs font-semibold transition duration-150 shadow-md shadow-black/50 cursor-pointer"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop thinking</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!canSend}
                  title="Send message"
                  className="w-9 h-9 rounded-full bg-neutral-200 text-neutral-900 hover:bg-white active:scale-95 flex items-center justify-center transition duration-150 disabled:opacity-30 disabled:pointer-events-none shadow-md cursor-pointer"
                >
                  <Send className="w-4 h-4 ml-0.5" />
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
