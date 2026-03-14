import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useCallback } from 'react'
import TableLayout from '../components/Table/TableLayout'
import { ActionPanel } from '../components/Actions'
import ChatPanel from '../components/Table/ChatPanel'
import ChatInput from '../components/Table/ChatInput'
import GameLog from '../components/Table/GameLog'
import CardHand from '../components/Cards/CardHand'
import { ThoughtDrawer } from '../components/Thought'
import CopilotErrorModal from '../components/CopilotErrorModal'
import { useGameStore } from '../stores/gameStore'
import { useUIStore } from '../stores/uiStore'
import { useGame } from '../hooks/useGame'
import type { ConnectionStatus } from '../hooks/useWebSocket'

/**
 * 连接状态指示器
 */
function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const colorMap: Record<ConnectionStatus, string> = {
    connected: 'bg-[var(--color-success)]',
    connecting: 'bg-[var(--color-warning)] animate-pulse',
    reconnecting: 'bg-[var(--color-warning)] animate-pulse',
    disconnected: 'bg-[var(--color-danger)]',
  }
  const labelMap: Record<ConnectionStatus, string> = {
    connected: '已连接',
    connecting: '连接中...',
    reconnecting: '重连中...',
    disconnected: '已断开',
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
      <span className={`inline-block w-2 h-2 rounded-full ${colorMap[status]}`} />
      <span>{labelMap[status]}</span>
    </div>
  )
}

