/**
 * useGame hook 单元测试
 *
 * useGame 整合了 useWebSocket 和 Store 更新。
 * 我们 mock useWebSocket 返回值，然后手动触发 onMessage 回调，
 * 验证 store 状态正确更新。
 *
 * 覆盖：
 * - null config → 返回 disconnected
 * - game_state 事件 → setGameState + setMyPlayerId
 * - round_started → 重置状态 + 发牌动画
 * - cards_dealt → setMyCards
 * - turn_changed → setActivePlayer + setAvailableActions
 * - player_acted → addActionLog + chip animation
 * - chat_message → addChatMessage
 * - round_ended → addRoundResult + win animation
 * - game_ended → status = finished
 * - ai_thinking → setThinkingPlayer
 * - ai_reviewing → setReviewingPlayer
 * - error → pushErrorPopup
 * - copilot_error → setCopilotError
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'

import { useGame } from '../useGame'
import { useGameStore } from '../../stores/gameStore'
import { useUIStore } from '../../stores/uiStore'
import type { ServerEvent } from '../../types/game'

// ---- Mock useWebSocket ----

let capturedOnMessage: ((event: ServerEvent) => void) | null = null

vi.mock('../useWebSocket', () => ({
  useWebSocket: (config: { onMessage?: (event: ServerEvent) => void } | null) => {
    if (config?.onMessage) {
      capturedOnMessage = config.onMessage
    }
    return {
      status: config ? 'connected' : 'disconnected',
      sendAction: vi.fn(),
      sendChatMessage: vi.fn(),
      sendStartRound: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    }
  },
}))

function resetStores() {
  useGameStore.getState().reset()
  useUIStore.getState().resetUI()
}

function fire(event: ServerEvent) {
  act(() => {
    capturedOnMessage?.(event)
  })
}

describe('useGame', () => {
  beforeEach(() => {
    resetStores()
    capturedOnMessage = null
    vi.clearAllMocks()
  })

  // ---- null config ----

  it('returns disconnected when config is null', () => {
    const { result } = renderHook(() => useGame(null))
    expect(result.current.connectionStatus).toBe('disconnected')
  })

  // ---- game_state ----

  it('game_state → updates game store', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'game_state',
      data: {
        game_id: 'g1',
        players: [
          { id: 'p1', name: 'Me', avatar: '', player_type: 'human', chips: 1000, status: 'active_blind', hand: null, total_bet_this_round: 0, model_id: null },
          { id: 'p2', name: 'Bot', avatar: '', player_type: 'ai', chips: 1000, status: 'active_blind', hand: null, total_bet_this_round: 0, model_id: 'm1' },
        ],
        current_round: null,
        round_history: [],
        config: { initial_chips: 1000, ante: 10, max_bet: 200, max_turns: 10 },
        status: 'playing',
      },
    })

    expect(useGameStore.getState().gameId).toBe('g1')
    expect(useGameStore.getState().myPlayerId).toBe('p1')
    expect(useGameStore.getState().players).toHaveLength(2)
  })

  // ---- round_started ----

  it('round_started → resets state + starts dealing animation', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    // Pre-set some state
    useGameStore.getState().addChatMessage({
      id: 'old', game_id: 'g1', round_number: 1, player_id: 'p1',
      player_name: 'X', message_type: 'action_talk', content: 'hi', timestamp: 1,
    })

    fire({
      type: 'round_started',
      data: { round_number: 2, dealer: 'p2', dealer_index: 1, pot: 30, current_bet: 10, max_turns: 10 },
    })

    expect(useGameStore.getState().chatMessages).toEqual([])
    expect(useGameStore.getState().myCards).toEqual([])
    expect(useUIStore.getState().dealingAnimation.isDealing).toBe(true)
    expect(useGameStore.getState().currentRound?.round_number).toBe(2)
  })

  // ---- cards_dealt ----

  it('cards_dealt → sets my cards', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    const cards = [
      { suit: 'hearts', rank: 14 },
      { suit: 'spades', rank: 10 },
      { suit: 'diamonds', rank: 7 },
    ]
    fire({ type: 'cards_dealt', data: { your_cards: cards } })

    expect(useGameStore.getState().myCards).toEqual(cards)
  })

  // ---- turn_changed ----

  it('turn_changed → sets active player and available actions for me', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'turn_changed',
      data: {
        current_player: 'Me',
        current_player_id: 'p1',
        available_actions: ['call', 'raise', 'fold'],
      },
    })

    expect(useUIStore.getState().activePlayerId).toBe('p1')
    expect(useGameStore.getState().availableActions).toEqual(['call', 'raise', 'fold'])
  })

  it('turn_changed → clears available actions when not my turn', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'turn_changed',
      data: {
        current_player: 'Bot',
        current_player_id: 'p2',
        available_actions: ['call', 'raise', 'fold'],
      },
    })

    expect(useGameStore.getState().availableActions).toEqual([])
    expect(useUIStore.getState().activePlayerId).toBe('p2')
  })

  // ---- player_acted ----

  it('player_acted → adds action log and triggers chip animation', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'player_acted',
      data: {
        player_id: 'p2',
        player_name: 'Bot',
        action: 'call',
        amount: 20,
        compare_result: null,
      },
    })

    expect(useGameStore.getState().actionLog).toHaveLength(1)
    expect(useGameStore.getState().actionLog[0].action).toBe('call')
    expect(useUIStore.getState().chipAnimation).toEqual({
      fromPlayerId: 'p2',
      amount: 20,
    })
  })

  it('player_acted check_cards by me → sets hasLookedAtCards', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'player_acted',
      data: {
        player_id: 'p1',
        player_name: 'Me',
        action: 'check_cards',
        amount: 0,
        compare_result: null,
      },
    })

    expect(useUIStore.getState().hasLookedAtCards).toBe(true)
  })

  // ---- chat_message ----

  it('chat_message → adds to chatMessages', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'chat_message',
      data: {
        id: 'c1',
        player_id: 'p2',
        player_name: 'Bot',
        message_type: 'action_talk',
        content: 'I raise!',
        timestamp: 12345,
      },
    })

    expect(useGameStore.getState().chatMessages).toHaveLength(1)
    expect(useGameStore.getState().chatMessages[0].content).toBe('I raise!')
  })

  // ---- round_ended ----

  it('round_ended → adds result and triggers win animation', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    // Set up players so chip changes can be applied
    useGameStore.setState({
      players: [
        { id: 'p1', name: 'Me', avatar: '', player_type: 'human', chips: 500, status: 'active_blind', hand: null, total_bet_this_round: 0, model_id: null },
        { id: 'p2', name: 'Bot', avatar: '', player_type: 'ai', chips: 500, status: 'active_blind', hand: null, total_bet_this_round: 0, model_id: 'm1' },
      ],
    })

    fire({
      type: 'round_ended',
      data: {
        round_number: 1,
        winner_id: 'p1',
        winner_name: 'Me',
        pot: 100,
        win_method: 'fold',
        hands_revealed: null,
        player_chip_changes: { p1: 50, p2: -50 },
      },
    })

    expect(useGameStore.getState().roundHistory).toHaveLength(1)
    expect(useUIStore.getState().winAnimation).toEqual({
      winnerId: 'p1',
      amount: 100,
      isPlaying: true,
    })
    // Chips updated
    expect(useGameStore.getState().players[0].chips).toBe(550)
    expect(useGameStore.getState().players[1].chips).toBe(450)
  })

  // ---- game_ended ----

  it('game_ended → sets status to finished', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    useGameStore.setState({
      players: [
        { id: 'p1', name: 'Me', avatar: '', player_type: 'human', chips: 900, status: 'active_blind', hand: null, total_bet_this_round: 0, model_id: null },
      ],
    })

    fire({
      type: 'game_ended',
      data: {
        final_standings: [{ id: 'p1', name: 'Me', chips: 2000 }],
      },
    })

    expect(useGameStore.getState().status).toBe('finished')
    expect(useGameStore.getState().players[0].chips).toBe(2000)
  })

  // ---- ai_thinking / ai_reviewing ----

  it('ai_thinking → sets thinking player', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'ai_thinking',
      data: { player_id: 'p2', player_name: 'Bot' },
    })

    expect(useUIStore.getState().thinkingPlayerId).toBe('p2')
    expect(useUIStore.getState().activePlayerId).toBe('p2')
  })

  it('ai_reviewing → sets reviewing player', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'ai_reviewing',
      data: { player_id: 'p2', player_name: 'Bot', trigger: 'periodic' },
    })

    expect(useUIStore.getState().reviewingPlayerId).toBe('p2')
  })

  // ---- error ----

  it('error → pushes error popup and chat message', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'error',
      data: { message: 'Something went wrong' },
    })

    expect(useUIStore.getState().errorPopups).toHaveLength(1)
    expect(useUIStore.getState().errorPopups[0].message).toBe('Something went wrong')
    expect(useGameStore.getState().chatMessages).toHaveLength(1)
    expect(useGameStore.getState().chatMessages[0].message_type).toBe('system_message')
  })

  // ---- copilot_error ----

  it('copilot_error → sets copilot error state', () => {
    renderHook(() => useGame({ gameId: 'g1', playerId: 'p1' }))

    fire({
      type: 'copilot_error',
      data: { message: 'Subscription expired', error_code: '403' },
    })

    expect(useUIStore.getState().copilotError).toEqual({
      message: 'Subscription expired',
      errorCode: '403',
    })
  })
})
