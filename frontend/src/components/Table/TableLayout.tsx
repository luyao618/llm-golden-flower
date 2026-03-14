import { useCallback, useMemo } from 'react'
import type { ChatMessage, Player } from '../../types/game'
import { useGameStore } from '../../stores/gameStore'
import { useUIStore } from '../../stores/uiStore'
import PlayerSeat from '../Player/PlayerSeat'
import PotDisplay from './PotDisplay'
import DealingAnimation from './DealingAnimation'
import ChipFlyAnimation, { WinChipAnimation } from './ChipFlyAnimation'

interface TableLayoutProps {
  className?: string
  onCheckCards?: () => void
}

// ============================================================
// 座位排列算法
// 椭圆形布局：玩家（人类）固定在底部中央，
// AI 对手按椭圆弧线均匀分布在其他位置
// ============================================================

/**
 * 计算 2-6 人在椭圆形牌桌上的座位位置
 *
 * 坐标系：百分比 (0-100)，(50, 50) 为中心
 * 玩家（人类）固定在底部中央
 *
 * 现在牌桌用纯 CSS 画，占据约 90% 的容器空间（padding 5%）
 * 牌桌皮革边框约 5-6% 宽 → 座位应在边框上
 * 椭圆 rx ≈ 42, ry ≈ 40 让座位刚好在边框上
 *
 * 座位从底部（人类）开始，逆时针均匀分布
 */
function calculateSeatPositions(
  playerCount: number
): Array<{ x: number; y: number }> {
  // 椭圆参数 — 匹配 CSS 牌桌的边缘
  const cx = 50
  const cy = 48    // 稍微上移中心点，防止底部玩家太靠下
  const rx = 43  // 水平半径 — 座位在皮革边框上
  const ry = 37  // 垂直半径 — 缩小以防止底部超出

  // 人类玩家固定在底部中央（角度 = 90度 = π/2，即椭圆底部）
  const startAngle = Math.PI / 2

  const positions: Array<{ x: number; y: number }> = []

  for (let i = 0; i < playerCount; i++) {
    // 从底部开始，顺时针均匀分布
    const angle = startAngle + (i * 2 * Math.PI) / playerCount

    const x = cx - rx * Math.cos(angle)
    const y = cy + ry * Math.sin(angle)

    positions.push({
      x: Math.round(x * 100) / 100,
      y: Math.round(y * 100) / 100,
    })
  }

  return positions
}

/**
 * 对玩家列表重新排序：人类玩家放在第一位
 * 这样 calculateSeatPositions 的第一个位置（底部中央）就分配给人类
 */
function reorderPlayersHumanFirst(players: Player[]): Player[] {
  const humanIndex = players.findIndex((p) => p.player_type === 'human')
  if (humanIndex <= 0) return players

  return [...players.slice(humanIndex), ...players.slice(0, humanIndex)]
}

/**
 * 椭圆形牌桌布局组件
 *
 * 功能：
 * - 3D 牌桌俯视图背景（table-bg.png）
 * - 底池筹码显示（牌桌中央）
 * - 2-6 人环形座位布局
 * - 人类玩家固定在底部
 * - 当前行动玩家高亮
 * - 庄家标记
 */
