import { useEffect, useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUIStore } from '../../stores/uiStore'
import CardFace from '../Cards/CardFace'

// ============================================================
// DealingAnimation - 发牌飞行动画
//
// 卡牌从牌桌中心（牌堆位置）依次飞向各玩家座位。
// 发牌顺序模拟真实发牌：3 轮，每轮每人 1 张。
// 使用 Framer Motion absolute positioning + left/top 动画。
// ============================================================

interface SeatPosition {
  x: number // 百分比 0-100
  y: number // 百分比 0-100
}

export interface DealingAnimationProps {
  /** 各玩家座位位置（百分比坐标），顺序与玩家列表一致 */
  seatPositions: SeatPosition[]
  /** 玩家数量 */
  playerCount: number
  /** 发牌完成回调 */
  onComplete?: () => void
  /** 每张牌飞行时间（ms） */
  cardFlyDuration?: number
  /** 发牌间隔（ms） */
  dealInterval?: number
}

/** 牌堆位置：牌桌中心 */
const DECK_POSITION = { x: 50, y: 45 }

/** 单张飞行牌的状态 */
interface FlyingCard {
  id: number
  targetPlayerIndex: number
  cardIndex: number // 该玩家的第几张牌 (0, 1, 2)
  target: SeatPosition
}

export default function DealingAnimation({
  seatPositions,
  playerCount,
  onComplete,
  cardFlyDuration = 300,
  dealInterval = 100,
}: DealingAnimationProps) {
  const { dealingAnimation } = useUIStore()
  const [visibleCards, setVisibleCards] = useState<FlyingCard[]>([])
  const [completedCards, setCompletedCards] = useState<Set<number>>(new Set())
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([])
  const onCompleteRef = useRef(onComplete)
  onCompleteRef.current = onComplete

  // 构建发牌序列：3 轮，每轮每人 1 张
  const buildDealSequence = useCallback((): FlyingCard[] => {
    const seq: FlyingCard[] = []
    let id = 0
    for (let round = 0; round < 3; round++) {
      for (let pIdx = 0; pIdx < playerCount; pIdx++) {
        if (seatPositions[pIdx]) {
          seq.push({
            id: id++,
            targetPlayerIndex: pIdx,
            cardIndex: round,
            target: seatPositions[pIdx],
          })
        }
      }
    }
    return seq
  }, [playerCount, seatPositions])

  // 启动或停止发牌动画
  useEffect(() => {
    // 清理旧的定时器
    timersRef.current.forEach(clearTimeout)
    timersRef.current = []

    if (!dealingAnimation.isDealing) {
      return
    }

    const sequence = buildDealSequence()
    if (sequence.length === 0) return

    setVisibleCards([])
    setCompletedCards(new Set())

    // 依次发出每张牌
    sequence.forEach((card, index) => {
      const timer = setTimeout(() => {
        setVisibleCards((prev) => [...prev, card])
      }, index * dealInterval)
      timersRef.current.push(timer)
    })

    // 所有牌发完后等飞行结束再回调
    const totalTime = sequence.length * dealInterval + cardFlyDuration + 300
    const completeTimer = setTimeout(() => {
      onCompleteRef.current?.()
    }, totalTime)
    timersRef.current.push(completeTimer)

    return () => {
      timersRef.current.forEach(clearTimeout)
      timersRef.current = []
    }
  }, [dealingAnimation.isDealing, buildDealSequence, dealInterval, cardFlyDuration])

  // 牌飞行完毕
  const handleLanded = useCallback((cardId: number) => {
    setCompletedCards((prev) => {
      const next = new Set(prev)
      next.add(cardId)
      return next
    })
  }, [])

  if (!dealingAnimation.isDealing && visibleCards.length === 0) {
    return null
  }

  return (
    <div className="absolute inset-0 pointer-events-none z-30">
      {/* 牌堆（中心叠放的牌背） */}
      <AnimatePresence>
        {dealingAnimation.isDealing && (
          <motion.div
            className="absolute"
            style={{
              left: `${DECK_POSITION.x}%`,
              top: `${DECK_POSITION.y}%`,
              transform: 'translate(-50%, -50%)',
            }}
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.5, opacity: 0, transition: { duration: 0.3 } }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
          >
            <div className="relative">
              {[2, 1, 0].map((i) => (
                <div
                  key={i}
                  className="absolute"
                  style={{
                    top: `${-i * 2}px`,
                    left: `${i * 1.5}px`,
                    zIndex: i,
                  }}
                >
                  <CardFace card={null} faceUp={false} size="sm" />
                </div>
              ))}
              {/* 占位保持尺寸 */}
              <div className="invisible">
                <CardFace card={null} faceUp={false} size="sm" />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 飞行中的牌 */}
      {visibleCards.map((card) => {
        if (completedCards.has(card.id)) return null

        // 落点微调：根据 cardIndex 横向偏移，模拟扇形手牌
        const spreadOffset = (card.cardIndex - 1) * 1.5 // -1.5%, 0%, +1.5%

        return (
          <motion.div
            key={card.id}
            className="absolute"
            style={{ zIndex: 40 + card.id }}
            initial={{
              left: `${DECK_POSITION.x}%`,
              top: `${DECK_POSITION.y}%`,
              x: '-50%',
              y: '-50%',
              scale: 1,
              rotate: 0,
            }}
            animate={{
              left: `${card.target.x + spreadOffset}%`,
              top: `${card.target.y + 9}%`,
              x: '-50%',
              y: '-50%',
              scale: 0.8,
              rotate: (card.cardIndex - 1) * 6, // 扇形旋转 -6°, 0°, 6°
            }}
            transition={{
              duration: cardFlyDuration / 1000,
              ease: [0.22, 0.68, 0.35, 1.0], // custom ease-out curve
            }}
            onAnimationComplete={() => handleLanded(card.id)}
          >
            <CardFace card={null} faceUp={false} size="sm" />
          </motion.div>
        )
      })}
    </div>
  )
}
