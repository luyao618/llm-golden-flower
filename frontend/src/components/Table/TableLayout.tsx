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
}

// ============================================================
// 座位排列算法
// 椭圆形布局：玩家（人类）固定在底部中央，
// AI 对手按椭圆弧线均匀分布在其他位置
// ============================================================

/**
 * 计算 2-6 人在椭圆形牌桌上的座位位置
 *
 * 坐标系：百分比 (0-100)，(50, 50) 为椭圆中心
 * 玩家（人类）固定在底部中央 (50, 88)
 *
 * 椭圆参数：
 *   水平半径 a = 40（横向分布更宽）
 *   垂直半径 b = 35（纵向稍紧凑）
 *   中心 (50, 48)
 *
 * 座位从底部（人类）开始，逆时针均匀分布
 */
function calculateSeatPositions(
  playerCount: number
): Array<{ x: number; y: number }> {
  // 椭圆参数
  const cx = 50 // 中心 X
  const cy = 48 // 中心 Y（稍偏上，给底部操作面板留空间）
  const rx = 40 // 水平半径
  const ry = 35 // 垂直半径

  // 人类玩家固定在底部中央（角度 = 90度 = π/2，即椭圆底部）
  const startAngle = Math.PI / 2

  const positions: Array<{ x: number; y: number }> = []

  for (let i = 0; i < playerCount; i++) {
    // 从底部开始，顺时针均匀分布
    // 角度递增 = 2π / playerCount
    const angle = startAngle + (i * 2 * Math.PI) / playerCount

    const x = cx - rx * Math.cos(angle) // 负号使其顺时针
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

  // 旋转数组，使人类玩家排在第一位，保持其他玩家的相对顺序
  return [...players.slice(humanIndex), ...players.slice(0, humanIndex)]
}

/**
 * 椭圆形牌桌布局组件
 *
 * 功能：
 * - 中央绿色椭圆牌桌
 * - 底池筹码显示（牌桌中央）
 * - 2-6 人环形座位布局
 * - 人类玩家固定在底部
 * - 当前行动玩家高亮
 * - 庄家标记
 */
export default function TableLayout({ className = '' }: TableLayoutProps) {
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
    // 正向遍历，后面的消息覆盖前面的
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

  // 看牌回调
  const handleLookAtCards = useCallback(() => {
    setHasLookedAtCards(true)
  }, [setHasLookedAtCards])

  // 赢家动画完成回调
  const handleWinAnimationComplete = useCallback(() => {
    clearWinAnimation()
  }, [clearWinAnimation])

  return (
    <div className={`relative w-full h-full ${className}`}>
      {/* 椭圆形牌桌 */}
      <div className="absolute inset-[5%]">
        {/* 牌桌 - 霓虹发光边框 */}
        <div className="w-full h-full rounded-[50%] p-[2px] shadow-2xl"
          style={{
            background: 'linear-gradient(135deg, rgba(0,212,255,0.5), rgba(139,92,246,0.3), rgba(0,212,255,0.5))',
            boxShadow: '0 0 40px rgba(0,212,255,0.15), 0 0 80px rgba(0,212,255,0.05)'
          }}>
          {/* 内层 - 深蓝灰毡面 */}
          <div className="w-full h-full rounded-[50%] flex items-center justify-center relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, #0d1b2a, #162035, #0d1b2a)'
            }}>
            {/* 微妙的桌面纹理/光泽 */}
            <div className="absolute inset-0 rounded-[50%] opacity-20"
              style={{
                backgroundImage: 'radial-gradient(circle at 30% 40%, rgba(0,212,255,0.05) 0%, transparent 50%), radial-gradient(circle at 70% 60%, rgba(139,92,246,0.03) 0%, transparent 40%)'
              }}
            />

              {/* 牌桌中央内容 - 底池 */}
              <PotDisplay
                pot={pot}
                currentBet={currentBet}
                roundNumber={roundNumber}
              />
            </div>
          </div>
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
