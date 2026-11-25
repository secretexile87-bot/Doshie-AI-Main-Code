export type TabType = 'chat' | 'gaming' | 'media' | 'system'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  model?: string
  status?: 'sending' | 'sent' | 'error'
}

export interface HardwareTelemetry {
  gpu_temp?: number
  gpu_utilization?: number
  gpu_power_watts?: number
  vram_used_mb?: number
  vram_total_mb?: number
  cpu_percent?: number
  ram_used_gb?: number
  ram_total_gb?: number
  load_avg?: string
  updated_at?: string
}

export interface GamingStatus {
  dallas_ping_ms?: number
  local_ping_ms?: number
  tunnel_active?: boolean
  packet_loss?: number
  status_summary?: string
  ipv6_disabled?: boolean
  ip_forwarding?: boolean
  last_check?: string
}
