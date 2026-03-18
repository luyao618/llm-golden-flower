// ============================================================
// 游戏设置 Store (Zustand)
// 管理全局设置：AI 调用配置、LLM max_tokens
// ============================================================

import { create } from 'zustand'
import { getSettings, updateSettings, type AiThinkingMode, type SettingsData } from '../services/api'
import { useUIStore } from './uiStore'

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
