import { motion } from 'framer-motion'
import type { Player } from '../../types/game'
import { getAvatarAccent } from '../../utils/theme'

// ---- 排名徽章 ----

const RANK_STYLES: Record<number, { bg: string; text: string; label: string }> = {
  1: { bg: 'bg-gradient-to-r from-amber-400 to-yellow-500', text: 'text-amber-950', label: '1st' },
  2: { bg: 'bg-gradient-to-r from-gray-300 to-gray-400', text: 'text-gray-800', label: '2nd' },
  3: { bg: 'bg-gradient-to-r from-amber-600 to-amber-700', text: 'text-amber-100', label: '3rd' },
}

function RankBadge({ rank }: { rank: number }) {
  const style = RANK_STYLES[rank]
  if (style) {
    return (
      <div className={`w-8 h-8 rounded-full ${style.bg} flex items-center justify-center`}>
        <span className={`text-xs font-black ${style.text}`}>{style.label}</span>
      </div>
    )
  }
  return (
    <div className="w-8 h-8 rounded-full bg-[var(--bg-surface)] border border-[var(--border-default)] flex items-center justify-center">
      <span className="text-xs font-bold text-[var(--text-muted)]">{rank}th</span>
    </div>
  )
}

// ---- 主组件 ----

export interface LeaderboardPlayer {
  player: Player
  chipChange: number // 总筹码变化
  initialChips: number
}

interface LeaderboardProps {
  rankings: LeaderboardPlayer[]
}

export default function Leaderboard({ rankings }: LeaderboardProps) {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="text-xl font-bold text-[var(--text-primary)] mb-4 text-center"
          style={{ fontFamily: 'var(--font-display)' }}>
        最终排名
      </h2>

      <div className="space-y-2">
        {rankings.map((entry, index) => {
          const rank = index + 1
          const isFirst = rank === 1
          const chipDiff = entry.player.chips - entry.initialChips
          const isPositive = chipDiff > 0
          const isNegative = chipDiff < 0
          const accent = getAvatarAccent(entry.player.id)

          return (
            <motion.div
              key={entry.player.id}
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.12, duration: 0.4, ease: 'easeOut' }}
              className={`
                flex items-center gap-4 px-5 py-3 rounded-xl border transition-all backdrop-blur-sm
                ${isFirst
                  ? 'bg-[var(--color-gold)]/5 border-[var(--color-gold)]/30'
                  : 'bg-[var(--bg-surface)]/30 border-[var(--border-default)] hover:bg-[var(--bg-hover)]/30'
                }
              `}
              style={isFirst ? { boxShadow: '0 0 20px rgba(255, 215, 0, 0.1)' } : undefined}
            >
              {/* 排名 */}
              <RankBadge rank={rank} />

              {/* 头像 — 赛博朋克风格：暗底 + 细边框发光 */}
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm shrink-0"
                style={{
                  background: 'rgba(15, 15, 35, 0.6)',
                  border: `1.5px solid ${isFirst ? 'rgba(255, 215, 0, 0.5)' : accent.border}`,
                  boxShadow: isFirst
                    ? '0 0 8px rgba(255, 215, 0, 0.2), inset 0 0 6px rgba(255, 215, 0, 0.05)'
                    : `0 0 8px ${accent.glow}, inset 0 0 6px ${accent.glow}`,
                  color: isFirst ? 'rgba(255, 225, 140, 0.9)' : accent.text,
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {entry.player.avatar || entry.player.name.charAt(0)}
              </div>

              {/* 名字 + 类型 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold truncate ${isFirst ? 'text-[var(--color-gold)]' : 'text-[var(--text-primary)]'}`}>
                    {entry.player.name}
                  </span>
                  {entry.player.player_type === 'human' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-primary)]/10 text-[var(--color-primary)] border border-[var(--color-primary)]/20">
                      你
                    </span>
                  )}
                  {entry.player.personality && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-elevated)] text-[var(--text-muted)] border border-[var(--border-default)]">
                      {entry.player.personality}
                    </span>
                  )}
                </div>
              </div>

              {/* 筹码变化 */}
              <div className="text-right shrink-0">
                <div className={`text-lg font-bold tabular-nums ${isFirst ? 'neon-text-gold' : 'text-[var(--text-primary)]'}`}
                     style={{ fontFamily: 'var(--font-mono)' }}>
                  {entry.player.chips}
                </div>
                <div
                  className={`text-xs font-medium tabular-nums ${
                    isPositive ? 'text-[var(--color-success)]' : isNegative ? 'text-[var(--color-danger)]' : 'text-[var(--text-muted)]'
                  }`}
                  style={{ fontFamily: 'var(--font-mono)' }}
                >
                  {isPositive ? '+' : ''}{chipDiff}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
