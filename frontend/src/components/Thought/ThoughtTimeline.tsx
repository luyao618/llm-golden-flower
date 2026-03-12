import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ThoughtRecord, ExperienceReview, RoundNarrative } from '../../types/game'
import { getRoundThoughts, getExperienceReviews, getRoundNarrative } from '../../services/api'
import ThoughtCard from './ThoughtCard'
import NarrativeView from './NarrativeView'

// ---- 经验回顾触发类型显示 ----

const TRIGGER_LABELS: Record<string, string> = {
  chip_crisis: '筹码危机',
  consecutive_losses: '连续失利',
  big_loss: '重大损失',
  opponent_shift: '对手策略变化',
  periodic: '定期回顾',
}

const TRIGGER_COLORS: Record<string, string> = {
  chip_crisis: 'text-red-400 bg-red-500/20 border-red-500/40',
  consecutive_losses: 'text-orange-400 bg-orange-500/20 border-orange-500/40',
  big_loss: 'text-rose-400 bg-rose-500/20 border-rose-500/40',
  opponent_shift: 'text-cyan-400 bg-cyan-500/20 border-cyan-500/40',
  periodic: 'text-purple-400 bg-purple-500/20 border-purple-500/40',
}

// ---- Props ----

interface ThoughtTimelineProps {
  gameId: string
  agentId: string
  /** 已完成的局数列表 */
  completedRounds: number[]
}

/** 视图模式 */
type ViewMode = 'timeline' | 'narrative'

/**
 * 思考时间线组件
 *
 * 以时间线形式展示单局内每步决策的结构化思考。
 * 支持按局选择、在时间线/叙事视图间切换。
 * 经验回顾记录以特殊"策略调整"节点标注。
 */