export default function GamePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const gameId = useGameStore((s) => s.gameId)
  const myPlayerId = useGameStore((s) => s.myPlayerId)
  const players = useGameStore((s) => s.players)
  const status = useGameStore((s) => s.status)
  const currentRound = useGameStore((s) => s.currentRound)
  const roundHistory = useGameStore((s) => s.roundHistory)
  const chatMessages = useGameStore((s) => s.chatMessages)
  const reset = useGameStore((s) => s.reset)
  const resetUI = useUIStore((s) => s.resetUI)
  const isChatPanelExpanded = useUIStore((s) => s.isChatPanelExpanded)
  const toggleChatPanel = useUIStore((s) => s.toggleChatPanel)
  const toggleThoughtDrawer = useUIStore((s) => s.toggleThoughtDrawer)
  const showPlayerCards = useUIStore((s) => s.showPlayerCards)
  const hasLookedAtCards = useUIStore((s) => s.hasLookedAtCards)
  const setHasLookedAtCards = useUIStore((s) => s.setHasLookedAtCards)
  const myCards = useGameStore((s) => s.myCards)

  // 使用 URL 中的 gameId，如果 store 中有 myPlayerId 就用它
  // 否则等 WebSocket 连接后通过 game_state 事件获取
  const effectiveGameId = id ?? gameId ?? ''

  // 连接 WebSocket（只有当 gameId 和 playerId 都有效时才连接）
  const gameConfig = useMemo(
    () =>
      effectiveGameId && myPlayerId
        ? { gameId: effectiveGameId, playerId: myPlayerId }
        : null,
    [effectiveGameId, myPlayerId],
  )

  const { connectionStatus, sendAction, sendStartRound, sendChatMessage, disconnect } = useGame(gameConfig)

  // 清理：离开页面时断开连接并重置状态
  useEffect(() => {
    return () => {
      disconnect()
      resetUI()
    }
  }, [disconnect, resetUI])

  // 处理结束游戏
  const handleEndGame = () => {
    disconnect()
    navigate(`/result/${effectiveGameId}`)
  }

  // 处理返回大厅
  const handleBackToLobby = () => {
    disconnect()
    reset()
    resetUI()
    navigate('/')
  }

  // 判断是否可以开始新局
  const canStartRound =
    connectionStatus === 'connected' &&
    players.length > 0 &&
    status === 'playing' &&
    !currentRound

  // 看牌回调（点击手牌触发）—— 同时发送 check_cards 操作给后端
  const handleLookAtCards = useCallback(() => {
    setHasLookedAtCards(true)
    sendAction('check_cards')
  }, [setHasLookedAtCards, sendAction])

  // 人类玩家信息
  const availableActions = useGameStore((s) => s.availableActions)
  const myPlayer = players.find((p) => p.id === myPlayerId)
  const isMyActive = myPlayer && myPlayer.status !== 'folded' && myPlayer.status !== 'out'
  // 只有当轮到自己且 check_cards 在可用操作中时，才允许点击牌面看牌
  const canLookAtCards = !hasLookedAtCards && myCards.length > 0 && availableActions.includes('check_cards')
  const showMyCards = showPlayerCards && currentRound && isMyActive && myCards.length > 0

  // 如果没有 myPlayerId，显示加载状态
  if (!myPlayerId) {
    return (
      <div className="h-screen bg-[var(--bg-deepest)] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="inline-block w-8 h-8 border-2 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
          <p className="text-[var(--color-primary)] text-sm">正在加载游戏...</p>
          <button
            onClick={handleBackToLobby}
            className="text-[var(--text-muted)] hover:text-[var(--color-primary)] text-xs underline cursor-pointer"
          >
            返回大厅
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-[var(--bg-deepest)] flex flex-col">
      {/* 顶部栏 */}
      <header className="flex items-center justify-between px-4 py-2 bg-[var(--bg-deep)]/80 backdrop-blur-md border-b border-[var(--border-default)]">
        <button
          onClick={handleBackToLobby}
          className="text-[var(--color-primary)] hover:text-[var(--color-primary)] text-sm transition-colors cursor-pointer"
        >
          ← 返回大厅
        </button>
        <div className="flex items-center gap-3">
          <div className="text-[var(--text-muted)] text-xs font-mono">
            ID: {effectiveGameId.slice(0, 8)}
          </div>
          <ConnectionIndicator status={connectionStatus} />
        </div>
        <div className="flex items-center gap-2">
          {/* 心路历程按钮 - 有已完成局时显示 */}
          {roundHistory.length > 0 && (
            <button
              onClick={() => toggleThoughtDrawer()}
              className="text-[var(--color-secondary)]/70 hover:text-[var(--color-secondary)] text-sm transition-colors cursor-pointer"
              title="查看 AI 心路历程"
            >
              心路历程
            </button>
          )}
          {status === 'finished' ? (
            <button
              onClick={() => navigate(`/result/${effectiveGameId}`)}
              className="text-[var(--color-gold)] hover:text-[var(--color-gold)] text-sm transition-colors cursor-pointer"
            >
              查看结果
            </button>
          ) : (
            <button
              onClick={handleEndGame}
              className="text-[var(--color-gold)] hover:text-[var(--color-gold)] text-sm transition-colors cursor-pointer"
            >
              结束游戏
            </button>
          )}
        </div>
      </header>

      {/* 牌桌 + 聊天区域 */}
      <main className="flex-1 relative min-h-0 flex">
        {/* 牌桌区域 */}
        <div className="flex-1 relative min-w-0 overflow-hidden">
          <TableLayout className="w-full h-full" />

          {/* 行动日志 - 左上角浮层 */}
          <div className="absolute top-2 left-2 w-64 z-10">
            <GameLog />
          </div>
        </div>

        {/* 聊天面板 */}
        <div
          className={`
            relative border-l border-[var(--border-default)] bg-[var(--bg-deep)]/40
            flex flex-col transition-all duration-300
            ${isChatPanelExpanded ? 'w-72' : 'w-8'}
          `}
        >
          {/* 折叠/展开按钮 */}
          <button
            onClick={toggleChatPanel}
            className="absolute -left-3 top-1/2 -translate-y-1/2 z-10
              w-6 h-12 bg-[var(--bg-surface)] border border-[var(--border-default)]
              rounded-l-md flex items-center justify-center
              hover:bg-[var(--bg-elevated)] transition-colors cursor-pointer"
            title={isChatPanelExpanded ? '收起聊天' : '展开聊天'}
          >
            <span className="text-[var(--color-primary)] text-xs">
              {isChatPanelExpanded ? '›' : '‹'}
            </span>
          </button>

          {isChatPanelExpanded && (
            <>
              {/* 聊天标题栏 */}
              <div className="px-3 py-2 border-b border-[var(--border-default)] flex items-center justify-between">
                <h3 className="text-xs font-medium text-[var(--color-primary)]/80">牌桌聊天</h3>
                <span className="text-[10px] text-[var(--text-muted)]">
                  {chatMessages.length} 条消息
                </span>
              </div>

              {/* 消息列表 */}
              <ChatPanel
                messages={chatMessages}
                className="flex-1 min-h-0 py-1"
              />

              {/* 输入框 */}
              <ChatInput
                onSend={sendChatMessage}
                disabled={connectionStatus !== 'connected'}
                placeholder={connectionStatus !== 'connected' ? '未连接...' : '说点什么...'}
              />
            </>
          )}
        </div>
      </main>

      {/* 底部操作区域：人类手牌 + 操作按钮 */}
      <footer className="shrink-0 bg-[var(--bg-deep)]/80 backdrop-blur-md border-t border-[var(--border-default)] relative z-20">
        {/* 人类玩家手牌行（仅在牌局进行中且玩家有牌时显示） */}
        {showMyCards && (
          <div className="flex items-center justify-center gap-3 pt-2 pb-1 border-b border-[var(--border-default)]">
            <CardHand
              cards={myCards}
              faceUp={hasLookedAtCards}
              size="sm"
              clickable={!!canLookAtCards}
              onClick={canLookAtCards ? handleLookAtCards : undefined}
              fanAngle={6}
            />
            {canLookAtCards && (
              <span className="text-[10px] text-[var(--color-gold)]/70 animate-pulse">
                点击看牌
              </span>
            )}
          </div>
        )}
        {/* 操作按钮行 */}
        <div className="h-16 flex items-center justify-center gap-4">
          {canStartRound && (
            <button
              onClick={sendStartRound}
              className="relative px-6 py-2 font-bold rounded-lg transition-all cursor-pointer text-sm text-[var(--text-primary)] bg-[var(--bg-surface)] border border-[var(--color-primary)]/40 hover:border-[var(--color-primary)]/70 hover:shadow-[0_0_15px_rgba(0,212,255,0.3)]"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              {roundHistory.length === 0 ? '开始第一局' : '开始下一局'}
            </button>
          )}
          {status === 'finished' && (
            <span className="text-[var(--color-gold)] text-sm font-medium">游戏已结束</span>
          )}
          {!canStartRound && status === 'playing' && currentRound && (
            <ActionPanel onAction={sendAction} />
          )}
          {connectionStatus === 'disconnected' && status !== 'finished' && (
            <span className="text-[var(--color-danger)] text-sm">连接已断开</span>
          )}
          {(connectionStatus === 'connecting' || connectionStatus === 'reconnecting') && (
            <span className="text-[var(--color-warning)] text-sm animate-pulse">正在连接服务器...</span>
          )}
        </div>
      </footer>

      {/* 心路历程抽屉 */}
      <ThoughtDrawer />

      {/* Copilot 错误弹窗 */}
      <CopilotErrorModal />
    </div>
  )
}
