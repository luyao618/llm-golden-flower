import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import Leaderboard from '../components/Settlement/Leaderboard'
import type { LeaderboardPlayer } from '../components/Settlement/Leaderboard'
import AgentSummaryCard from '../components/Settlement/AgentSummaryCard'
import type { Player, GameSummary, ExperienceReview } from '../types/game'
import resultBg from '../assets/result-bg.png'

// ---- Mock 数据 ----

const mockPlayers: Player[] = [
  { id: 'p1', name: '赌神小明', avatar: '', player_type: 'human', chips: 1350, status: 'active_seen', hand: null, total_bet_this_round: 0, model_id: null },
  { id: 'p2', name: 'DeepBluff', avatar: '', player_type: 'ai', chips: 1120, status: 'active_seen', hand: null, total_bet_this_round: 0, model_id: 'gpt-4' },
  { id: 'p3', name: 'PokerMind', avatar: '', player_type: 'ai', chips: 870, status: 'active_blind', hand: null, total_bet_this_round: 0, model_id: 'claude-3' },
  { id: 'p4', name: 'CardShark', avatar: '', player_type: 'ai', chips: 660, status: 'folded', hand: null, total_bet_this_round: 0, model_id: 'gemini' },
]

const initialChips = 1000

const rankings: LeaderboardPlayer[] = mockPlayers
  .sort((a, b) => b.chips - a.chips)
  .map((p) => ({ player: p, chipChange: p.chips - initialChips, initialChips }))

const mockSummary: GameSummary = {
  agent_id: 'p2',
  rounds_played: 12,
  rounds_won: 5,
  total_chips_won: 620,
  total_chips_lost: 500,
  biggest_win: 280,
  biggest_loss: 150,
  fold_rate: 0.25,
  key_moments: [
    '第 3 局用对子A成功诈唬对手弃牌，赢得 280 筹码',
    '第 7 局识破对手虚张声势，果断比牌获胜',
    '第 10 局面对三人混战，选择保守弃牌避免大额损失',
  ],
  opponent_impressions: {
    '赌神小明': '打法灵活多变，善于在关键时刻加注施压，是最难对付的对手',
    'PokerMind': '非常保守，几乎只在有好牌时才跟注，容易被诈唬',
    'CardShark': '行为难以预测，时而激进时而保守，需要更多数据才能把握规律',
  },
  self_reflection: '本场比赛整体表现中规中矩。在前半段过于激进导致损失了一些筹码，后半段调整策略后逐渐稳定。需要提高对对手心理变化的感知能力。',
  chat_strategy_summary: '通过聊天制造压力，在加注前发送自信的消息来影响对手判断。',
  learning_journey: '从一开始的盲目激进，到中期学会观察对手行为模式，再到后期能够根据局势灵活调整策略。',
  narrative_summary: '这是一场充满转折的对局。DeepBluff 在经历了前期的挫折后，逐渐找到了自己的节奏，最终以稳健的打法守住了胜果。',
}

const mockSummary2: GameSummary = {
  agent_id: 'p3',
  rounds_played: 12,
  rounds_won: 3,
  total_chips_won: 350,
  total_chips_lost: 480,
  biggest_win: 200,
  biggest_loss: 180,
  fold_rate: 0.42,
  key_moments: [
    '第 5 局拿到豹子但因过于保守只赢了底池',
    '第 9 局被 DeepBluff 诈唬成功，损失 180 筹码',
  ],
  opponent_impressions: {
    '赌神小明': '攻守平衡的高手，很难找到破绽',
    'DeepBluff': '频繁使用诈唬策略，需要更多勇气去跟注',
  },
  self_reflection: '保守策略在这场比赛中效果不佳，错失了多次赢取大额筹码的机会。',
  chat_strategy_summary: '',
  learning_journey: '意识到过度保守会导致机会流失。',
  narrative_summary: 'PokerMind 以保守著称，但这一场的保守让它错过了太多好机会。',
}

const mockReviews: ExperienceReview[] = [
  {
    agent_id: 'p2',
    trigger: 'big_loss' as const,
    triggered_at_round: 4,
    rounds_reviewed: [1, 2, 3, 4],
    self_analysis: '前4局过于冒进，在没有好牌时也频繁加注，导致损失超出预期。',
    opponent_patterns: { '赌神小明': '倾向在有好牌时慢打，需要注意他突然加注的信号' },
    strategy_adjustment: '降低诈唬频率，在没有足够牌力支撑时选择跟注或弃牌而非加注。',
    confidence_shift: -0.15,
    strategy_context: '调整后胜率有所提升',
  },
  {
    agent_id: 'p2',
    trigger: 'periodic' as const,
    triggered_at_round: 8,
    rounds_reviewed: [5, 6, 7, 8],
    self_analysis: '策略调整后表现稳定，成功利用对手保守打法进行了几次有效的诈唬。',
    opponent_patterns: { 'PokerMind': '极度保守，弃牌率很高，适合用小额加注逼迫其弃牌' },
    strategy_adjustment: '针对保守型对手增加小额诈唬频率，针对人类对手保持稳健。',
    confidence_shift: 0.1,
    strategy_context: '',
  },
]

