import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { GameSummary, ExperienceReview, Player } from '../../types/game'

// ---- 头像颜色 ----

const AVATAR_COLORS = [
  'from-rose-500 to-pink-600',
  'from-violet-500 to-purple-600',
  'from-blue-500 to-indigo-600',
  'from-cyan-500 to-teal-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
]

function getAvatarColor(playerId: string): string {
  let hash = 0
  for (let i = 0; i < playerId.length; i++) {
    hash = ((hash << 5) - hash + playerId.charCodeAt(i)) | 0
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

// ---- 触发条件中文映射 ----

const TRIGGER_LABELS: Record<string, string> = {
  chip_crisis: '筹码危机',
  consecutive_losses: '连续输牌',
  big_loss: '大额损失',
  opponent_shift: '对手行为突变',
  periodic: '定期回顾',
}

// ---- 可折叠区块 ----

function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
  badge,
}: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
  badge?: string | number
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="border border-green-700/30 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-2.5
          bg-green-900/30 hover:bg-green-900/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-green-300">{title}</span>
          {badge !== undefined && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-700/40 text-green-400/80">
              {badge}
            </span>
          )}
        </div>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-green-500/60 text-xs"
        >
          ▼
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-4 py-3 text-sm leading-relaxed text-green-200/80">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// ---- 统计条 ----

function StatBar({ label, value, suffix = '' }: { label: string; value: string | number; suffix?: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-green-400/60 text-xs">{label}</span>
      <span className="text-green-200 text-sm font-medium tabular-nums">
        {value}{suffix}
      </span>
    </div>
  )
}

// ---- 主组件 ----

interface AgentSummaryCardProps {
  player: Player
  summary: GameSummary | null
  reviews: ExperienceReview[]
  loading?: boolean
  initialOpen?: boolean
}

