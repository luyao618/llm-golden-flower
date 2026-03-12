import { motion } from 'framer-motion'
import type { Player } from '../../types/game'

// ---- 头像颜色（复用 PlayerSeat 的逻辑）----

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

function getAvatarText(name: string): string {
  const firstChar = name.charAt(0)
  if (/[\u4e00-\u9fff]/.test(firstChar)) return firstChar
  return firstChar.toUpperCase()
}

// ---- 状态标签 ----

const STATUS_LABELS: Record<string, string> = {
  active_blind: '暗注',
  active_seen: '明注',
}

// ---- Props ----

interface CompareSelectorProps {
  /** 可选择的比牌对手 */
  targets: Player[]
  /** 比牌费用 */
  cost: number
  /** 选择对手回调 */
  onSelect: (targetId: string) => void
  /** 取消比牌回调 */
  onCancel: () => void
}

/**
 * 比牌对手选择组件
 *
 * 在操作面板区域显示可选对手列表，
 * 玩家点击某个对手即发起比牌。
 */
export default function CompareSelector({
  targets,
  cost,
  onSelect,
  onCancel,
}: CompareSelectorProps) {
  if (targets.length === 0) {
    return (
      <div className="flex items-center justify-center h-full gap-3">
        <span className="text-red-400 text-sm">没有可比牌的对手</span>
        <button
          onClick={onCancel}
          className="px-3 py-1.5 rounded-lg text-sm text-green-400 bg-green-800/40 hover:bg-green-800/60 border border-green-600/30 transition-colors cursor-pointer"
        >
          返回
        </button>
      </div>
    )
  }

  return (
    <motion.div
      className="flex items-center justify-center h-full gap-2 px-4"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
    >
      {/* 提示文字 */}
      <div className="flex flex-col items-end mr-1 shrink-0">
        <span className="text-purple-300 text-sm font-medium">
          选择比牌对手
        </span>
        <span className="text-purple-400/60 text-[10px]">
          费用: {cost} 筹码
        </span>
      </div>

      {/* 对手列表 */}
      <div className="flex items-center gap-2">
        {targets.map((target) => (
          <motion.button
            key={target.id}
            onClick={() => onSelect(target.id)}
            className="
              flex items-center gap-2 px-3 py-1.5 rounded-lg
              bg-purple-800/40 hover:bg-purple-700/60
              border border-purple-500/30 hover:border-purple-400/50
              transition-all cursor-pointer
              active:scale-95 hover:shadow-lg hover:shadow-purple-500/20
            "
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.95 }}
          >
            {/* 小头像 */}
            <div
              className={`
                w-7 h-7 rounded-full flex items-center justify-center
                text-white text-xs font-bold
                bg-gradient-to-br ${getAvatarColor(target.id)}
              `}
            >
              {target.avatar || getAvatarText(target.name)}
            </div>
            {/* 名字和状态 */}
            <div className="flex flex-col items-start">
              <span className="text-white text-xs font-medium leading-tight">
                {target.name}
              </span>
              <span className="text-purple-300/60 text-[10px] leading-tight">
                {STATUS_LABELS[target.status] ?? target.status} ·{' '}
                {target.chips}
              </span>
            </div>
          </motion.button>
        ))}
      </div>

      {/* 取消按钮 */}
      <button
        onClick={onCancel}
        className="px-3 py-1.5 rounded-lg text-sm text-green-400/80 hover:text-green-300 bg-green-800/30 hover:bg-green-800/50 border border-green-600/20 transition-all cursor-pointer ml-1 shrink-0"
      >
        取消
      </button>
    </motion.div>
  )
}
