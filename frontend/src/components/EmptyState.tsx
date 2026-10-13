import React from 'react'

interface EmptyStateProps {
  onSelectPrompt: (prompt: string) => void
  assistantEmoji?: string
  greetingTitle?: string
  greetingSubtitle?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  onSelectPrompt: _onSelectPrompt,
  greetingTitle = 'doshie',
  greetingSubtitle = 'Ready to assist. Ask anything or propose commands to execute.',
}) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-md mx-auto text-center select-none font-mono">
      <div className="text-xl font-bold text-white tracking-widest mb-1">
        {greetingTitle}
      </div>
      <p className="text-xs text-neutral-400 max-w-sm leading-relaxed">
        {greetingSubtitle}
      </p>
    </div>
  )
}

export default EmptyState
