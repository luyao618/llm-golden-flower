import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUIStore } from '../../stores/uiStore'
import { useGameStore } from '../../stores/gameStore'
import type { Player } from '../../types/game'
import ThoughtTimeline from './ThoughtTimeline'

/**
 * 心路历程抽屉组件
 *
 * 侧边滑出的面板，局结束后可展开查看 AI 的思考过程。
 * - 顶部有 AI Tab 切换（每个 AI 一个 tab）
 * - 内容区域展示选中 AI 的思考时间线/叙事
 * - 右侧固定位置，不遮挡牌桌操作
 */
export default function ThoughtDrawer() {
  const isOpen = useUIStore((s) => s.isThoughtDrawerOpen)
  const selectedAgentId = useUIStore((s) => s.thoughtDrawerAgentId)
  const toggleThoughtDrawer = useUIStore((s) => s.toggleThoughtDrawer)

  const gameId = useGameStore((s) => s.gameId)
  const players = useGameStore((s) => s.players)
  const roundHistory = useGameStore((s) => s.roundHistory)

  // 获取所有 AI 玩家
  const aiPlayers = useMemo(
    () => players.filter((p) => p.player_type === 'ai'),
    [players],
  )

  // 已完成的局数列表
  const completedRounds = useMemo(
    () => roundHistory.map((r) => r.round_number),
    [roundHistory],
  )

  // 当前选中的 AI（确保选中的仍存在于列表中）
  const activeAgentId = useMemo(() => {
    if (selectedAgentId && aiPlayers.some((p) => p.id === selectedAgentId)) {
      return selectedAgentId
    }
    return aiPlayers[0]?.id ?? null
  }, [selectedAgentId, aiPlayers])

  const activeAgent = useMemo(
    () => aiPlayers.find((p) => p.id === activeAgentId),
    [aiPlayers, activeAgentId],
  )

  if (aiPlayers.length === 0) return null

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* 半透明背景遮罩 */}
          <motion.div
            className="fixed inset-0 bg-black/40 z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => toggleThoughtDrawer()}
          />

          {/* 抽屉面板 */}
          <motion.div
            className="fixed top-0 right-0 h-full w-[420px] max-w-[90vw] z-50
              bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950
              border-l border-green-800/50 shadow-2xl
              flex flex-col"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* 头部 */}
            <div className="px-4 py-3 border-b border-green-800/40 bg-black/30 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-green-400/80 text-sm font-medium">心路历程</span>
                {activeAgent && (
                  <span className="text-green-600/50 text-xs">
                    — {activeAgent.name}
                  </span>
                )}
              </div>
              <button
                onClick={() => toggleThoughtDrawer()}
                className="w-7 h-7 flex items-center justify-center rounded-md
                  text-green-500/60 hover:text-green-400 hover:bg-green-900/30
                  transition-colors cursor-pointer text-lg"
                title="关闭"
              >
                ×
              </button>
            </div>

            {/* AI Tab 切换 */}
            {aiPlayers.length > 1 && (
              <div className="flex items-center gap-1 px-3 py-2 border-b border-green-800/30 overflow-x-auto shrink-0
                scrollbar-thin scrollbar-thumb-green-800/30">
                {aiPlayers.map((ai) => (
                  <AgentTab
                    key={ai.id}
                    player={ai}
                    isActive={ai.id === activeAgentId}
                    onClick={() => toggleThoughtDrawer(ai.id)}
                  />
                ))}
              </div>
            )}

            {/* 内容区域 */}
            <div className="flex-1 min-h-0">
              {activeAgentId && gameId ? (
                <ThoughtTimeline
                  key={activeAgentId} // 切换 AI 时重新挂载
                  gameId={gameId}
                  agentId={activeAgentId}
                  completedRounds={completedRounds}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-green-600/50 text-sm">
                  请选择一个 AI 查看
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

// ---- AI Tab 组件 ----

/** 头像背景色 (与 PlayerSeat 保持一致) */
const AVATAR_COLORS = [
  'from-rose-500 to-pink-600',
  'from-violet-500 to-purple-600',
  'from-blue-500 to-indigo-600',
  'from-cyan-500 to-teal-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
]

function getAvatarColor(playerId: string): string {
  let hash = 0
  for (let i = 0; i < playerId.length; i++) {
    hash = ((hash << 5) - hash + playerId.charCodeAt(i)) | 0
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function AgentTab({
  player,
  isActive,
  onClick,
}: {
  player: Player
  isActive: boolean
  onClick: () => void
}) {
  const avatarText = player.name.charAt(0)

  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg transition-all shrink-0 cursor-pointer
        ${isActive
          ? 'bg-green-700/30 border border-green-500/50'
          : 'hover:bg-green-900/30 border border-transparent'
        }
      `}
    >
      {/* 小头像 */}
      <div
        className={`w-5 h-5 rounded-full flex items-center justify-center text-white text-[9px] font-bold
          bg-gradient-to-br ${getAvatarColor(player.id)}`}
      >
        {avatarText}
      </div>
      {/* 名字 */}
      <span
        className={`text-xs truncate max-w-[60px] ${isActive ? 'text-green-300' : 'text-green-500/60'}`}
      >
        {player.name}
      </span>
    </button>
  )
}
