// ============================================================
// 游戏状态 Store (Zustand)
// 管理游戏配置、创建、基础状态
// ============================================================

import { create } from 'zustand'
import type {
  AIModelInfo,
  AIPlayerConfig,
  Card,
  ChatMessage,
  CreateGameResponse,
  GameAction,
  GameConfig,
  GameState,
  Player,
  RoundResult,
  RoundState,
} from '../types/game'

// ---- 操作日志条目（用于行动日志 T6.5）----

export interface ActionLogEntry {
  player_id: string
  player_name: string
  action: GameAction
  amount: number
  compare_result: Record<string, unknown> | null
  timestamp: number
}
import { createGame as apiCreateGame, getAvailableModels } from '../services/api'

// ---- AI 对手配置 (大厅用) ----

export interface AIOpponentConfig {
  model_id: string
  name: string
  personality: string
}

// ---- Store 类型 ----

interface GameStore {
  // 游戏状态
  gameId: string | null
  players: Player[]
  gameState: GameState | null
  status: 'idle' | 'creating' | 'playing' | 'finished'
  error: string | null

  // 牌桌运行时状态
  myPlayerId: string | null
  myCards: Card[]
  currentRound: RoundState | null
  roundHistory: RoundResult[]
  config: GameConfig | null
  chatMessages: ChatMessage[]
  availableActions: GameAction[]
  actionLog: ActionLogEntry[]

  // 大厅配置
  playerName: string
  aiOpponents: AIOpponentConfig[]
  gameConfig: GameConfig

  // 可用模型
  availableModels: AIModelInfo[]
  modelsLoading: boolean

  // Actions
  setPlayerName: (name: string) => void
  setGameConfig: (config: Partial<GameConfig>) => void

  // AI 对手管理
  addAIOpponent: () => void
  removeAIOpponent: (index: number) => void
  updateAIOpponent: (index: number, update: Partial<AIOpponentConfig>) => void

  // API 操作
  fetchModels: () => Promise<void>
  createGame: () => Promise<CreateGameResponse>
  setGameState: (state: GameState) => void
  reset: () => void

  // 牌桌运行时操作
  setMyPlayerId: (id: string) => void
  setMyCards: (cards: Card[]) => void
  setAvailableActions: (actions: GameAction[]) => void
  updatePlayer: (playerId: string, updates: Partial<Player>) => void
  setCurrentRound: (round: RoundState | null) => void
  addRoundResult: (result: RoundResult) => void
  addChatMessage: (message: ChatMessage) => void
  clearChatMessages: () => void
  addActionLog: (entry: Omit<ActionLogEntry, 'timestamp'>) => void
  clearActionLog: () => void

  // 衍生状态
  getMyPlayer: () => Player | undefined
  getCurrentPlayer: () => Player | undefined
  getPlayerById: (id: string) => Player | undefined
  isMyTurn: () => boolean
}

// ---- 默认值 ----

const DEFAULT_GAME_CONFIG: GameConfig = {
  initial_chips: 1000,
  ante: 10,
  max_bet: 200,
  max_turns: 10,
}

const DEFAULT_AI_OPPONENT: AIOpponentConfig = {
  model_id: '',  // will be auto-set to first available model by fetchModels()
  name: '',
  personality: '',
}

function createDefaultAIOpponent(): AIOpponentConfig {
  return { ...DEFAULT_AI_OPPONENT }
}

// ---- Store ----

