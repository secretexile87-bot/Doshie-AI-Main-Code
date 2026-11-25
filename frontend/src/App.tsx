import { useState, useEffect, useCallback } from 'react'
import type { TabType, ChatMessage, HardwareTelemetry, GamingStatus } from './types'
import { Header } from './components/Header'
import { ChatView } from './components/ChatView'
import { GamingCockpitView } from './components/GamingCockpitView'
import { MediaView } from './components/MediaView'
import { SystemView } from './components/SystemView'
import { UnlockModal } from './components/UnlockModal'

export function App() {
  const [activeTab, setActiveTab] = useState<TabType>('chat')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      role: 'assistant',
      content:
        "Hey Hermes! Everything on the Acer Nitro is running smooth and quiet.\n\nI'm ready for whatever's on your mind—whether you want to catch up, chat about life and gaming, or have me tune and diagnose the systems. Communication is key. How are you doing today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ])
  const [chatLoading, setChatLoading] = useState(false)
  const [showUnlockModal, setShowUnlockModal] = useState(false)
  const [pendingMessage, setPendingMessage] = useState<string | null>(null)
  const [telemetry, setTelemetry] = useState<HardwareTelemetry | null>({
    gpu_temp: 42,
    gpu_power_watts: 2.99,
    vram_used_mb: 683,
    vram_total_mb: 12227,
    cpu_percent: 2.1
  })
  const [gamingStatus, setGamingStatus] = useState<GamingStatus | null>({
    dallas_ping_ms: 23,
    local_ping_ms: 1,
    tunnel_active: true,
    packet_loss: 0.0,
    status_summary: 'Dallas high-speed gaming route active.'
  })

  // Poll hardware metrics periodically
  const fetchTelemetry = async () => {
    try {
      const res = await fetch('/dashboard')
      if (res.ok) {
        const data = await res.json()
        if (data?.system) {
          setTelemetry((prev) => ({
            ...prev,
            cpu_percent: data.system.cpu_percent,
            ram_used_gb: data.system.ram_used_gb,
            ram_total_gb: data.system.ram_total_gb,
            load_avg: data.system.load_avg
          }))
        }
      }
    } catch {
      // Ignore background fetch error
    }

    try {
      const gRes = await fetch('/api/gaming-status')
      if (gRes.ok) {
        const gData = await gRes.json()
        if (gData?.ok && gData?.gaming) {
          setGamingStatus(gData.gaming)
        }
      }
    } catch {
      // Ignore background fetch error
    }
  }

  useEffect(() => {
    fetchTelemetry()
    const timer = setInterval(fetchTelemetry, 10000)
    return () => clearInterval(timer)
  }, [])

  const executeChatRequest = useCallback(async (text: string) => {
    setChatLoading(true)

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, profile: 'Hermes', brain_mode: 'cloud' })
      })

      if (res.ok) {
        const data = await res.json()
        const botReply = data.reply || data.response || data.message || (data.status ? `Status: ${data.status}` : 'Action processed, sir.')
        const botMsg: ChatMessage = {
          id: `bot-${Date.now()}`,
          role: 'assistant',
          content: botReply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          model: data.model || 'Doshie'
        }
        setMessages((prev) => [...prev, botMsg])
      } else if (res.status === 423) {
        // Profile lock triggered - open unlock modal
        setPendingMessage(text)
        setShowUnlockModal(true)
        const lockMsg: ChatMessage = {
          id: `lock-${Date.now()}`,
          role: 'assistant',
          content: "Hermes's profile is locked. Please enter your PIN to authorize this session.",
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        setMessages((prev) => [...prev, lockMsg])
      } else {
        let errDesc = `Apologies, sir. The system encountered an error (HTTP ${res.status}).`
        try {
          const errData = await res.json()
          if (errData?.error) errDesc = errData.error
        } catch {
          // fallback to default
        }
        const errMsg: ChatMessage = {
          id: `err-${Date.now()}`,
          role: 'assistant',
          content: errDesc,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        setMessages((prev) => [...prev, errMsg])
      }
    } catch (err: any) {
      const errMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `Connection error: ${err.message}. The server might be restarting.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages((prev) => [...prev, errMsg])
    } finally {
      setChatLoading(false)
    }
  }, [])

  const handleSendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    setMessages((prev) => [...prev, userMsg])
    await executeChatRequest(text)
  }

  const handleUnlockSuccess = () => {
    if (pendingMessage) {
      const retryText = pendingMessage
      setPendingMessage(null)
      executeChatRequest(retryText)
    }
  }

  return (
    <div className="h-[100dvh] max-h-[100dvh] w-full bg-black text-slate-100 flex flex-col font-sans overflow-hidden selection:bg-cyan-500 selection:text-black">
      {/* HUD Header */}
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        telemetry={telemetry}
      />

      {/* Main Tactical View Controller */}
      <main className="flex-1 min-h-0 w-full flex flex-col overflow-hidden relative">
        {activeTab === 'chat' && (
          <ChatView
            messages={messages}
            onSendMessage={handleSendMessage}
            loading={chatLoading}
          />
        )}

        {activeTab === 'gaming' && (
          <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain scroll-touch">
            <GamingCockpitView
              telemetry={telemetry}
              gamingStatus={gamingStatus}
              onRefresh={fetchTelemetry}
            />
          </div>
        )}

        {activeTab === 'media' && (
          <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain scroll-touch">
            <MediaView />
          </div>
        )}

        {activeTab === 'system' && (
          <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain scroll-touch">
            <SystemView
              telemetry={telemetry}
              onRefresh={fetchTelemetry}
            />
          </div>
        )}
      </main>

      {/* Security Profile Unlock Modal */}
      <UnlockModal
        isOpen={showUnlockModal}
        onClose={() => setShowUnlockModal(false)}
        onSuccess={handleUnlockSuccess}
        profileName="Hermes"
      />
    </div>
  )
}
export default App
