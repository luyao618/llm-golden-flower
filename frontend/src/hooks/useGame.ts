// ============================================================
// 游戏逻辑 Hook (T6.1)
//
// 整合 WebSocket 通信和 Store 状态管理。
// 处理全部服务端事件，更新 gameStore 和 uiStore。
// 提供客户端操作方法（发送玩家操作、聊天、开始新局）。
// ============================================================

import { useCallback, useMemo } from 'react'
import { useGameStore } from '../stores/gameStore'
import { useUIStore } from '../stores/uiStore'
import { useWebSocket, type ConnectionStatus } from './useWebSocket'
import type {
  Card,
  ChatMessage,
  GameAction,
  GameState,
  RoundResult,
  ServerEvent,
} from '../types/game'

// ---- 服务端事件 data 类型 ----

interface GameStateData extends GameState {}

interface RoundStartedData {
  round_number: number
  dealer: string
}

interface CardsDealtData {
  your_cards: Card[]
}

interface TurnChangedData {
  current_player: string
  current_player_id: string
  available_actions: string[]
}

interface PlayerActedData {
  player_id: string
  player_name: string
  action: string
  amount: number
  compare_result: Record<string, unknown> | null
}

interface ChatMessageData {
  id: string
  player_id: string
  player_name: string
  message_type: string
  content: string
  timestamp: number
}

interface RoundEndedData extends RoundResult {}

interface GameEndedData {
  final_standings: Array<{
    id: string
    name: string
    chips: number
  }>
}

interface AIThinkingData {
  player_id: string
  player_name: string
}

interface AIReviewingData {
  player_id: string
  player_name: string
  trigger: string
}

interface ErrorData {
  message: string
}

// ---- Hook 配置 ----

interface UseGameConfig {
  /** 游戏 ID */
  gameId: string
  /** 玩家 ID */
  playerId: string
}

// ---- Hook 返回值 ----

export interface UseGameReturn {
  /** WebSocket 连接状态 */
  connectionStatus: ConnectionStatus
  /** 发送玩家操作 */
  sendAction: (action: GameAction, target?: string) => void
  /** 发送聊天消息 */
  sendChatMessage: (content: string) => void
  /** 发送开始新局 */
  sendStartRound: () => void
  /** 手动断开 */
  disconnect: () => void
  /** 手动重连 */
  reconnect: () => void
}

// ---- Hook ----

