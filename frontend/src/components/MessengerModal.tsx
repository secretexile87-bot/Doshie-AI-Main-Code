import React, { useState, useEffect, useRef, useCallback } from 'react'
import {
  MessageSquare,
  Send,
  Plus,
  Users,
  X,
  Search,
  Check,
  CheckCheck,
  ChevronLeft,
  Circle,
  Sparkles,
} from 'lucide-react'
import type { GuiCustomization } from '../types'

interface Person {
  name: string
  role: string
  initials: string
  avatar_url?: string
  is_admin: boolean
  online: boolean
  self: boolean
  is_ai?: boolean
}

interface Message {
  id: number
  conversation_id: string
  sender_profile: string
  body: string
  created_at: string
  edited_at?: string
}

interface Conversation {
  id: string
  kind: 'direct' | 'group'
  title: string
  members: string[]
  updated_at: string
  last_message?: {
    id: number
    sender_profile: string
    body: string
    created_at: string
  }
  unread_count: number
}

interface MessengerModalProps {
  isOpen: boolean
  onClose: () => void
  activeProfile: string
  customization: GuiCustomization
}

export const MessengerModal: React.FC<MessengerModalProps> = ({
  isOpen,
  onClose,
  activeProfile,
  customization: _customization,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [people, setPeople] = useState<Person[]>([])
  const [inputBody, setInputBody] = useState('')
  const [typingUsers, setTypingUsers] = useState<string[]>([])
  const [searchFilter, setSearchFilter] = useState('')
  const [isCreatingNew, setIsCreatingNew] = useState(false)
  const [newChatKind, setNewChatKind] = useState<'direct' | 'group'>('direct')
  const [selectedMembers, setSelectedMembers] = useState<string[]>([])
  const [newGroupTitle, setNewGroupTitle] = useState('')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const typingTimerRef = useRef<any>(null)
  const isTypingRef = useRef(false)

  // Scroll messages to bottom smoothly
  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    messagesEndRef.current?.scrollIntoView({ behavior })
  }, [])

  // Fetch People / Contacts catalog
  const fetchPeople = useCallback(async () => {
    try {
      const res = await fetch(`/messaging/people?profile=${encodeURIComponent(activeProfile)}`)
      if (res.ok) {
        const data = await res.json()
        setPeople(data.people || [])
      }
    } catch (err) {
      console.error('Failed to load contacts:', err)
    }
  }, [activeProfile])

  // Fetch Conversations list
  const fetchConversations = useCallback(async () => {
    try {
      const res = await fetch(`/messaging/conversations?profile=${encodeURIComponent(activeProfile)}`)
      if (res.ok) {
        const data = await res.json()
        const list: Conversation[] = data.conversations || []
        setConversations(list)
        if (list.length > 0 && !activeConversationId) {
          setActiveConversationId(list[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to load conversations:', err)
    }
  }, [activeProfile, activeConversationId])

  // Fetch Messages for active conversation
  const fetchMessages = useCallback(async (conversationId: string) => {
    try {
      const res = await fetch(
        `/messaging/conversations/${conversationId}/messages?profile=${encodeURIComponent(activeProfile)}&limit=100`
      )
      if (res.ok) {
        const data = await res.json()
        setMessages(data.messages || [])
        // Mark as read
        fetch(`/messaging/conversations/${conversationId}/read`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile: activeProfile }),
        }).catch(() => {})
      }
    } catch (err) {
      console.error('Failed to load messages:', err)
    }
  }, [activeProfile])

  // Fetch Typing users for active conversation
  const fetchTyping = useCallback(async (conversationId: string) => {
    try {
      const res = await fetch(
        `/messaging/conversations/${conversationId}/typing?profile=${encodeURIComponent(activeProfile)}`
      )
      if (res.ok) {
        const data = await res.json()
        setTypingUsers(data.typing || [])
      }
    } catch {}
  }, [activeProfile])

  // Initial load when modal opens
  useEffect(() => {
    if (!isOpen) return
    Promise.all([fetchPeople(), fetchConversations()])
  }, [isOpen, fetchPeople, fetchConversations])

  // Load messages when active conversation changes
  useEffect(() => {
    if (!isOpen || !activeConversationId) return
    fetchMessages(activeConversationId)
    fetchTyping(activeConversationId)
    setTimeout(() => scrollToBottom('auto'), 80)
  }, [isOpen, activeConversationId, fetchMessages, fetchTyping, scrollToBottom])

  // Real-time polling when modal is open
  useEffect(() => {
    if (!isOpen) return
    const interval = setInterval(() => {
      fetchConversations()
      if (activeConversationId) {
        fetchMessages(activeConversationId)
        fetchTyping(activeConversationId)
      }
    }, 2800)
    return () => clearInterval(interval)
  }, [isOpen, activeConversationId, fetchConversations, fetchMessages, fetchTyping])

  // Emit typing indicator
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputBody(e.target.value)
    if (!activeConversationId) return

    if (!isTypingRef.current) {
      isTypingRef.current = true
      fetch('/messaging/typing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          conversation_id: activeConversationId,
          typing: true,
        }),
      }).catch(() => {})
    }

    if (typingTimerRef.current) clearTimeout(typingTimerRef.current)
    typingTimerRef.current = setTimeout(() => {
      isTypingRef.current = false
      if (activeConversationId) {
        fetch('/messaging/typing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile: activeProfile,
            conversation_id: activeConversationId,
            typing: false,
          }),
        }).catch(() => {})
      }
    }, 2500)
  }

  // Send message
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const trimmed = inputBody.trim()
    if (!trimmed || !activeConversationId) return

    setInputBody('')
    isTypingRef.current = false
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current)

    // Clear typing state
    fetch('/messaging/typing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile: activeProfile,
        conversation_id: activeConversationId,
        typing: false,
      }),
    }).catch(() => {})

    // Optimistic UI update
    const tempMsg: Message = {
      id: Date.now(),
      conversation_id: activeConversationId,
      sender_profile: activeProfile,
      body: trimmed,
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, tempMsg])
    setTimeout(() => scrollToBottom('smooth'), 50)

    try {
      const res = await fetch(`/messaging/conversations/${activeConversationId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          body: trimmed,
        }),
      })
      if (res.ok) {
        fetchMessages(activeConversationId)
        fetchConversations()
      }
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }

  // Create new conversation
  const handleCreateConversation = async () => {
    if (selectedMembers.length === 0) return

    try {
      const res = await fetch('/messaging/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          members: selectedMembers,
          kind: newChatKind,
          title: newChatKind === 'group' ? newGroupTitle : '',
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setIsCreatingNew(false)
        setSelectedMembers([])
        setNewGroupTitle('')
        fetchConversations()
        if (data.conversation_id) {
          setActiveConversationId(data.conversation_id)
        }
      }
    } catch (err) {
      console.error('Failed to create conversation:', err)
    }
  }

  // Quick start direct chat with person
  const handleStartDirectChat = async (targetPerson: Person) => {
    try {
      const res = await fetch('/messaging/conversations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: activeProfile,
          members: [targetPerson.name],
          kind: 'direct',
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setIsCreatingNew(false)
        fetchConversations()
        if (data.conversation_id) {
          setActiveConversationId(data.conversation_id)
        }
      }
    } catch (err) {
      console.error('Failed to start chat with', targetPerson.name, err)
    }
  }

  if (!isOpen) return null

  const activeConv = conversations.find(c => c.id === activeConversationId)
  const isDirectDoshie =
    activeConv?.kind === 'direct' &&
    activeConv.members.some(m => m.toLowerCase() === 'doshie')

  const filteredConversations = conversations.filter(c =>
    c.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
    c.members.some(m => m.toLowerCase().includes(searchFilter.toLowerCase()))
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-4xl h-[92vh] max-h-[820px] bg-[#07130c] border border-emerald-900/60 rounded-2xl shadow-2xl flex flex-col overflow-hidden text-neutral-100">
        
        {/* Top Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#0a1b12]/90 border-b border-emerald-900/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-semibold tracking-wide text-white flex items-center gap-2">
                Doshie Messenger
                <span className="px-1.5 py-0.5 text-[10px] bg-emerald-500/20 text-emerald-300 rounded font-mono">
                  Family &amp; AI
                </span>
              </h2>
              <p className="text-[11px] text-emerald-400/70">
                Direct peer chats, family groups, &amp; private DMs with Doshie
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsCreatingNew(!isCreatingNew)}
              className="px-2.5 py-1.5 bg-emerald-600/30 hover:bg-emerald-600/50 border border-emerald-500/40 rounded-lg text-xs font-medium text-emerald-300 flex items-center gap-1.5 transition-all cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">New Chat</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 hover:bg-white/10 rounded-lg text-neutral-400 hover:text-white transition-all cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Main Body: Two-Pane Layout */}
        <div className="flex-1 flex overflow-hidden">
          
          {/* Left Pane: Conversations & Contacts */}
          <div
            className={`w-full sm:w-72 md:w-80 border-r border-emerald-900/40 flex flex-col bg-[#05110a] ${
              activeConversationId && !isCreatingNew ? 'hidden sm:flex' : 'flex'
            }`}
          >
            {/* Search Box */}
            <div className="p-2.5 border-b border-emerald-900/30">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-neutral-500" />
                <input
                  type="text"
                  placeholder="Search chats or members..."
                  value={searchFilter}
                  onChange={e => setSearchFilter(e.target.value)}
                  className="w-full bg-[#091b12] border border-emerald-900/50 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-emerald-500/60"
                />
              </div>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto divide-y divide-emerald-950/40">
              {filteredConversations.length === 0 ? (
                <div className="p-6 text-center text-neutral-400 text-xs">
                  <p>No conversations yet.</p>
                  <button
                    onClick={() => setIsCreatingNew(true)}
                    className="mt-2.5 px-3 py-1.5 bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-lg hover:bg-emerald-600/40 transition-all text-xs"
                  >
                    Start your first chat
                  </button>
                </div>
              ) : (
                filteredConversations.map(conv => {
                  const isActive = conv.id === activeConversationId
                  const isDoshieConv = conv.members.some(m => m.toLowerCase() === 'doshie')
                  const isGroup = conv.kind === 'group'

                  return (
                    <button
                      key={conv.id}
                      onClick={() => {
                        setActiveConversationId(conv.id)
                        setIsCreatingNew(false)
                      }}
                      className={`w-full p-3 flex items-start gap-2.5 text-left transition-colors cursor-pointer ${
                        isActive
                          ? 'bg-emerald-900/30 border-l-2 border-emerald-400'
                          : 'hover:bg-emerald-950/30'
                      }`}
                    >
                      {/* Avatar */}
                      <div className="relative flex-none">
                        <div className="w-10 h-10 rounded-full bg-emerald-950 border border-emerald-700/50 flex items-center justify-center text-sm font-bold text-emerald-300 overflow-hidden">
                          {isDoshieConv ? (
                            <span className="text-lg">🦖</span>
                          ) : isGroup ? (
                            <Users className="w-5 h-5 text-emerald-400" />
                          ) : (
                            conv.title.slice(0, 2).toUpperCase()
                          )}
                        </div>
                        {isDoshieConv && (
                          <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-emerald-400 border border-black" />
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1 mb-0.5">
                          <span className="text-xs font-semibold text-white truncate flex items-center gap-1">
                            {conv.title}
                            {isDoshieConv && (
                              <span className="text-[9px] px-1 py-0.2 bg-emerald-500/20 text-emerald-300 rounded font-normal">
                                AI
                              </span>
                            )}
                          </span>
                          {conv.last_message && (
                            <span className="text-[10px] text-neutral-400">
                              {new Date(conv.last_message.created_at).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                          )}
                        </div>

                        <p className="text-[11px] text-neutral-300 truncate">
                          {conv.last_message
                            ? `${conv.last_message.sender_profile}: ${conv.last_message.body}`
                            : 'No messages yet'}
                        </p>
                      </div>

                      {/* Unread badge */}
                      {conv.unread_count > 0 && (
                        <div className="flex-none px-1.5 py-0.5 rounded-full bg-emerald-500 text-neutral-950 text-[10px] font-bold">
                          {conv.unread_count}
                        </div>
                      )}
                    </button>
                  )
                })
              )}
            </div>

            {/* Quick Contacts Bar */}
            <div className="p-2 border-t border-emerald-900/40 bg-[#040e08]">
              <span className="text-[10px] uppercase tracking-wider font-semibold text-emerald-400/80 px-2 block mb-1.5">
                Online Family &amp; AI
              </span>
              <div className="flex gap-2 overflow-x-auto pb-1 px-1">
                {people.map(p => (
                  <button
                    key={p.name}
                    onClick={() => handleStartDirectChat(p)}
                    title={`Chat with ${p.name}`}
                    className="flex flex-col items-center flex-none group cursor-pointer"
                  >
                    <div className="relative w-8 h-8 rounded-full bg-emerald-950 border border-emerald-600/40 flex items-center justify-center text-xs text-white group-hover:border-emerald-400 transition-all">
                      {p.is_ai ? '🦖' : p.initials}
                      {p.online && (
                        <span className="absolute bottom-0 right-0 w-2 h-2 rounded-full bg-emerald-400 border border-black" />
                      )}
                    </div>
                    <span className="text-[9px] text-neutral-300 truncate max-w-[48px] mt-0.5">
                      {p.name.split(' ')[0]}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Pane: Thread View OR New Chat Creator */}
          <div
            className={`flex-1 flex flex-col bg-[#07150e] ${
              !activeConversationId && !isCreatingNew ? 'hidden sm:flex' : 'flex'
            }`}
          >
            {isCreatingNew ? (
              /* New Chat Form */
              <div className="flex-1 p-4 sm:p-6 overflow-y-auto">
                <div className="max-w-md mx-auto space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-emerald-900/40">
                    <h3 className="text-sm font-semibold text-white">Start a New Conversation</h3>
                    <button
                      onClick={() => setIsCreatingNew(false)}
                      className="text-xs text-neutral-400 hover:text-white"
                    >
                      Cancel
                    </button>
                  </div>

                  {/* Kind selector */}
                  <div className="flex gap-2">
                    <button
                      onClick={() => setNewChatKind('direct')}
                      className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border transition-all ${
                        newChatKind === 'direct'
                          ? 'bg-emerald-600 text-white border-emerald-500'
                          : 'bg-emerald-950/40 text-neutral-300 border-emerald-900/50'
                      }`}
                    >
                      Direct Message
                    </button>
                    <button
                      onClick={() => setNewChatKind('group')}
                      className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-medium border transition-all ${
                        newChatKind === 'group'
                          ? 'bg-emerald-600 text-white border-emerald-500'
                          : 'bg-emerald-950/40 text-neutral-300 border-emerald-900/50'
                      }`}
                    >
                      Group Chat
                    </button>
                  </div>

                  {/* Group title input */}
                  {newChatKind === 'group' && (
                    <div>
                      <label className="block text-xs text-neutral-300 mb-1">Group Title</label>
                      <input
                        type="text"
                        placeholder="e.g. Family Chat, Game Night"
                        value={newGroupTitle}
                        onChange={e => setNewGroupTitle(e.target.value)}
                        className="w-full bg-[#091b12] border border-emerald-900/50 rounded-lg px-3 py-2 text-xs text-white"
                      />
                    </div>
                  )}

                  {/* Member selection */}
                  <div>
                    <label className="block text-xs text-neutral-300 mb-2">
                      Select Contact{newChatKind === 'group' ? 's' : ''}:
                    </label>
                    <div className="space-y-1.5 max-h-60 overflow-y-auto">
                      {people
                        .filter(p => !p.self)
                        .map(p => {
                          const isSelected = selectedMembers.includes(p.name)
                          return (
                            <button
                              key={p.name}
                              type="button"
                              onClick={() => {
                                if (newChatKind === 'direct') {
                                  setSelectedMembers([p.name])
                                } else {
                                  setSelectedMembers(prev =>
                                    isSelected
                                      ? prev.filter(m => m !== p.name)
                                      : [...prev, p.name]
                                  )
                                }
                              }}
                              className={`w-full p-2.5 rounded-lg border flex items-center justify-between text-left transition-all ${
                                isSelected
                                  ? 'bg-emerald-900/40 border-emerald-500 text-white'
                                  : 'bg-emerald-950/20 border-emerald-900/40 text-neutral-300 hover:bg-emerald-950/40'
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                <span className="text-base">{p.is_ai ? '🦖' : '👤'}</span>
                                <div>
                                  <div className="text-xs font-medium text-white">{p.name}</div>
                                  <div className="text-[10px] text-emerald-400/70">{p.role}</div>
                                </div>
                              </div>
                              {isSelected && <Check className="w-4 h-4 text-emerald-400" />}
                            </button>
                          )
                        })}
                    </div>
                  </div>

                  <button
                    onClick={handleCreateConversation}
                    disabled={selectedMembers.length === 0}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium rounded-lg text-xs transition-all cursor-pointer"
                  >
                    Start Chat
                  </button>
                </div>
              </div>
            ) : activeConv ? (
              /* Active Conversation Thread */
              <>
                {/* Thread Header */}
                <div className="flex items-center justify-between px-4 py-2.5 bg-[#091d12] border-b border-emerald-900/40">
                  <div className="flex items-center gap-2.5">
                    <button
                      onClick={() => setActiveConversationId(null)}
                      className="sm:hidden p-1 -ml-1 text-neutral-400 hover:text-white"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <div className="w-8 h-8 rounded-full bg-emerald-950 border border-emerald-600/40 flex items-center justify-center text-sm">
                      {isDirectDoshie ? '🦖' : activeConv.kind === 'group' ? '👥' : '👤'}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white flex items-center gap-1.5">
                        {activeConv.title}
                        {isDirectDoshie && (
                          <span className="text-[9px] px-1 py-0.2 bg-emerald-500/20 text-emerald-300 rounded font-mono">
                            AI
                          </span>
                        )}
                      </h4>
                      <p className="text-[10px] text-emerald-400/80 flex items-center gap-1">
                        <Circle className="w-1.5 h-1.5 fill-emerald-400 text-emerald-400" />
                        {isDirectDoshie
                          ? 'Doshie AI Assistant • Always ready'
                          : activeConv.kind === 'group'
                          ? `${activeConv.members.length} members`
                          : 'Online'}
                      </p>
                    </div>
                  </div>

                  {isDirectDoshie && (
                    <div className="flex items-center gap-1 text-[10px] text-emerald-300 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/40">
                      <Sparkles className="w-3 h-3 text-emerald-400" />
                      <span>Direct AI Messaging</span>
                    </div>
                  )}
                </div>

                {/* Messages Scroll Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center text-neutral-400 text-xs">
                      <div className="text-3xl mb-2">{isDirectDoshie ? '🦖' : '💬'}</div>
                      <p className="font-medium text-white mb-1">
                        {isDirectDoshie
                          ? 'Say hello to Doshie!'
                          : `Start the conversation with ${activeConv.title}`}
                      </p>
                      <p className="text-[11px] text-neutral-400 max-w-xs">
                        {isDirectDoshie
                          ? 'Ask questions, share updates, or talk like texting a friend.'
                          : 'Messages are stored privately on your local server.'}
                      </p>
                    </div>
                  ) : (
                    messages.map((msg, idx) => {
                      const isSelf = msg.sender_profile.toLowerCase() === activeProfile.toLowerCase()
                      const isDoshie = msg.sender_profile.toLowerCase() === 'doshie'

                      return (
                        <div
                          key={msg.id || idx}
                          className={`flex flex-col ${isSelf ? 'items-end' : 'items-start'}`}
                        >
                          {/* Sender name for groups / peer */}
                          {!isSelf && (
                            <span className="text-[10px] font-medium text-neutral-400 mb-0.5 ml-1 flex items-center gap-1">
                              {isDoshie ? '🦖 Doshie' : msg.sender_profile}
                            </span>
                          )}

                          {/* Bubble */}
                          <div
                            className={`max-w-[82%] sm:max-w-[70%] px-3.5 py-2 rounded-2xl text-xs leading-relaxed break-words shadow-md ${
                              isSelf
                                ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-br-xs'
                                : isDoshie
                                ? 'bg-[#0f291b] border border-emerald-600/40 text-emerald-100 rounded-bl-xs'
                                : 'bg-[#14231b] border border-emerald-900/40 text-neutral-100 rounded-bl-xs'
                            }`}
                          >
                            <div className="whitespace-pre-wrap">{msg.body}</div>
                            <div
                              className={`flex items-center justify-end gap-1 mt-1 text-[9px] ${
                                isSelf ? 'text-emerald-200/70' : 'text-neutral-400'
                              }`}
                            >
                              <span>
                                {new Date(msg.created_at).toLocaleTimeString([], {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                })}
                              </span>
                              {isSelf && <CheckCheck className="w-3 h-3 text-emerald-300" />}
                            </div>
                          </div>
                        </div>
                      )
                    })
                  )}

                  {/* Typing Indicator */}
                  {typingUsers.length > 0 && (
                    <div className="flex items-center gap-1.5 text-[11px] text-emerald-400 italic py-1">
                      <span className="animate-bounce">●</span>
                      <span className="animate-bounce delay-100">●</span>
                      <span className="animate-bounce delay-200">●</span>
                      <span className="ml-1">
                        {typingUsers.join(', ')} {typingUsers.length > 1 ? 'are' : 'is'} typing...
                      </span>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Input Bar */}
                <form
                  onSubmit={handleSendMessage}
                  className="p-2.5 sm:p-3 bg-[#08170f] border-t border-emerald-900/50 flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={inputBody}
                    onChange={handleInputChange}
                    placeholder={
                      isDirectDoshie
                        ? 'Message Doshie...'
                        : `Message ${activeConv.title}...`
                    }
                    className="flex-1 bg-[#0d2618] border border-emerald-800/50 rounded-xl px-3.5 py-2 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-emerald-500"
                  />
                  <button
                    type="submit"
                    disabled={!inputBody.trim()}
                    className="p-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white transition-all cursor-pointer flex-none"
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </>
            ) : (
              /* No selection empty state */
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-neutral-400">
                <MessageSquare className="w-10 h-10 text-emerald-800 mb-2" />
                <p className="text-sm font-semibold text-white">Select a conversation</p>
                <p className="text-xs text-neutral-400 max-w-xs mt-1">
                  Choose an existing chat or start a new direct message with family or Doshie.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
export default MessengerModal
