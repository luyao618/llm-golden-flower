import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useState, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useGameStore } from '../stores/gameStore'
import Leaderboard from '../components/Settlement/Leaderboard'
import type { LeaderboardPlayer } from '../components/Settlement/Leaderboard'
import AgentSummaryCard from '../components/Settlement/AgentSummaryCard'
import { getGameSummary, getExperienceReviews, getGameState } from '../services/api'
import type { GameSummary, ExperienceReview, Player } from '../types/game'

export default function ResultPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const gameId = id ?? ''

  // 从 store 获取状态（如果有的话）
  const storePlayers = useGameStore((s) => s.players)
  const storeConfig = useGameStore((s) => s.config)
  const reset = useGameStore((s) => s.reset)

  // 本地状态
  const [players, setPlayers] = useState<Player[]>(storePlayers)
  const [initialChips, setInitialChips] = useState(storeConfig?.initial_chips ?? 1000)
  const [summaries, setSummaries] = useState<Record<string, GameSummary>>({})
  const [reviews, setReviews] = useState<Record<string, ExperienceReview[]>>({})
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({})
  const [pageLoading, setPageLoading] = useState(true)

  // 如果 store 中没有 players 数据（例如直接访问 URL），从 API 加载
  useEffect(() => {
    async function loadGameData() {
      if (storePlayers.length > 0) {
        setPlayers(storePlayers)
        setInitialChips(storeConfig?.initial_chips ?? 1000)
        setPageLoading(false)
        return
      }

      if (!gameId) {
        setPageLoading(false)
        return
      }

      try {
        const state = await getGameState(gameId)
        const loaded = state.players.map((p: Record<string, unknown>) => ({
          id: p.id as string,
          name: p.name as string,
          avatar: (p.avatar as string) || '',
          player_type: p.player_type as 'human' | 'ai',
          chips: p.chips as number,
          status: p.status as Player['status'],
          hand: null,
          total_bet_this_round: 0,
          model_id: (p.model_id as string) || null,
          personality: (p.personality as string) || null,
        }))
        setPlayers(loaded)
        const config = state.config as Record<string, unknown>
        if (config?.initial_chips) {
          setInitialChips(config.initial_chips as number)
        }
      } catch (err) {
        console.error('Failed to load game state:', err)
      } finally {
        setPageLoading(false)
      }
    }

    loadGameData()
  }, [gameId, storePlayers, storeConfig])

  // AI 玩家列表
  const aiPlayers = useMemo(
    () => players.filter((p) => p.player_type === 'ai'),
    [players],
  )

  // 排行榜数据：按筹码降序
  const rankings: LeaderboardPlayer[] = useMemo(() => {
    return [...players]
      .sort((a, b) => b.chips - a.chips)
      .map((p) => ({
        player: p,
        chipChange: p.chips - initialChips,
        initialChips,
      }))
  }, [players, initialChips])

  // 加载所有 AI 的 summary 和 reviews
  const loadSummaries = useCallback(async () => {
    if (!gameId || aiPlayers.length === 0) return

    const loadingMap: Record<string, boolean> = {}
    aiPlayers.forEach((ai) => { loadingMap[ai.id] = true })
    setLoadingStates(loadingMap)

    await Promise.allSettled(
      aiPlayers.map(async (ai) => {
        try {
          const [summary, reviewList] = await Promise.all([
            getGameSummary(gameId, ai.id),
            getExperienceReviews(gameId, ai.id),
          ])
          setSummaries((prev) => ({ ...prev, [ai.id]: summary }))
          setReviews((prev) => ({ ...prev, [ai.id]: reviewList }))
        } catch (err) {
          console.error(`Failed to load summary for ${ai.name}:`, err)
        } finally {
          setLoadingStates((prev) => ({ ...prev, [ai.id]: false }))
        }
      }),
    )
  }, [gameId, aiPlayers])

  useEffect(() => {
    if (!pageLoading && aiPlayers.length > 0) {
      loadSummaries()
    }
  }, [pageLoading, aiPlayers.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // 返回大厅
  const handleBackToLobby = () => {
    reset()
    navigate('/')
  }

  // 加载中
  if (pageLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-950 via-green-900 to-green-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="inline-block w-8 h-8 border-2 border-green-400/30 border-t-green-400 rounded-full animate-spin" />
          <p className="text-green-400 text-sm">加载游戏结果...</p>
        </div>
      </div>
    )
  }

  // 没有数据
  if (players.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-950 via-green-900 to-green-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-green-400">未找到游戏数据</p>
          <button
            onClick={handleBackToLobby}
            className="px-6 py-2 bg-amber-500 hover:bg-amber-400 text-green-950 font-bold rounded-lg transition-colors cursor-pointer"
          >
            返回大厅
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-950 via-green-900 to-green-950">
      {/* 顶部栏 */}
      <header className="sticky top-0 z-10 bg-black/40 backdrop-blur border-b border-green-800/50">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <button
            onClick={handleBackToLobby}
            className="text-green-400 hover:text-green-300 text-sm transition-colors cursor-pointer"
          >
            ← 返回大厅
          </button>
          <div className="text-green-500/60 text-xs font-mono">
            ID: {gameId.slice(0, 8)}
          </div>
          <button
            onClick={handleBackToLobby}
            className="px-4 py-1.5 bg-amber-500 hover:bg-amber-400 text-green-950 font-bold rounded-lg transition-colors cursor-pointer text-sm"
          >
            再来一局
          </button>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-10">
        {/* 标题 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center"
        >
          <h1 className="text-3xl font-bold text-amber-400 mb-2">游戏结束</h1>
          <p className="text-green-400/60 text-sm">
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
        {aiPlayers.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.5 }}
            className="space-y-4"
          >
            <h2 className="text-xl font-bold text-amber-400 text-center">AI 总结报告</h2>
            <p className="text-green-500/50 text-xs text-center mb-4">
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
                    summary={summaries[ai.id] ?? null}
                    reviews={reviews[ai.id] ?? []}
                    loading={loadingStates[ai.id] ?? false}
                    initialOpen={index === 0}
                  />
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        {/* 底部 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.5 }}
          className="text-center pb-8"
        >
          <button
            onClick={handleBackToLobby}
            className="px-8 py-3 bg-amber-500 hover:bg-amber-400 text-green-950 font-bold rounded-lg transition-colors cursor-pointer"
          >
            再来一局
          </button>
        </motion.div>
      </main>
    </div>
  )
}
