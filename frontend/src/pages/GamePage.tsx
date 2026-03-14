import { useParams, useNavigate } from 'react-router-dom'
import { useEffect, useMemo, useRef } from 'react'
import TableLayout from '../components/Table/TableLayout'
import { ActionPanel } from '../components/Actions'
import ChatPanel from '../components/Table/ChatPanel'
import ChatInput from '../components/Table/ChatInput'
import GameLog from '../components/Table/GameLog'
import { ThoughtDrawer } from '../components/Thought'
import CopilotErrorModal from '../components/CopilotErrorModal'
import { useGameStore } from '../stores/gameStore'
import { useUIStore } from '../stores/uiStore'
import { useGame } from '../hooks/useGame'
import type { ConnectionStatus } from '../hooks/useWebSocket'
import type { Player, RoundState, GameConfig, Card, ActionLogEntry } from '../types/game'

// ============================================================
// DEV MOCK — 仅开发模式下填充假数据以预览 UI
// ============================================================

const DEV_MOCK_ENABLED = import.meta.env.DEV

const MOCK_PLAYERS: Player[] = [
  {
    id: 'human-1',
    name: '玩家',
    avatar: '🧑',
    player_type: 'human',
    chips: 850,
    status: 'active_seen',
    hand: [
      { suit: 'hearts', rank: 14 },
      { suit: 'spades', rank: 13 },
      { suit: 'diamonds', rank: 12 },
    ],
    total_bet_this_round: 40,
    model_id: null,
    personality: null,
  },
  {
    id: 'ai-1',
    name: 'GPT-4o',
    avatar: '🤖',
    player_type: 'ai',
    chips: 1120,
    status: 'active_blind',
    hand: null,
    total_bet_this_round: 20,
    model_id: 'openai-gpt4o',
    personality: '谨慎',
  },
  {
    id: 'ai-2',
    name: 'Claude',
    avatar: '🤖',
    player_type: 'ai',
    chips: 980,
    status: 'active_seen',
    hand: null,
    total_bet_this_round: 40,
    model_id: 'anthropic-claude',
    personality: '激进',
  },
  {
    id: 'ai-3',
    name: 'Gemini',
    avatar: '🤖',
    player_type: 'ai',
    chips: 650,
    status: 'folded',
    hand: null,
    total_bet_this_round: 10,
    model_id: 'google-gemini',
    personality: '随机',
  },
]

const MOCK_ROUND: RoundState = {
  round_number: 3,
  pot: 110,
  current_bet: 40,
  dealer_index: 1,
  current_player_index: 0,
  actions: [
    { player_id: 'ai-1', player_name: 'GPT-4o', action: 'call', amount: 20, target_id: null, timestamp: Date.now() / 1000 - 30 },
    { player_id: 'ai-2', player_name: 'Claude', action: 'raise', amount: 40, target_id: null, timestamp: Date.now() / 1000 - 20 },
    { player_id: 'ai-3', player_name: 'Gemini', action: 'fold', amount: 0, target_id: null, timestamp: Date.now() / 1000 - 10 },
  ],
  phase: 'betting',
  turn_count: 4,
  max_turns: 10,
}

const MOCK_CONFIG: GameConfig = {
  initial_chips: 1000,
  ante: 10,
  max_bet: 200,
  max_turns: 10,
}

const MOCK_MY_CARDS: Card[] = [
  { suit: 'hearts', rank: 14 },
  { suit: 'spades', rank: 13 },
  { suit: 'diamonds', rank: 12 },
]

const MOCK_ACTION_LOG: Omit<ActionLogEntry, 'timestamp'>[] = [
  { player_id: 'ai-1', player_name: 'GPT-4o', action: 'call', amount: 20, compare_result: null },
  { player_id: 'ai-2', player_name: 'Claude', action: 'raise', amount: 40, compare_result: null },
  { player_id: 'ai-3', player_name: 'Gemini', action: 'fold', amount: 0, compare_result: null },
]

