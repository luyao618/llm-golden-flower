import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ThoughtRecord, ExperienceReview, RoundNarrative, GameAction } from '../types/game'
import { getAvatarColor } from '../utils/theme'
import ThoughtCard from '../components/Thought/ThoughtCard'
import NarrativeView from '../components/Thought/NarrativeView'

// ============================================================
// Mock Data
// ============================================================

interface MockAgent {
  id: string
  name: string
}

const MOCK_AGENTS: MockAgent[] = [
  { id: 'agent-001', name: '火焰哥' },
  { id: 'agent-002', name: '稳如山' },
  { id: 'agent-003', name: '数据侠' },
]

const MOCK_ROUNDS = [1, 2, 3, 4, 5]

function makeMockThoughts(agentId: string, round: number): ThoughtRecord[] {
  const decisions: GameAction[] = ['check_cards', 'call', 'raise', 'compare', 'fold']
  const emotions = ['谨慎', '自信', '紧张', '兴奋', '犹豫', '冷静']
  const reasonings = [
    '对手加注幅度不大，可能是在试探，我手牌还不错，先跟注观察。',
    '手牌评估为中等偏上，对手行为偏保守，适合加注施压。',
    '当前局面不利，筹码消耗过大，选择弃牌保存实力。',
    '已经看过牌了，手牌是顺子，胜率较高，可以主动比牌。',
    '盲注阶段先看牌了解手牌强度，再决定后续策略。',
  ]

  const count = 2 + (round % 3)
  return Array.from({ length: count }, (_, i) => ({
    agent_id: agentId,
    round_number: round,
    turn_number: i + 1,
    hand_evaluation: `手牌强度评估：当前牌型为${['高牌', '对子', '顺子', '同花', '豹子'][i % 5]}，在当前局面下属于${['较弱', '中等', '中等偏上', '较强', '极强'][i % 5]}水平。`,
    opponent_analysis: `对手 ${i === 0 ? '火焰哥' : '稳如山'} 近几轮行为偏${['激进', '保守', '稳健'][i % 3]}，加注频率${['较高', '一般', '较低'][i % 3]}，需要${['谨慎应对', '寻找机会反击', '保持观察'][i % 3]}。`,
    risk_assessment: `当前底池 ${150 + round * 50 + i * 30}，我的筹码 ${800 - round * 40}，风险收益比${['可接受', '需要谨慎', '较为有利'][i % 3]}。`,
    chat_analysis: i % 2 === 0 ? `对手发言"${['别紧张，跟注就好', '这把我感觉不错', '你确定要加注吗？'][i % 3]}"，可能是${['虚张声势', '真实自信', '试探性言论'][i % 3]}。` : null,
    reasoning: reasonings[i % reasonings.length],
    confidence: [0.35, 0.55, 0.72, 0.88, 0.45][i % 5],
    emotion: emotions[i % emotions.length],
    decision: decisions[i % decisions.length],
    decision_target: decisions[i % decisions.length] === 'compare' ? 'agent-002' : null,
    table_talk: i % 3 === 0 ? ['跟你玩玩', '这把我有信心', '算了，不跟了'][i % 3] : null,
    raw_response: '{}',
  }))
}

function makeMockReviews(agentId: string, round: number): ExperienceReview[] {
  if (round !== 3) return []
  return [
    {
      agent_id: agentId,
      trigger: 'consecutive_losses' as const,
      triggered_at_round: 3,
      rounds_reviewed: [1, 2, 3],
      self_analysis: '连续两局亏损，主要原因是在对手加注时没有及时弃牌，导致筹码持续流失。需要调整对"沉没成本"的心理依赖。',
      opponent_patterns: {
        '火焰哥': '偏激进，经常在第二轮大幅加注，但实际牌力不一定强。',
        '稳如山': '非常保守，只在牌好的时候才跟注或加注，他加注时要特别小心。',
      },
      strategy_adjustment: '减少在不确定局面的跟注，对保守型玩家的加注保持警惕，对激进型玩家可适当跟注观察真实牌力。',
      confidence_shift: -0.15,
      strategy_context: '前三局整体表现不佳，需要调整策略。',
    },
  ]
}

