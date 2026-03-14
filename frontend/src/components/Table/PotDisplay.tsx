import { motion, AnimatePresence } from 'framer-motion'

interface PotDisplayProps {
  pot: number
  currentBet: number
  roundNumber: number
  className?: string
}

/**
 * 底池筹码显示组件
 * 显示在牌桌中央，展示底池金额、当前注额和局数
 */
export default function PotDisplay({
  pot,
  currentBet,
  roundNumber,
  className = '',
}: PotDisplayProps) {
  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      {/* 底池金额 */}
      <div className="relative">
        {/* 筹码图标堆叠 */}
        <div className="flex items-center justify-center gap-1 mb-1">
          {generateChipStack(pot)}
        </div>

        {/* 底池数字 */}
        <AnimatePresence mode="wait">
          <motion.div
            key={pot}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="bg-[var(--bg-deep)]/80 backdrop-blur-sm rounded-full px-4 py-1.5 border border-[var(--color-gold)]/30 shadow-[0_0_20px_rgba(255,215,0,0.1)]"
          >
            <div className="flex items-center gap-1.5">
              <ChipIcon className="w-4 h-4 text-[var(--color-gold)]" />
              <span className="neon-text-gold font-bold text-lg tabular-nums">
                {pot.toLocaleString()}
              </span>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* 局信息 */}
      <div className="flex items-center gap-3 text-xs">
        <span className="text-[var(--text-muted)]">
          第 <span className="text-[var(--text-secondary)] font-medium">{roundNumber}</span> 局
        </span>
        <span className="text-[var(--text-disabled)]">|</span>
        <span className="text-[var(--text-muted)]">
          注额{' '}
          <span className="text-[var(--color-gold)]/80 font-medium tabular-nums">
            {currentBet}
          </span>
        </span>
      </div>
    </div>
  )
}

// ---- 辅助组件 ----

/** 筹码图标 SVG */
function ChipIcon({ className = '' }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className}
    >
      <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.9" />
      <circle
        cx="12"
        cy="12"
        r="7"
        fill="none"
        stroke="currentColor"
        strokeWidth="1"
        opacity="0.5"
      />
      <circle cx="12" cy="12" r="4" fill="currentColor" opacity="0.6" />
    </svg>
  )
}

/**
 * 根据底池大小生成筹码堆叠的视觉效果
 * 底池越大，显示的筹码越多
 */
function generateChipStack(pot: number) {
  if (pot <= 0) return null

  // 根据底池大小决定筹码数量（1-5 个）
  const chipCount = Math.min(5, Math.max(1, Math.ceil(pot / 100)))

  const chipColors = [
    'bg-amber-500',
    'bg-red-500',
    'bg-blue-500',
    'bg-green-500',
    'bg-purple-500',
  ]

  return (
    <div className="flex items-end gap-0.5">
      {Array.from({ length: chipCount }, (_, i) => (
        <motion.div
          key={i}
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: i * 0.05 }}
          className="flex flex-col-reverse"
        >
          {/* 每一堆的筹码 */}
          {Array.from({ length: Math.min(3, chipCount - i + 1) }, (_, j) => (
            <div
              key={j}
              className={`w-3 h-1 rounded-full ${chipColors[i % chipColors.length]} border border-white/20`}
              style={{ marginTop: j > 0 ? '-2px' : '0' }}
            />
          ))}
        </motion.div>
      ))}
    </div>
  )
}
