import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ThoughtRecord, ExperienceReview, RoundNarrative } from '../../types/game'
import { getRoundThoughts, getExperienceReviews, getRoundNarrative } from '../../services/api'
import { useSettingsStore } from '../../stores/settingsStore'
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
  chip_crisis: 'text-red-400 bg-red-500/10 border-red-500/30',
  consecutive_losses: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  big_loss: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
  opponent_shift: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
  periodic: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
}

// ---- 时间线节点颜色轮换 ----

const NODE_COLORS = [
  { ring: 'rgba(0, 212, 255, 0.6)', glow: 'rgba(0, 212, 255, 0.3)', text: '#00d4ff' },   // cyan
  { ring: 'rgba(139, 92, 246, 0.6)', glow: 'rgba(139, 92, 246, 0.3)', text: '#8b5cf6' },  // purple
  { ring: 'rgba(255, 102, 170, 0.6)', glow: 'rgba(255, 102, 170, 0.3)', text: '#ff66aa' }, // pink
  { ring: 'rgba(0, 170, 255, 0.6)', glow: 'rgba(0, 170, 255, 0.3)', text: '#00aaff' },    // blue
]

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
      <div className="flex items-center justify-center h-full text-[var(--text-muted)] text-sm">
        暂无已完成的局
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* 顶部：局选择 + 视图切换 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--border-default)]">
        {/* 局选择器 */}
        <div className="flex items-center gap-1 overflow-x-auto">
          {completedRounds.map((roundNum) => (
            <button
              key={roundNum}
              onClick={() => setSelectedRound(roundNum)}
              className={`
                px-2 py-0.5 rounded text-[11px] transition-all shrink-0 cursor-pointer
                ${selectedRound === roundNum
                  ? 'bg-[var(--color-primary)]/15 text-[var(--color-primary)] border border-[var(--color-primary)]/40 shadow-[0_0_8px_rgba(0,212,255,0.15)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-white/5 border border-transparent'
                }
              `}
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              R{roundNum}
            </button>
          ))}
        </div>

        {/* 视图切换 */}
        <div className="flex items-center gap-0.5 bg-[var(--bg-deep)]/60 rounded-md p-0.5 shrink-0 ml-2 border border-[var(--border-default)]">
          <button
            onClick={() => setViewMode('timeline')}
            className={`
              px-2 py-0.5 rounded text-[10px] transition-all cursor-pointer
              ${viewMode === 'timeline'
                ? 'bg-[var(--color-primary)]/15 text-[var(--color-primary)] shadow-[0_0_6px_rgba(0,212,255,0.15)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
              }
            `}
          >
            思考
          </button>
          <button
            onClick={() => setViewMode('narrative')}
            className={`
              px-2 py-0.5 rounded text-[10px] transition-all cursor-pointer
              ${viewMode === 'narrative'
                ? 'bg-[var(--color-secondary)]/15 text-[var(--color-secondary)] shadow-[0_0_6px_rgba(139,92,246,0.15)]'
                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
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
      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="inline-block w-5 h-5 border-2 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
            <span className="text-[var(--text-muted)] text-xs ml-2">加载中...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 gap-2">
            <span className="text-[var(--color-danger)]/70 text-xs">{error}</span>
            <button
              onClick={fetchRoundData}
              className="text-[var(--text-muted)] text-[10px] hover:text-[var(--color-primary)] underline cursor-pointer"
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
                className="p-3"
              >
                {/* 经验回顾节点（如果本局触发了） */}
                {reviews.map((review, i) => (
                  <ReviewNode key={`review-${i}`} review={review} />
                ))}

                {/* 思考记录 — 垂直时间线 */}
                {thoughts.length === 0 ? (
                  <EmptyThoughtsHint />
                ) : (
                  <div className="relative">
                    {/* 垂直时间线主线 */}
                    <div
                      className="absolute left-[22px] top-4 bottom-4 w-[2px] pointer-events-none"
                      style={{
                        background: 'linear-gradient(180deg, rgba(0,212,255,0.4), rgba(139,92,246,0.3), rgba(0,212,255,0.4))',
                        boxShadow: '0 0 6px rgba(0,212,255,0.15)',
                      }}
                    />

                    {/* 时间线节点 + 思考卡片 */}
                    {thoughts.map((thought, i) => {
                      const nodeColor = NODE_COLORS[i % NODE_COLORS.length]
                      return (
                        <div key={`t-${thought.turn_number}`} className="relative flex gap-3 mb-3">
                          {/* 时间线圆形节点 */}
                          <div className="shrink-0 z-10 flex items-start pt-2">
                            <div
                              className="w-[44px] h-[44px] rounded-full flex items-center justify-center relative"
                              style={{
                                background: `rgba(${nodeColor.ring === 'rgba(0, 212, 255, 0.6)' ? '6,6,15' : nodeColor.ring === 'rgba(139, 92, 246, 0.6)' ? '6,6,15' : '6,6,15'}, 1)`,
                              }}
                            >
                              {/* 环形进度条 (SVG) */}
                              <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 44 44">
                                {/* 背景环 */}
                                <circle
                                  cx="22" cy="22" r="18"
                                  fill="none"
                                  stroke="rgba(255,255,255,0.06)"
                                  strokeWidth="3"
                                />
                                {/* 进度环 — 置信度 */}
                                <circle
                                  cx="22" cy="22" r="18"
                                  fill="none"
                                  stroke={nodeColor.ring}
                                  strokeWidth="3"
                                  strokeDasharray={`${thought.confidence * 113} 113`}
                                  strokeLinecap="round"
                                  style={{
                                    filter: `drop-shadow(0 0 4px ${nodeColor.glow})`,
                                  }}
                                />
                              </svg>
                              {/* 中心置信度数字 */}
                              <span
                                className="relative text-xs font-bold"
                                style={{
                                  fontFamily: 'var(--font-mono)',
                                  color: nodeColor.text,
                                  textShadow: `0 0 6px ${nodeColor.glow}`,
                                }}
                              >
                                {Math.round(thought.confidence * 100)}
                              </span>
                            </div>
                          </div>

                          {/* 思考卡片 */}
                          <div className="flex-1 min-w-0">
                            <ThoughtCard thought={thought} index={i} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
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
                  <div className="text-[var(--text-muted)] text-xs text-center py-4">
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

// ---- 空思考记录提示 ----

function EmptyThoughtsHint() {
  const aiThinkingMode = useSettingsStore((s) => s.aiThinkingMode)

  if (aiThinkingMode === 'turbo') {
    return (
      <div className="text-center py-6 space-y-2">
        <div className="text-[var(--text-muted)] text-xs">
          当前为「极速决策」模式，AI 不输出思考过程
        </div>
        <div className="text-[var(--text-muted)]/60 text-[10px]">
          切换至「快速思考」或「详细思考」模式可查看心路历程
        </div>
      </div>
    )
  }

  return (
    <div className="text-[var(--text-muted)] text-xs text-center py-4">
      该局暂无思考记录
    </div>
  )
}

// ---- 经验回顾节点 ----

function ReviewNode({ review }: { review: ExperienceReview }) {
  const [isExpanded, setIsExpanded] = useState(false)

  const triggerLabel = TRIGGER_LABELS[review.trigger] ?? review.trigger
  const triggerColor = TRIGGER_COLORS[review.trigger] ?? 'text-purple-400 bg-purple-500/10 border-purple-500/30'

  return (
    <motion.div
      className="bg-[var(--color-secondary)]/5 border border-[var(--color-secondary)]/25 rounded-lg overflow-hidden mb-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        boxShadow: '0 0 15px rgba(139,92,246,0.06)',
      }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-[var(--color-secondary)]/5 transition-colors cursor-pointer text-left"
      >
        {/* 策略调整标记 */}
        <span className="text-[var(--color-secondary)] text-[10px] font-medium shrink-0">
          策略调整
        </span>

        {/* 触发类型 */}
        <span className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${triggerColor}`}>
          {triggerLabel}
        </span>

        {/* 策略摘要 */}
        <span className="text-[var(--text-secondary)]/60 text-xs truncate flex-1">
          {review.strategy_adjustment}
        </span>

        {/* 置信度变化 */}
        <span className={`text-[10px] shrink-0 ${review.confidence_shift >= 0 ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}
          style={{ fontFamily: 'var(--font-mono)' }}>
          {review.confidence_shift >= 0 ? '+' : ''}{Math.round(review.confidence_shift * 100)}%
        </span>

        <motion.span
          className="text-[var(--text-muted)] text-xs shrink-0"
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
            <div className="px-3 pb-3 space-y-2 border-t border-[var(--color-secondary)]/15 pt-2">
              {/* 自我分析 */}
              <div>
                <span className="text-[var(--color-secondary)]/60 text-[10px] font-medium">自我分析</span>
                <p className="text-[var(--text-secondary)] text-xs leading-relaxed mt-0.5"
                  style={{ fontFamily: 'var(--font-mono)' }}>
                  {review.self_analysis}
                </p>
              </div>

              {/* 对手模式分析 */}
              {Object.keys(review.opponent_patterns).length > 0 && (
                <div>
                  <span className="text-[var(--color-secondary)]/60 text-[10px] font-medium">对手模式</span>
                  <div className="mt-0.5 space-y-0.5">
                    {Object.entries(review.opponent_patterns).map(([name, pattern]) => (
                      <div key={name} className="text-xs">
                        <span className="text-[var(--color-primary)]/70">{name}:</span>
                        <span className="text-[var(--text-secondary)]/60 ml-1">{pattern}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 策略调整 */}
              <div>
                <span className="text-[var(--color-secondary)]/60 text-[10px] font-medium">策略调整</span>
                <p className="text-[var(--text-secondary)] text-xs leading-relaxed mt-0.5"
                  style={{ fontFamily: 'var(--font-mono)' }}>
                  {review.strategy_adjustment}
                </p>
              </div>

              {/* 回顾了哪些局 */}
              <div className="text-[var(--text-muted)] text-[10px]">
                回顾了第 {review.rounds_reviewed.join(', ')} 局
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