function useDevMock() {
  const injected = useRef(false)
  const gameId = useGameStore((s) => s.gameId)

  useEffect(() => {
    if (!DEV_MOCK_ENABLED || injected.current || gameId) return

    const store = useGameStore.getState()
    useGameStore.setState({
      gameId: 'dev-mock-game-001',
      myPlayerId: 'human-1',
      players: MOCK_PLAYERS,
      status: 'playing',
      currentRound: MOCK_ROUND,
      config: MOCK_CONFIG,
      myCards: MOCK_MY_CARDS,
      availableActions: ['fold', 'call', 'raise', 'compare'],
      chatMessages: [
        {
          id: 'chat-1',
          game_id: 'dev-mock-game-001',
          round_number: 3,
          player_id: 'ai-1',
          player_name: 'GPT-4o',
          message_type: 'action_talk',
          content: '我跟了',
          timestamp: Date.now() / 1000 - 25,
        },
        {
          id: 'chat-2',
          game_id: 'dev-mock-game-001',
          round_number: 3,
          player_id: 'ai-2',
          player_name: 'Claude',
          message_type: 'action_talk',
          content: '加注！',
          timestamp: Date.now() / 1000 - 15,
        },
      ],
      roundHistory: [
        {
          round_number: 1,
          winner_id: 'human-1',
          winner_name: '玩家',
          pot: 60,
          win_method: 'all_folded',
          hands_revealed: null,
          player_chip_changes: { 'human-1': 40, 'ai-1': -20, 'ai-2': -10, 'ai-3': -10 },
        },
        {
          round_number: 2,
          winner_id: 'ai-2',
          winner_name: 'Claude',
          pot: 120,
          win_method: 'compare',
          hands_revealed: null,
          player_chip_changes: { 'human-1': -40, 'ai-1': -40, 'ai-2': 80, 'ai-3': 0 },
        },
      ],
    })

    for (const entry of MOCK_ACTION_LOG) {
      store.addActionLog(entry)
    }

    injected.current = true
    console.log('[DEV MOCK] 已注入模拟游戏数据')
  }, [gameId])
}

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
  useDevMock()

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

  const effectiveGameId = id ?? gameId ?? ''

  const gameConfig = useMemo(
    () =>
      effectiveGameId && myPlayerId
        ? { gameId: effectiveGameId, playerId: myPlayerId }
        : null,
    [effectiveGameId, myPlayerId],
  )

  const { connectionStatus, sendAction, sendStartRound, sendChatMessage, disconnect } = useGame(gameConfig)

  useEffect(() => {
    return () => {
      disconnect()
      resetUI()
    }
  }, [disconnect, resetUI])

  const handleEndGame = () => {
    disconnect()
    navigate(`/result/${effectiveGameId}`)
  }

  const handleBackToLobby = () => {
    disconnect()
    reset()
    resetUI()
    navigate('/')
  }

  const canStartRound =
    connectionStatus === 'connected' &&
    players.length > 0 &&
    status === 'playing' &&
    !currentRound

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
    <div className="h-screen bg-[var(--bg-deepest)] flex flex-col overflow-hidden">
      {/* 牌桌 + 侧面板 */}
      <main className="flex-1 relative min-h-0">
        {/* 牌桌区域 — 全屏 */}
        <div className="w-full h-full relative overflow-hidden">
          {/* 环境氛围光效 — 柔和的四角渐变 */}
          <div className="absolute inset-0 pointer-events-none z-0" aria-hidden="true">
            <div
              className="absolute inset-0"
              style={{
                background: `
                  radial-gradient(ellipse at 10% 10%, rgba(0,180,140,0.08) 0%, transparent 50%),
                  radial-gradient(ellipse at 90% 90%, rgba(180,50,70,0.06) 0%, transparent 50%),
                  radial-gradient(ellipse at 90% 10%, rgba(100,70,200,0.04) 0%, transparent 40%),
                  radial-gradient(ellipse at 10% 90%, rgba(100,70,200,0.04) 0%, transparent 40%)
                `,
              }}
            />
          </div>

          <TableLayout className="w-full h-full" onCheckCards={() => sendAction('check_cards')} />

          {/* 浮动顶部栏 */}
          <header className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-4 py-1.5 bg-black/40 backdrop-blur-sm border-b border-white/[0.04]">
            <button
              onClick={handleBackToLobby}
              className="text-[var(--text-muted)] hover:text-[var(--color-primary)] text-xs transition-colors cursor-pointer"
            >
              ← 返回
            </button>
            <div className="flex items-center gap-2">
              <span className="text-[var(--text-muted)] text-[10px] font-mono">
                {effectiveGameId.slice(0, 8)}
              </span>
              <ConnectionIndicator status={connectionStatus} />
            </div>
            <div className="flex items-center gap-2">
              {roundHistory.length > 0 && (
                <button
                  onClick={() => toggleThoughtDrawer()}
                  className="text-[var(--color-secondary)]/60 hover:text-[var(--color-secondary)] text-xs transition-colors cursor-pointer"
                  title="查看 AI 心路历程"
                >
                  心路历程
                </button>
              )}
              {status === 'finished' ? (
                <button
                  onClick={() => navigate(`/result/${effectiveGameId}`)}
                  className="text-[var(--color-gold)]/80 hover:text-[var(--color-gold)] text-xs transition-colors cursor-pointer"
                >
                  查看结果
                </button>
              ) : (
                <button
                  onClick={handleEndGame}
                  className="text-[var(--color-gold)]/60 hover:text-[var(--color-gold)] text-xs transition-colors cursor-pointer"
                >
                  结束
                </button>
              )}
            </div>
          </header>

          {/* 行动日志 - 左上角浮层（放大） */}
          <div className="absolute top-10 left-2 w-72 z-10">
            <GameLog />
          </div>

          {/* 聊天面板 - 左下角浮层 */}
          <div className="absolute bottom-2 left-2 w-72 z-10">
            <div className="flex flex-col bg-black/40 border border-[var(--border-default)] rounded-lg overflow-hidden backdrop-blur-sm">
              <button
                onClick={toggleChatPanel}
                className="flex items-center justify-between px-3 py-1.5 bg-black/30 hover:bg-black/50 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[var(--color-primary)]/80 text-xs font-medium">
                    牌桌聊天
                  </span>
                  {chatMessages.length > 0 && (
                    <span className="text-[var(--text-muted)] text-[10px]">
                      {chatMessages.length} 条
                    </span>
                  )}
                </div>
                <span className={`text-[var(--color-primary)]/60 text-xs transition-transform duration-200 ${isChatPanelExpanded ? 'rotate-180' : ''}`}>
                  ▴
                </span>
              </button>
              {isChatPanelExpanded && (
                <>
                  <ChatPanel
                    messages={chatMessages}
                    className="h-48 py-1"
                  />
                  <ChatInput
                    onSend={sendChatMessage}
                    disabled={connectionStatus !== 'connected'}
                    placeholder={connectionStatus !== 'connected' ? '未连接...' : '说点什么...'}
                  />
                </>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* 底部操作区域 — 更紧凑，与牌桌视觉融合 */}
      <footer className="shrink-0 bg-black/60 backdrop-blur-md border-t border-white/[0.06] relative z-20">
        {/* 操作按钮行 */}
        <div className="h-14 flex items-center justify-center gap-4">
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

      <ThoughtDrawer />
      <CopilotErrorModal />
    </div>
  )
}