export default function AgentSummaryCard({
  player,
  summary,
  reviews,
  loading = false,
  initialOpen = false,
}: AgentSummaryCardProps) {
  const [isExpanded, setIsExpanded] = useState(initialOpen)

  if (loading) {
    return (
      <div className="bg-green-900/20 border border-green-700/30 rounded-xl p-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-green-800/40 animate-pulse" />
          <div className="space-y-2 flex-1">
            <div className="h-4 w-24 bg-green-800/40 rounded animate-pulse" />
            <div className="h-3 w-16 bg-green-800/30 rounded animate-pulse" />
          </div>
        </div>
      </div>
    )
  }

  const winRate = summary
    ? summary.rounds_played > 0
      ? ((summary.rounds_won / summary.rounds_played) * 100).toFixed(1)
      : '0.0'
    : '-'
  const foldRate = summary ? (summary.fold_rate * 100).toFixed(1) : '-'

  return (
    <motion.div
      layout
      className="bg-green-900/20 border border-green-700/30 rounded-xl overflow-hidden"
    >
      {/* 头部 - 始终可见 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-4 px-5 py-4
          hover:bg-green-900/30 transition-colors cursor-pointer"
      >
        {/* 头像 */}
        <div
          className={`w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-sm
            bg-gradient-to-br ${getAvatarColor(player.id)} shrink-0`}
        >
          {player.avatar || player.name.charAt(0)}
        </div>

        {/* 基本信息 */}
        <div className="flex-1 min-w-0 text-left">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-green-200 truncate">{player.name}</span>
            {player.personality && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-800/40 text-green-400/70 border border-green-700/30 shrink-0">
                {player.personality}
              </span>
            )}
          </div>
          {summary && (
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-xs text-green-500/60">
                {summary.rounds_played} 局 / 胜率 {winRate}%
              </span>
              <span className="text-xs text-green-600/40">|</span>
              <span className="text-xs text-green-500/60">
                弃牌率 {foldRate}%
              </span>
            </div>
          )}
        </div>

        {/* 展开按钮 */}
        <motion.span
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-green-500/50 text-sm shrink-0"
        >
          ▼
        </motion.span>
      </button>

      {/* 展开内容 */}
      <AnimatePresence initial={false}>
        {isExpanded && summary && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-3">
              {/* 统计数据 */}
              <CollapsibleSection title="统计数据" defaultOpen>
                <div className="grid grid-cols-2 gap-x-6 gap-y-0.5">
                  <StatBar label="总局数" value={summary.rounds_played} />
                  <StatBar label="胜局" value={summary.rounds_won} />
                  <StatBar label="胜率" value={winRate} suffix="%" />
                  <StatBar label="弃牌率" value={foldRate} suffix="%" />
                  <StatBar label="最大赢" value={`+${summary.biggest_win}`} />
                  <StatBar label="最大输" value={`-${summary.biggest_loss}`} />
                  <StatBar label="总赢筹码" value={`+${summary.total_chips_won}`} />
                  <StatBar label="总输筹码" value={`-${summary.total_chips_lost}`} />
                </div>
              </CollapsibleSection>

              {/* 关键时刻 */}
              {summary.key_moments.length > 0 && (
                <CollapsibleSection title="关键时刻回顾" badge={summary.key_moments.length}>
                  <ul className="space-y-2">
                    {summary.key_moments.map((moment, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="text-amber-400/60 shrink-0">*</span>
                        <span>{moment}</span>
                      </li>
                    ))}
                  </ul>
                </CollapsibleSection>
              )}

              {/* 对手印象 */}
              {Object.keys(summary.opponent_impressions).length > 0 && (
                <CollapsibleSection
                  title="对手印象评价"
                  badge={Object.keys(summary.opponent_impressions).length}
                >
                  <div className="space-y-3">
                    {Object.entries(summary.opponent_impressions).map(([name, impression]) => (
                      <div key={name}>
                        <span className="text-green-300 font-medium text-xs">{name}:</span>
                        <p className="mt-0.5 text-green-200/70 pl-2 border-l-2 border-green-700/30">
                          {impression}
                        </p>
                      </div>
                    ))}
                  </div>
                </CollapsibleSection>
              )}

              {/* 自我风格总结 */}
              {summary.self_reflection && (
                <CollapsibleSection title="自我风格总结">
                  <p className="whitespace-pre-line">{summary.self_reflection}</p>
                </CollapsibleSection>
              )}

              {/* 聊天策略总结 */}
              {summary.chat_strategy_summary && (
                <CollapsibleSection title="聊天策略总结">
                  <p className="whitespace-pre-line">{summary.chat_strategy_summary}</p>
                </CollapsibleSection>
              )}

              {/* 学习历程 */}
              {summary.learning_journey && (
                <CollapsibleSection title="学习历程">
                  <p className="whitespace-pre-line">{summary.learning_journey}</p>
                </CollapsibleSection>
              )}

              {/* 整体叙事总结 */}
              {summary.narrative_summary && (
                <CollapsibleSection title="叙事总结">
                  <p className="whitespace-pre-line italic text-green-200/70">
                    {summary.narrative_summary}
                  </p>
                </CollapsibleSection>
              )}

              {/* 经验回顾记录 */}
              {reviews.length > 0 && (
                <CollapsibleSection title="策略调整记录" badge={reviews.length}>
                  <div className="space-y-4">
                    {reviews.map((review, i) => (
                      <div key={i} className="border-l-2 border-amber-500/40 pl-3 space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-amber-400/80 text-xs font-medium">
                            {TRIGGER_LABELS[review.trigger] || review.trigger}
                          </span>
                          <span className="text-green-600/40 text-xs">
                            第 {review.triggered_at_round} 局后触发
                          </span>
                        </div>
                        {review.self_analysis && (
                          <p className="text-green-200/70 text-xs">{review.self_analysis}</p>
                        )}
                        {review.strategy_adjustment && (
                          <p className="text-amber-300/70 text-xs">
                            策略调整: {review.strategy_adjustment}
                          </p>
                        )}
                        {Object.keys(review.opponent_patterns).length > 0 && (
                          <div className="text-xs text-green-400/60">
                            {Object.entries(review.opponent_patterns).map(([name, pattern]) => (
                              <div key={name} className="mt-1">
                                <span className="text-green-400/80">{name}:</span>{' '}
                                <span className="text-green-200/60">{pattern}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CollapsibleSection>
              )}
            </div>
          </motion.div>
        )}

        {/* 没有 summary 数据时的提示 */}
        {isExpanded && !summary && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-4 text-sm text-green-600/50">
              暂无总结数据
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