function makeMockNarrative(agentId: string, round: number): RoundNarrative {
  return {
    agent_id: agentId,
    round_number: round,
    narrative: `第${round}局开始了。我看了看自己的筹码，心里盘算着这一局的策略。\n\n底注下完后，我决定先看牌。翻开一看——还不错，是一副有潜力的牌。对面的火焰哥一如既往地快速加注，这让我有些犹豫。\n\n但转念一想，他经常在牌不好的时候也会这样做。我选择了跟注，想要试探他的真实意图。\n\n最终的结果证明了我的判断是正确的。这一局让我更加确信：在面对激进型玩家时，耐心和冷静是最好的武器。`,
    outcome: round % 2 === 0
      ? `第${round}局获胜，赢得底池 ${200 + round * 50} 筹码。`
      : `第${round}局落败，损失 ${80 + round * 20} 筹码。`,
  }
}

// ============================================================
// 时间线节点颜色
// ============================================================

const NODE_COLORS = [
  { ring: 'rgba(0, 212, 255, 0.6)', glow: 'rgba(0, 212, 255, 0.3)', text: '#00d4ff' },
  { ring: 'rgba(139, 92, 246, 0.6)', glow: 'rgba(139, 92, 246, 0.3)', text: '#8b5cf6' },
  { ring: 'rgba(255, 102, 170, 0.6)', glow: 'rgba(255, 102, 170, 0.3)', text: '#ff66aa' },
  { ring: 'rgba(0, 170, 255, 0.6)', glow: 'rgba(0, 170, 255, 0.3)', text: '#00aaff' },
]

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

// ============================================================
// Demo Page — 内嵌布局（不用抽屉模式）
// ============================================================

type ViewMode = 'timeline' | 'narrative'

