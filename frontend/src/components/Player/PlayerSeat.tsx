import { motion } from 'framer-motion'
import type { Card, ChatMessage, Player, PlayerStatus } from '../../types/game'
import { useUIStore } from '../../stores/uiStore'
import { getAvatarColor, getAvatarAccent, getAvatarText } from '../../utils/theme'
import ChatBubble from './ChatBubble'
import CardHand from '../Cards/CardHand'

interface PlayerSeatProps {
  player: Player
  position: { x: number; y: number }
  isActive: boolean
  isMe: boolean
  isDealer: boolean
  latestMessage?: ChatMessage | null
  myCards?: Card[]
  onLookAtCards?: () => void
  onClick?: () => void
}

/** 玩家状态的中文标签 */
const STATUS_LABELS: Record<PlayerStatus, string> = {
  active_blind: '暗注',
  active_seen: '明注',
  folded: '弃牌',
  out: '出局',
}

/**
 * 根据座位在桌面上的位置，计算手牌应该偏移的方向
 * 手牌应该朝向桌面中心方向放置
 */
function getCardOffset(position: { x: number; y: number }): { x: number; y: number } {
  // 桌面中心是 (50, 50)，手牌朝中心方向偏移
  const dx = 50 - position.x
  const dy = 50 - position.y
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist === 0) return { x: 0, y: 0 }
  // 归一化后按固定像素偏移（朝中心方向 40px）
  const scale = 40 / dist
  return { x: dx * scale, y: dy * scale }
}

