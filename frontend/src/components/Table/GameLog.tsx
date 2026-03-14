import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore, type ActionLogEntry } from '../../stores/gameStore'
import { useUIStore } from '../../stores/uiStore'
import type { GameAction } from '../../types/game'

// ---- Action display text ----

const ACTION_LABELS: Record<GameAction, string> = {
  fold: '弃牌',
  call: '跟注',
  raise: '加注',
  check_cards: '看牌',
  compare: '比牌',
}

const ACTION_ICONS: Record<GameAction, string> = {
  fold: '🏳',
  call: '✓',
  raise: '↑',
  check_cards: '👁',
  compare: '⚔',
}

const ACTION_COLORS: Record<GameAction, string> = {
  fold: 'text-gray-400',
  call: 'text-green-400',
  raise: 'text-amber-400',
  check_cards: 'text-blue-400',
  compare: 'text-rose-400',
}

/**
 * Format a single action log entry into concise text
 */
function formatLogEntry(entry: ActionLogEntry): {
  icon: string
  text: string
  detail: string | null
  color: string
} {
  const icon = ACTION_ICONS[entry.action]
  const label = ACTION_LABELS[entry.action]
  const color = ACTION_COLORS[entry.action]

  let detail: string | null = null

  if (entry.action === 'call' || entry.action === 'raise') {
    detail = `${entry.amount} 筹码`
  }

  if (entry.action === 'compare' && entry.compare_result) {
    const result = entry.compare_result as Record<string, unknown>
    const targetName = (result.loser_name as string) || (result.target_name as string)
    const won = result.winner_id === entry.player_id
    detail = targetName
      ? `vs ${targetName} ${won ? '胜出' : '落败'}`
      : null
  }

  return {
    icon,
    text: `${entry.player_name} ${label}`,
    detail,
    color,
  }
}

/**
 * Format timestamp to display time
 */
function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// ---- Single log entry component ----

function LogEntry({
  entry,
  isNew,
}: {
  entry: ActionLogEntry
  isNew: boolean
}) {
  const { icon, text, detail, color } = formatLogEntry(entry)

  return (
    <motion.div
      className="flex items-start gap-1.5 text-xs py-0.5"
      initial={isNew ? { opacity: 0, x: -10 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
    >
      {/* Time */}
      <span className="text-green-700/50 font-mono shrink-0 text-[10px] leading-4">
        {formatTime(entry.timestamp)}
      </span>

      {/* Icon + text */}
      <span className={`${color} shrink-0 leading-4`}>{icon}</span>
      <span className="text-green-300/90 leading-4">{text}</span>

      {/* Detail (amount, compare result) */}
      {detail && (
        <span className={`${color} font-medium leading-4`}>{detail}</span>
      )}
    </motion.div>
  )
}

// ---- GameLog main component ----

/**
 * GameLog - Action history log panel
 *
 * Displays:
 * - Current round number, bet amount, pot
 * - Scrollable action log with concise entries
 * - AI reviewing experience status
 * - Collapsible/expandable
 */
export default function GameLog() {
  const actionLog = useGameStore((s) => s.actionLog)
  const currentRound = useGameStore((s) => s.currentRound)
  const players = useGameStore((s) => s.players)
  const isExpanded = useUIStore((s) => s.isGameLogExpanded)
  const toggleGameLog = useUIStore((s) => s.toggleGameLog)
  const thinkingPlayerId = useUIStore((s) => s.thinkingPlayerId)
  const reviewingPlayerId = useUIStore((s) => s.reviewingPlayerId)
  const activePlayerId = useUIStore((s) => s.activePlayerId)

  const scrollRef = useRef<HTMLDivElement>(null)
  const prevLengthRef = useRef(0)

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (scrollRef.current && actionLog.length > prevLengthRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
    prevLengthRef.current = actionLog.length
  }, [actionLog.length])

  // Find player names for status hints
  const thinkingPlayer = thinkingPlayerId
    ? players.find((p) => p.id === thinkingPlayerId)
    : null
  const reviewingPlayer = reviewingPlayerId
    ? players.find((p) => p.id === reviewingPlayerId)
    : null
  const activePlayer = activePlayerId
    ? players.find((p) => p.id === activePlayerId)
    : null

  // Count active (non-folded, non-out) players
  const activePlayers = players.filter(
    (p) => p.status !== 'folded' && p.status !== 'out'
  ).length

  return (
    <div className="flex flex-col bg-black/40 border border-green-800/50 rounded-lg overflow-hidden backdrop-blur-sm">
      {/* Header - always visible */}
      <button
        onClick={toggleGameLog}
        className="flex items-center justify-between px-3 py-1.5 bg-black/30 hover:bg-black/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <span className="text-green-400/80 text-xs font-medium">
            行动日志
          </span>
          {currentRound && (
            <span className="text-green-600/60 text-[10px]">
              第 {currentRound.round_number} 局
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {actionLog.length > 0 && (
            <span className="text-green-700/50 text-[10px]">
              {actionLog.length} 条
            </span>
          )}
          <motion.span
            className="text-green-600/60 text-xs"
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            ▾
          </motion.span>
        </div>
      </button>

      {/* Expandable content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {/* Game info bar */}
            {currentRound && (
              <div className="flex items-center gap-3 px-3 py-1 border-b border-green-800/30 text-[10px]">
                <span className="text-green-500/70">
                  轮次 {currentRound.turn_count}/{currentRound.max_turns}
                </span>
                <span className="text-green-800/50">|</span>
                <span className="text-amber-500/70">
                  注额 {currentRound.current_bet}
                </span>
                <span className="text-green-800/50">|</span>
                <span className="text-amber-400/70">
                  底池 {currentRound.pot}
                </span>
                <span className="text-green-800/50">|</span>
                <span className="text-green-500/50">
                  {activePlayers} 人在局
                </span>
              </div>
            )}

            {/* Active player indicator */}
            {activePlayer && currentRound && (
              <div className="flex items-center gap-1.5 px-3 py-1 border-b border-green-800/30">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-amber-400/80 text-[10px]">
                  等待 {activePlayer.name} 行动
                </span>
              </div>
            )}

            {/* Status hints: AI thinking / reviewing */}
            <AnimatePresence>
              {thinkingPlayer && (
                <motion.div
                  key="thinking"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center gap-1.5 px-3 py-1 border-b border-green-800/30"
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                  <span className="text-blue-400/80 text-[10px]">
                    {thinkingPlayer.name} 正在思考...
                  </span>
                </motion.div>
              )}
              {reviewingPlayer && (
                <motion.div
                  key="reviewing"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center gap-1.5 px-3 py-1 border-b border-green-800/30"
                >
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse" />
                  <span className="text-purple-400/80 text-[10px]">
                    {reviewingPlayer.name} 正在回顾经验...
                  </span>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Action log entries */}
            <div
              ref={scrollRef}
              className="max-h-56 overflow-y-auto px-3 py-1 space-y-0.5 scrollbar-thin scrollbar-thumb-green-800/30 scrollbar-track-transparent"
            >
              {actionLog.length === 0 ? (
                <div className="text-green-700/40 text-xs text-center py-2">
                  {currentRound
                    ? '等待玩家行动...'
                    : '游戏尚未开始'}
                </div>
              ) : (
                actionLog.map((entry, index) => (
                  <LogEntry
                    key={`${entry.player_id}-${entry.timestamp}-${index}`}
                    entry={entry}
                    isNew={index >= prevLengthRef.current - 1}
                  />
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