export default function ThoughtTimeline({
  gameId,
  agentId,
  completedRounds,
}: ThoughtTimelineProps) {
  const [selectedRound, setSelectedRound] = useState<number | null>(null)
  const [viewMode, setViewMode] = useState<ViewMode>('timeline')
  const [thoughts, setThoughts] = useState<ThoughtRecord[]>([])
  const [reviews, setReviews] = useState<ExperienceReview[]>([])
  const [narrative, setNarrative] = useState<RoundNarrative | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 默认选中最新一局
  useEffect(() => {
    if (completedRounds.length > 0 && selectedRound === null) {
      setSelectedRound(completedRounds[completedRounds.length - 1])
    }
  }, [completedRounds, selectedRound])

  // 获取选中局的数据
  const fetchRoundData = useCallback(async () => {
    if (!selectedRound || !gameId || !agentId) return

    setLoading(true)
    setError(null)

    try {
      const [thoughtsData, reviewsData] = await Promise.all([
        getRoundThoughts(gameId, agentId, selectedRound),
        getExperienceReviews(gameId, agentId),
      ])

      setThoughts(thoughtsData)
      // 过滤出当前局触发的经验回顾
      setReviews(reviewsData.filter((r) => r.triggered_at_round === selectedRound))

      // 尝试获取叙事（可能还没生成）
      try {
        const narrativeData = await getRoundNarrative(gameId, agentId, selectedRound)
        setNarrative(narrativeData)
      } catch {
        setNarrative(null) // 叙事可能还没生成，不是错误
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
      setThoughts([])
      setReviews([])
      setNarrative(null)
    } finally {
      setLoading(false)
    }
  }, [gameId, agentId, selectedRound])

  useEffect(() => {
    fetchRoundData()
  }, [fetchRoundData])

  // 局切换后重置视图
  useEffect(() => {
    setViewMode('timeline')
  }, [selectedRound])

  // 没有已完成的局
  if (completedRounds.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-green-600/50 text-sm">
        暂无已完成的局
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* 顶部：局选择 + 视图切换 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-green-800/30">
        {/* 局选择器 */}
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-thin scrollbar-thumb-green-800/30">
          {completedRounds.map((roundNum) => (
            <button
              key={roundNum}
              onClick={() => setSelectedRound(roundNum)}
              className={`
                px-2 py-0.5 rounded text-[11px] font-mono transition-colors shrink-0 cursor-pointer
                ${selectedRound === roundNum
                  ? 'bg-green-600/30 text-green-300 border border-green-500/50'
                  : 'text-green-600/60 hover:text-green-400 hover:bg-green-900/30 border border-transparent'
                }
              `}
            >
              R{roundNum}
            </button>
          ))}
        </div>

        {/* 视图切换 */}
        <div className="flex items-center gap-0.5 bg-black/30 rounded-md p-0.5 shrink-0 ml-2">
          <button
            onClick={() => setViewMode('timeline')}
            className={`
              px-2 py-0.5 rounded text-[10px] transition-colors cursor-pointer
              ${viewMode === 'timeline'
                ? 'bg-green-700/40 text-green-300'
                : 'text-green-600/50 hover:text-green-400'
              }
            `}
          >
            思考
          </button>
          <button
            onClick={() => setViewMode('narrative')}
            className={`
              px-2 py-0.5 rounded text-[10px] transition-colors cursor-pointer
              ${viewMode === 'narrative'
                ? 'bg-green-700/40 text-green-300'
                : 'text-green-600/50 hover:text-green-400'
              }
            `}
            disabled={!narrative}
            title={narrative ? '查看叙事' : '叙事尚未生成'}
          >
            叙事
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-green-800/30 scrollbar-track-transparent">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="inline-block w-5 h-5 border-2 border-green-400/30 border-t-green-400 rounded-full animate-spin" />
            <span className="text-green-500/60 text-xs ml-2">加载中...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 gap-2">
            <span className="text-red-400/70 text-xs">{error}</span>
            <button
              onClick={fetchRoundData}
              className="text-green-500/60 text-[10px] hover:text-green-400 underline cursor-pointer"
            >
              重试
            </button>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            {viewMode === 'timeline' ? (
              <motion.div
                key="timeline"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-3 space-y-2"
              >
                {/* 经验回顾节点（如果本局触发了） */}
                {reviews.map((review, i) => (
                  <ReviewNode key={`review-${i}`} review={review} />
                ))}

                {/* 思考记录卡片 */}
                {thoughts.length === 0 ? (
                  <div className="text-green-600/50 text-xs text-center py-4">
                    该局暂无思考记录
                  </div>
                ) : (
                  thoughts.map((thought, i) => (
                    <ThoughtCard key={`t-${thought.turn_number}`} thought={thought} index={i} />
                  ))
                )}
              </motion.div>
            ) : (
              <motion.div
                key="narrative"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-3"
              >
                {narrative ? (
                  <NarrativeView narrative={narrative} />
                ) : (
                  <div className="text-green-600/50 text-xs text-center py-4">
                    叙事尚未生成
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        )}
      </div>
    </div>
  )
}

// ---- 经验回顾节点 ----

function ReviewNode({ review }: { review: ExperienceReview }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const triggerLabel = TRIGGER_LABELS[review.trigger] ?? review.trigger
  const triggerColor = TRIGGER_COLORS[review.trigger] ?? 'text-purple-400 bg-purple-500/20 border-purple-500/40'

  return (
    <motion.div
      className="bg-purple-900/20 border border-purple-700/40 rounded-lg overflow-hidden"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-purple-900/20 transition-colors cursor-pointer text-left"
      >
        {/* 策略调整标记 */}
        <span className="text-purple-400 text-[10px] font-medium shrink-0">
          策略调整
        </span>

        {/* 触发类型 */}
        <span className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${triggerColor}`}>
          {triggerLabel}
        </span>

        {/* 策略摘要 */}
        <span className="text-purple-300/60 text-xs truncate flex-1">
          {review.strategy_adjustment}
        </span>

        {/* 置信度变化 */}
        <span className={`text-[10px] font-mono shrink-0 ${review.confidence_shift >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {review.confidence_shift >= 0 ? '+' : ''}{Math.round(review.confidence_shift * 100)}%
        </span>

        <motion.span
          className="text-purple-600/50 text-xs shrink-0"
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.15 }}
        >
          ▾
        </motion.span>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-2 border-t border-purple-700/30 pt-2">
              {/* 自我分析 */}
              <div>
                <span className="text-purple-500/60 text-[10px] font-medium">自我分析</span>
                <p className="text-purple-300/70 text-xs leading-relaxed mt-0.5">{review.self_analysis}</p>
              </div>

              {/* 对手模式分析 */}
              {Object.keys(review.opponent_patterns).length > 0 && (
                <div>
                  <span className="text-purple-500/60 text-[10px] font-medium">对手模式</span>
                  <div className="mt-0.5 space-y-0.5">
                    {Object.entries(review.opponent_patterns).map(([name, pattern]) => (
                      <div key={name} className="text-xs">
                        <span className="text-purple-400/70">{name}:</span>
                        <span className="text-purple-300/60 ml-1">{pattern}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 策略调整 */}
              <div>
                <span className="text-purple-500/60 text-[10px] font-medium">策略调整</span>
                <p className="text-purple-300/70 text-xs leading-relaxed mt-0.5">{review.strategy_adjustment}</p>
              </div>

              {/* 回顾了哪些局 */}
              <div className="text-purple-600/50 text-[10px]">
                回顾了第 {review.rounds_reviewed.join(', ')} 局
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