/**
 * 玩家座位组件 — 紧凑版
 *
 * 布局：头像（带光环）+ 名字筹码信息浮在下方
 * 手牌朝桌面中心方向偏移放置
 * 参考设计图中玩家坐在桌边，头像为主体，信息简洁
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
  const { isCompareMode, thinkingPlayerId, reviewingPlayerId, showPlayerCards, hasLookedAtCards, toggleThoughtDrawer } = useUIStore()

  const isFolded = player.status === 'folded'
  const isOut = player.status === 'out'
  const isDimmed = isFolded || isOut
  const isThinking = thinkingPlayerId === player.id
  const isReviewing = reviewingPlayerId === player.id
  const isClickable = isCompareMode && !isMe && !isFolded && !isOut
  const isAI = player.player_type === 'ai'

  // 气泡位置
  const bubblePosition = position.y > 50 ? 'above' : 'below'

  // 手牌偏移方向（朝桌面中心）
  const cardOffset = getCardOffset(position)

  const accent = getAvatarAccent(player.id)

  // 是否显示手牌
  const shouldShowCards = showPlayerCards && !isOut && !isFolded
  const canLookAtCards = isMe && !hasLookedAtCards && _myCards.length > 0

  return (
    <motion.div
      className="absolute"
      style={{
        left: `${position.x}%`,
        top: `${position.y}%`,
        transform: 'translate(-50%, -50%)',
        zIndex: isActive ? 20 : 10,
      }}
      initial={{ scale: 0, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
    >
      {/* 手牌 — 朝桌面中心方向偏移 */}
      {shouldShowCards && (
        <motion.div
          className="absolute pointer-events-auto"
          style={{
            left: '50%',
            top: '50%',
            transform: `translate(calc(-50% + ${cardOffset.x}px), calc(-50% + ${cardOffset.y}px))`,
            zIndex: 5,
          }}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.15 }}
        >
          {isMe ? (
            <div
              className={canLookAtCards ? 'cursor-pointer' : ''}
              onClick={canLookAtCards ? _onLookAtCards : undefined}
            >
              <CardHand
                cards={_myCards.length > 0 ? _myCards : PLACEHOLDER_CARDS}
                faceUp={hasLookedAtCards && _myCards.length > 0}
                size="sm"
                fanAngle={6}
              />
              {canLookAtCards && (
                <div className="text-center text-[8px] text-[var(--color-gold)]/60 mt-0.5 animate-pulse">
                  点击看牌
                </div>
              )}
            </div>
          ) : (
            <CardHand
              cards={PLACEHOLDER_CARDS}
              faceUp={false}
              size="sm"
              fanAngle={6}
            />
          )}
        </motion.div>
      )}

      {/* 聊天气泡 */}
      <ChatBubble message={latestMessage ?? null} position={bubblePosition} />

      {/* 可点击容器 — 头像 + 信息 */}
      <div
        className={`
          relative flex flex-col items-center
          transition-all duration-300
          ${isDimmed ? 'opacity-40 grayscale-[0.5]' : ''}
          ${isClickable ? 'cursor-pointer hover:scale-110' : ''}
          ${isActive ? 'scale-105' : ''}
        `}
        onClick={isClickable ? onClick : undefined}
      >
        {/* 头像区域 */}
        <div
          className={`relative ${isAI && !isCompareMode ? 'cursor-pointer' : ''}`}
          onClick={isAI && !isCompareMode ? () => toggleThoughtDrawer(player.id) : undefined}
          title={isAI && !isCompareMode ? `查看 ${player.name} 的心路历程` : undefined}
        >
          {/* 发光光环 — 简洁的 box-shadow 发光 + border */}
          {!isDimmed && (
            <NeonGlow accent={accent} isActive={isActive} />
          )}

          {/* 头像主体 64px */}
          <div
            className={`
              relative z-10 w-16 h-16 rounded-full flex items-center justify-center
              text-white font-bold text-2xl
              bg-gradient-to-br ${getAvatarColor(player.id)}
              shadow-lg
            `}
          >
            {isAI ? '🤖' : '🧑'}
          </div>

          {/* 庄家标记 */}
          {isDealer && (
            <div className="absolute -top-0.5 -right-0.5 z-20 w-5 h-5 rounded-full bg-amber-500 border-2 border-amber-300 flex items-center justify-center shadow-md">
              <span className="text-[9px] font-bold text-amber-900">D</span>
            </div>
          )}

          {/* AI 标记 */}
          {isAI && (
            <div className="absolute -top-0.5 -left-0.5 z-20 w-5 h-5 rounded-full bg-[var(--color-primary)]/80 border border-[var(--color-primary)] flex items-center justify-center">
              <span className="text-[8px] font-bold text-white">AI</span>
            </div>
          )}

          {/* AI 思考指示器 */}
          {isThinking && (
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 z-20">
              <ThinkingDots />
            </div>
          )}

          {/* AI 经验回顾指示器 */}
          {isReviewing && (
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 z-20">
              <motion.div
                className="bg-[var(--color-secondary)]/80 rounded-full px-1.5 py-0.5 text-[7px] text-white whitespace-nowrap"
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              >
                回顾中
              </motion.div>
            </div>
          )}
        </div>

        {/* 名字 + 筹码（紧凑一行或两行小字） */}
        <div className="mt-1.5 flex flex-col items-center gap-0">
          <div className={`text-xs font-medium truncate max-w-[80px] leading-tight ${isMe ? 'text-[var(--color-gold)]' : 'text-[var(--text-primary)]'}`}>
            {player.name}
            {isMe && <span className="text-[var(--color-gold)]/50 text-[9px]"> (你)</span>}
          </div>

          {/* 筹码 + 状态合并一行 */}
          <div className="flex items-center gap-1 text-[10px] leading-tight">
            <span className="text-[var(--color-gold)]/80 font-mono font-semibold tabular-nums">
              {player.chips.toLocaleString()}
            </span>
            <span className="text-[var(--text-disabled)]">·</span>
            <span className={`${getStatusColor(player.status)}`}>
              {STATUS_LABELS[player.status]}
            </span>
          </div>

          {/* 本局下注额 */}
          {player.total_bet_this_round > 0 && (
            <div className="text-[var(--color-primary)]/50 text-[9px] leading-tight">
              下注 {player.total_bet_this_round}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

// ---- 辅助函数 ----

function getStatusColor(status: PlayerStatus): string {
  switch (status) {
    case 'active_blind':
      return 'text-[var(--color-info)]/70'
    case 'active_seen':
      return 'text-[var(--color-gold)]/70'
    case 'folded':
      return 'text-[var(--text-muted)]'
    case 'out':
      return 'text-[var(--color-danger)]/70'
  }
}

// ---- 辅助组件 ----

const PLACEHOLDER_CARDS: Card[] = [
  { suit: 'spades', rank: 14 },
  { suit: 'hearts', rank: 13 },
  { suit: 'diamonds', rank: 12 },
]

/**
 * 发光光环 — 使用简洁的 box-shadow 发光 + border
 * 行动中玩家有脉冲呼吸动画
 * 适配 64px 头像
 */
function NeonGlow({ accent, isActive }: { accent: { border: string; glow: string }; isActive: boolean }) {
  const baseStyle = {
    border: `2px solid ${accent.border}`,
    boxShadow: `0 0 10px ${accent.glow}, 0 0 20px ${accent.glow}`,
  }

  if (!isActive) {
    return (
      <div
        className="absolute -inset-[4px] rounded-full z-0"
        style={baseStyle}
      />
    )
  }

  return (
    <motion.div
      className="absolute -inset-[4px] rounded-full z-0"
      style={{
        border: `2px solid ${accent.border}`,
      }}
      animate={{
        boxShadow: [
          `0 0 10px ${accent.glow}, 0 0 20px ${accent.glow}`,
          `0 0 20px ${accent.border}, 0 0 40px ${accent.glow}, 0 0 60px ${accent.glow}`,
          `0 0 10px ${accent.glow}, 0 0 20px ${accent.glow}`,
        ],
        scale: [1, 1.06, 1],
      }}
      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
    />
  )
}

/** AI 思考中的动态圆点指示器 */
function ThinkingDots() {
  return (
    <div className="flex items-center gap-0.5 bg-black/70 rounded-full px-1.5 py-0.5">
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
