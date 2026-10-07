import React from 'react'
import { Calendar, Sparkles, Code2, Search, Heart, Bot, ArrowRight } from 'lucide-react'

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void
  assistantEmoji?: string
  greetingTitle?: string
  greetingSubtitle?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  onSelectPrompt,
  assistantEmoji = '🦖',
  greetingTitle = 'How can I help you today?',
  greetingSubtitle = 'Private local AI companion running directly on your RTX 5070 workstation.',
}) => {
  const suggestions = [
    {
      icon: <Heart className="w-4 h-4 text-rose-400" />,
      tag: "Reflection",
      title: "Humble Reflection",
      desc: "Thoughtful, gentle guidance & encouragement",
      prompt: "Can you share a gentle, humble, and encouraging thought to start my day with peace?",
      gradient: "from-rose-500/10 to-orange-500/5",
    },
    {
      icon: <Calendar className="w-4 h-4 text-emerald-400" />,
      tag: "Productivity",
      title: "Plan our schedule",
      desc: "Review daily routines, reminders & tasks",
      prompt: "What tasks, routines, or reminders are on the schedule for today?",
      gradient: "from-emerald-500/10 to-teal-500/5",
    },
    {
      icon: <Code2 className="w-4 h-4 text-sky-400" />,
      tag: "Development",
      title: "Coding & Linux System",
      desc: "Debug scripts, local APIs & Docker services",
      prompt: "Can you help me review and improve my project code with clear explanations?",
      gradient: "from-sky-500/10 to-indigo-500/5",
    },
    {
      icon: <Search className="w-4 h-4 text-teal-400" />,
      tag: "Intelligence",
      title: "Deep Research",
      desc: "Synthesize tech updates and insights",
      prompt: "Can you help me research and summarize the latest updates on tech and AI?",
      gradient: "from-teal-500/10 to-emerald-500/5",
    },
    {
      icon: <Sparkles className="w-4 h-4 text-amber-400" />,
      tag: "Creativity",
      title: "Creative Brainstorming",
      desc: "Meals, project architectures & ideas",
      prompt: "Give me 3 quick healthy dinner ideas with simple ingredients for tonight.",
      gradient: "from-amber-500/10 to-yellow-500/5",
    },
    {
      icon: <Bot className="w-4 h-4 text-purple-400" />,
      tag: "Specialists",
      title: "Specialist Agents",
      desc: "Assign tasks to autonomous specialists",
      prompt: "What specialist agents are currently active and what can they help me accomplish?",
      gradient: "from-purple-500/10 to-pink-500/5",
    },
  ]

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-6 max-w-2xl mx-auto text-center animate-message-enter">
      {/* Brand Hero with Glowing Halo */}
      <div className="relative mb-5 group">
        <div className="absolute -inset-2 bg-gradient-to-r from-[var(--accent)] via-[var(--accent-light)] to-[var(--accent-hover)] rounded-3xl blur-xl opacity-30 group-hover:opacity-50 transition duration-500 animate-pulse-subtle" />
        <div className="relative w-18 h-18 rounded-3xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-4xl shadow-2xl shadow-black/60 border border-white/20 transform group-hover:scale-105 transition-transform duration-300">
          {assistantEmoji}
        </div>
      </div>

      <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight drop-shadow-sm">
        {greetingTitle}
      </h2>
      <p className="text-xs sm:text-sm text-[var(--accent-light)]/85 mt-2 max-w-md mb-8 leading-relaxed font-medium">
        {greetingSubtitle}
      </p>

      {/* Suggestion Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full text-left">
        {suggestions.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            className={`group relative flex items-start gap-3.5 p-3.5 rounded-2xl bg-gradient-to-br ${item.gradient} bg-white/[0.03] hover:bg-white/[0.07] border border-white/10 hover:border-[var(--accent)]/50 transition-all duration-200 text-left active:scale-[0.98] cursor-pointer shadow-lg shadow-black/20 hover:shadow-xl hover:-translate-y-0.5 backdrop-blur-md`}
          >
            <div className="p-2.5 rounded-xl bg-black/40 border border-white/10 group-hover:border-[var(--accent)]/40 transition-colors flex-none shadow-xs">
              {item.icon}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-1 mb-0.5">
                <span className="font-semibold text-xs sm:text-sm text-neutral-100 group-hover:text-white truncate">
                  {item.title}
                </span>
                <span className="text-[9px] uppercase tracking-wider font-semibold text-neutral-400 group-hover:text-[var(--accent-light)] transition-colors opacity-70">
                  {item.tag}
                </span>
              </div>
              <div className="text-[11px] text-neutral-400 group-hover:text-neutral-300 line-clamp-1">
                {item.desc}
              </div>
            </div>
            <ArrowRight className="w-3.5 h-3.5 text-neutral-500 group-hover:text-[var(--accent-light)] opacity-0 group-hover:opacity-100 transition-all self-center -translate-x-1 group-hover:translate-x-0 flex-none" />
          </button>
        ))}
      </div>
    </div>
  )
}
export default EmptyState
