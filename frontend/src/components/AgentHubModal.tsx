import React, { useState, useEffect } from 'react'
import {
  Bot,
  Play,
  CheckCircle2,
  AlertCircle,
  RotateCw,
  Terminal,
  Cpu,
  Search,
  Plus,
  X,
  ChevronDown,
  ChevronRight,
  Wrench,
  Trash2,
  Check,
  Send,
  Sparkles,
  ArrowLeft
} from 'lucide-react'
import type { SpecialistAgent, AgentTask, AntigravitySkill } from '../types'

interface AgentHubModalProps {
  isOpen: boolean
  onClose: () => void
  activeProfile: string
  isAdmin?: boolean
  onSelectAgentForChat?: (agent: SpecialistAgent | null) => void
  selectedAgentId?: string | null
  onOpenAgentConsole?: () => void
}

export const AgentHubModal: React.FC<AgentHubModalProps> = ({
  isOpen,
  onClose,
  activeProfile,
  isAdmin: _isAdmin = false,
  onSelectAgentForChat,
  selectedAgentId,
  onOpenAgentConsole,
}) => {
  const [activeTab, setActiveTab] = useState<'agents' | 'tasks' | 'skills'>('agents')
  const [agents, setAgents] = useState<SpecialistAgent[]>([])
  const [tasks, setTasks] = useState<AgentTask[]>([])
  const [skills, setSkills] = useState<AntigravitySkill[]>([])
  const [loading, setLoading] = useState(false)

  const [expandedTaskId, setExpandedTaskId] = useState<string | null>(null)

  // New task form state
  const [isNewTaskOpen, setIsNewTaskOpen] = useState(false)
  const [taskAgentId, setTaskAgentId] = useState<string>('')
  const [taskGoal, setTaskGoal] = useState('')
  const [taskContext, setTaskContext] = useState('')
  const [submittingTask, setSubmittingTask] = useState(false)

  // Search filters
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch agents
  const fetchAgents = async () => {
    try {
      const res = await fetch('/api/agents')
      if (res.ok) {
        const data = await res.json()
        if (data.ok && Array.isArray(data.agents)) {
          setAgents(data.agents)
          if (!taskAgentId && data.agents.length > 0) {
            setTaskAgentId(data.agents[0].id)
          }
        }
      }
    } catch (e) {
      console.error('Failed to fetch agents:', e)
    }
  }

  // Fetch tasks
  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/agent-tasks')
      if (res.ok) {
        const data = await res.json()
        if (data.ok && Array.isArray(data.tasks)) {
          setTasks(data.tasks)
        }
      }
    } catch (e) {
      console.error('Failed to fetch tasks:', e)
    }
  }

  // Fetch Antigravity skills
  const fetchSkills = async () => {
    try {
      const res = await fetch('/api/antigravity/skills')
      if (res.ok) {
        const data = await res.json()
        if (data.ok && Array.isArray(data.skills)) {
          setSkills(data.skills)
        }
      }
    } catch (e) {
      console.error('Failed to fetch skills:', e)
    }
  }

  useEffect(() => {
    if (isOpen) {
      setLoading(true)
      Promise.all([fetchAgents(), fetchTasks(), fetchSkills()]).finally(() => setLoading(false))
    }
  }, [isOpen])

  // Polling for tasks when tasks tab is active
  useEffect(() => {
    if (!isOpen || activeTab !== 'tasks') return
    const timer = setInterval(fetchTasks, 3000)
    return () => clearInterval(timer)
  }, [isOpen, activeTab])

  const handleDispatchTask = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!taskGoal.trim() || !taskAgentId) return
    setSubmittingTask(true)
    try {
      const res = await fetch('/api/agent-tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: taskAgentId,
          goal: taskGoal.trim(),
          context: taskContext.trim(),
          profile: activeProfile,
        }),
      })
      if (res.ok) {
        setTaskGoal('')
        setTaskContext('')
        setIsNewTaskOpen(false)
        setActiveTab('tasks')
        await fetchTasks()
      }
    } catch (e) {
      console.error('Failed to dispatch task:', e)
    } finally {
      setSubmittingTask(false)
    }
  }

  const handleCancelTask = async (taskId: string) => {
    try {
      await fetch(`/api/agent-tasks/${encodeURIComponent(taskId)}/cancel`, { method: 'POST' })
      await fetchTasks()
    } catch (e) {
      console.error('Failed to cancel task:', e)
    }
  }

  const handleClearCompleted = async () => {
    try {
      await fetch('/api/agent-tasks/completed', { method: 'DELETE' })
      await fetchTasks()
    } catch (e) {
      console.error('Failed to clear tasks:', e)
    }
  }

  if (!isOpen) return null

  const filteredAgents = agents.filter(
    a =>
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.purpose.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredTasks = tasks.filter(
    t =>
      t.goal.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.agent_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredSkills = skills.filter(
    s =>
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.category.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/75 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl h-[88vh] max-h-[850px] bg-[var(--bg-dark)] border border-[var(--border-dark)] rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div
          className="flex-none px-4 sm:px-5 py-3 sm:py-4 border-b border-[var(--border-dark)] flex items-center justify-between bg-[var(--card-dark)]/60"
          style={{
            paddingTop: 'max(env(safe-area-inset-top, 0px), var(--native-safe-top, 0px), 12px)',
          }}
        >
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-[var(--card-hover)] hover:bg-[var(--bg-dark)] border border-[var(--border-dark)] text-neutral-300 hover:text-white transition-colors cursor-pointer flex items-center gap-1 text-xs font-semibold sm:hidden"
              title="Back to chat"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back</span>
            </button>
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-white shadow-md flex-none">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm sm:text-base font-bold text-white tracking-wide">Doshie Working Agents</h2>
                {loading && <RotateCw className="w-3.5 h-3.5 animate-spin text-[var(--accent-light)]" />}
                <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full bg-[var(--accent)]/20 text-[var(--accent-light)] border border-[var(--accent)]/40 hidden sm:inline">
                  Autonomous Core
                </span>
              </div>
              <p className="text-xs text-neutral-400 hidden sm:block">
                Specialist AI agents, autonomous background execution, and Google Antigravity skills.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-neutral-400 hover:text-white hover:bg-[var(--card-hover)] transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Bar & Search */}
        <div className="flex-none px-5 py-3 border-b border-[var(--border-dark)] flex flex-wrap items-center justify-between gap-3 bg-[var(--bg-dark)]/80">
          {/* Navigation Tabs */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)] text-xs font-semibold">
            <button
              onClick={() => setActiveTab('agents')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'agents'
                  ? 'bg-[var(--accent)] text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]'
              }`}
            >
              <Bot className="w-3.5 h-3.5" />
              <span>Specialist Agents ({agents.length})</span>
            </button>
            <button
              onClick={() => setActiveTab('tasks')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'tasks'
                  ? 'bg-[var(--accent)] text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>
                Background Tasks ({tasks.filter(t => t.status === 'running' || t.status === 'queued').length}/
                {tasks.length})
              </span>
            </button>
            <button
              onClick={() => setActiveTab('skills')}
              className={`px-3 py-1.5 rounded-lg flex items-center gap-2 transition-all cursor-pointer ${
                activeTab === 'skills'
                  ? 'bg-[var(--accent)] text-white shadow-sm'
                  : 'text-neutral-400 hover:text-white hover:bg-[var(--card-hover)]'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span>Antigravity Skills ({skills.length})</span>
            </button>

            {onOpenAgentConsole && (
              <button
                type="button"
                onClick={onOpenAgentConsole}
                className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-teal-300 hover:text-white bg-teal-950/70 hover:bg-teal-900 border border-teal-500/40 transition-all cursor-pointer font-bold shadow-sm"
                title="Launch Autonomous Agent Console & CLI"
              >
                <Terminal className="w-3.5 h-3.5 text-teal-400" />
                <span>Agent CLI</span>
              </button>
            )}
          </div>

          {/* Search bar & Action button */}
          <div className="flex items-center gap-2 flex-1 max-w-xs">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder={`Search ${activeTab}...`}
                className="w-full pl-8 pr-3 py-1.5 bg-[var(--card-dark)] border border-[var(--border-dark)] rounded-lg text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)]"
              />
            </div>

            {activeTab === 'tasks' && (
              <button
                onClick={() => setIsNewTaskOpen(!isNewTaskOpen)}
                className="px-3 py-1.5 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white text-xs font-semibold flex items-center gap-1.5 transition-all flex-none cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">New Goal</span>
              </button>
            )}
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* TAB 1: SPECIALIST AGENTS */}
          {activeTab === 'agents' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {filteredAgents.map(agent => {
                const isSelected = selectedAgentId === agent.id
                return (
                  <div
                    key={agent.id}
                    style={{ borderTopColor: agent.accent || 'var(--accent)' }}
                    className={`relative p-4 rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)] border-t-4 transition-all flex flex-col justify-between hover:shadow-lg ${
                      isSelected ? 'ring-2 ring-[var(--accent)]' : ''
                    }`}
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2.5">
                          <div
                            style={{ backgroundColor: `${agent.accent || '#35f2d0'}20`, color: agent.accent || '#35f2d0' }}
                            className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm"
                          >
                            {agent.name.charAt(0)}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="text-sm font-bold text-white">{agent.name}</h3>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-dark)] border border-[var(--border-dark)] text-neutral-300 font-mono">
                                {agent.model_mode}
                              </span>
                            </div>
                            <span className="text-[11px] text-neutral-400">Scope: {agent.memory_scope}</span>
                          </div>
                        </div>

                        {isSelected && (
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-[var(--accent)]/20 text-[var(--accent-light)] font-bold flex items-center gap-1 border border-[var(--accent)]/40">
                            <Check className="w-3 h-3" /> Active in Chat
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-neutral-300 mb-3 leading-relaxed">{agent.purpose}</p>

                      {/* Capabilities pills */}
                      <div className="flex flex-wrap gap-1.5 mb-4">
                        {agent.capabilities.map(cap => (
                          <span
                            key={cap}
                            className="text-[10px] px-2 py-0.5 rounded-md bg-[var(--bg-dark)] border border-[var(--border-dark)] text-neutral-300 font-mono flex items-center gap-1"
                          >
                            <Wrench className="w-2.5 h-2.5 text-[var(--accent-light)]" />
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 pt-2 border-t border-[var(--border-dark)]/60">
                      <button
                        onClick={() => {
                          if (onSelectAgentForChat) {
                            onSelectAgentForChat(isSelected ? null : agent)
                          }
                          onClose()
                        }}
                        className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-neutral-800 text-neutral-300 hover:text-white'
                            : 'bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white shadow-sm'
                        }`}
                      >
                        <Bot className="w-3.5 h-3.5" />
                        <span>{isSelected ? 'Reset to Default Doshie' : `Chat as ${agent.name}`}</span>
                      </button>

                      <button
                        onClick={() => {
                          setTaskAgentId(agent.id)
                          setIsNewTaskOpen(true)
                          setActiveTab('tasks')
                        }}
                        title="Assign autonomous background task"
                        className="py-1.5 px-3 rounded-lg bg-[var(--card-hover)] hover:bg-[var(--accent)]/20 hover:text-[var(--accent-light)] border border-[var(--border-dark)] text-neutral-300 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer"
                      >
                        <Play className="w-3 h-3" />
                        <span>Dispatch Goal</span>
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* TAB 2: AUTONOMOUS BACKGROUND TASKS */}
          {activeTab === 'tasks' && (
            <div className="space-y-4">
              {/* New Task Dispatch Drawer */}
              {isNewTaskOpen && (
                <form
                  onSubmit={handleDispatchTask}
                  className="p-4 rounded-xl bg-[var(--card-dark)] border border-[var(--accent)]/40 shadow-lg space-y-3 animate-fadeIn"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[var(--accent-light)]" />
                      Dispatch Autonomous Agent Goal
                    </h3>
                    <button
                      type="button"
                      onClick={() => setIsNewTaskOpen(false)}
                      className="text-neutral-400 hover:text-white"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-neutral-300 mb-1">
                        Assigned Specialist Agent
                      </label>
                      <select
                        value={taskAgentId}
                        onChange={e => setTaskAgentId(e.target.value)}
                        className="w-full py-1.5 px-2.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] text-xs text-white focus:outline-none focus:border-[var(--accent)] cursor-pointer"
                      >
                        {agents.map(a => (
                          <option key={a.id} value={a.id}>
                            {a.name} ({a.purpose.slice(0, 35)}...)
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="sm:col-span-2">
                      <label className="block text-[11px] font-semibold text-neutral-300 mb-1">
                        High-Level Goal / Objective
                      </label>
                      <input
                        type="text"
                        value={taskGoal}
                        onChange={e => setTaskGoal(e.target.value)}
                        placeholder="e.g. Research latest news on quantum computing and summarize key breakthroughs"
                        className="w-full py-1.5 px-3 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)]"
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-neutral-300 mb-1">
                      Additional Context / Constraints (Optional)
                    </label>
                    <textarea
                      value={taskContext}
                      onChange={e => setTaskContext(e.target.value)}
                      placeholder="Provide specific URLs, file paths, parameters, or guidelines..."
                      rows={2}
                      className="w-full p-2.5 rounded-lg bg-[var(--bg-dark)] border border-[var(--border-dark)] text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-[var(--accent)]"
                    />
                  </div>

                  <div className="flex justify-end gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => setIsNewTaskOpen(false)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold text-neutral-400 hover:text-white hover:bg-[var(--card-hover)] cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={submittingTask || !taskGoal.trim()}
                      className="px-4 py-1.5 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent)]/90 text-white text-xs font-bold flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
                    >
                      {submittingTask ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                      <span>Launch Autonomous Task</span>
                    </button>
                  </div>
                </form>
              )}

              {/* Tasks Toolbar */}
              <div className="flex items-center justify-between text-xs text-neutral-400 px-1">
                <span>Autonomous Task Runs ({filteredTasks.length})</span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={fetchTasks}
                    className="p-1 text-neutral-400 hover:text-white rounded hover:bg-[var(--card-hover)] transition-all cursor-pointer"
                    title="Refresh task list"
                  >
                    <RotateCw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={handleClearCompleted}
                    className="flex items-center gap-1 text-[11px] text-neutral-400 hover:text-amber-300 transition-all cursor-pointer"
                  >
                    <Trash2 className="w-3 h-3" />
                    <span>Clear Finished</span>
                  </button>
                </div>
              </div>

              {/* Tasks List */}
              {filteredTasks.length === 0 ? (
                <div className="p-8 text-center bg-[var(--card-dark)] border border-[var(--border-dark)] rounded-xl text-neutral-400 space-y-2">
                  <Cpu className="w-8 h-8 mx-auto text-neutral-500 opacity-60" />
                  <p className="text-xs">No autonomous tasks yet.</p>
                  <button
                    onClick={() => setIsNewTaskOpen(true)}
                    className="px-3 py-1.5 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold cursor-pointer"
                  >
                    Create First Agent Goal
                  </button>
                </div>
              ) : (
                filteredTasks.map(t => {
                  const isExpanded = expandedTaskId === t.id
                  const isRunning = t.status === 'running' || t.status === 'queued'

                  return (
                    <div
                      key={t.id}
                      className="rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)] overflow-hidden transition-all"
                    >
                      {/* Task Summary Row */}
                      <div
                        onClick={() => setExpandedTaskId(isExpanded ? null : t.id)}
                        className="p-4 flex items-center justify-between gap-3 cursor-pointer hover:bg-[var(--card-hover)]/40 transition-colors"
                      >
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <div
                            style={{ backgroundColor: `${t.agent_accent || '#35f2d0'}25`, color: t.agent_accent || '#35f2d0' }}
                            className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs flex-none"
                          >
                            {t.agent_name.charAt(0)}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-bold text-white truncate">{t.goal}</span>
                            </div>
                            <div className="flex items-center gap-2 text-[11px] text-neutral-400 mt-0.5">
                              <span className="text-[var(--accent-light)] font-medium">{t.agent_name}</span>
                              <span>·</span>
                              <span>{new Date(t.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              <span>·</span>
                              <span>{t.steps?.length || 0} tool steps</span>
                            </div>
                          </div>
                        </div>

                        {/* Status badge & controls */}
                        <div className="flex items-center gap-3 flex-none">
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1.5 border ${
                              t.status === 'completed'
                                ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800'
                                : t.status === 'running'
                                ? 'bg-amber-950/60 text-amber-300 border-amber-800 animate-pulse'
                                : t.status === 'failed'
                                ? 'bg-rose-950/60 text-rose-300 border-rose-800'
                                : 'bg-neutral-800 text-neutral-400 border-neutral-700'
                            }`}
                          >
                            {t.status === 'completed' && <CheckCircle2 className="w-3 h-3" />}
                            {t.status === 'running' && <RotateCw className="w-3 h-3 animate-spin" />}
                            {t.status === 'failed' && <AlertCircle className="w-3 h-3" />}
                            {t.status}
                          </span>

                          {isRunning && (
                            <button
                              onClick={e => {
                                e.stopPropagation()
                                handleCancelTask(t.id)
                              }}
                              className="text-[10px] px-2 py-1 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-200 border border-rose-800 font-semibold cursor-pointer"
                            >
                              Cancel
                            </button>
                          )}

                          {isExpanded ? <ChevronDown className="w-4 h-4 text-neutral-400" /> : <ChevronRight className="w-4 h-4 text-neutral-400" />}
                        </div>
                      </div>

                      {/* Progress Bar */}
                      {isRunning && (
                        <div className="w-full bg-[var(--bg-dark)] h-1 overflow-hidden">
                          <div
                            style={{ width: `${t.progress || 20}%` }}
                            className="bg-[var(--accent)] h-full transition-all duration-500 animate-pulse"
                          />
                        </div>
                      )}

                      {/* Expandable Step-by-Step Execution Logs */}
                      {isExpanded && (
                        <div className="p-4 border-t border-[var(--border-dark)] bg-[var(--bg-dark)]/60 space-y-3">
                          {t.result && (
                            <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-800/60 space-y-1.5">
                              <div className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                                <CheckCircle2 className="w-3.5 h-3.5" />
                                Final Agent Synthesis & Report
                              </div>
                              <p className="text-xs text-neutral-200 whitespace-pre-wrap leading-relaxed">{t.result}</p>
                            </div>
                          )}

                          {t.error && (
                            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-xs text-rose-300">
                              <strong>Error:</strong> {t.error}
                            </div>
                          )}

                          {/* Step-by-step trace */}
                          <div>
                            <h4 className="text-[11px] font-bold text-neutral-400 uppercase tracking-wider mb-2">
                              Agent Execution Trace ({t.steps?.length || 0} Steps)
                            </h4>
                            <div className="space-y-2">
                              {t.steps?.map((step, idx) => (
                                <div
                                  key={idx}
                                  className="p-3 rounded-lg bg-[var(--card-dark)] border border-[var(--border-dark)] text-xs space-y-1.5 font-mono"
                                >
                                  <div className="flex items-center justify-between text-[11px] text-neutral-400">
                                    <span className="font-semibold text-[var(--accent-light)]">Step {step.step}: {step.type}</span>
                                    <span>{new Date(step.timestamp).toLocaleTimeString()}</span>
                                  </div>

                                  {step.thought && (
                                    <div className="text-neutral-300 bg-[var(--bg-dark)]/50 p-2 rounded border border-[var(--border-dark)]/40 text-[11px]">
                                      💭 {step.thought}
                                    </div>
                                  )}

                                  {step.tool_calls && step.tool_calls.length > 0 && (
                                    <div className="space-y-1 pt-1">
                                      {step.tool_calls.map((tc, tcIdx) => (
                                        <div key={tcIdx} className="p-2 rounded bg-black/40 border border-neutral-800 text-[11px]">
                                          <div className="flex items-center gap-1.5 text-amber-300 font-bold">
                                            <Wrench className="w-3 h-3" />
                                            <span>Tool: {tc.tool}</span>
                                          </div>
                                          <div className="text-neutral-400 mt-1 truncate">
                                            Args: {JSON.stringify(tc.arguments)}
                                          </div>
                                          {tc.result && (
                                            <div className="text-emerald-300/90 mt-1 max-h-24 overflow-y-auto whitespace-pre-wrap">
                                              Out: {typeof tc.result === 'string' ? tc.result : JSON.stringify(tc.result, null, 2)}
                                            </div>
                                          )}
                                          {tc.error && (
                                            <div className="text-rose-400 mt-1">
                                              Err: {tc.error}
                                            </div>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })
              )}
            </div>
          )}

          {/* TAB 3: ANTIGRAVITY SKILLS */}
          {activeTab === 'skills' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-gradient-to-r from-cyan-950/40 to-blue-950/40 border border-cyan-800/50 flex items-center justify-between text-xs text-cyan-200">
                <div className="flex items-center gap-2.5">
                  <Terminal className="w-5 h-5 text-cyan-400" />
                  <div>
                    <strong className="block text-white font-semibold">Google Antigravity Multi-Agent Skills</strong>
                    <span>Discovered from local plugins and Antigravity SDK CLI runtime.</span>
                  </div>
                </div>
                <span className="text-[11px] px-2.5 py-1 rounded-full bg-cyan-900/60 border border-cyan-700 text-cyan-300 font-bold">
                  {skills.length} Loaded
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {filteredSkills.map(skill => (
                  <div
                    key={skill.name}
                    className="p-3.5 rounded-xl bg-[var(--card-dark)] border border-[var(--border-dark)] hover:border-cyan-500/40 transition-all flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-xs font-bold text-white truncate font-mono">{skill.name}</span>
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-[var(--bg-dark)] border border-[var(--border-dark)] text-neutral-400 font-semibold uppercase">
                          {skill.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-neutral-300 line-clamp-3 leading-relaxed mb-2">
                        {skill.description}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-[var(--border-dark)]/50 text-[10px] text-neutral-500 font-mono truncate">
                      {skill.path}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
