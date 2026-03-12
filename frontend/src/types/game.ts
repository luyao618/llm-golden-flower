// ============================================================
// 前端 TypeScript 类型定义
// 对应后端 app/models/ 下的数据模型
// ============================================================

// ---- 扑克牌 ----

export type Suit = 'hearts' | 'diamonds' | 'clubs' | 'spades'

export type Rank = 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14

export interface Card {
  suit: Suit
  rank: Rank
}

/** 花色显示符号 */
export const SUIT_SYMBOLS: Record<Suit, string> = {
  hearts: '♥',
  diamonds: '♦',
  clubs: '♣',
  spades: '♠',
}

/** 花色中文名 */
export const SUIT_NAMES: Record<Suit, string> = {
  hearts: '红心',
  diamonds: '方块',
  clubs: '梅花',
  spades: '黑桃',
}

/** 点数显示文本 */
export const RANK_DISPLAY: Record<Rank, string> = {
  2: '2',
  3: '3',
  4: '4',
  5: '5',
  6: '6',
  7: '7',
  8: '8',
  9: '9',
  10: '10',
  11: 'J',
  12: 'Q',
  13: 'K',
  14: 'A',
}

/** 花色颜色 */
export const SUIT_COLORS: Record<Suit, 'red' | 'black'> = {
  hearts: 'red',
  diamonds: 'red',
  clubs: 'black',
  spades: 'black',
}

// ---- 牌型 ----

export const HandType = {
  HIGH_CARD: 1,
  PAIR: 2,
  STRAIGHT: 3,
  FLUSH: 4,
  STRAIGHT_FLUSH: 5,
  THREE_OF_A_KIND: 6,
} as const

export type HandType = (typeof HandType)[keyof typeof HandType]

export const HAND_TYPE_NAMES: Record<HandType, string> = {
  [HandType.HIGH_CARD]: '散牌',
  [HandType.PAIR]: '对子',
  [HandType.STRAIGHT]: '顺子',
  [HandType.FLUSH]: '同花',
  [HandType.STRAIGHT_FLUSH]: '同花顺',
  [HandType.THREE_OF_A_KIND]: '豹子',
}

export interface HandResult {
  hand_type: HandType
  ranks: Rank[]
  description: string
}

// ---- 玩家 ----

export type PlayerType = 'human' | 'ai'

export type PlayerStatus =
  | 'active_blind'
  | 'active_seen'
  | 'folded'
  | 'out'

export interface Player {
  id: string
  name: string
  avatar: string
  player_type: PlayerType
  chips: number
  status: PlayerStatus
  hand: Card[] | null
  total_bet_this_round: number
  model_id: string | null
  personality: string | null
}

// ---- 游戏操作 ----

export type GamePhase =
  | 'waiting'
  | 'dealing'
  | 'betting'
  | 'comparing'
  | 'settlement'
  | 'game_over'

export type GameAction =
  | 'fold'
  | 'call'
  | 'raise'
  | 'check_cards'
  | 'compare'

export interface ActionRecord {
  player_id: string
  player_name: string
  action: GameAction
  amount: number | null
  target_id: string | null
  timestamp: number
}

// ---- 局面状态 ----

export interface RoundResult {
  round_number: number
  winner_id: string
  winner_name: string
  pot: number
  win_method: string
  hands_revealed: Record<string, Card[]> | null
  player_chip_changes: Record<string, number>
}

export interface RoundState {
  round_number: number
  pot: number
  current_bet: number
  dealer_index: number
  current_player_index: number
  actions: ActionRecord[]
  phase: GamePhase
  turn_count: number
  max_turns: number
}

export interface GameConfig {
  initial_chips: number
  ante: number
  max_bet: number
  max_turns: number
}

export interface GameState {
  game_id: string
  players: Player[]
  current_round: RoundState | null
  round_history: RoundResult[]
  config: GameConfig
  status: 'waiting' | 'playing' | 'finished'
}

// ---- 聊天 ----

export type ChatMessageType =
  | 'action_talk'
  | 'bystander_react'
  | 'player_message'
  | 'system_message'

