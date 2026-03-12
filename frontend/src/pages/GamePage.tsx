import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useMemo } from 'react'
import TableLayout from '../components/Table/TableLayout'
import { ActionPanel } from '../components/Actions'
import ChatPanel from '../components/Table/ChatPanel'
import ChatInput from '../components/Table/ChatInput'
import { useGameStore } from '../stores/gameStore'
import { useUIStore } from '../stores/uiStore'
import { useGame } from '../hooks/useGame'
import type { ConnectionStatus } from '../hooks/useWebSocket'

/**
 * 连接状态指示器
 */
function ConnectionIndicator({ status }: { status: ConnectionStatus }) {
  const colorMap: Record<ConnectionStatus, string> = {
    connected: 'bg-green-400',
    connecting: 'bg-yellow-400 animate-pulse',
    reconnecting: 'bg-amber-400 animate-pulse',
    disconnected: 'bg-red-400',
  }
  const labelMap: Record<ConnectionStatus, string> = {
    connected: '已连接',
    connecting: '连接中...',
    reconnecting: '重连中...',
    disconnected: '已断开',
  }

  return (
    <div className="flex items-center gap-1.5 text-xs text-green-500/60">
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

  // 如果没有 myPlayerId，显示加载状态
  if (!myPlayerId) {
    return (
      <div className="h-screen bg-gradient-to-b from-green-950 via-green-900 to-green-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="inline-block w-8 h-8 border-2 border-green-400/30 border-t-green-400 rounded-full animate-spin" />
          <p className="text-green-400 text-sm">正在加载游戏...</p>
          <button
            onClick={handleBackToLobby}
            className="text-green-600 hover:text-green-400 text-xs underline cursor-pointer"
          >
            返回大厅
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-gradient-to-b from-green-950 via-green-900 to-green-950 flex flex-col">
      {/* 顶部栏 */}
      <header className="flex items-center justify-between px-4 py-2 bg-black/30 border-b border-green-800/50">
        <button
          onClick={handleBackToLobby}
          className="text-green-400 hover:text-green-300 text-sm transition-colors cursor-pointer"
        >
          ← 返回大厅
        </button>
        <div className="flex items-center gap-3">
          <div className="text-green-500/60 text-xs font-mono">
            ID: {effectiveGameId.slice(0, 8)}
          </div>
          <ConnectionIndicator status={connectionStatus} />
        </div>
        <div className="flex items-center gap-2">
          {status === 'finished' ? (
            <button
              onClick={() => navigate(`/result/${effectiveGameId}`)}
              className="text-amber-500 hover:text-amber-400 text-sm transition-colors cursor-pointer"
            >
              查看结果
            </button>
          ) : (
            <button
              onClick={handleEndGame}
              className="text-amber-500 hover:text-amber-400 text-sm transition-colors cursor-pointer"
            >
              结束游戏
            </button>
          )}
        </div>
      </header>

      {/* 牌桌 + 聊天区域 */}
      <main className="flex-1 relative min-h-0 flex">
        {/* 牌桌区域 */}
        <div className="flex-1 relative min-w-0">
          <TableLayout className="w-full h-full" />
        </div>

        {/* 聊天面板 */}
        <div
          className={`
            relative border-l border-green-800/50 bg-black/20
            flex flex-col transition-all duration-300
            ${isChatPanelExpanded ? 'w-72' : 'w-8'}
          `}
        >
          {/* 折叠/展开按钮 */}
          <button
            onClick={toggleChatPanel}
            className="absolute -left-3 top-1/2 -translate-y-1/2 z-10
              w-6 h-12 bg-green-900/80 border border-green-700/50
              rounded-l-md flex items-center justify-center
              hover:bg-green-800/80 transition-colors cursor-pointer"
            title={isChatPanelExpanded ? '收起聊天' : '展开聊天'}
          >
            <span className="text-green-400 text-xs">
              {isChatPanelExpanded ? '›' : '‹'}
            </span>
          </button>

          {isChatPanelExpanded && (
            <>
              {/* 聊天标题栏 */}
              <div className="px-3 py-2 border-b border-green-800/40 flex items-center justify-between">
                <h3 className="text-xs font-medium text-green-400/80">牌桌聊天</h3>
                <span className="text-[10px] text-green-700/50">
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

      {/* 底部操作区域 */}
      <footer className="h-20 bg-black/40 border-t border-green-800/50 flex items-center justify-center gap-4">
        {canStartRound && (
          <button
            onClick={sendStartRound}
            className="px-6 py-2 bg-amber-500 hover:bg-amber-400 text-green-950 font-bold rounded-lg transition-all cursor-pointer text-sm"
          >
            {roundHistory.length === 0 ? '开始第一局' : '开始下一局'}
          </button>
        )}
        {status === 'finished' && (
          <span className="text-amber-400 text-sm font-medium">游戏已结束</span>
        )}
        {!canStartRound && status === 'playing' && currentRound && (
          <ActionPanel onAction={sendAction} />
        )}
        {connectionStatus === 'disconnected' && status !== 'finished' && (
          <span className="text-red-400 text-sm">连接已断开</span>
        )}
        {(connectionStatus === 'connecting' || connectionStatus === 'reconnecting') && (
          <span className="text-yellow-400 text-sm animate-pulse">正在连接服务器...</span>
        )}
      </footer>
    </div>
  )
}
