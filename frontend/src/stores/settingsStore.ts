// ============================================================
// 游戏设置 Store (Zustand)
// 管理全局设置：AI 调用配置、LLM max_tokens
// 管理 Provider API Keys（持久化到 localStorage）
// ============================================================

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { getSettings, updateSettings, type AiThinkingMode, type SettingsData } from '../services/api'
import { useUIStore } from './uiStore'

// ---- Provider Keys Store (localStorage 持久化) ----

export type ProviderName = 'openrouter' | 'siliconflow' | 'azure_openai' | 'zhipu'

interface ProviderKeysState {
  /** provider -> API Key */
  keys: Partial<Record<ProviderName, string>>
  /** 设置某个 Provider 的 API Key */
  setKey: (provider: ProviderName, key: string) => void
  /** 移除某个 Provider 的 API Key */
  removeKey: (provider: ProviderName) => void
  /** 获取某个 Provider 的 API Key */
  getKey: (provider: ProviderName) => string | undefined
  /** 获取所有已配置的 keys（用于传递给后端） */
  getAllKeys: () => Record<string, string>
}

export const useProviderKeysStore = create<ProviderKeysState>()(
  persist(
    (set, get) => ({
      keys: {},

      setKey: (provider, key) => {
        set((state) => ({
          keys: { ...state.keys, [provider]: key },
        }))
      },

      removeKey: (provider) => {
        set((state) => {
          const newKeys = { ...state.keys }
          delete newKeys[provider]
          return { keys: newKeys }
        })
      },

      getKey: (provider) => get().keys[provider],

      getAllKeys: () => {
        const keys = get().keys
        const result: Record<string, string> = {}
        for (const [k, v] of Object.entries(keys)) {
          if (v) result[k] = v
        }
        return result
      },
    }),
    {
      name: 'golden-flower-provider-keys',
    },
  ),
)

// ---- Settings Store (非持久化，从后端拉取) ----

export interface SettingsState {
  /** LLM 最大生成 token 数，null 表示无上限 */
  maxTokens: number | null
  /** AI 思考模式 */
  aiThinkingMode: AiThinkingMode
  /** AI 调用配置 */
  llmTimeout: number
  llmMaxRetries: number
  llmTemperature: number
  /** 加载/保存状态 */
  loading: boolean
  saving: boolean

  /** 从后端拉取当前设置 */
  fetchSettings: () => Promise<void>
  /** 更新 max_tokens */
  setMaxTokens: (value: number | null) => Promise<void>
  /** 更新 AI 思考模式 */
  setAiThinkingMode: (mode: AiThinkingMode) => Promise<void>
  /** 更新单个设置项 */
  updateSetting: <K extends keyof SettingsData>(key: K, value: SettingsData[K]) => Promise<void>
}

export const useSettingsStore = create<SettingsState>((set) => ({
  maxTokens: null,
  aiThinkingMode: 'fast',
  llmTimeout: 30,
  llmMaxRetries: 3,
  llmTemperature: 0.7,
  loading: false,
  saving: false,

  fetchSettings: async () => {
    set({ loading: true })
    try {
      const res = await getSettings()
      set({
        maxTokens: res.llm_max_tokens,
        aiThinkingMode: res.ai_thinking_mode,
        llmTimeout: res.llm_timeout,
        llmMaxRetries: res.llm_max_retries,
        llmTemperature: res.llm_temperature,
      })
    } catch (err) {
      useUIStore.getState().pushErrorPopup({
        message: err instanceof Error ? err.message : '获取设置失败',
        source: '加载设置',
      })
    } finally {
      set({ loading: false })
    }
  },

  setMaxTokens: async (value: number | null) => {
    set({ saving: true })
    try {
      await updateSettings({ llm_max_tokens: value })
      set({ maxTokens: value })
    } catch (err) {
      useUIStore.getState().pushErrorPopup({
        message: err instanceof Error ? err.message : '更新设置失败',
        source: '保存设置',
      })
    } finally {
      set({ saving: false })
    }
  },

  setAiThinkingMode: async (mode: AiThinkingMode) => {
    set({ saving: true })
    try {
      await updateSettings({ ai_thinking_mode: mode })
      set({ aiThinkingMode: mode })
    } catch (err) {
      useUIStore.getState().pushErrorPopup({
        message: err instanceof Error ? err.message : '更新设置失败',
        source: '保存设置',
      })
    } finally {
      set({ saving: false })
    }
  },

  updateSetting: async (key, value) => {
    set({ saving: true })
    try {
      const res = await updateSettings({ [key]: value })
      set({
        maxTokens: res.llm_max_tokens,
        aiThinkingMode: res.ai_thinking_mode,
        llmTimeout: res.llm_timeout,
        llmMaxRetries: res.llm_max_retries,
        llmTemperature: res.llm_temperature,
      })
    } catch (err) {
      useUIStore.getState().pushErrorPopup({
        message: err instanceof Error ? err.message : '更新设置失败',
        source: '保存设置',
      })
    } finally {
      set({ saving: false })
    }
  },
}))
