import React, { useState, useEffect } from 'react'
import { X, Save, Copy, Check, Download, FileText, FileCode, Loader2 } from 'lucide-react'
import type { ChatAttachment } from '../types'

interface FileEditorModalProps {
  isOpen: boolean
  onClose: () => void
  attachment: ChatAttachment | null
  activeProfile?: string
  readOnly?: boolean
  onSave?: (updatedAttachment: ChatAttachment) => void
}

export const FileEditorModal: React.FC<FileEditorModalProps> = ({
  isOpen,
  onClose,
  attachment,
  activeProfile = 'Hermes',
  readOnly = false,
  onSave,
}) => {
  const [fileName, setFileName] = useState('')
  const [content, setContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [copied, setCopied] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [isTextFile, setIsTextFile] = useState(true)

  useEffect(() => {
    if (!isOpen || !attachment) return

    setFileName(attachment.name)
    setErrorMsg(null)

    const isText =
      attachment.kind === 'file' &&
      (attachment.name.match(/\.(txt|md|py|js|ts|json|csv|html|css|xml|yaml|yml|sh|c|cpp|h|java|go|rs|php|rb|sql|log|ini|env)$/i) ||
        attachment.mime_type.startsWith('text/') ||
        attachment.mime_type.includes('json') ||
        attachment.mime_type.includes('javascript') ||
        attachment.mime_type.includes('xml'))

    setIsTextFile(Boolean(isText))

    if (!isText) {
      setContent('')
      return
    }

    setIsLoading(true)
    const fileUrl =
      attachment.url ||
      `/chat-attachment/${attachment.id}?profile=${encodeURIComponent(activeProfile)}`

    fetch(fileUrl)
      .then(res => {
        if (!res.ok) throw new Error('Could not fetch file content')
        return res.text()
      })
      .then(text => {
        setContent(text)
        setIsLoading(false)
      })
      .catch(err => {
        setErrorMsg(err.message || 'Failed to load file content')
        setIsLoading(false)
      })
  }, [isOpen, attachment, activeProfile])

  if (!isOpen || !attachment) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const formatFileSize = (bytes: number) => {
    if (!bytes) return '0 B'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const handleSave = async () => {
    if (isSaving || !onSave) return

    const trimmedName = fileName.trim() || attachment.name
    setIsSaving(true)
    setErrorMsg(null)

    try {
      const blob = new Blob([content], { type: attachment.mime_type || 'text/plain' })
      const fileToUpload = new File([blob], trimmedName, {
        type: attachment.mime_type || 'text/plain',
      })

      const formData = new FormData()
      formData.append('profile', activeProfile)
      formData.append('attachment', fileToUpload)

      const res = await fetch(`/chat-attachment?profile=${encodeURIComponent(activeProfile)}`, {
        method: 'POST',
        body: formData,
      })

      const data = await res.json()
      if (!res.ok || data.error) {
        throw new Error(data.error || 'Failed to save updated file')
      }

      if (data.attachment) {
        const updated: ChatAttachment = {
          id: data.attachment.id,
          name: data.attachment.name,
          size: data.attachment.size,
          mime_type: data.attachment.mime || data.attachment.mime_type || attachment.mime_type,
          kind: data.attachment.kind || attachment.kind,
          url:
            data.attachment.url ||
            `/chat-attachment/${data.attachment.id}?profile=${encodeURIComponent(activeProfile)}`,
        }
        onSave(updated)
        onClose()
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Error saving file')
    } finally {
      setIsSaving(false)
    }
  }

  const getDownloadUrl = () => {
    if (attachment.url) {
      const sep = attachment.url.includes('?') ? '&' : '?'
      return `${attachment.url}${sep}download=1`
    }
    return `/chat-attachment/${attachment.id}?profile=${encodeURIComponent(activeProfile)}&download=1`
  }

  return (
    <div
      onClick={onClose}
      style={{
        paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 24px)',
        paddingBottom: 'max(env(safe-area-inset-bottom, 0px), var(--native-safe-bottom, 0px), 24px)',
      }}
      className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-3 sm:p-4 animate-fadeIn"
    >
      <div
        onClick={e => e.stopPropagation()}
        className="relative w-full max-w-4xl h-full max-h-[88vh] bg-[var(--card-dark)] border border-[var(--border-dark)] rounded-2xl sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden text-neutral-100"
      >
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-3.5 border-b border-[var(--border-dark)] bg-[var(--bg-dark)] flex-none">
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div className="p-2 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent-light)] flex-none">
              {attachment.name.match(/\.(py|js|ts|json|html|css|xml|sql|sh)$/i) ? (
                <FileCode className="w-5 h-5" />
              ) : (
                <FileText className="w-5 h-5" />
              )}
            </div>

            <div className="flex flex-col min-w-0 flex-1">
              {readOnly ? (
                <span className="font-semibold text-white text-sm sm:text-base truncate">
                  {attachment.name}
                </span>
              ) : (
                <input
                  type="text"
                  value={fileName}
                  onChange={e => setFileName(e.target.value)}
                  placeholder="File name (e.g. script.py)..."
                  className="bg-[var(--card-dark)] text-white font-medium text-xs sm:text-sm px-2.5 py-1 rounded-lg border border-[var(--border-dark)] focus:border-[var(--accent)] outline-none max-w-sm"
                />
              )}
              <span className="text-[10px] text-neutral-400 mt-0.5">
                {formatFileSize(content ? new Blob([content]).size : attachment.size)} • {attachment.mime_type || 'Text Document'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-none">
            <button
              onClick={handleCopy}
              disabled={isLoading || !content}
              className="px-2.5 py-1.5 rounded-xl bg-[var(--bg-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] text-neutral-200 text-xs font-medium flex items-center gap-1.5 transition-all cursor-pointer disabled:opacity-40"
              title="Copy file content"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
            </button>

            <a
              href={getDownloadUrl()}
              download={fileName || attachment.name}
              className="p-2 rounded-xl bg-[var(--bg-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] text-neutral-200 transition-all cursor-pointer"
              title="Download file"
            >
              <Download className="w-4 h-4" />
            </a>

            <button
              onClick={onClose}
              className="p-2 rounded-xl text-neutral-400 hover:text-white hover:bg-[var(--card-hover)] transition-colors cursor-pointer"
              title="Close editor"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {errorMsg && (
          <div className="px-4 py-2 bg-rose-950/80 border-b border-rose-800 text-rose-200 text-xs flex-none">
            {errorMsg}
          </div>
        )}

        {/* Editor / Content Area */}
        <div className="flex-1 p-3 sm:p-4 overflow-hidden flex flex-col bg-[#0b0f19]">
          {isLoading ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-2 text-neutral-400">
              <Loader2 className="w-6 h-6 animate-spin text-[var(--accent)]" />
              <span className="text-xs">Loading file content...</span>
            </div>
          ) : isTextFile ? (
            <div className="relative flex-1 flex flex-col overflow-hidden rounded-xl border border-[var(--border-dark)] focus-within:border-[var(--accent)] bg-[#070a12]">
              <textarea
                value={content}
                readOnly={readOnly}
                onChange={e => setContent(e.target.value)}
                placeholder="File content..."
                className="flex-1 p-3 sm:p-4 bg-transparent text-emerald-300 font-mono text-xs sm:text-sm leading-relaxed resize-none outline-none overflow-y-auto"
                spellCheck="false"
              />
              <div className="flex items-center justify-between px-3 py-1.5 bg-[var(--bg-dark)] border-t border-[var(--border-dark)] text-[10px] text-neutral-400 flex-none select-none">
                <span>{content.split('\n').length} lines • {content.length} characters</span>
                <span>{readOnly ? 'View Only' : 'Editable'}</span>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center gap-3 p-6 text-center text-neutral-400">
              <FileText className="w-12 h-12 text-neutral-500" />
              <div className="max-w-md space-y-1">
                <p className="text-sm font-semibold text-white">{attachment.name}</p>
                <p className="text-xs text-neutral-400">
                  Binary or non-text document ({formatFileSize(attachment.size)}).
                </p>
              </div>
              <a
                href={getDownloadUrl()}
                download={attachment.name}
                className="px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-xs font-semibold flex items-center gap-2 shadow-md transition-all cursor-pointer"
              >
                <Download className="w-4 h-4" />
                <span>Download File</span>
              </a>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {!readOnly && isTextFile && (
          <div className="px-4 sm:px-6 py-3 border-t border-[var(--border-dark)] bg-[var(--bg-dark)] flex items-center justify-between flex-none">
            <span className="text-xs text-neutral-400 hidden sm:inline">
              Changes will update your attachment before sending.
            </span>
            <div className="flex items-center gap-2 ml-auto">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] text-neutral-300 border border-[var(--border-dark)] text-xs font-medium transition-all cursor-pointer"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving || isLoading}
                className="px-5 py-2 rounded-xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-hover)] hover:opacity-90 active:scale-95 text-white text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md disabled:opacity-40 disabled:pointer-events-none cursor-pointer"
              >
                {isSaving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                <span>{isSaving ? 'Saving...' : 'Save & Attach'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
