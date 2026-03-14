import { motion } from 'framer-motion'
import type { Card, ChatMessage, Player, PlayerStatus } from '../../types/game'
import { useUIStore } from '../../stores/uiStore'
import { getAvatarColor, getAvatarText } from '../../utils/theme'
import ChatBubble from './ChatBubble'
import CardHand from '../Cards/CardHand'

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
  /** 人类玩家的手牌（只有 isMe 时有值） */
  myCards?: Card[]
  /** 看牌回调（点击自己的牌背触发看牌） */
  onLookAtCards?: () => void
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
  active_blind: 'text-[var(--color-info)] bg-[var(--color-info)]/10 border-[var(--color-info)]/30',
  active_seen: 'text-[var(--color-gold)] bg-[var(--color-gold)]/10 border-[var(--color-gold)]/30',
  folded: 'text-[var(--text-muted)] bg-white/5 border-white/10',
  out: 'text-[var(--color-danger)] bg-[var(--color-danger)]/10 border-[var(--color-danger)]/30',
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
  myCards: _myCards = [],
  onLookAtCards: _onLookAtCards,
  onClick,
}: PlayerSeatProps) {
  const { isCompareMode, thinkingPlayerId, reviewingPlayerId, showPlayerCards, hasLookedAtCards: _hasLookedAtCards, toggleThoughtDrawer } = useUIStore()

  const isFolded = player.status === 'folded'
  const isOut = player.status === 'out'
  const isDimmed = isFolded || isOut
  const isThinking = thinkingPlayerId === player.id
  const isReviewing = reviewingPlayerId === player.id
  const isClickable = isCompareMode && !isMe && !isFolded && !isOut
  const isAI = player.player_type === 'ai'

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
            className="absolute -inset-1 rounded-xl border-2 border-[var(--color-primary)]/70 shadow-[0_0_15px_rgba(0,212,255,0.3)]"
            animate={{
              boxShadow: [
                '0 0 10px rgba(0,212,255,0.2)',
                '0 0 25px rgba(0,212,255,0.5)',
                '0 0 10px rgba(0,212,255,0.2)',
              ],
            }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
        )}

        {/* 头像 */}
        <div
          className={`relative ${isAI && !isCompareMode ? 'cursor-pointer' : ''}`}
          onClick={isAI && !isCompareMode ? () => toggleThoughtDrawer(player.id) : undefined}
          title={isAI && !isCompareMode ? `查看 ${player.name} 的心路历程` : undefined}
        >
          <div
            className={`
              w-12 h-12 rounded-full flex items-center justify-center
              text-white font-bold text-lg shadow-lg
              bg-gradient-to-br ${getAvatarColor(player.id)}
              ${isDimmed ? 'grayscale' : ''}
              ${isMe ? 'ring-2 ring-[var(--color-gold)] shadow-[0_0_12px_rgba(255,215,0,0.3)]' : 'ring-2 ring-white/15'}
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
                className="bg-[var(--color-secondary)]/80 rounded-full px-1.5 py-0.5 text-[8px] text-white whitespace-nowrap"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                回顾中
              </motion.div>
            </div>
          )}

          {/* 玩家类型标记 (AI) */}
          {player.player_type === 'ai' && (
            <div className="absolute -top-1 -left-1 w-4 h-4 rounded-full bg-[var(--color-primary)]/80 border border-[var(--color-primary)] flex items-center justify-center">
              <span className="text-[8px] font-bold text-white">AI</span>
            </div>
          )}
        </div>

        {/* 名字 */}
        <div className={`text-sm font-medium truncate max-w-[80px] ${isMe ? 'text-[var(--color-gold)]' : 'text-[var(--text-primary)]'}`}>
          {player.name}
          {isMe && <span className="text-[var(--color-gold)]/60 text-xs"> (你)</span>}
        </div>

        {/* 筹码 */}
        <div className="flex items-center gap-1">
          <div className="w-2.5 h-2.5 rounded-full bg-[var(--color-gold)] border border-[var(--color-gold)]/50" />
          <span className="text-[var(--color-gold)] text-xs font-mono font-semibold tabular-nums">
            {player.chips.toLocaleString()}
          </span>
        </div>

        {/* 本局下注额 */}
        {player.total_bet_this_round > 0 && (
          <div className="text-[var(--color-primary)]/60 text-[10px]">
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

        {/* 手牌显示 - 人类玩家的手牌在 footer 中显示，桌面上只显示 AI 手牌 */}
        {showPlayerCards && !isOut && !isFolded && !isMe && (
          <PlayerCards
            isMe={false}
            myCards={[]}
            hasLookedAtCards={false}
            playerStatus={player.status}
            onLookAtCards={undefined}
          />
        )}
      </div>
    </motion.div>
  )
}

// ---- 辅助组件 ----

/**
 * 玩家手牌显示
 * - 人类玩家：点击牌背触发看牌（3D翻转），看牌后显示正面
 * - AI 玩家：始终显示牌背
 */
function PlayerCards({
  isMe,
  myCards,
  hasLookedAtCards,
  playerStatus,
  onLookAtCards,
}: {
  isMe: boolean
  myCards: Card[]
  hasLookedAtCards: boolean
  playerStatus: PlayerStatus
  onLookAtCards?: () => void
}) {
  // 人类玩家
  if (isMe) {
    // 没有手牌数据时显示 3 张牌背占位
    const cards = myCards.length > 0 ? myCards : PLACEHOLDER_CARDS
    const isFaceUp = hasLookedAtCards && myCards.length > 0
    const canLook = !hasLookedAtCards && myCards.length > 0 && playerStatus === 'active_blind'

    return (
      <motion.div
        className="mt-1"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        <CardHand
          cards={cards}
          faceUp={isFaceUp}
          size="sm"
          clickable={canLook}
          onClick={canLook ? onLookAtCards : undefined}
          fanAngle={6}
        />
        {canLook && (
          <div className="text-center text-[9px] text-[var(--color-gold)]/70 mt-0.5 animate-pulse">
            点击看牌
          </div>
        )}
      </motion.div>
    )
  }

  // AI 玩家：显示牌背
  return (
    <motion.div
      className="mt-1"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
    >
      <CardHand
        cards={PLACEHOLDER_CARDS}
        faceUp={false}
        size="sm"
        fanAngle={6}
      />
    </motion.div>
  )
}

/** 占位牌数据（仅用于牌背显示） */
const PLACEHOLDER_CARDS: Card[] = [
  { suit: 'spades', rank: 14 },
  { suit: 'hearts', rank: 13 },
  { suit: 'diamonds', rank: 12 },
]

/** AI 思考中的动态圆点指示器 */
function ThinkingDots() {
  return (
    <div className="flex items-center gap-0.5 bg-black/60 rounded-full px-1.5 py-0.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-1 h-1 rounded-full bg-[var(--color-primary)]"
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
