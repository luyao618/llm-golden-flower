import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import GameInfoPanel from '../components/Table/GameInfoPanel'
import { useGameStore, type ActionLogEntry } from '../stores/gameStore'
import { useUIStore } from '../stores/uiStore'
import gameBg from '../assets/game-bg.jpg'

/**
 * GameDemoPage — 游戏信息面板 Demo 预览页
 *
 * 在完整的游戏背景上展示合并后的 GameInfoPanel，
 * 注入丰富的模拟数据（至少 8 条行动日志）方便检查效果。
 */

const DEMO_ACTION_LOG: Omit<ActionLogEntry, 'timestamp'>[] = [
  { player_id: 'ai-1', player_name: 'GPT-4o', action: 'call', amount: 20, compare_result: null },
  { player_id: 'ai-2', player_name: 'Claude', action: 'raise', amount: 40, compare_result: null },
  { player_id: 'ai-3', player_name: 'Gemini', action: 'fold', amount: 0, compare_result: null },
  { player_id: 'human-1', player_name: '玩家', action: 'check_cards', amount: 0, compare_result: null },
  { player_id: 'human-1', player_name: '玩家', action: 'call', amount: 40, compare_result: null },
  { player_id: 'ai-1', player_name: 'GPT-4o', action: 'raise', amount: 80, compare_result: null },
  { player_id: 'ai-2', player_name: 'Claude', action: 'call', amount: 80, compare_result: null },
  { player_id: 'human-1', player_name: '玩家', action: 'compare', amount: 80, compare_result: { winner_id: 'human-1', loser_name: 'GPT-4o', target_name: 'GPT-4o' } },
]

export default function GameDemoPage() {
  const navigate = useNavigate()
  const injected = useRef(false)

  useEffect(() => {
    if (injected.current) return

    // Inject mock state into stores
    useGameStore.setState({
      gameId: 'demo-game-info-panel',
      myPlayerId: 'human-1',
      players: [
        {
          id: 'human-1',
          name: '玩家',
          avatar: '🧑',
          player_type: 'human',
          chips: 850,
          status: 'active_seen',
          hand: null,
          total_bet_this_round: 80,
          model_id: null,
        },
        {
          id: 'ai-1',
          name: 'GPT-4o',
          avatar: '🤖',
          player_type: 'ai',
          chips: 1120,
          status: 'active_blind',
          hand: null,
          total_bet_this_round: 80,
          model_id: 'openai-gpt4o',
        },
        {
          id: 'ai-2',
          name: 'Claude',
          avatar: '🤖',
          player_type: 'ai',
          chips: 980,
          status: 'active_seen',
          hand: null,
          total_bet_this_round: 80,
          model_id: 'anthropic-claude',
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
        },
      ],
      status: 'playing',
      currentRound: {
        round_number: 3,
        pot: 520,
        current_bet: 80,
        dealer_index: 1,
        current_player_index: 2,
        actions: [],
        phase: 'betting',
        turn_count: 5,
        max_turns: 10,
      },
      actionLog: [],
    })

    // Add action log entries with staggered timestamps
    const baseTime = Date.now() / 1000 - DEMO_ACTION_LOG.length * 8
    for (let i = 0; i < DEMO_ACTION_LOG.length; i++) {
      // We need to set timestamp manually
      useGameStore.setState((s) => ({
        actionLog: [
          ...s.actionLog,
          { ...DEMO_ACTION_LOG[i], timestamp: baseTime + i * 8 },
        ],
      }))
    }

    // Set some UI state for demo
    useUIStore.setState({
      activePlayerId: 'ai-2',
      thinkingPlayerId: 'ai-2',
      isGameLogExpanded: true,
    })

    injected.current = true

    // Cleanup on unmount
    return () => {
      useGameStore.getState().reset()
      useUIStore.getState().resetUI()
    }
  }, [])

  return (
    <div className="h-screen bg-[var(--bg-deepest)] flex flex-col overflow-hidden">
      {/* Header */}
      <header className="shrink-0 flex items-center justify-between px-6 py-3 bg-black/60 backdrop-blur-md border-b border-white/[0.06] z-30">
        <button
          onClick={() => navigate(-1)}
          className="text-[var(--text-muted)] hover:text-[var(--color-primary)] text-sm transition-colors cursor-pointer"
        >
          ← 返回
        </button>
        <h1 className="text-[var(--color-primary)] text-sm font-medium tracking-wide" style={{ fontFamily: 'var(--font-display)' }}>
          GameInfoPanel Demo
        </h1>
        <div className="w-12" />
      </header>

      {/* Main area — game background with centered panel */}
      <main className="flex-1 relative min-h-0">
        {/* Background */}
        <div
          className="absolute inset-0 z-0"
          style={{
            backgroundImage: `url(${gameBg})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center center',
            backgroundRepeat: 'no-repeat',
          }}
        />
        <div
          className="absolute inset-0 z-0"
          style={{
            background: 'linear-gradient(to bottom, transparent 70%, rgba(6,6,15,0.5) 90%, #06060f 100%)',
          }}
        />

        {/* Ambient glow */}
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

        {/* The merged panel — positioned as it would be in-game */}
        <div className="absolute left-1/2 -translate-x-1/2 z-10" style={{ top: '40px' }}>
          <GameInfoPanel />
        </div>

        {/* Annotation */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 text-center space-y-2">
          <p className="text-[var(--text-muted)] text-sm">
            合并后的 <span className="text-[var(--color-primary)]">底池信息 + 行动日志</span> 面板
          </p>
          <p className="text-[var(--text-disabled)] text-xs">
            点击「行动日志」标题可折叠/展开 | 行动信息自动滚动到最新
          </p>
        </div>
      </main>
    </div>
  )
}
