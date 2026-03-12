import { motion } from 'framer-motion'
import type { ChatMessage, Player, PlayerStatus } from '../../types/game'
import { useUIStore } from '../../stores/uiStore'
import ChatBubble from './ChatBubble'

interface PlayerSeatProps {
  player: Player
  /** 座位位置（通过 style 的 left/top 传入） */
  position: { x: number; y: number }
  /** 是否是当前行动玩家 */
  isActive: boolean
  /** 是否是当前用户自己 */
  isMe: boolean
  /** 是否是庄家 */
  isDealer: boolean
  /** 该玩家最新的聊天消息（用于头顶气泡） */
  latestMessage?: ChatMessage | null
  /** 点击玩家座位的回调（比牌选择等） */
  onClick?: () => void
}

/** 玩家状态的中文标签 */
const STATUS_LABELS: Record<PlayerStatus, string> = {
  active_blind: '暗注',
  active_seen: '明注',
  folded: '已弃牌',
  out: '出局',
}

/** 玩家状态对应的颜色 */
const STATUS_COLORS: Record<PlayerStatus, string> = {
  active_blind: 'text-blue-400 bg-blue-500/20 border-blue-500/40',
  active_seen: 'text-amber-400 bg-amber-500/20 border-amber-500/40',
  folded: 'text-gray-500 bg-gray-500/20 border-gray-500/40',
  out: 'text-red-500 bg-red-500/20 border-red-500/40',
}

/** 获取头像显示文本（使用名字首字符） */
function getAvatarText(name: string): string {
  // 如果是中文名，取第一个字
  // 如果是英文名，取首字母大写
  const firstChar = name.charAt(0)
  if (/[\u4e00-\u9fff]/.test(firstChar)) {
    return firstChar
  }
  return firstChar.toUpperCase()
}

/** 头像背景色，根据玩家 ID 哈希确定 */
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

/**
 * 玩家座位组件
 * 显示玩家头像、名字、筹码和状态标记
 * 支持当前行动高亮、比牌选择模式
 */
export default function PlayerSeat({
  player,
  position,
  isActive,
  isMe,
  isDealer,
  latestMessage,
  onClick,
}: PlayerSeatProps) {
  const { isCompareMode, thinkingPlayerId, reviewingPlayerId } = useUIStore()

  const isFolded = player.status === 'folded'
  const isOut = player.status === 'out'
  const isDimmed = isFolded || isOut
  const isThinking = thinkingPlayerId === player.id
  const isReviewing = reviewingPlayerId === player.id
  const isClickable = isCompareMode && !isMe && !isFolded && !isOut

  // 气泡位置：牌桌下半部分的玩家气泡显示在上方，上半部分显示在下方
  const bubblePosition = position.y > 50 ? 'above' : 'below'

  return (
    <motion.div
      className="absolute flex flex-col items-center"
      style={{
        left: `${position.x}%`,
        top: `${position.y}%`,
        transform: 'translate(-50%, -50%)',
      }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      {/* 整体容器 */}
      <div
        className={`
          relative flex flex-col items-center gap-1 p-2 rounded-xl
          transition-all duration-300
          ${isDimmed ? 'opacity-50' : ''}
          ${isClickable ? 'cursor-pointer hover:scale-105' : ''}
          ${isActive ? 'scale-105' : ''}
        `}
        onClick={isClickable ? onClick : undefined}
      >
        {/* 聊天气泡 */}
        <ChatBubble message={latestMessage ?? null} position={bubblePosition} />

        {/* 行动指示器 - 外部发光环 */}
        {isActive && (
          <motion.div
            className="absolute -inset-1 rounded-xl border-2 border-amber-400/70 shadow-[0_0_15px_rgba(251,191,36,0.3)]"
            animate={{
              boxShadow: [
                '0 0 10px rgba(251,191,36,0.2)',
                '0 0 20px rgba(251,191,36,0.4)',
                '0 0 10px rgba(251,191,36,0.2)',
              ],
            }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}

        {/* 头像 */}
        <div className="relative">
          <div
            className={`
              w-12 h-12 rounded-full flex items-center justify-center
              text-white font-bold text-lg shadow-lg
              bg-gradient-to-br ${getAvatarColor(player.id)}
              ${isDimmed ? 'grayscale' : ''}
              border-2 ${isMe ? 'border-amber-400' : 'border-white/20'}
            `}
          >
            {player.avatar || getAvatarText(player.name)}
          </div>

          {/* 庄家标记 */}
          {isDealer && (
            <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-amber-500 border border-amber-300 flex items-center justify-center shadow-md">
              <span className="text-[10px] font-bold text-amber-900">D</span>
            </div>
          )}

          {/* AI 思考指示器 */}
          {isThinking && (
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
              <ThinkingDots />
            </div>
          )}

          {/* AI 经验回顾指示器 */}
          {isReviewing && (
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2">
              <motion.div
                className="bg-purple-500/80 rounded-full px-1.5 py-0.5 text-[8px] text-white whitespace-nowrap"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                回顾中
              </motion.div>
            </div>
          )}

          {/* 玩家类型标记 (AI) */}
          {player.player_type === 'ai' && (
            <div className="absolute -top-1 -left-1 w-4 h-4 rounded-full bg-green-600 border border-green-400 flex items-center justify-center">
              <span className="text-[8px] font-bold text-white">AI</span>
            </div>
          )}
        </div>

        {/* 名字 */}
        <div className={`text-sm font-medium truncate max-w-[80px] ${isMe ? 'text-amber-300' : 'text-white'}`}>
          {player.name}
          {isMe && <span className="text-amber-400/60 text-xs"> (你)</span>}
        </div>

        {/* 筹码 */}
        <div className="flex items-center gap-1">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-amber-300/50" />
          <span className="text-amber-400 text-xs font-mono font-semibold tabular-nums">
            {player.chips.toLocaleString()}
          </span>
        </div>

        {/* 本局下注额 */}
        {player.total_bet_this_round > 0 && (
          <div className="text-green-400/70 text-[10px]">
            本局已下 {player.total_bet_this_round}
          </div>
        )}

        {/* 状态标签 */}
        <div
          className={`
            text-[10px] px-2 py-0.5 rounded-full border
            ${STATUS_COLORS[player.status]}
          `}
        >
          {STATUS_LABELS[player.status]}
        </div>
      </div>
    </motion.div>
  )
}

// ---- 辅助组件 ----

/** AI 思考中的动态圆点指示器 */
function ThinkingDots() {
  return (
    <div className="flex items-center gap-0.5 bg-black/60 rounded-full px-1.5 py-0.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-1 h-1 rounded-full bg-amber-400"
          animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  )
}
