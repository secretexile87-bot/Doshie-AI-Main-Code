import React from 'react'
import { Calendar, Sparkles, Code2, Search, Heart } from 'lucide-react'

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
      title: "Humble Reflection",
      desc: "Thoughtful, gentle guidance & encouragement",
      prompt: "Can you share a gentle, humble, and encouraging thought to start my day with peace?",
    },
    {
      icon: <Calendar className="w-4 h-4 text-emerald-400" />,
      title: "Plan our schedule",
      desc: "What routines or tasks are due today?",
      prompt: "What tasks, routines, or reminders are on the schedule for today?",
    },
    {
      icon: <Code2 className="w-4 h-4 text-cyan-400" />,
      title: "Coding & Tech",
      desc: "Debug scripts, APIs, or Linux system tasks",
      prompt: "Can you help me review and improve my project code with clear explanations?",
    },
    {
      icon: <Search className="w-4 h-4 text-teal-400" />,
      title: "Search & Research",
      desc: "Find quick answers and summaries",
      prompt: "Can you help me research and summarize the latest updates on tech and AI?",
    },
    {
      icon: <Sparkles className="w-4 h-4 text-amber-400" />,
      title: "Brainstorming",
      desc: "Organize ideas, dinner menus, or projects",
      prompt: "Give me 3 quick healthy dinner ideas with simple ingredients for tonight.",
    },
  ]

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-4 max-w-lg mx-auto text-center">
      {/* Brand Hero */}
      <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-[var(--accent)] to-[var(--accent-light)] flex items-center justify-center text-3xl shadow-lg shadow-black/50 mb-4 animate-bounce duration-1000">
        {assistantEmoji}
      </div>
      <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
        {greetingTitle}
      </h2>
      <p className="text-xs sm:text-sm text-[var(--accent-light)]/80 mt-1.5 max-w-sm mb-6">
        {greetingSubtitle}
      </p>

      {/* Suggestion Chips */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full text-left">
        {suggestions.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            className="flex items-start gap-3 p-3 rounded-2xl bg-[var(--card-dark)] hover:bg-[var(--card-hover)] border border-[var(--border-dark)] hover:border-[var(--accent)]/50 transition-all duration-150 text-left active:scale-98 group cursor-pointer"
          >
            <div className="p-2 rounded-xl bg-[var(--bg-dark)] border border-[var(--border-dark)] group-hover:border-[var(--accent)]/40">
              {item.icon}
            </div>
            <div>
              <div className="font-medium text-xs sm:text-sm text-neutral-100 group-hover:text-white">
                {item.title}
              </div>
              <div className="text-[11px] text-[var(--accent-light)]/70 line-clamp-1 mt-0.5">
                {item.desc}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
