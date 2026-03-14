import { useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUIStore } from '../../stores/uiStore'
import { useGameStore } from '../../stores/gameStore'
import type { Player } from '../../types/game'
import { getAvatarColor } from '../../utils/theme'
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
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => toggleThoughtDrawer()}
          />

          {/* 抽屉面板 */}
          <motion.div
            className="fixed top-0 right-0 h-full w-[420px] max-w-[90vw] z-50
              bg-[var(--bg-elevated)]/95 backdrop-blur-xl
              border-l border-[var(--color-primary)]/15
              flex flex-col"
            style={{
              boxShadow: '-20px 0 60px rgba(0,212,255,0.05), -5px 0 30px rgba(0,0,0,0.5)',
            }}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          >
            {/* 左侧发光边缘装饰线 */}
            <div
              className="absolute left-0 top-0 bottom-0 w-[1px] pointer-events-none"
              style={{
                background: 'linear-gradient(180deg, rgba(0,212,255,0.5), rgba(139,92,246,0.3), rgba(0,212,255,0.5))',
                boxShadow: '0 0 8px rgba(0,212,255,0.3), 0 0 20px rgba(0,212,255,0.1)',
              }}
            />

            {/* 头部 */}
            <div className="px-4 py-3 border-b border-[var(--border-default)] bg-[var(--bg-deep)]/50 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-2">
                {/* AI 头像 */}
                {activeAgent && (
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold
                      bg-gradient-to-br ${getAvatarColor(activeAgent.id)}
                      ring-1 ring-[var(--color-primary)]/30 shadow-[0_0_8px_rgba(0,212,255,0.2)]`}
                  >
                    {activeAgent.name.charAt(0)}
                  </div>
                )}
                <div className="flex flex-col">
                  <span className="text-[var(--color-primary)]/80 text-sm font-medium"
                    style={{ fontFamily: 'var(--font-display)' }}>
                    心路历程
                  </span>
                  {activeAgent && (
                    <span className="text-[var(--text-muted)] text-[10px]">
                      {activeAgent.name}
                    </span>
                  )}
                </div>
              </div>
              <button
                onClick={() => toggleThoughtDrawer()}
                className="w-7 h-7 flex items-center justify-center rounded-md
                  text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5
                  transition-colors cursor-pointer text-lg"
                title="关闭"
              >
                ×
              </button>
            </div>

            {/* AI Tab 切换 */}
            {aiPlayers.length > 1 && (
              <div className="flex items-center gap-1 px-3 py-2 border-b border-[var(--border-default)] overflow-x-auto shrink-0">
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
                <div className="flex items-center justify-center h-full text-[var(--text-muted)] text-sm">
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
          ? 'bg-[var(--color-primary)]/15 border border-[var(--color-primary)]/40 shadow-[0_0_10px_rgba(0,212,255,0.1)]'
          : 'hover:bg-white/5 border border-transparent'
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
        className={`text-xs truncate max-w-[60px] ${isActive ? 'text-[var(--color-primary)]' : 'text-[var(--text-muted)]'}`}
      >
        {player.name}
      </span>
    </button>
  )
}