export default function TableLayout({ className = '', onCheckCards }: TableLayoutProps) {
  const {
    players,
    currentRound,
    myPlayerId,
    myCards,
    chatMessages,
  } = useGameStore()

  const {
    setCompareTarget,
    isCompareMode,
    stopDealingAnimation,
    setShowPlayerCards,
    setHasLookedAtCards,
    winAnimation,
    clearWinAnimation,
  } = useUIStore()

  // 重新排序：人类放底部
  const orderedPlayers = reorderPlayersHumanFirst(players)
  const seatPositions = calculateSeatPositions(orderedPlayers.length)

  // 每个玩家的最新非系统聊天消息（用于头顶气泡）
  const latestMessageByPlayer = useMemo(() => {
    const map: Record<string, ChatMessage> = {}
    for (const msg of chatMessages) {
      if (msg.message_type !== 'system_message') {
        map[msg.player_id] = msg
      }
    }
    return map
  }, [chatMessages])

  // 当前行动玩家
  const currentPlayerIndex = currentRound?.current_player_index ?? -1
  const currentPlayerId = players[currentPlayerIndex]?.id ?? null

  // 庄家
  const dealerIndex = currentRound?.dealer_index ?? -1
  const dealerId = players[dealerIndex]?.id ?? null

  // 底池信息
  const pot = currentRound?.pot ?? 0
  const currentBet = currentRound?.current_bet ?? 0
  const roundNumber = currentRound?.round_number ?? 0

  // 构建 playerID → 座位位置的映射（供 ChipFlyAnimation 使用）
  const playerPositions = useMemo(() => {
    const map: Record<string, { x: number; y: number }> = {}
    orderedPlayers.forEach((player, index) => {
      if (seatPositions[index]) {
        map[player.id] = seatPositions[index]
      }
    })
    return map
  }, [orderedPlayers, seatPositions])

  // 赢家座位位置
  const winnerPosition = useMemo(() => {
    if (!winAnimation) return null
    return playerPositions[winAnimation.winnerId] ?? null
  }, [winAnimation, playerPositions])

  // 发牌动画完成回调
  const handleDealingComplete = useCallback(() => {
    stopDealingAnimation()
    setShowPlayerCards(true)
  }, [stopDealingAnimation, setShowPlayerCards])

  // 看牌回调 — 翻转手牌并发送看牌操作到后端
  const handleLookAtCards = useCallback(() => {
    setHasLookedAtCards(true)
    onCheckCards?.()
  }, [setHasLookedAtCards, onCheckCards])

  // 赢家动画完成回调
  const handleWinAnimationComplete = useCallback(() => {
    clearWinAnimation()
  }, [clearWinAnimation])

  return (
    <div className={`relative w-full h-full ${className}`}>
      {/* ====== CSS 牌桌 ====== */}
      {/* 外层 — 皮革边框（stadium / oblong 圆角矩形） */}
      <div
        className="absolute"
        style={{
          left: '4%',
          right: '4%',
          top: '4%',
          bottom: '4%',
          borderRadius: '9999px',
          /* 皮革灰色渐变 + 微妙纹理 */
          background: `
            radial-gradient(ellipse at 50% 20%, rgba(100,100,110,0.9) 0%, rgba(55,55,65,0.95) 60%, rgba(35,35,45,1) 100%)
          `,
          boxShadow: `
            0 8px 40px rgba(0,0,0,0.7),
            0 2px 15px rgba(0,0,0,0.5),
            inset 0 2px 4px rgba(255,255,255,0.08),
            inset 0 -2px 4px rgba(0,0,0,0.4)
          `,
        }}
      >
        {/* 内层 — 桌面绒布区域 */}
        <div
          className="absolute"
          style={{
            left: '5.5%',
            right: '5.5%',
            top: '8%',
            bottom: '8%',
            borderRadius: '9999px',
            /* 深蓝色桌面绒布 */
            background: `
              radial-gradient(ellipse at 50% 40%, rgba(25,40,60,1) 0%, rgba(15,25,45,1) 50%, rgba(10,18,35,1) 100%)
            `,
            /* 霓虹内边线 — 用 border + box-shadow */
            border: '1.5px solid rgba(0, 212, 255, 0.5)',
            boxShadow: `
              0 0 8px rgba(0,212,255,0.25),
              0 0 20px rgba(0,212,255,0.12),
              inset 0 0 30px rgba(0,212,255,0.04),
              inset 0 0 60px rgba(0,0,0,0.3)
            `,
          }}
        />
      </div>

      {/* 牌桌中央内容 - 底池 */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-[5]">
        <PotDisplay
          pot={pot}
          currentBet={currentBet}
          roundNumber={roundNumber}
        />
      </div>

      {/* 玩家座位 */}
      {orderedPlayers.map((player, index) => (
        <PlayerSeat
          key={player.id}
          player={player}
          position={seatPositions[index]}
          isActive={player.id === currentPlayerId}
          isMe={player.id === myPlayerId}
          isDealer={player.id === dealerId}
          latestMessage={latestMessageByPlayer[player.id] ?? null}
          myCards={player.id === myPlayerId ? myCards : undefined}
          onLookAtCards={player.id === myPlayerId ? handleLookAtCards : undefined}
          onClick={
            isCompareMode
              ? () => setCompareTarget(player.id)
              : undefined
          }
        />
      ))}

      {/* 发牌动画 */}
      <DealingAnimation
        seatPositions={seatPositions}
        playerCount={orderedPlayers.length}
        onComplete={handleDealingComplete}
      />

      {/* 下注筹码飞行动画 */}
      <ChipFlyAnimation playerPositions={playerPositions} />

      {/* 赢家筹码飞行动画 */}
      <WinChipAnimation
        winnerPosition={winnerPosition}
        amount={winAnimation?.amount ?? 0}
        isPlaying={winAnimation?.isPlaying ?? false}
        onComplete={handleWinAnimationComplete}
      />

      {/* 游戏等待提示 */}
      {players.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-[var(--text-muted)] text-lg">等待游戏开始...</div>
        </div>
      )}
    </div>
  )
}