export default function ThoughtDemoPage() {
  const [activeAgentId, setActiveAgentId] = useState(MOCK_AGENTS[0].id)
  const [selectedRound, setSelectedRound] = useState(1)
  const [viewMode, setViewMode] = useState<ViewMode>('timeline')

  const activeAgent = MOCK_AGENTS.find((a) => a.id === activeAgentId)!
  const thoughts = makeMockThoughts(activeAgentId, selectedRound)
  const reviews = makeMockReviews(activeAgentId, selectedRound)
  const narrative = makeMockNarrative(activeAgentId, selectedRound)

  return (
    <div
      className="min-h-screen flex"
      style={{ background: 'var(--bg-deepest)' }}
    >
      {/* ===== 左侧信息区 ===== */}
      <div className="flex-1 flex flex-col items-center justify-center relative">
        {/* 背景装饰 */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              'radial-gradient(ellipse at 70% 30%, rgba(0,212,255,0.06) 0%, transparent 50%), radial-gradient(ellipse at 30% 70%, rgba(139,92,246,0.04) 0%, transparent 50%)',
          }}
        />

        <div className="relative z-10 flex flex-col items-center gap-4 px-8">
          <h1
            className="text-3xl font-bold"
            style={{
              fontFamily: 'var(--font-display)',
              color: '#00d4ff',
              textShadow: '0 0 20px rgba(0,212,255,0.5)',
            }}
          >
            思维面板 Demo
          </h1>
          <p
            className="text-sm max-w-sm text-center leading-relaxed"
            style={{ color: '#7a7a9a' }}
          >
            右侧面板展示 AI 的心路历程。可切换 AI、切换局数、查看时间线和叙事视图。
          </p>
          <p
            className="text-xs max-w-sm text-center"
            style={{ color: '#505070' }}
          >
            选择第 3 局可查看「策略调整」经验回顾节点。
          </p>
        </div>
      </div>

      {/* ===== 右侧思维面板 ===== */}
      <div
        className="w-[420px] max-w-[50vw] h-screen flex flex-col relative"
        style={{
          background: '#1a1a35',
          backdropFilter: 'blur(24px)',
          borderLeft: '1px solid rgba(0, 212, 255, 0.15)',
          boxShadow: '-20px 0 60px rgba(0,212,255,0.05), -5px 0 30px rgba(0,0,0,0.5)',
        }}
      >
        {/* 左侧发光边缘装饰线 */}
        <div
          className="absolute left-0 top-0 bottom-0 w-[1px] pointer-events-none"
          style={{
            background:
              'linear-gradient(180deg, rgba(0,212,255,0.5), rgba(139,92,246,0.3), rgba(0,212,255,0.5))',
            boxShadow:
              '0 0 8px rgba(0,212,255,0.3), 0 0 20px rgba(0,212,255,0.1)',
          }}
        />

        {/* 头部 */}
        <div
          className="px-4 py-3 flex items-center justify-between shrink-0"
          style={{
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            background: 'rgba(10, 10, 26, 0.5)',
          }}
        >
          <div className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold
                bg-gradient-to-br ${getAvatarColor(activeAgent.id)}`}
              style={{
                boxShadow: '0 0 8px rgba(0,212,255,0.2)',
                outline: '1px solid rgba(0,212,255,0.3)',
                outlineOffset: '1px',
              }}
            >
              {activeAgent.name.charAt(0)}
            </div>
            <div className="flex flex-col">
              <span
                className="text-sm font-medium"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: 'rgba(0, 212, 255, 0.8)',
                }}
              >
                心路历程
              </span>
              <span
                className="text-[10px]"
                style={{ color: 'var(--text-muted)' }}
              >
                {activeAgent.name}
              </span>
            </div>
          </div>
        </div>

        {/* AI Tab 切换 */}
        <div
          className="flex items-center gap-1 px-3 py-2 overflow-x-auto shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          {MOCK_AGENTS.map((ai) => {
            const isActive = ai.id === activeAgentId
            return (
              <button
                key={ai.id}
                onClick={() => setActiveAgentId(ai.id)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all shrink-0 cursor-pointer"
                style={{
                  background: isActive ? 'rgba(0, 212, 255, 0.15)' : 'transparent',
                  border: isActive ? '1px solid rgba(0, 212, 255, 0.4)' : '1px solid transparent',
                  boxShadow: isActive ? '0 0 10px rgba(0,212,255,0.1)' : 'none',
                }}
              >
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-white text-[10px] font-bold
                    bg-gradient-to-br ${getAvatarColor(ai.id)}`}
                >
                  {ai.name.charAt(0)}
                </div>
                <span
                  className="text-xs truncate max-w-[60px]"
                  style={{
                    color: isActive ? 'var(--color-primary)' : 'var(--text-muted)',
                  }}
                >
                  {ai.name}
                </span>
              </button>
            )
          })}
        </div>

        {/* 局选择 + 视图切换 */}
        <div
          className="flex items-center justify-between px-3 py-2"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-1 overflow-x-auto">
            {MOCK_ROUNDS.map((r) => {
              const isActive = selectedRound === r
              return (
                <button
                  key={r}
                  onClick={() => { setSelectedRound(r); setViewMode('timeline') }}
                  className="px-2 py-0.5 rounded text-[11px] transition-all shrink-0 cursor-pointer"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    background: isActive ? 'rgba(0, 212, 255, 0.15)' : 'transparent',
                    color: isActive ? 'var(--color-primary)' : 'var(--text-muted)',
                    border: isActive ? '1px solid rgba(0, 212, 255, 0.4)' : '1px solid transparent',
                    boxShadow: isActive ? '0 0 8px rgba(0,212,255,0.15)' : 'none',
                  }}
                >
                  R{r}
                </button>
              )
            })}
          </div>

          <div
            className="flex items-center gap-0.5 rounded-md p-0.5 shrink-0 ml-2"
            style={{
              background: 'rgba(10, 10, 26, 0.6)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <button
              onClick={() => setViewMode('timeline')}
              className="px-2 py-0.5 rounded text-[10px] transition-all cursor-pointer"
              style={{
                background: viewMode === 'timeline' ? 'rgba(0, 212, 255, 0.15)' : 'transparent',
                color: viewMode === 'timeline' ? 'var(--color-primary)' : 'var(--text-muted)',
                boxShadow: viewMode === 'timeline' ? '0 0 6px rgba(0,212,255,0.15)' : 'none',
              }}
            >
              思考
            </button>
            <button
              onClick={() => setViewMode('narrative')}
              className="px-2 py-0.5 rounded text-[10px] transition-all cursor-pointer"
              style={{
                background: viewMode === 'narrative' ? 'rgba(139, 92, 246, 0.15)' : 'transparent',
                color: viewMode === 'narrative' ? 'var(--color-secondary)' : 'var(--text-muted)',
                boxShadow: viewMode === 'narrative' ? '0 0 6px rgba(139,92,246,0.15)' : 'none',
              }}
            >
              叙事
            </button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="flex-1 overflow-y-auto min-h-0">
          <AnimatePresence mode="wait">
            {viewMode === 'timeline' ? (
              <motion.div
                key={`timeline-${activeAgentId}-${selectedRound}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-3"
              >
                {/* 经验回顾 */}
                {reviews.map((review, i) => (
                  <ReviewNode key={`review-${i}`} review={review} />
                ))}

                {/* 垂直时间线 */}
                <div className="relative">
                  <div
                    className="absolute left-[22px] top-4 bottom-4 w-[2px] pointer-events-none"
                    style={{
                      background:
                        'linear-gradient(180deg, rgba(0,212,255,0.4), rgba(139,92,246,0.3), rgba(0,212,255,0.4))',
                      boxShadow: '0 0 6px rgba(0,212,255,0.15)',
                    }}
                  />

                  {thoughts.map((thought, i) => {
                    const nodeColor = NODE_COLORS[i % NODE_COLORS.length]
                    return (
                      <div key={`t-${thought.turn_number}`} className="relative flex gap-3 mb-3">
                        <div className="shrink-0 z-10 flex items-start pt-2">
                          <div
                            className="w-[44px] h-[44px] rounded-full flex items-center justify-center relative"
                            style={{ background: 'var(--bg-deepest)' }}
                          >
                            <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 44 44">
                              <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="3" />
                              <circle
                                cx="22" cy="22" r="18" fill="none"
                                stroke={nodeColor.ring} strokeWidth="3"
                                strokeDasharray={`${thought.confidence * 113} 113`}
                                strokeLinecap="round"
                                style={{ filter: `drop-shadow(0 0 4px ${nodeColor.glow})` }}
                              />
                            </svg>
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
                        <div className="flex-1 min-w-0">
                          <ThoughtCard thought={thought} index={i} />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key={`narrative-${activeAgentId}-${selectedRound}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="p-3"
              >
                <NarrativeView narrative={narrative} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
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
      className="rounded-lg overflow-hidden mb-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        background: 'rgba(139, 92, 246, 0.05)',
        border: '1px solid rgba(139, 92, 246, 0.25)',
        boxShadow: '0 0 15px rgba(139,92,246,0.06)',
      }}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 transition-colors cursor-pointer text-left"
        style={{ color: 'var(--text-secondary)' }}
      >
        <span
          className="text-[10px] font-medium shrink-0"
          style={{ color: 'var(--color-secondary)' }}
        >
          策略调整
        </span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded border shrink-0 ${triggerColor}`}>
          {triggerLabel}
        </span>
        <span
          className="text-xs truncate flex-1"
          style={{ color: 'rgba(176, 176, 208, 0.6)' }}
        >
          {review.strategy_adjustment}
        </span>
        <span
          className="text-[10px] shrink-0"
          style={{
            fontFamily: 'var(--font-mono)',
            color: review.confidence_shift >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
          }}
        >
          {review.confidence_shift >= 0 ? '+' : ''}{Math.round(review.confidence_shift * 100)}%
        </span>
        <motion.span
          className="text-xs shrink-0"
          style={{ color: 'var(--text-muted)' }}
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
            <div
              className="px-3 pb-3 space-y-2 pt-2"
              style={{ borderTop: '1px solid rgba(139, 92, 246, 0.15)' }}
            >
              <div>
                <span
                  className="text-[10px] font-medium"
                  style={{ color: 'rgba(139, 92, 246, 0.6)' }}
                >
                  自我分析
                </span>
                <p
                  className="text-xs leading-relaxed mt-0.5"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {review.self_analysis}
                </p>
              </div>
              {Object.keys(review.opponent_patterns).length > 0 && (
                <div>
                  <span
                    className="text-[10px] font-medium"
                    style={{ color: 'rgba(139, 92, 246, 0.6)' }}
                  >
                    对手模式
                  </span>
                  <div className="mt-0.5 space-y-0.5">
                    {Object.entries(review.opponent_patterns).map(([name, pattern]) => (
                      <div key={name} className="text-xs">
                        <span style={{ color: 'rgba(0, 212, 255, 0.7)' }}>{name}:</span>
                        <span className="ml-1" style={{ color: 'rgba(176, 176, 208, 0.6)' }}>{pattern}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <span
                  className="text-[10px] font-medium"
                  style={{ color: 'rgba(139, 92, 246, 0.6)' }}
                >
                  策略调整
                </span>
                <p
                  className="text-xs leading-relaxed mt-0.5"
                  style={{
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  {review.strategy_adjustment}
                </p>
              </div>
              <div
                className="text-[10px]"
                style={{ color: 'var(--text-muted)' }}
              >
                回顾了第 {review.rounds_reviewed.join(', ')} 局
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
