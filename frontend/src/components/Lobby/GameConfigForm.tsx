// ============================================================
// 游戏配置表单 - AI 对手数量选择 + 模型选择
// ============================================================

import { useEffect } from 'react'
import { useGameStore } from '../../stores/gameStore'

/** AI 性格选项 */
const PERSONALITY_OPTIONS = [
  { value: '', label: '随机分配' },
  { value: 'aggressive', label: '激进型' },
  { value: 'conservative', label: '保守型' },
  { value: 'analytical', label: '分析型' },
  { value: 'intuitive', label: '直觉型' },
  { value: 'bluffer', label: '诈唬型' },
] as const

/** Provider 对应的图标/颜色 */
const PROVIDER_STYLES: Record<string, { color: string; label: string }> = {
  openai: { color: 'text-green-400', label: 'OpenAI' },
  anthropic: { color: 'text-orange-400', label: 'Anthropic' },
  google: { color: 'text-blue-400', label: 'Google' },
  github_copilot: { color: 'text-purple-400', label: 'Copilot' },
}

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

  // 加载可用模型列表
  useEffect(() => {
    if (availableModels.length === 0 && !modelsLoading) {
      fetchModels()
    }
  }, [availableModels.length, modelsLoading, fetchModels])

  return (
    <div className="space-y-6">
      {/* 玩家名称 */}
      <div>
        <label className="block text-green-300 text-sm font-medium mb-2">
          你的名称
        </label>
        <input
          type="text"
          value={playerName}
          onChange={(e) => setPlayerName(e.target.value)}
          placeholder="输入你的名称"
          maxLength={12}
          className="w-full px-4 py-2.5 bg-green-900/60 border border-green-700/50 rounded-lg
                     text-white placeholder-green-600 focus:outline-none focus:border-amber-500/50
                     focus:ring-1 focus:ring-amber-500/30 transition-colors"
        />
      </div>

      {/* AI 对手列表 */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-green-300 text-sm font-medium">
            AI 对手 ({aiOpponents.length}/5)
          </label>
          {aiOpponents.length < 5 && (
            <button
              type="button"
              onClick={addAIOpponent}
              className="text-sm text-amber-400 hover:text-amber-300 transition-colors cursor-pointer"
            >
              + 添加对手
            </button>
          )}
        </div>

        <div className="space-y-3">
          {aiOpponents.map((opponent, index) => (
            <div
              key={index}
              className="bg-green-900/40 border border-green-700/30 rounded-lg p-4"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-white text-sm font-medium">
                  对手 {index + 1}
                </span>
                {aiOpponents.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeAIOpponent(index)}
                    className="text-red-400/70 hover:text-red-400 text-sm transition-colors cursor-pointer"
                  >
                    移除
                  </button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                {/* 模型选择 */}
                <div>
                  <label className="block text-green-400/70 text-xs mb-1">
                    AI 模型
                  </label>
                  <select
                    value={opponent.model_id}
                    onChange={(e) =>
                      updateAIOpponent(index, { model_id: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-green-950/60 border border-green-700/40 rounded-md
                               text-white text-sm focus:outline-none focus:border-amber-500/50 cursor-pointer"
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
                        请先配置模型 (点击右上角「配置模型」)
                      </option>
                    )}
                  </select>
                </div>

                {/* 性格选择 */}
                <div>
                  <label className="block text-green-400/70 text-xs mb-1">
                    性格
                  </label>
                  <select
                    value={opponent.personality}
                    onChange={(e) =>
                      updateAIOpponent(index, { personality: e.target.value })
                    }
                    className="w-full px-3 py-2 bg-green-950/60 border border-green-700/40 rounded-md
                               text-white text-sm focus:outline-none focus:border-amber-500/50 cursor-pointer"
                  >
                    {PERSONALITY_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 自定义名称 (可选) */}
              <div className="mt-3">
                <input
                  type="text"
                  value={opponent.name}
                  onChange={(e) =>
                    updateAIOpponent(index, { name: e.target.value })
                  }
                  placeholder="自定义名称 (可选，留空自动生成)"
                  maxLength={12}
                  className="w-full px-3 py-1.5 bg-green-950/40 border border-green-700/30 rounded-md
                             text-white text-sm placeholder-green-700 focus:outline-none
                             focus:border-amber-500/40 transition-colors"
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
