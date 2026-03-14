import { motion } from 'framer-motion'
import type { Player } from '../../types/game'
import { getAvatarColor } from '../../utils/theme'

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
    <div className="w-8 h-8 rounded-full bg-green-900/60 border border-green-700/40 flex items-center justify-center">
      <span className="text-xs font-bold text-green-500/80">{rank}th</span>
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
      <h2 className="text-xl font-bold text-amber-400 mb-4 text-center">最终排名</h2>

      <div className="space-y-2">
        {rankings.map((entry, index) => {
          const rank = index + 1
          const isFirst = rank === 1
          const chipDiff = entry.player.chips - entry.initialChips
          const isPositive = chipDiff > 0
          const isNegative = chipDiff < 0

          return (
            <motion.div
              key={entry.player.id}
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.12, duration: 0.4, ease: 'easeOut' }}
              className={`
                flex items-center gap-4 px-5 py-3 rounded-xl border transition-colors
                ${isFirst
                  ? 'bg-amber-500/10 border-amber-500/40 shadow-lg shadow-amber-500/10'
                  : 'bg-green-900/30 border-green-700/30 hover:bg-green-900/50'
                }
              `}
            >
              {/* 排名 */}
              <RankBadge rank={rank} />

              {/* 头像 */}
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm
                  bg-gradient-to-br ${getAvatarColor(entry.player.id)}
                  ${isFirst ? 'ring-2 ring-amber-400/50' : ''}
                `}
              >
                {entry.player.avatar || entry.player.name.charAt(0)}
              </div>

              {/* 名字 + 类型 */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`font-semibold truncate ${isFirst ? 'text-amber-300' : 'text-green-200'}`}>
                    {entry.player.name}
                  </span>
                  {entry.player.player_type === 'human' && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                      你
                    </span>
                  )}
                  {entry.player.personality && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-800/40 text-green-400/70 border border-green-700/30">
                      {entry.player.personality}
                    </span>
                  )}
                </div>
              </div>

              {/* 筹码变化 */}
              <div className="text-right shrink-0">
                <div className={`text-lg font-bold tabular-nums ${isFirst ? 'text-amber-300' : 'text-green-200'}`}>
                  {entry.player.chips}
                </div>
                <div
                  className={`text-xs font-medium tabular-nums ${
                    isPositive ? 'text-emerald-400' : isNegative ? 'text-red-400' : 'text-green-600'
                  }`}
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