// ---- 预览页组件 ----

export default function ResultPreview() {
  const navigate = useNavigate()
  const aiPlayers = mockPlayers.filter((p) => p.player_type === 'ai')
  const summariesMap: Record<string, GameSummary> = { p2: mockSummary, p3: mockSummary2 }
  const reviewsMap: Record<string, ExperienceReview[]> = { p2: mockReviews }

  const handleBackToLobby = () => navigate('/')

  return (
    <div className="min-h-screen bg-[var(--bg-deepest)] relative overflow-hidden">
      {/* 背景图 — 固定定位，滚动时不动 */}
      <div className="fixed inset-0 pointer-events-none">
        <img
          src={resultBg}
          alt=""
          className="w-full h-full object-cover"
          style={{ objectPosition: 'center 20%', filter: 'brightness(0.75) saturate(1.2)' }}
        />
        {/* 暗色叠加层 — 保证文字可读性 */}
        <div className="absolute inset-0"
          style={{
            background: 'linear-gradient(to bottom, rgba(5,5,15,0.35) 0%, rgba(5,5,15,0.5) 50%, rgba(5,5,15,0.7) 100%)'
          }}
        />
      </div>
      {/* 背景装饰：径向光晕（叠在图片上方） */}
      <div className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 10%, rgba(0,212,255,0.06) 0%, transparent 50%), radial-gradient(ellipse at 50% 90%, rgba(139,92,246,0.04) 0%, transparent 50%)'
        }}
      />
      {/* 背景装饰：底部透视网格 */}
      <div className="absolute bottom-0 left-0 right-0 h-1/3 perspective-grid opacity-20 pointer-events-none" />

      {/* 顶部栏 */}
      <header className="sticky top-0 z-10 bg-[var(--bg-deep)]/80 backdrop-blur-md border-b border-[var(--border-default)]">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            onClick={handleBackToLobby}
            className="lobby-back-btn flex items-center gap-2.5 px-5 py-2.5 rounded-2xl
                       transition-all cursor-pointer group"
          >
            <svg className="w-5 h-5 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                 style={{ color: '#00d4ff', filter: 'drop-shadow(0 0 4px rgba(0,212,255,0.6))' }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="text-sm font-semibold tracking-wider"
                  style={{
                    fontFamily: 'var(--font-display)',
                    color: '#d5fbff',
                    textShadow: '0 0 8px rgba(0,212,255,0.5), 0 0 20px rgba(0,212,255,0.25)',
                  }}>
              返回大厅
            </span>
          </button>
          <div className="text-[var(--text-muted)] text-xs font-mono">
            ID: preview0
          </div>
          <div className="neon-btn-wrapper inline-block">
            <button
              onClick={handleBackToLobby}
              className="relative px-4 py-1.5 font-bold rounded-xl text-sm bg-[var(--bg-surface)] text-[var(--text-primary)] transition-all cursor-pointer hover:bg-[var(--bg-elevated)]"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              再来一局
            </button>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-10 relative z-[1]">
        {/* 标题 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <h1 className="text-4xl font-bold neon-text-hero mb-3"
              style={{ fontFamily: 'var(--font-display)' }}>
            GAME OVER
          </h1>
          <div className="mx-auto w-48 title-deco-line mb-3" />
          <p className="text-[var(--text-muted)] text-sm">
            共 {rankings.length} 名玩家参与了本场对局
          </p>
        </motion.div>

        {/* 排行榜 */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.5 }}
        >
          <Leaderboard rankings={rankings} />
        </motion.section>

        {/* AI 总结报告 */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.5 }}
          className="space-y-4"
        >
          <h2 className="text-xl font-bold text-[var(--text-primary)] text-center"
              style={{ fontFamily: 'var(--font-display)' }}>
            AI 总结报告
          </h2>
          <p className="text-[var(--text-muted)] text-xs text-center mb-4">
            点击卡片查看每个 AI 的详细总结、关键时刻回顾和策略调整历程
          </p>

          <div className="space-y-3">
            {aiPlayers.map((ai, index) => (
              <motion.div
                key={ai.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + index * 0.1, duration: 0.4 }}
              >
                <AgentSummaryCard
                  player={ai}
                  summary={summariesMap[ai.id] ?? null}
                  reviews={reviewsMap[ai.id] ?? []}
                  loading={false}
                  initialOpen={index === 0}
                />
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* 底部按钮 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.5 }}
          className="text-center pb-8"
        >
          <div className="neon-btn-wrapper inline-block">
            <button
              onClick={handleBackToLobby}
              className="relative px-8 py-3 font-bold rounded-xl text-lg bg-[var(--bg-surface)] text-[var(--text-primary)] transition-all cursor-pointer hover:bg-[var(--bg-elevated)] active:scale-[0.98]"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              再来一局
            </button>
          </div>
        </motion.div>
      </main>
    </div>
  )
}