export function useGame(config: UseGameConfig | null): UseGameReturn {
  const { gameId = '', playerId = '' } = config ?? {}

  // Store actions（从 store 中获取稳定的 action 引用）
  const setGameState = useGameStore((s) => s.setGameState)
  const setMyPlayerId = useGameStore((s) => s.setMyPlayerId)
  const setMyCards = useGameStore((s) => s.setMyCards)
  const setAvailableActions = useGameStore((s) => s.setAvailableActions)
  const setCurrentRound = useGameStore((s) => s.setCurrentRound)
  const addRoundResult = useGameStore((s) => s.addRoundResult)
  const addChatMessage = useGameStore((s) => s.addChatMessage)
  const clearChatMessages = useGameStore((s) => s.clearChatMessages)

  const setActivePlayer = useUIStore((s) => s.setActivePlayer)
  const setThinkingPlayer = useUIStore((s) => s.setThinkingPlayer)
  const setReviewingPlayer = useUIStore((s) => s.setReviewingPlayer)
  const startDealingAnimation = useUIStore((s) => s.startDealingAnimation)
  const triggerChipAnimation = useUIStore((s) => s.triggerChipAnimation)
  const startWinAnimation = useUIStore((s) => s.startWinAnimation)
  const setShowPlayerCards = useUIStore((s) => s.setShowPlayerCards)
  const setHasLookedAtCards = useUIStore((s) => s.setHasLookedAtCards)

  // ---- Server event handler ----

  const handleServerEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        // ---- game_state: 完整游戏状态（连接时收到）----
        case 'game_state': {
          const data = event.data as GameStateData
          setGameState(data)
          setMyPlayerId(playerId)

          // 如果玩家有手牌（重连场景）
          const me = data.players?.find((p) => p.id === playerId)
          if (me?.hand) {
            setMyCards(me.hand)
          }

          // 如果当前轮到我
          if (data.current_round) {
            const currentPlayer = data.players?.[data.current_round.current_player_index]
            if (currentPlayer) {
              setActivePlayer(currentPlayer.id)
            }
          }
          break
        }

        // ---- game_started: 游戏开始 ----
        case 'game_started': {
          const data = event.data as GameStateData
          setGameState(data)
          setMyPlayerId(playerId)
          break
        }

        // ---- round_started: 新一局开始 ----
        case 'round_started': {
          const data = event.data as RoundStartedData
          // 清空上一局的状态
          setMyCards([])
          setAvailableActions([])
          clearChatMessages()
          setThinkingPlayer(null)
          setReviewingPlayer(null)
          useGameStore.getState().clearActionLog()

          // 重置卡牌和看牌状态
          setShowPlayerCards(false)
          setHasLookedAtCards(false)

          // 触发发牌动画
          startDealingAnimation()

          // 更新局信息（部分信息，完整的 RoundState 会通过 game_state 更新）
          setCurrentRound({
            round_number: data.round_number,
            pot: 0,
            current_bet: 0,
            dealer_index: 0,
            current_player_index: 0,
            actions: [],
            phase: 'dealing',
            turn_count: 0,
            max_turns: 10,
          })
          break
        }

        // ---- cards_dealt: 发牌（只有自己的手牌）----
        case 'cards_dealt': {
          const data = event.data as CardsDealtData
          if (data.your_cards) {
            // 先保存手牌数据（不立即显示，等发牌动画完成后 showPlayerCards=true 再显示）
            setMyCards(data.your_cards)
          }
          break
        }

        // ---- turn_changed: 轮到某个玩家行动 ----
        case 'turn_changed': {
          const data = event.data as TurnChangedData
          setActivePlayer(data.current_player_id)
          setThinkingPlayer(null) // 清除 AI 思考状态

          // 如果轮到自己，设置可用操作
          if (data.current_player_id === playerId) {
            setAvailableActions(data.available_actions as GameAction[])
          } else {
            setAvailableActions([])
          }
          break
        }

        // ---- player_acted: 某个玩家执行了操作 ----
        case 'player_acted': {
          const data = event.data as PlayerActedData
          setThinkingPlayer(null) // 清除 AI 思考状态

          // 筹码飞行动画：下注/加注/跟注 等涉及筹码的操作
          if (data.amount > 0 && ['bet', 'raise', 'call', 'ante'].includes(data.action)) {
            triggerChipAnimation(data.player_id, data.amount)
          }

          // 将操作记录添加到 store 中的 actionLog（用于行动日志 T6.5）
          const store = useGameStore.getState()
          store.addActionLog({
            player_id: data.player_id,
            player_name: data.player_name,
            action: data.action as GameAction,
            amount: data.amount,
            compare_result: data.compare_result,
          })

          break
        }

        // ---- chat_message: 聊天消息 ----
        case 'chat_message': {
          const data = event.data as ChatMessageData
          const chatMsg: ChatMessage = {
            id: data.id,
            game_id: gameId,
            round_number: 0,
            player_id: data.player_id,
            player_name: data.player_name,
            message_type: data.message_type as ChatMessage['message_type'],
            content: data.content,
            timestamp: data.timestamp,
          }
          addChatMessage(chatMsg)
          break
        }

        // ---- round_ended: 本局结束 ----
        case 'round_ended': {
          const data = event.data as RoundEndedData
          addRoundResult(data)
          setAvailableActions([])
          setActivePlayer(null)
          setThinkingPlayer(null)
          setReviewingPlayer(null)

          // 触发赢家筹码飞行动画（底池 → 赢家）
          if (data.winner_id && data.pot > 0) {
            startWinAnimation(data.winner_id, data.pot)
          }

          // 延迟清理 round 状态，让赢家动画有时间播放
          setTimeout(() => {
            setCurrentRound(null)
            setShowPlayerCards(false)
            setHasLookedAtCards(false)
          }, 1500)
          break
        }

        // ---- game_ended: 整场游戏结束 ----
        case 'game_ended': {
          const data = event.data as GameEndedData
          setAvailableActions([])
          setActivePlayer(null)
          setThinkingPlayer(null)
          setReviewingPlayer(null)

          // 更新玩家最终筹码
          const store = useGameStore.getState()
          for (const standing of data.final_standings) {
            store.updatePlayer(standing.id, { chips: standing.chips })
          }

          // 设置游戏状态为完成
          useGameStore.setState({ status: 'finished' })
          break
        }

        // ---- ai_thinking: AI 正在思考 ----
        case 'ai_thinking': {
          const data = event.data as AIThinkingData
          setThinkingPlayer(data.player_id)
          setActivePlayer(data.player_id)
          break
        }

        // ---- ai_reviewing: AI 正在经验回顾 ----
        case 'ai_reviewing': {
          const data = event.data as AIReviewingData
          setReviewingPlayer(data.player_id)
          break
        }

        // ---- error: 错误消息 ----
        case 'error': {
          const data = event.data as ErrorData
          console.error('[Game] Server error:', data.message)
          // 将错误消息显示为系统聊天消息
          const errorMsg: ChatMessage = {
            id: `error-${Date.now()}`,
            game_id: gameId,
            round_number: 0,
            player_id: 'system',
            player_name: '系统',
            message_type: 'system_message',
            content: data.message,
            timestamp: Date.now() / 1000,
          }
          addChatMessage(errorMsg)
          break
        }

        default:
          console.warn('[Game] Unknown server event type:', event.type)
      }
    },
    [
      playerId,
      gameId,
      setGameState,
      setMyPlayerId,
      setMyCards,
      setAvailableActions,
      setCurrentRound,
      addRoundResult,
      addChatMessage,
      clearChatMessages,
      setActivePlayer,
      setThinkingPlayer,
      setReviewingPlayer,
      startDealingAnimation,
      triggerChipAnimation,
      startWinAnimation,
      setShowPlayerCards,
      setHasLookedAtCards,
    ],
  )

  // ---- WebSocket config (only when we have both IDs) ----

  const wsConfig = useMemo(
    () =>
      config && gameId && playerId
        ? {
            gameId,
            playerId,
            onMessage: handleServerEvent,
            onConnected: () => {
              console.log('[Game] WebSocket connected')
            },
            onDisconnected: () => {
              console.log('[Game] WebSocket disconnected')
            },
            onError: (error: string) => {
              console.error('[Game] WebSocket error:', error)
            },
          }
        : null,
    [config, gameId, playerId, handleServerEvent],
  )

  const ws = useWebSocket(wsConfig)

  return {
    connectionStatus: ws.status,
    sendAction: ws.sendAction,
    sendChatMessage: ws.sendChatMessage,
    sendStartRound: ws.sendStartRound,
    disconnect: ws.disconnect,
    reconnect: ws.reconnect,
  }
}
