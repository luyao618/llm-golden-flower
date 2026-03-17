import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ScrollText, ChevronDown } from 'lucide-react'
import { useGameStore, type ActionLogEntry } from '../../stores/gameStore'
import { useUIStore } from '../../stores/uiStore'
import type { GameAction } from '../../types/game'

// ---- Action display config ----

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

  return { icon, text: `${entry.player_name} ${label}`, detail, color }
}

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

// ---- Single log entry ----

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
      className="flex items-center gap-2 text-xs py-1 px-2 rounded-md hover:bg-white/[0.03] transition-colors"
      initial={isNew ? { opacity: 0, x: -10, filter: 'blur(4px)' } : false}
      animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {/* Time */}
      <span className="text-[var(--text-disabled)] font-mono shrink-0 text-[10px] leading-4 tabular-nums">
        {formatTime(entry.timestamp)}
      </span>

      {/* Icon */}
      <span className={`${color} shrink-0 leading-4 text-[11px]`}>{icon}</span>

      {/* Player + action */}
      <span className="text-[var(--text-secondary)] leading-4 truncate">{text}</span>

      {/* Detail */}
      {detail && (
        <span className={`${color} font-medium leading-4 shrink-0 text-[11px]`}>{detail}</span>
      )}

      {/* Fallback indicator */}
      {entry.is_fallback && (
        <span className="text-[9px] px-1 py-0.5 rounded bg-orange-500/15 text-orange-400/90 border border-orange-500/20 shrink-0 leading-3">
          LLM降级
        </span>
      )}
    </motion.div>
  )
}

// ---- Chip icon SVG ----

function ChipIcon({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.9" />
      <circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" strokeWidth="1" opacity="0.5" />
      <circle cx="12" cy="12" r="4" fill="currentColor" opacity="0.6" />
    </svg>
  )
}

// ---- Main merged component ----

/**
 * GameInfoPanel — 合并的底池信息 + 行动日志面板
 *
 * 置于牌桌中央上方，统一 UI 风格（赛博朋克毛玻璃）
 * 上半部分：底池筹码、局信息、注额、在局人数
 * 下半部分：行动日志（最少显示 5 条），可折叠，带动画
 */
export default function GameInfoPanel() {
  const actionLog = useGameStore((s) => s.actionLog)
  const currentRound = useGameStore((s) => s.currentRound)
  const players = useGameStore((s) => s.players)
  const isExpanded = useUIStore((s) => s.isGameLogExpanded)
  const toggleGameLog = useUIStore((s) => s.toggleGameLog)
  const scrollRef = useRef<HTMLDivElement>(null)
  const prevLengthRef = useRef(0)

  // Auto-scroll to bottom on new entries
  useEffect(() => {
    if (scrollRef.current && actionLog.length > prevLengthRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
    prevLengthRef.current = actionLog.length
  }, [actionLog.length])

  // Active (non-folded, non-out) player count
  const activePlayers = players.filter(
    (p) => p.status !== 'folded' && p.status !== 'out'
  ).length

  const pot = currentRound?.pot ?? 0
  const currentBet = currentRound?.current_bet ?? 0
  const roundNumber = currentRound?.round_number ?? 0

  return (
    <div className="flex flex-col w-[340px] bg-black/50 backdrop-blur-md border border-[var(--color-primary)]/15 rounded-xl overflow-hidden shadow-[0_4px_40px_rgba(0,0,0,0.5),0_0_20px_rgba(0,212,255,0.05)]">

      {/* ===== Top: Pot & Game Info ===== */}
      <div className="px-4 pt-3 pb-2">
        {/* Pot amount - hero display */}
        <div className="flex items-center justify-center gap-2.5 mb-2">
          <ChipIcon className="w-5 h-5 text-[var(--color-gold)]" />
          <AnimatePresence mode="wait">
            <motion.span
              key={pot}
              initial={{ scale: 0.85, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.85, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="neon-text-gold font-bold text-2xl tabular-nums tracking-wide"
            >
              {pot.toLocaleString()}
            </motion.span>
          </AnimatePresence>
        </div>

        {/* Stats row */}
        <div className="flex items-center justify-center gap-3 text-[11px]">
          <span className="text-[var(--text-muted)]">
            第 <span className="text-[var(--text-secondary)] font-medium">{roundNumber}</span> 局
          </span>
          <span className="text-[var(--text-disabled)]">|</span>
          {currentRound && (
            <>
              <span className="text-[var(--text-muted)]">
                轮次 <span className="text-[var(--text-secondary)] tabular-nums">{currentRound.turn_count}/{currentRound.max_turns}</span>
              </span>
              <span className="text-[var(--text-disabled)]">|</span>
            </>
          )}
          <span className="text-[var(--text-muted)]">
            注额 <span className="text-[var(--color-gold)]/80 font-medium tabular-nums">{currentBet}</span>
          </span>
          <span className="text-[var(--text-disabled)]">|</span>
          <span className="text-[var(--text-muted)]">
            <span className="text-[var(--text-secondary)] tabular-nums">{activePlayers}</span> 人在局
          </span>
        </div>
      </div>

      {/* ===== Divider ===== */}
      <div className="h-px bg-gradient-to-r from-transparent via-[var(--color-primary)]/20 to-transparent" />

      {/* ===== Bottom: Action Log Toggle ===== */}
      <button
        onClick={toggleGameLog}
        className="group flex items-center justify-between px-4 py-2 hover:bg-white/[0.04] transition-all cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <ScrollText className="w-3.5 h-3.5 text-[var(--color-primary)]/50 group-hover:text-[var(--color-primary)]/80 transition-colors" />
          <span className="text-[var(--color-primary)]/70 group-hover:text-[var(--color-primary)] text-xs font-medium transition-colors">
            行动日志
          </span>
          {actionLog.length > 0 && (
            <span className="text-[9px] tabular-nums px-1.5 py-0.5 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)]/60 border border-[var(--color-primary)]/10">
              {actionLog.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
          >
            <ChevronDown className="w-3.5 h-3.5 text-[var(--color-primary)]/40 group-hover:text-[var(--color-primary)]/70 transition-colors" />
          </motion.div>
        </div>
      </button>

      {/* ===== Expandable action log area with smooth animation ===== */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            key="action-log-area"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 140, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            className="flex flex-col overflow-hidden border-t border-white/[0.04]"
          >
            {/* Scrollable log entries */}
            <div
              ref={scrollRef}
              className="flex-1 min-h-0 overflow-y-auto px-2 py-1 space-y-0 game-info-scroll"
            >
              {actionLog.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <span className="text-[var(--text-disabled)] text-xs italic">
                    {currentRound
                      ? '等待玩家行动...'
                      : '游戏尚未开始'}
                  </span>
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
