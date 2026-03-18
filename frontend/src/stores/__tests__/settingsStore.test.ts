/**
 * settingsStore 单元测试
 *
 * 覆盖：
 * - 初始状态
 * - fetchSettings（成功 / 失败 → 错误弹窗）
 * - setMaxTokens（成功 / 失败）
 * - setAiThinkingMode（成功 / 失败）
 * - updateSetting（成功 / 失败）
 */

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useSettingsStore } from '../settingsStore'
import { useUIStore } from '../uiStore'

// ---- Mock API ----

vi.mock('../../services/api', () => ({
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
  // re-export type (no-op at runtime)
  createGame: vi.fn(),
  getAvailableModels: vi.fn(),
}))

const api = await import('../../services/api')
const mockGetSettings = api.getSettings as ReturnType<typeof vi.fn>
const mockUpdateSettings = api.updateSettings as ReturnType<typeof vi.fn>

// ---- Helpers ----

const DEFAULT_SETTINGS_RESPONSE = {
  llm_max_tokens: null,
  ai_thinking_mode: 'fast' as const,
  llm_timeout: 30,
  llm_max_retries: 3,
  llm_temperature: 0.7,
}

function resetStores() {
  useSettingsStore.setState({
    maxTokens: null,
    aiThinkingMode: 'fast',
    llmTimeout: 30,
    llmMaxRetries: 3,
    llmTemperature: 0.7,
    loading: false,
    saving: false,
  })
  useUIStore.getState().resetUI()
}

describe('useSettingsStore', () => {
  beforeEach(() => {
    resetStores()
    vi.clearAllMocks()
  })

  // ---- Initial state ----

  describe('initial state', () => {
    it('has sensible defaults', () => {
      const s = useSettingsStore.getState()
      expect(s.maxTokens).toBeNull()
      expect(s.aiThinkingMode).toBe('fast')
      expect(s.llmTimeout).toBe(30)
      expect(s.llmMaxRetries).toBe(3)
      expect(s.llmTemperature).toBe(0.7)
      expect(s.loading).toBe(false)
      expect(s.saving).toBe(false)
    })
  })

  // ---- fetchSettings ----

  describe('fetchSettings', () => {
    it('populates state from backend', async () => {
      mockGetSettings.mockResolvedValue({
        ...DEFAULT_SETTINGS_RESPONSE,
        llm_max_tokens: 4096,
        ai_thinking_mode: 'detailed',
        llm_temperature: 0.9,
      })

      await useSettingsStore.getState().fetchSettings()

      const s = useSettingsStore.getState()
      expect(s.maxTokens).toBe(4096)
      expect(s.aiThinkingMode).toBe('detailed')
      expect(s.llmTemperature).toBe(0.9)
      expect(s.loading).toBe(false)
    })

    it('pushes error popup on failure', async () => {
      mockGetSettings.mockRejectedValue(new Error('timeout'))
      await useSettingsStore.getState().fetchSettings()

      expect(useSettingsStore.getState().loading).toBe(false)
      expect(useUIStore.getState().errorPopups).toHaveLength(1)
      expect(useUIStore.getState().errorPopups[0].message).toBe('timeout')
    })
  })

  // ---- setMaxTokens ----

  describe('setMaxTokens', () => {
    it('updates state on success', async () => {
      mockUpdateSettings.mockResolvedValue(undefined)
      await useSettingsStore.getState().setMaxTokens(2048)

      expect(useSettingsStore.getState().maxTokens).toBe(2048)
      expect(useSettingsStore.getState().saving).toBe(false)
    })

    it('pushes error popup on failure', async () => {
      mockUpdateSettings.mockRejectedValue(new Error('fail'))
      await useSettingsStore.getState().setMaxTokens(2048)

      // maxTokens should NOT be updated on failure
      expect(useSettingsStore.getState().maxTokens).toBeNull()
      expect(useUIStore.getState().errorPopups).toHaveLength(1)
    })
  })

  // ---- setAiThinkingMode ----

  describe('setAiThinkingMode', () => {
    it('updates mode on success', async () => {
      mockUpdateSettings.mockResolvedValue(undefined)
      await useSettingsStore.getState().setAiThinkingMode('turbo')

      expect(useSettingsStore.getState().aiThinkingMode).toBe('turbo')
      expect(useSettingsStore.getState().saving).toBe(false)
    })

    it('does not update mode on failure', async () => {
      mockUpdateSettings.mockRejectedValue(new Error('nope'))
      await useSettingsStore.getState().setAiThinkingMode('turbo')

      expect(useSettingsStore.getState().aiThinkingMode).toBe('fast') // unchanged
    })
  })

  // ---- updateSetting ----

  describe('updateSetting', () => {
    it('applies full response to state', async () => {
      mockUpdateSettings.mockResolvedValue({
        llm_max_tokens: 1024,
        ai_thinking_mode: 'turbo',
        llm_timeout: 60,
        llm_max_retries: 5,
        llm_temperature: 0.5,
      })

      await useSettingsStore.getState().updateSetting('llm_timeout', 60)

      const s = useSettingsStore.getState()
      expect(s.llmTimeout).toBe(60)
      expect(s.maxTokens).toBe(1024) // response drives state
      expect(s.aiThinkingMode).toBe('turbo')
      expect(s.saving).toBe(false)
    })

    it('pushes error popup on failure and keeps saving=false', async () => {
      mockUpdateSettings.mockRejectedValue(new Error('oops'))
      await useSettingsStore.getState().updateSetting('llm_timeout', 60)

      expect(useSettingsStore.getState().saving).toBe(false)
      expect(useUIStore.getState().errorPopups).toHaveLength(1)
    })
  })
})
