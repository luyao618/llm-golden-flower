import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ThoughtRecord, GameAction } from '../../types/game'

// ---- 操作显示文本 ----

const ACTION_LABELS: Record<GameAction, string> = {
  fold: '弃牌',
  call: '跟注',
  raise: '加注',
  check_cards: '看牌',
  compare: '比牌',
}

const ACTION_COLORS: Record<GameAction, string> = {
  fold: 'text-red-400 bg-red-500/10 border-red-500/30',
  call: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  raise: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  check_cards: 'text-sky-400 bg-sky-500/10 border-sky-500/30',
  compare: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
}

// ---- 置信度颜色 ----

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'text-[var(--color-primary)]'
  if (confidence >= 0.4) return 'text-[var(--color-gold)]'
  return 'text-[var(--color-danger)]'
}

function getConfidenceBarColor(confidence: number): string {
  if (confidence >= 0.7) return 'bg-[var(--color-primary)]'
  if (confidence >= 0.4) return 'bg-[var(--color-gold)]'
  return 'bg-[var(--color-danger)]'
}

function getConfidenceBarGlow(confidence: number): string {
  if (confidence >= 0.7) return '0 0 8px rgba(0,212,255,0.4)'
  if (confidence >= 0.4) return '0 0 8px rgba(255,215,0,0.3)'
  return '0 0 8px rgba(255,68,68,0.3)'
}

// ---- Props ----

interface ThoughtCardProps {
  thought: ThoughtRecord
  /** 在时间线中的索引，用于动画延迟 */
  index?: number
}

/**
 * 单条思考记录卡片
 *
 * 展示 AI 每步决策的结构化思考过程：
 * - 手牌评估、对手分析、风险评估
 * - 推理过程、最终决策
 * - 置信度、情绪状态
 * - 可展开查看详细内容
 */
export default function ThoughtCard({ thought, index = 0 }: ThoughtCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const actionLabel = ACTION_LABELS[thought.decision] ?? thought.decision
  const actionColor = ACTION_COLORS[thought.decision] ?? 'text-gray-400 bg-gray-500/10 border-gray-500/30'

  return (
    <motion.div
      className="bg-[var(--bg-surface)]/80 border border-[var(--border-default)] rounded-xl overflow-hidden
        hover:border-[var(--border-hover)] transition-colors"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      {/* 摘要行 - 始终可见 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/[0.02] transition-colors cursor-pointer text-left"
      >
        {/* 轮次标记 */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-[var(--text-muted)] text-[10px]"
            style={{ fontFamily: 'var(--font-mono)' }}>
            T{thought.turn_number}
          </span>
        </div>

        {/* 决策标签 */}
        <span className={`text-[11px] px-1.5 py-0.5 rounded border shrink-0 ${actionColor}`}>
          {actionLabel}
        </span>

        {/* 推理摘要（截断） */}
        <span className="text-[var(--text-secondary)]/70 text-xs truncate flex-1">
          {thought.reasoning}
        </span>

        {/* 情绪 */}
        <span className="text-[var(--text-muted)] text-[10px] shrink-0 max-w-[40px] truncate">
          {thought.emotion}
        </span>

        {/* 展开/折叠 */}
        <motion.span
          className="text-[var(--text-muted)] text-xs shrink-0"
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.15 }}
        >
          ▾
        </motion.span>
      </button>

      {/* 详情 - 可折叠 */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2.5 border-t border-[var(--border-default)] pt-2">
              {/* 手牌评估 */}
              <DetailSection title="手牌评估" icon="cards">
                {thought.hand_evaluation}
              </DetailSection>

              {/* 对手分析 */}
              <DetailSection title="对手分析" icon="opponents">
                {thought.opponent_analysis}
              </DetailSection>

              {/* 风险评估 */}
              <DetailSection title="风险评估" icon="risk">
                {thought.risk_assessment}
              </DetailSection>

              {/* 聊天分析 */}
              {thought.chat_analysis && (
                <DetailSection title="聊天分析" icon="chat">
                  {thought.chat_analysis}
                </DetailSection>
              )}

              {/* 推理过程 */}
              <DetailSection title="推理过程" icon="reasoning">
                {thought.reasoning}
              </DetailSection>

              {/* 置信度条 */}
              <div className="flex items-center gap-2">
                <span className="text-[var(--text-muted)] text-[10px] shrink-0 w-14">置信度</span>
                <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${getConfidenceBarColor(thought.confidence)}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${thought.confidence * 100}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    style={{ boxShadow: getConfidenceBarGlow(thought.confidence) }}
                  />
                </div>
                <span className={`text-[10px] shrink-0 ${getConfidenceColor(thought.confidence)}`}
                  style={{ fontFamily: 'var(--font-mono)' }}>
                  {Math.round(thought.confidence * 100)}%
                </span>
              </div>

              {/* 情绪状态 */}
              <div className="flex items-center gap-2">
                <span className="text-[var(--text-muted)] text-[10px] shrink-0 w-14">情绪</span>
                <span className="text-[var(--text-secondary)] text-xs">{thought.emotion}</span>
              </div>

              {/* 牌桌发言 */}
              {thought.table_talk && (
                <div className="bg-[var(--bg-deep)]/60 rounded-md px-2.5 py-1.5 border border-[var(--border-default)]">
                  <span className="text-[var(--text-muted)] text-[10px] block mb-0.5">牌桌发言</span>
                  <span className="text-[var(--color-primary)]/80 text-xs italic"
                    style={{ fontFamily: 'var(--font-mono)' }}>
                    "{thought.table_talk}"
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ---- 辅助组件 ----

const SECTION_ICONS: Record<string, string> = {
  cards: '🃏',
  opponents: '👥',
  risk: '⚠',
  chat: '💬',
  reasoning: '🧠',
}

function DetailSection({
  title,
  icon,
  children,
}: {
  title: string
  icon: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-1 mb-0.5">
        <span className="text-[10px]">{SECTION_ICONS[icon] ?? '•'}</span>
        <span className="text-[var(--text-muted)] text-[10px] font-medium">{title}</span>
      </div>
      <p className="text-[var(--text-secondary)] text-xs leading-relaxed pl-3.5"
        style={{ fontFamily: 'var(--font-mono)' }}>
        {children}
      </p>
    </div>
  )
}
