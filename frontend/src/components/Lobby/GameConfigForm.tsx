// ============================================================
// 游戏配置表单 - AI 对手数量选择 + 模型选择
// ============================================================

import { useEffect, useRef } from 'react'
import { useGameStore } from '../../stores/gameStore'

/** Provider 对应的图标/颜色 */
const PROVIDER_STYLES: Record<string, { color: string; label: string }> = {
  openrouter: { color: 'text-cyan-400', label: 'OpenRouter' },
  siliconflow: { color: 'text-emerald-400', label: 'SiliconFlow' },
  azure_openai: { color: 'text-blue-400', label: 'Azure' },
  github_copilot: { color: 'text-purple-400', label: 'Copilot' },
}

/** Icon circle colors for opponent rows */
const ICON_COLORS = [
  'from-cyan-400 to-blue-500',
  'from-violet-400 to-purple-500',
  'from-pink-400 to-rose-500',
  'from-amber-400 to-orange-500',
  'from-emerald-400 to-green-500',
]

export default function GameConfigForm() {
  const {
    playerName,
    setPlayerName,
    aiOpponents,
    addAIOpponent,
    removeAIOpponent,
    updateAIOpponent,
    availableModels,
    modelsLoading,
    fetchModels,
  } = useGameStore()

  // 加载可用模型列表（仅首次加载）
  const hasFetched = useRef(false)
  useEffect(() => {
    if (!hasFetched.current && availableModels.length === 0 && !modelsLoading) {
      hasFetched.current = true
      fetchModels()
    }
  }, [availableModels.length, modelsLoading, fetchModels])

  return (
      <div className="space-y-2">
      {/* 玩家名称 — 带明确输入框 */}
      <div className="form-row flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <span className="text-sm flex-shrink-0 font-medium" style={{ fontFamily: 'var(--font-display)', color: '#c8d8e8' }}>昵称</span>
        <input
          type="text"
          value={playerName}
          onChange={(e) => setPlayerName(e.target.value)}
          placeholder="人类一败涂地"
          maxLength={12}
          className="flex-1 px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                     text-white text-sm placeholder-[#8090a0]
                     focus:outline-none focus:border-[var(--color-primary)]/30 transition-colors"
        />
      </div>

      {/* AI 对手列表 */}
    <div className="space-y-2">
        <div className="flex items-center justify-between px-1">
          <span className="text-xs font-medium" style={{ fontFamily: 'var(--font-display)', color: '#c8d8e8' }}>
            AI 对手 ({aiOpponents.length}/5)
          </span>
          {aiOpponents.length < 5 && (
            <button
              type="button"
              onClick={addAIOpponent}
              className="text-xs transition-colors cursor-pointer font-medium"
              style={{ color: '#7dd3fc', textShadow: '0 0 6px rgba(0,212,255,0.3)' }}
            >
              + 添加对手
            </button>
          )}
        </div>

        <div className="ai-opponents-list h-[280px] overflow-y-auto space-y-2 pr-1">
        {aiOpponents.map((opponent, index) => (
          <div key={index} className="form-row space-y-3">
            {/* Header row with icon + name + remove */}
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full bg-gradient-to-br ${ICON_COLORS[index % ICON_COLORS.length]} flex items-center justify-center flex-shrink-0`}>
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <span className="text-white text-sm font-medium flex-1" style={{ fontFamily: 'var(--font-display)' }}>
                对手 {index + 1}
              </span>
              {aiOpponents.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeAIOpponent(index)}
                  className="text-xs font-medium transition-colors cursor-pointer"
                  style={{ color: '#8090a0' }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = '#f87171')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = '#8090a0')}
                >
                  移除
                </button>
              )}
            </div>

            {/* Model select + Custom name */}
            <div className="grid grid-cols-2 gap-2 pl-11">
              <select
                value={opponent.model_id}
                onChange={(e) =>
                  updateAIOpponent(index, { model_id: e.target.value })
                }
                className="w-full px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                           text-white text-xs focus:outline-none focus:border-[var(--color-primary)]/30 cursor-pointer
                           appearance-none"
              >
                {modelsLoading ? (
                  <option>加载中...</option>
                ) : availableModels.length > 0 ? (
                  availableModels.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.display_name}
                      {PROVIDER_STYLES[model.provider]
                        ? ` (${PROVIDER_STYLES[model.provider].label})`
                        : ''}
                    </option>
                  ))
                ) : (
                  <option value="" disabled>
                    请先配置模型
                  </option>
                )}
              </select>

              <input
                type="text"
                value={opponent.name}
                onChange={(e) =>
                  updateAIOpponent(index, { name: e.target.value })
                }
                placeholder="自定义名称"
                maxLength={12}
                className="w-full px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                           text-white text-xs placeholder-[#8090a0] focus:outline-none
                           focus:border-[var(--color-primary)]/30 transition-colors"
              />
            </div>
          </div>
        ))}
        </div>
      </div>
    </div>
  )
}