export interface ChatMessage {
  id: string
  game_id: string
  round_number: number
  player_id: string
  player_name: string
  message_type: ChatMessageType
  content: string
  timestamp: number
  trigger_event?: string
  inner_thought?: string
}

// ---- 心路历程 ----

export interface ThoughtRecord {
  agent_id: string
  round_number: number
  turn_number: number
  hand_evaluation: string
  opponent_analysis: string
  risk_assessment: string
  chat_analysis: string | null
  reasoning: string
  confidence: number
  emotion: string
  decision: GameAction
  decision_target: string | null
  table_talk: string | null
  raw_response: string
}

export interface RoundNarrative {
  agent_id: string
  round_number: number
  narrative: string
  outcome: string
}

export interface GameSummary {
  agent_id: string
  rounds_played: number
  rounds_won: number
  total_chips_won: number
  total_chips_lost: number
  biggest_win: number
  biggest_loss: number
  fold_rate: number
  key_moments: string[]
  opponent_impressions: Record<string, string>
  self_reflection: string
  chat_strategy_summary: string
  learning_journey: string
  narrative_summary: string
}

// ---- 经验回顾 ----

export type ReviewTrigger =
  | 'chip_crisis'
  | 'consecutive_losses'
  | 'big_loss'
  | 'opponent_shift'
  | 'periodic'

export interface ExperienceReview {
  agent_id: string
  trigger: ReviewTrigger
  triggered_at_round: number
  rounds_reviewed: number[]
  self_analysis: string
  opponent_patterns: Record<string, string>
  strategy_adjustment: string
  confidence_shift: number
  strategy_context: string
}

// ---- API 请求/响应 ----

export interface AIPlayerConfig {
  model_id: string
  name?: string
  personality?: string
}

export interface CreateGameRequest {
  player_name: string
  ai_opponents: AIPlayerConfig[]
  initial_chips: number
  ante: number
  max_bet: number
  max_turns: number
}

export interface CreateGameResponse {
  game_id: string
  message: string
  players: Array<{
    id: string
    name: string
    player_type: PlayerType
    chips: number
    model_id: string | null
    personality: string | null
    avatar: string
  }>
}

export interface PlayerActionRequest {
  player_id: string
  action: GameAction
  target_id?: string
}

export interface ActionResponse {
  success: boolean
  action: GameAction
  player_id: string
  amount: number
  message: string
  compare_result: Record<string, unknown> | null
  round_ended: boolean
  round_result: RoundResult | null
  game_state: GameState | null
}

export interface AIModelInfo {
  id: string
  model: string
  display_name: string
  provider: string
}

// ---- Provider / Copilot 配置 (T8.0) ----

export type ProviderName = 'openai' | 'anthropic' | 'google'

export interface ProviderStatus {
  provider: ProviderName
  name: string
  configured: boolean
  key_preview: string | null
}

export interface CopilotDeviceFlowResponse {
  user_code: string
  verification_uri: string
  expires_in: number
}

export interface CopilotPollResponse {
  status: 'pending' | 'connected'
  models?: AIModelInfo[]
}

export interface CopilotStatusResponse {
  connected: boolean
  has_valid_token: boolean
  models: AIModelInfo[]
}

export interface SetKeyResponse {
  message: string
  provider: string
  configured: boolean
}

export interface VerifyKeyResponse {
  valid: boolean
  message: string
}

// ---- WebSocket 事件 ----

export type ServerEventType =
  | 'game_state'
  | 'game_started'
  | 'round_started'
  | 'cards_dealt'
  | 'turn_changed'
  | 'player_acted'
  | 'chat_message'
  | 'round_ended'
  | 'game_ended'
  | 'ai_thinking'
  | 'ai_reviewing'
  | 'error'

export interface ServerEvent<T = unknown> {
  type: ServerEventType
  data: T
}

export type ClientEventType =
  | 'player_action'
  | 'chat_message'
  | 'start_round'

export interface ClientEvent<T = unknown> {
  type: ClientEventType
  data?: T
}
