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
  fold: 'text-gray-400 bg-gray-500/20 border-gray-500/40',
  call: 'text-green-400 bg-green-500/20 border-green-500/40',
  raise: 'text-amber-400 bg-amber-500/20 border-amber-500/40',
  check_cards: 'text-blue-400 bg-blue-500/20 border-blue-500/40',
  compare: 'text-rose-400 bg-rose-500/20 border-rose-500/40',
}

// ---- 置信度颜色 ----

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return 'text-green-400'
  if (confidence >= 0.4) return 'text-amber-400'
  return 'text-red-400'
}

function getConfidenceBarColor(confidence: number): string {
  if (confidence >= 0.7) return 'bg-green-500'
  if (confidence >= 0.4) return 'bg-amber-500'
  return 'bg-red-500'
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
  const actionColor = ACTION_COLORS[thought.decision] ?? 'text-gray-400 bg-gray-500/20 border-gray-500/40'

  return (
    <motion.div
      className="bg-black/30 border border-green-800/40 rounded-lg overflow-hidden"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
    >
      {/* 摘要行 - 始终可见 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-green-900/20 transition-colors cursor-pointer text-left"
      >
        {/* 轮次标记 */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-green-600/60 text-[10px] font-mono">
            T{thought.turn_number}
          </span>
        </div>

        {/* 决策标签 */}
        <span className={`text-[11px] px-1.5 py-0.5 rounded border shrink-0 ${actionColor}`}>
          {actionLabel}
        </span>

        {/* 推理摘要（截断） */}
        <span className="text-green-300/70 text-xs truncate flex-1">
          {thought.reasoning}
        </span>

        {/* 置信度 */}
        <span className={`text-[10px] font-mono shrink-0 ${getConfidenceColor(thought.confidence)}`}>
          {Math.round(thought.confidence * 100)}%
        </span>

        {/* 情绪 */}
        <span className="text-green-500/50 text-[10px] shrink-0 max-w-[40px] truncate">
          {thought.emotion}
        </span>

        {/* 展开/折叠 */}
        <motion.span
          className="text-green-600/50 text-xs shrink-0"
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
            <div className="px-3 pb-3 space-y-2.5 border-t border-green-800/30 pt-2">
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
                <span className="text-green-500/60 text-[10px] shrink-0 w-14">置信度</span>
                <div className="flex-1 h-1.5 bg-green-900/30 rounded-full overflow-hidden">
                  <motion.div
                    className={`h-full rounded-full ${getConfidenceBarColor(thought.confidence)}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${thought.confidence * 100}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                  />
                </div>
                <span className={`text-[10px] font-mono shrink-0 ${getConfidenceColor(thought.confidence)}`}>
                  {Math.round(thought.confidence * 100)}%
                </span>
              </div>

              {/* 情绪状态 */}
              <div className="flex items-center gap-2">
                <span className="text-green-500/60 text-[10px] shrink-0 w-14">情绪</span>
                <span className="text-green-300/80 text-xs">{thought.emotion}</span>
              </div>

              {/* 牌桌发言 */}
              {thought.table_talk && (
                <div className="bg-green-900/20 rounded-md px-2.5 py-1.5 border border-green-800/30">
                  <span className="text-green-500/60 text-[10px] block mb-0.5">牌桌发言</span>
                  <span className="text-green-300/80 text-xs italic">"{thought.table_talk}"</span>
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
        <span className="text-green-500/60 text-[10px] font-medium">{title}</span>
      </div>
      <p className="text-green-300/70 text-xs leading-relaxed pl-3.5">
        {children}
      </p>
    </div>
  )
}