export const useGameStore = create<GameStore>((set, get) => ({
  // 初始状态
  gameId: null,
  players: [],
  gameState: null,
  status: 'idle',
  error: null,

  myPlayerId: null,
  myCards: [],
  currentRound: null,
  roundHistory: [],
  config: null,
  chatMessages: [],
  availableActions: [],
  actionLog: [],

  playerName: '',
  aiOpponents: [createDefaultAIOpponent(), createDefaultAIOpponent()],
  gameConfig: { ...DEFAULT_GAME_CONFIG },

  availableModels: [],
  modelsLoading: false,

  // ---- 基础设置 ----

  setPlayerName: (name) => set({ playerName: name }),

  setGameConfig: (config) =>
    set((state) => ({
      gameConfig: { ...state.gameConfig, ...config },
    })),

  // ---- AI 对手管理 ----

  addAIOpponent: () =>
    set((state) => {
      if (state.aiOpponents.length >= 5) return state
      // 使用第一个可用模型作为默认值，避免使用不可用的硬编码模型
      const defaultModelId = state.availableModels.length > 0
        ? state.availableModels[0].id
        : DEFAULT_AI_OPPONENT.model_id
      const newOpponent: AIOpponentConfig = { ...DEFAULT_AI_OPPONENT, model_id: defaultModelId }
      return { aiOpponents: [...state.aiOpponents, newOpponent] }
    }),

  removeAIOpponent: (index) =>
    set((state) => {
      if (state.aiOpponents.length <= 1) return state
      return {
        aiOpponents: state.aiOpponents.filter((_, i) => i !== index),
      }
    }),

  updateAIOpponent: (index, update) =>
    set((state) => ({
      aiOpponents: state.aiOpponents.map((op, i) =>
        i === index ? { ...op, ...update } : op
      ),
    })),

  // ---- API 操作 ----

  fetchModels: async () => {
    set({ modelsLoading: true })
    try {
      const models = await getAvailableModels()
      // 如果当前 AI 对手的 model_id 不在可用模型列表中，自动修正为第一个可用模型
      const validIds = new Set(models.map((m) => m.id))
      const firstModelId = models.length > 0 ? models[0].id : ''
      const { aiOpponents } = get()
      const needsUpdate = aiOpponents.some((op) => !validIds.has(op.model_id))
      if (needsUpdate && firstModelId) {
        const updatedOpponents = aiOpponents.map((op) =>
          validIds.has(op.model_id) ? op : { ...op, model_id: firstModelId }
        )
        set({ availableModels: models, modelsLoading: false, aiOpponents: updatedOpponents })
      } else {
        set({ availableModels: models, modelsLoading: false })
      }
    } catch (err) {
      console.error('Failed to fetch models:', err)
      set({ modelsLoading: false })
    }
  },

  createGame: async () => {
    const { playerName, aiOpponents, gameConfig } = get()

    set({ status: 'creating', error: null })

    try {
      const aiConfigs: AIPlayerConfig[] = aiOpponents.map((op) => ({
        model_id: op.model_id,
        ...(op.name ? { name: op.name } : {}),
        ...(op.personality ? { personality: op.personality } : {}),
      }))

      const response = await apiCreateGame({
        player_name: playerName,
        ai_opponents: aiConfigs,
        initial_chips: gameConfig.initial_chips,
        ante: gameConfig.ante,
        max_bet: gameConfig.max_bet,
        max_turns: gameConfig.max_turns,
      })

      // 从响应中找到人类玩家的 ID
      const humanPlayer = response.players.find((p) => p.player_type === 'human')

      set({
        gameId: response.game_id,
        myPlayerId: humanPlayer?.id ?? null,
        status: 'playing',
      })

      return response
    } catch (err) {
      const message = err instanceof Error ? err.message : '创建游戏失败'
      set({ status: 'idle', error: message })
      throw err
    }
  },

  setGameState: (state) =>
    set({
      gameState: state,
      gameId: state.game_id,
      players: state.players,
      currentRound: state.current_round,
      roundHistory: state.round_history,
      config: state.config,
      status: state.status === 'finished' ? 'finished' : 'playing',
    }),

  reset: () =>
    set({
      gameId: null,
      players: [],
      gameState: null,
      status: 'idle',
      error: null,
      myPlayerId: null,
      myCards: [],
      currentRound: null,
      roundHistory: [],
      config: null,
      chatMessages: [],
      availableActions: [],
      actionLog: [],
      playerName: '',
      aiOpponents: [createDefaultAIOpponent(), createDefaultAIOpponent()],
      gameConfig: { ...DEFAULT_GAME_CONFIG },
    }),

  // ---- 牌桌运行时操作 ----

  setMyPlayerId: (id) => set({ myPlayerId: id }),

  setMyCards: (cards) => set({ myCards: cards }),

  setAvailableActions: (actions) => set({ availableActions: actions }),

  updatePlayer: (playerId, updates) =>
    set((state) => ({
      players: state.players.map((p) =>
        p.id === playerId ? { ...p, ...updates } : p
      ),
    })),

  setCurrentRound: (round) => set({ currentRound: round }),

  addRoundResult: (result) =>
    set((state) => ({
      roundHistory: [...state.roundHistory, result],
    })),

  addChatMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),

  clearChatMessages: () => set({ chatMessages: [] }),

  addActionLog: (entry) =>
    set((state) => ({
      actionLog: [
        ...state.actionLog,
        { ...entry, timestamp: Date.now() / 1000 },
      ],
    })),

  clearActionLog: () => set({ actionLog: [] }),

  // ---- 衍生状态 ----

  getMyPlayer: () => {
    const { players, myPlayerId } = get()
    return players.find((p) => p.id === myPlayerId)
  },

  getCurrentPlayer: () => {
    const { players, currentRound } = get()
    if (!currentRound) return undefined
    return players[currentRound.current_player_index]
  },

  getPlayerById: (id) => {
    return get().players.find((p) => p.id === id)
  },

  isMyTurn: () => {
    const { myPlayerId } = get()
    const currentPlayer = get().getCurrentPlayer()
    return currentPlayer?.id === myPlayerId
  },
}))
