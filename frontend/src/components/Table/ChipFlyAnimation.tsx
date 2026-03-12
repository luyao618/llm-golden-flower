import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUIStore } from '../../stores/uiStore'

// ============================================================
// ChipFlyAnimation - 筹码飞行动画
//
// 两种场景:
// 1. 玩家下注 → 筹码从玩家座位飞入底池中心
// 2. 局结束 → 筹码从底池飞向赢家座位
//
// 通过 uiStore.chipAnimation 触发
// ============================================================

interface SeatPosition {
  x: number
  y: number
}

export interface ChipFlyAnimationProps {
  /** 玩家ID → 座位位置的映射 */
  playerPositions: Record<string, SeatPosition>
  /** 底池中心位置 */
  potPosition?: SeatPosition
}

/** 单个飞行筹码 */
interface FlyingChip {
  id: number
  from: SeatPosition
  to: SeatPosition
  color: string
  delay: number
}

const CHIP_COLORS = [
  'bg-amber-500',
  'bg-amber-400',
  'bg-yellow-500',
  'bg-orange-400',
]

const POT_CENTER: SeatPosition = { x: 50, y: 45 }

export default function ChipFlyAnimation({
  playerPositions,
  potPosition = POT_CENTER,
}: ChipFlyAnimationProps) {
  const { chipAnimation, clearChipAnimation } = useUIStore()
  const [chips, setChips] = useState<FlyingChip[]>([])

  useEffect(() => {
    if (!chipAnimation) {
      setChips([])
      return
    }

    const { fromPlayerId, amount } = chipAnimation

    if (!fromPlayerId || !playerPositions[fromPlayerId]) {
      clearChipAnimation()
      return
    }

    const playerPos = playerPositions[fromPlayerId]
    // 根据金额决定筹码数量（1-4个）
    const chipCount = Math.min(4, Math.max(1, Math.ceil(amount / 50)))

    const newChips: FlyingChip[] = Array.from({ length: chipCount }, (_, i) => ({
      id: Date.now() + i,
      from: playerPos,
      to: potPosition,
      color: CHIP_COLORS[i % CHIP_COLORS.length],
      delay: i * 0.06,
    }))

    setChips(newChips)

    // 动画结束后清理
    const timer = setTimeout(() => {
      setChips([])
      clearChipAnimation()
    }, 800)

    return () => clearTimeout(timer)
  }, [chipAnimation, playerPositions, potPosition, clearChipAnimation])

  return (
    <div className="absolute inset-0 pointer-events-none z-25">
      <AnimatePresence>
        {chips.map((chip) => (
          <motion.div
            key={chip.id}
            className="absolute"
            initial={{
              left: `${chip.from.x}%`,
              top: `${chip.from.y + 5}%`,
              x: '-50%',
              y: '-50%',
              scale: 1,
              opacity: 1,
            }}
            animate={{
              left: `${chip.to.x}%`,
              top: `${chip.to.y}%`,
              x: '-50%',
              y: '-50%',
              scale: 0.6,
              opacity: 0.8,
            }}
            exit={{
              opacity: 0,
              scale: 0,
            }}
            transition={{
              duration: 0.45,
              delay: chip.delay,
              ease: [0.25, 0.1, 0.25, 1],
            }}
          >
            {/* 筹码视觉 */}
            <div className="relative">
              <div
                className={`w-4 h-4 rounded-full ${chip.color} border-2 border-white/40 shadow-lg`}
              />
              <div
                className={`absolute top-[-2px] w-4 h-4 rounded-full ${chip.color} border-2 border-white/30 opacity-60`}
              />
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// ============================================================
// WinChipAnimation - 赢家筹码飞行（底池 → 赢家）
// ============================================================

export interface WinChipAnimationProps {
  /** 赢家座位位置 */
  winnerPosition: SeatPosition | null
  /** 赢得的筹码数 */
  amount: number
  /** 是否播放动画 */
  isPlaying: boolean
  /** 动画完成回调 */
  onComplete?: () => void
}

export function WinChipAnimation({
  winnerPosition,
  amount,
  isPlaying,
  onComplete,
}: WinChipAnimationProps) {
  const [chips, setChips] = useState<FlyingChip[]>([])

  useEffect(() => {
    if (!isPlaying || !winnerPosition) {
      setChips([])
      return
    }

    const chipCount = Math.min(5, Math.max(2, Math.ceil(amount / 80)))

    const newChips: FlyingChip[] = Array.from({ length: chipCount }, (_, i) => ({
      id: Date.now() + i,
      from: POT_CENTER,
      to: winnerPosition,
      color: CHIP_COLORS[i % CHIP_COLORS.length],
      delay: i * 0.08,
    }))

    setChips(newChips)

    const timer = setTimeout(() => {
      setChips([])
      onComplete?.()
    }, 1000)

    return () => clearTimeout(timer)
  }, [isPlaying, winnerPosition, amount, onComplete])

  return (
    <div className="absolute inset-0 pointer-events-none z-25">
      <AnimatePresence>
        {chips.map((chip) => (
          <motion.div
            key={chip.id}
            className="absolute"
            initial={{
              left: `${chip.from.x}%`,
              top: `${chip.from.y}%`,
              x: '-50%',
              y: '-50%',
              scale: 0.6,
              opacity: 0.8,
            }}
            animate={{
              left: `${chip.to.x}%`,
              top: `${chip.to.y + 3}%`,
              x: '-50%',
              y: '-50%',
              scale: 1,
              opacity: 1,
            }}
            exit={{
              opacity: 0,
              scale: 0.5,
            }}
            transition={{
              duration: 0.5,
              delay: chip.delay,
              ease: [0.22, 0.68, 0.35, 1],
            }}
          >
            <div
              className={`w-4 h-4 rounded-full ${chip.color} border-2 border-white/40 shadow-lg`}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
