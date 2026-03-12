import type { Card } from '../../types/game'
import CardFace, { type CardSize } from './CardFace'

// ============================================================
// CardHand - 三张手牌组合展示
// ============================================================

export interface CardHandProps {
  /** 手牌（最多 3 张） */
  cards: Card[]
  /** 是否显示正面 */
  faceUp?: boolean
  /** 卡牌尺寸 */
  size?: CardSize
  /** 扇形展开角度（度），默认 8 */
  fanAngle?: number
  /** 卡牌间距偏移（px），默认根据 size 自动计算 */
  overlap?: number
  /** 是否可点击（用于看牌交互） */
  clickable?: boolean
  /** 点击手牌回调 */
  onClick?: () => void
  /** 高亮的牌索引（赢牌展示等） */
  highlightedIndices?: number[]
  /** 发光效果 */
  glowing?: boolean
  /** 额外的 className */
  className?: string
}

/** 根据 card size 获取默认的卡牌重叠偏移量 */
function getDefaultOverlap(size: CardSize): number {
  switch (size) {
    case 'sm': return 24
    case 'md': return 32
    case 'lg': return 44
    case 'xl': return 56
  }
}

/**
 * 三张手牌组合展示组件
 *
 * 特性:
 * - 扇形展开布局，模拟真实手持效果
 * - 可配置展开角度和重叠度
 * - 支持正面/背面切换
 * - 悬停时单张牌上移突出显示
 */
export default function CardHand({
  cards,
  faceUp = false,
  size = 'md',
  fanAngle = 8,
  overlap,
  clickable = false,
  onClick,
  highlightedIndices = [],
  glowing = false,
  className = '',
}: CardHandProps) {
  const actualOverlap = overlap ?? getDefaultOverlap(size)
  const count = cards.length

  // 计算每张牌的旋转角度和水平偏移
  function getCardTransform(index: number): React.CSSProperties {
    if (count <= 1) {
      return {}
    }

    // 将牌均匀分布在 [-fanAngle, +fanAngle] 范围内
    const totalAngle = fanAngle * (count - 1)
    const startAngle = -totalAngle / 2
    const angle = startAngle + index * fanAngle

    // 水平偏移：中间的牌在中心，两侧展开
    const centerIndex = (count - 1) / 2
    const xOffset = (index - centerIndex) * actualOverlap

    // 垂直偏移：两侧的牌略微下沉，形成弧形
    const normalizedPos = (index - centerIndex) / (count > 1 ? centerIndex : 1)
    const yOffset = Math.abs(normalizedPos) * 4

    return {
      transform: `translateX(${xOffset}px) translateY(${yOffset}px) rotate(${angle}deg)`,
      zIndex: index + 1,
      transformOrigin: 'center bottom',
    }
  }

  return (
    <div
      className={`card-hand ${clickable ? 'cursor-pointer' : ''} ${className}`}
      onClick={clickable ? onClick : undefined}
      style={{ position: 'relative', display: 'inline-flex', alignItems: 'flex-end', justifyContent: 'center' }}
    >
      {cards.map((card, index) => (
        <div
          key={`${card.suit}-${card.rank}`}
          className="card-hand-slot"
          style={getCardTransform(index)}
        >
          <CardFace
            card={card}
            faceUp={faceUp}
            size={size}
            highlighted={highlightedIndices.includes(index)}
            glowing={glowing}
          />
        </div>
      ))}

      {/* 没有牌时显示占位的牌背 */}
      {cards.length === 0 && (
        <div style={{ opacity: 0.3 }}>
          <CardFace card={null} faceUp={false} size={size} />
        </div>
      )}
    </div>
  )
}
