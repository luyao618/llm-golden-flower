import { type Card, type Rank, SUIT_SYMBOLS, SUIT_COLORS, RANK_DISPLAY } from '../../types/game'
import '../../styles/cards.css'

// ============================================================
// CardFace - 单张拟物风格扑克牌
// ============================================================

export type CardSize = 'sm' | 'md' | 'lg' | 'xl'

export interface CardFaceProps {
  /** 牌面数据，null 时显示牌背 */
  card: Card | null
  /** 是否显示正面（true = 正面，false = 背面） */
  faceUp?: boolean
  /** 尺寸 */
  size?: CardSize
  /** 是否可点击 */
  clickable?: boolean
  /** 点击回调 */
  onClick?: () => void
  /** 高亮状态 */
  highlighted?: boolean
  /** 发光效果（赢牌时） */
  glowing?: boolean
  /** 额外的 className */
  className?: string
}

/**
 * 单张扑克牌组件
 *
 * 支持:
 * - 52 张标准扑克牌正面渲染（经典 pip 布局）
 * - 牌背渲染（深蓝菱形纹理 + 金色装饰）
 * - 正面/背面 3D 翻转动画
 * - sm / md / lg / xl 四种尺寸
 */
export default function CardFace({
  card,
  faceUp = false,
  size = 'md',
  clickable = false,
  onClick,
  highlighted = false,
  glowing = false,
  className = '',
}: CardFaceProps) {
  const showFace = faceUp && card !== null

  return (
    <div
      className={`card-container card-size-${size} ${clickable ? 'card-clickable' : ''} ${className}`}
      onClick={clickable ? onClick : undefined}
    >
      <div className={`card-inner ${showFace ? 'flipped' : ''}`}>
        {/* 牌背（默认可见面） */}
        <div className="card-back">
          <CardBackDesign />
        </div>

        {/* 牌面（翻转后可见） */}
        <div className="card-face">
          {card ? (
            <CardFaceDesign
              card={card}
              highlighted={highlighted}
              glowing={glowing}
            />
          ) : (
            <CardBackDesign />
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 牌背设计
// ============================================================

function CardBackDesign() {
  return (
    <div className="card-back-inner">
      <div className="card-back-border" />
      <div className="card-back-pattern" />
      <div className="card-back-center">
        <span className="card-back-center-icon">GF</span>
      </div>
    </div>
  )
}

// ============================================================
// 牌面设计
// ============================================================

interface CardFaceDesignProps {
  card: Card
  highlighted: boolean
  glowing: boolean
}

function CardFaceDesign({ card, highlighted, glowing }: CardFaceDesignProps) {
  const { suit, rank } = card
  const colorClass = SUIT_COLORS[suit] === 'red' ? 'suit-red' : 'suit-black'
  const suitSymbol = SUIT_SYMBOLS[suit]
  const rankText = RANK_DISPLAY[rank]

  return (
    <div
      className={`card-face-inner ${colorClass} ${highlighted ? 'card-highlighted' : ''} ${glowing ? 'card-glow' : ''}`}
    >
      <div className="card-face-content">
        {/* 左上角 */}
        <div className="card-corner card-corner-top">
          <span className="card-corner-rank">{rankText}</span>
          <span className="card-corner-suit">{suitSymbol}</span>
        </div>

        {/* 右下角（倒置） */}
        <div className="card-corner card-corner-bottom">
          <span className="card-corner-rank">{rankText}</span>
          <span className="card-corner-suit">{suitSymbol}</span>
        </div>

        {/* 中央区域 */}
        <CenterPips rank={rank} suitSymbol={suitSymbol} />
      </div>
    </div>
  )
}

// ============================================================
// 中央花色排列 (经典扑克牌 pip 布局)
// ============================================================

/**
 * Pip 位置定义
 * 使用百分比坐标 [x%, y%] 相对于 pip-grid
 * inverted: 是否倒置（下半部分的 pip）
 */
interface PipPosition {
  x: number
  y: number
  inverted?: boolean
}

/**
 * 经典扑克牌各点数的 pip 排列
 * 参考真实扑克牌的标准布局
 */
function getPipPositions(rank: Rank): PipPosition[] {
  switch (rank) {
    case 14: // Ace - 单个大花色居中
      return []
    case 2:
      return [
        { x: 50, y: 10 },
        { x: 50, y: 90, inverted: true },
      ]
    case 3:
      return [
        { x: 50, y: 10 },
        { x: 50, y: 50 },
        { x: 50, y: 90, inverted: true },
      ]
    case 4:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    case 5:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 50, y: 50 },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    case 6:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 25, y: 50 },
        { x: 75, y: 50 },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    case 7:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 50, y: 30 },
        { x: 25, y: 50 },
        { x: 75, y: 50 },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    case 8:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 50, y: 30 },
        { x: 25, y: 50 },
        { x: 75, y: 50 },
        { x: 50, y: 70, inverted: true },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    case 9:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 25, y: 35 },
        { x: 75, y: 35 },
        { x: 50, y: 50 },
        { x: 25, y: 65, inverted: true },
        { x: 75, y: 65, inverted: true },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    case 10:
      return [
        { x: 25, y: 10 },
        { x: 75, y: 10 },
        { x: 50, y: 25 },
        { x: 25, y: 35 },
        { x: 75, y: 35 },
        { x: 25, y: 65, inverted: true },
        { x: 75, y: 65, inverted: true },
        { x: 50, y: 75, inverted: true },
        { x: 25, y: 90, inverted: true },
        { x: 75, y: 90, inverted: true },
      ]
    // J, Q, K - 使用大字母 + 花色，不用 pip 排列
    case 11:
    case 12:
    case 13:
      return []
    default:
      return []
  }
}

interface CenterPipsProps {
  rank: Rank
  suitSymbol: string
}

function CenterPips({ rank, suitSymbol }: CenterPipsProps) {
  // Ace: 大号居中花色
  if (rank === 14) {
    return (
      <div className="ace-center-suit">
        {suitSymbol}
      </div>
    )
  }

  // J, Q, K: 大字母 + 小花色
  if (rank >= 11 && rank <= 13) {
    const letter = RANK_DISPLAY[rank]
    return (
      <>
        <div className="face-card-letter">{letter}</div>
        <div className="ace-center-suit" style={{ opacity: 0.6, fontSize: '60%' }}>
          {suitSymbol}
        </div>
      </>
    )
  }

  // 数字牌 2-10: pip 排列
  const positions = getPipPositions(rank)
  return (
    <div className="pip-grid">
      {positions.map((pos, i) => (
        <div
          key={i}
          className={`pip ${pos.inverted ? 'pip-inverted' : ''}`}
          style={{
            left: `${pos.x}%`,
            top: `${pos.y}%`,
            transform: `translate(-50%, -50%) ${pos.inverted ? 'rotate(180deg)' : ''}`,
          }}
        >
          {suitSymbol}
        </div>
      ))}
    </div>
  )
}
