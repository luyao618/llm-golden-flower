// ============================================================
// REST API 调用封装
// 封装所有后端 HTTP 接口调用
// ============================================================

import type {
  AIModelInfo,
  ActionResponse,
  ChatMessage,
  CopilotDeviceFlowResponse,
  CopilotPollResponse,
  CopilotStatusResponse,
  CreateGameRequest,
  CreateGameResponse,
  ExperienceReview,
  GameSummary,
  OpenRouterAddedModel,
  OpenRouterModel,
  PlayerActionRequest,
  ProviderStatus,
  RoundNarrative,
  SetKeyResponse,
  ThoughtRecord,
  VerifyKeyResponse,
} from '../types/game'

const BASE_URL = '/api'

// ---- 通用请求方法 ----

async function request<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${BASE_URL}${url}`, {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

// ---- 游戏管理 ----

/** 创建新游戏 */
export async function createGame(req: CreateGameRequest): Promise<CreateGameResponse> {
  return request<CreateGameResponse>('/game/create', {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

/** 获取游戏状态 */
export async function getGameState(gameId: string, playerId?: string) {
  const params = playerId ? `?player_id=${playerId}` : ''
  return request<{
    game_id: string
    status: string
    players: Array<Record<string, unknown>>
    current_round: Record<string, unknown> | null
    round_history: Array<Record<string, unknown>>
    config: Record<string, unknown>
  }>(`/game/${gameId}${params}`)
}

/** 开始游戏（开始第一局） */
export async function startGame(gameId: string) {
  return request<{
    message: string
    round_number: number
    dealer_index: number
    pot: number
    current_player_index: number
    game_state: Record<string, unknown>
  }>(`/game/${gameId}/start`, { method: 'POST' })
}

/** 结束游戏 */
export async function endGame(gameId: string) {
  return request<{
    message: string
    game_id: string
    final_standings: Array<{ id: string; name: string; chips: number }>
  }>(`/game/${gameId}/end`, { method: 'POST' })
}

/** 玩家执行操作 */
export async function playerAction(
  gameId: string,
  req: PlayerActionRequest
): Promise<ActionResponse> {
  return request<ActionResponse>(`/game/${gameId}/action`, {
    method: 'POST',
    body: JSON.stringify(req),
  })
}

/** 获取可用 AI 模型列表 */
export async function getAvailableModels(): Promise<AIModelInfo[]> {
  return request<AIModelInfo[]>('/models')
}

// ---- 心路历程 ----

/** 获取某 AI 的所有思考记录 */
export async function getThoughts(
  gameId: string,
  agentId: string
): Promise<ThoughtRecord[]> {
  const res = await request<{ thoughts: ThoughtRecord[] }>(
    `/game/${gameId}/thoughts/${agentId}`
  )
  return res.thoughts
}

/** 获取某 AI 某局的思考记录 */
export async function getRoundThoughts(
  gameId: string,
  agentId: string,
  roundNum: number
): Promise<ThoughtRecord[]> {
  const res = await request<{ thoughts: ThoughtRecord[] }>(
    `/game/${gameId}/thoughts/${agentId}/round/${roundNum}`
  )
  return res.thoughts
}

/** 获取某 AI 某局的叙事 */
export async function getRoundNarrative(
  gameId: string,
  agentId: string,
  roundNum: number
): Promise<RoundNarrative> {
  return request<RoundNarrative>(
    `/game/${gameId}/narrative/${agentId}/round/${roundNum}`
  )
}

/** 获取某 AI 的游戏总结 */
export async function getGameSummary(
  gameId: string,
  agentId: string
): Promise<GameSummary> {
  // Backend returns GameSummaryResponse with stats nested in a dict;
  // transform to the flat GameSummary shape the frontend expects.
  const res = await request<{
    agent_id: string
    stats: Record<string, unknown> | null
    key_moments: string[] | null
    opponent_impressions: Record<string, string> | null
    self_reflection: string | null
    chat_strategy_summary: string | null
    learning_journey: string | null
    narrative_summary: string | null
  }>(`/game/${gameId}/summary/${agentId}`)

  const stats = res.stats ?? {}
  return {
    agent_id: res.agent_id,
    rounds_played: (stats.rounds_played as number) ?? 0,
    rounds_won: (stats.rounds_won as number) ?? 0,
    total_chips_won: (stats.total_chips_won as number) ?? 0,
    total_chips_lost: (stats.total_chips_lost as number) ?? 0,
    biggest_win: (stats.biggest_win as number) ?? 0,
    biggest_loss: (stats.biggest_loss as number) ?? 0,
    fold_rate: (stats.fold_rate as number) ?? 0,
    key_moments: res.key_moments ?? [],
    opponent_impressions: res.opponent_impressions ?? {},
    self_reflection: res.self_reflection ?? '',
    chat_strategy_summary: res.chat_strategy_summary ?? '',
    learning_journey: res.learning_journey ?? '',
    narrative_summary: res.narrative_summary ?? '',
  }
}

/** 获取某 AI 的所有经验回顾记录 */
export async function getExperienceReviews(
  gameId: string,
  agentId: string
): Promise<ExperienceReview[]> {
  const res = await request<{ reviews: ExperienceReview[] }>(
    `/game/${gameId}/reviews/${agentId}`
  )
  return res.reviews
}

// ---- 聊天 ----

/** 获取聊天历史 */
export async function getChatHistory(gameId: string): Promise<ChatMessage[]> {
  const res = await request<{ messages: ChatMessage[] }>(`/game/${gameId}/chat`)
  return res.messages
}

/** 获取某局聊天历史 */
export async function getRoundChatHistory(
  gameId: string,
  roundNum: number
): Promise<ChatMessage[]> {
  const res = await request<{ messages: ChatMessage[] }>(
    `/game/${gameId}/chat/round/${roundNum}`
  )
  return res.messages
}

// ---- Provider 管理 (T8.0) ----

/** 获取所有 Provider 状态 */
export async function getProviders(): Promise<ProviderStatus[]> {
  return request<ProviderStatus[]>('/providers')
}

/** 设置 Provider API Key */
export async function setProviderKey(
  provider: string,
  key: string
): Promise<SetKeyResponse> {
  return request<SetKeyResponse>(`/providers/${provider}/key`, {
    method: 'POST',
    body: JSON.stringify({ key }),
  })
}

/** 验证 Provider API Key */
export async function verifyProviderKey(
  provider: string,
  key?: string
): Promise<VerifyKeyResponse> {
  return request<VerifyKeyResponse>(`/providers/${provider}/verify`, {
    method: 'POST',
    body: JSON.stringify({ key: key ?? null }),
  })
}

/** 移除 Provider API Key */
export async function removeProviderKey(
  provider: string
): Promise<{ message: string; provider: string; configured: boolean }> {
  return request(`/providers/${provider}/key`, { method: 'DELETE' })
}

// ---- GitHub Copilot (T8.0) ----

/** 发起 Copilot Device Flow 连接 */
export async function connectCopilot(): Promise<CopilotDeviceFlowResponse> {
  return request<CopilotDeviceFlowResponse>('/copilot/connect', {
    method: 'POST',
  })
}

/** 轮询 Copilot 授权状态 */
export async function pollCopilotAuth(): Promise<CopilotPollResponse> {
  return request<CopilotPollResponse>('/copilot/poll')
}

/** 获取 Copilot 连接状态 */
export async function getCopilotStatus(): Promise<CopilotStatusResponse> {
  return request<CopilotStatusResponse>('/copilot/status')
}

/** 断开 Copilot 连接 */
export async function disconnectCopilot(): Promise<{ message: string }> {
  return request('/copilot/disconnect', { method: 'POST' })
}

// ---- OpenRouter 模型管理 ----

/** 从 OpenRouter API 获取可用模型列表 */
export async function fetchOpenRouterModels(): Promise<{
  models: OpenRouterModel[]
  total: number
}> {
  return request('/openrouter/models')
}

/** 获取已添加到游戏的 OpenRouter 模型列表 */
export async function getAddedOpenRouterModels(): Promise<{
  models: OpenRouterAddedModel[]
}> {
  return request('/openrouter/models/added')
}

/** 添加一个 OpenRouter 模型到游戏 */
export async function addOpenRouterModel(
  modelId: string,
  displayName: string
): Promise<{
  message: string
  model_id: string
  openrouter_id: string
  display_name: string
}> {
  return request('/openrouter/models', {
    method: 'POST',
    body: JSON.stringify({ model_id: modelId, display_name: displayName }),
  })
}

/** 从游戏中移除一个 OpenRouter 模型 */
export async function removeOpenRouterModel(
  modelId: string
): Promise<{ message: string; model_id: string }> {
  return request(`/openrouter/models/${modelId}`, { method: 'DELETE' })
}
