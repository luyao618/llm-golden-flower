// ============================================================
// 游戏设置弹窗 — 单面板布局
// 所有 LLM 相关设置集中在一个可滚动面板中
// ============================================================

import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useSettingsStore } from '../../stores/settingsStore'
import type { AiThinkingMode } from '../../services/api'

interface GameSettingsModalProps {
  open: boolean
  onClose: () => void
}

// ---- Max Token 预设 ----

interface MaxTokenPreset {
  label: string
  value: number | null  // null = 无上限
  desc: string
}

const MAX_TOKEN_PRESETS: MaxTokenPreset[] = [
  { label: '2048', value: 2048, desc: '极短响应' },
  { label: '4096', value: 4096, desc: '标准（Copilot 默认）' },
  { label: '8192', value: 8192, desc: '较长响应' },
  { label: '16384', value: 16384, desc: '长篇输出' },
  { label: '40960', value: 40960, desc: '超长（LiteLLM 默认）' },
  { label: '无上限', value: null, desc: '不限制，使用模型最大值' },
]

// ---- AI 思考模式预设 ----

interface ThinkingModePreset {
  mode: AiThinkingMode
  label: string
  desc: string
  icon: string
}

const THINKING_MODE_PRESETS: ThinkingModePreset[] = [
  { mode: 'detailed', label: '详细思考', desc: '完整思考过程，心路历程最丰富', icon: '🔍' },
  { mode: 'fast', label: '快速思考', desc: '精简思考，速度与质量平衡（默认）', icon: '⚡' },
  { mode: 'turbo', label: '极速决策', desc: '跳过思考过程，最快响应', icon: '🚀' },
]

// ================================================================
// 通用数值输入行组件
// ================================================================

function SettingNumberRow({
  label,
  desc,
  value,
  min,
  max,
  step,
  unit,
  saving,
  onChange,
}: {
  label: string
  desc: string
  value: number
  min: number
  max: number
  step: number
  unit?: string
  saving: boolean
  onChange: (v: number) => void
}) {
  return (
    <div className="p-3 rounded-lg border border-cyan-500/40 bg-cyan-500/8">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h4 className="text-sm font-medium text-[#d0dce8]">{label}</h4>
          <p className="text-[10px] text-[#8090a0] mt-0.5">{desc}</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={value}
            onChange={(e) => {
              const v = Number(e.target.value)
              if (!isNaN(v)) onChange(Math.max(min, Math.min(max, v)))
            }}
            min={min}
            max={max}
            step={step}
            disabled={saving}
            className="w-24 px-3 py-1.5 bg-white/[0.06] border border-white/[0.12] rounded-lg
                       text-cyan-300 text-sm font-mono text-right
                       focus:outline-none focus:border-white/[0.25] transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          />
          {unit && <span className="text-[10px] text-[#8090a0] w-6">{unit}</span>}
        </div>
      </div>
      {/* slider */}
      <input
        type="range"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={saving}
        className="w-full h-1 rounded-full appearance-none cursor-pointer
                   bg-white/[0.08] accent-current disabled:cursor-not-allowed"
        style={{ accentColor: '#22d3ee' }}
      />
    </div>
  )
}

// ================================================================
// SettingsPanel — 统一设置面板
// ================================================================

function SettingsPanel() {
  const {
    maxTokens, aiThinkingMode, llmTimeout, llmMaxRetries, llmTemperature,
    loading, saving, fetchSettings, setMaxTokens, setAiThinkingMode, updateSetting,
  } = useSettingsStore()
  const [selectedTokens, setSelectedTokens] = useState<number | null>(null)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    fetchSettings().then(() => setInitialized(true))
  }, [fetchSettings])

  // 同步 store 到本地 selectedTokens
  useEffect(() => {
    if (initialized) {
      setSelectedTokens(maxTokens)
    }
  }, [maxTokens, initialized])

  const handleSelectTokens = useCallback(async (value: number | null) => {
    setSelectedTokens(value)
    await setMaxTokens(value)
  }, [setMaxTokens])

  if (loading && !initialized) {
    return (
      <div className="flex items-center justify-center h-32 text-[#8090a0] text-sm">
        加载中...
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm bg-cyan-500/10 text-cyan-400">
            ⚙
          </div>
          <h3 className="text-base font-semibold text-cyan-400">模型设置</h3>
        </div>
        <p className="text-xs text-[#8090a0] leading-relaxed ml-9">
          调整 LLM 调用参数。修改立即生效，影响所有 AI 玩家。
        </p>
      </div>

      {/* ---- AI 思考模式 ---- */}
      <div className="space-y-3">
        <div>
          <h4 className="text-sm font-medium text-[#d0dce8] mb-1">AI 思考模式</h4>
          <p className="text-xs text-[#8090a0] leading-relaxed">
            控制 AI 决策时的思考深度。详细模式产出丰富的心路历程，极速模式跳过思考以降低延迟。
          </p>
        </div>

        {/* 三选一 pill 按钮 */}
        <div className="grid grid-cols-3 gap-2">
          {THINKING_MODE_PRESETS.map((preset) => {
            const isSelected = aiThinkingMode === preset.mode
            return (
              <button
                key={preset.mode}
                onClick={() => setAiThinkingMode(preset.mode)}
                disabled={saving}
                className={`group relative px-3 py-3 rounded-lg border transition-all cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${isSelected
                    ? 'border-cyan-500/60 bg-cyan-500/12 shadow-[0_0_16px_rgba(0,212,255,0.10)]'
                    : 'border-white/[0.10] bg-white/[0.03] hover:border-white/[0.20] hover:bg-white/[0.06]'
                  }`}
              >
                <div className={`text-sm font-bold mb-0.5 ${isSelected ? 'text-cyan-300' : 'text-[#d0dce8]'}`}>
                  <span className="mr-1">{preset.icon}</span>{preset.label}
                </div>
                <div className={`text-[10px] leading-tight ${isSelected ? 'text-cyan-400/70' : 'text-[#6a7a8a]'}`}>
                  {preset.desc}
                </div>
                {/* 选中指示器 */}
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(0,212,255,0.5)]" />
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* ---- 分隔线 ---- */}
      <div className="border-t border-white/[0.08]" />

      {/* ---- 调用参数 ---- */}
      <div className="space-y-3">
        <SettingNumberRow
          label="调用超时"
          desc="单次 LLM API 请求的最大等待时间"
          value={llmTimeout}
          min={5} max={120} step={5}
          unit="秒"
          saving={saving}
          onChange={(v) => updateSetting('llm_timeout', v)}
        />
        <SettingNumberRow
          label="最大重试次数"
          desc="调用失败后的自动重试次数（0 = 不重试）"
          value={llmMaxRetries}
          min={0} max={10} step={1}
          unit="次"
          saving={saving}
          onChange={(v) => updateSetting('llm_max_retries', v)}
        />

        {/* Temperature — 特殊处理，用 0.1 步长 */}
        <div className="p-3 rounded-lg border border-cyan-500/40 bg-cyan-500/8">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h4 className="text-sm font-medium text-[#d0dce8]">生成温度</h4>
              <p className="text-[10px] text-[#8090a0] mt-0.5">
                控制 AI 回复的随机性。低温度更保守，高温度更有创意
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={llmTemperature}
                onChange={(e) => {
                  const v = Number(e.target.value)
                  if (!isNaN(v)) updateSetting('llm_temperature', Math.max(0, Math.min(2, Math.round(v * 10) / 10)))
                }}
                min={0} max={2} step={0.1}
                disabled={saving}
                className="w-24 px-3 py-1.5 bg-white/[0.06] border border-white/[0.12] rounded-lg
                           text-cyan-300 text-sm font-mono text-right
                           focus:outline-none focus:border-white/[0.25] transition-colors
                           disabled:opacity-50 disabled:cursor-not-allowed"
              />
            </div>
          </div>
          <input
            type="range"
            value={llmTemperature}
            onChange={(e) => updateSetting('llm_temperature', Math.round(Number(e.target.value) * 10) / 10)}
            min={0} max={2} step={0.1}
            disabled={saving}
            className="w-full h-1 rounded-full appearance-none cursor-pointer
                       bg-white/[0.08] disabled:cursor-not-allowed"
            style={{ accentColor: '#22d3ee' }}
          />
          <div className="flex justify-between text-[9px] text-[#6a7a8a] mt-1 px-0.5">
            <span>保守 (0)</span>
            <span>平衡 (0.7)</span>
            <span>创意 (2.0)</span>
          </div>
        </div>
      </div>

      {/* ---- 分隔线 ---- */}
      <div className="border-t border-white/[0.08]" />

      {/* ---- Max Tokens ---- */}
      <div className="space-y-3">
        <div>
          <h4 className="text-sm font-medium text-[#d0dce8] mb-1">Max Tokens</h4>
          <p className="text-xs text-[#8090a0] leading-relaxed">
            控制 LLM 单次回复的最大 token 数量。较大的值允许更详细的 AI 思考和叙事，但可能增加延迟和费用。
          </p>
        </div>

        {/* 预设选项 — pill 按钮 */}
        <div className="grid grid-cols-3 gap-2">
          {MAX_TOKEN_PRESETS.map((preset) => {
            const isSelected = selectedTokens === preset.value
            return (
              <button
                key={preset.label}
                onClick={() => handleSelectTokens(preset.value)}
                disabled={saving}
                className={`group relative px-3 py-3 rounded-lg border transition-all cursor-pointer
                  disabled:opacity-50 disabled:cursor-not-allowed
                  ${isSelected
                    ? 'border-cyan-500/60 bg-cyan-500/12 shadow-[0_0_16px_rgba(0,212,255,0.10)]'
                    : 'border-white/[0.10] bg-white/[0.03] hover:border-white/[0.20] hover:bg-white/[0.06]'
                  }`}
              >
                <div className={`text-sm font-bold mb-0.5 ${isSelected ? 'text-cyan-300' : 'text-[#d0dce8]'}`}>
                  {preset.label}
                </div>
                <div className={`text-[10px] leading-tight ${isSelected ? 'text-cyan-400/70' : 'text-[#6a7a8a]'}`}>
                  {preset.desc}
                </div>
                {/* 选中指示器 */}
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(0,212,255,0.5)]" />
                )}
              </button>
            )
          })}
        </div>

        {/* 当前值显示 */}
        <div className="model-config-section p-3 flex items-center justify-between">
          <span className="text-xs text-[#a0b0c8]">当前值</span>
          <span className="text-sm font-mono text-cyan-300">
            {saving ? '保存中...' : selectedTokens === null ? '无上限' : selectedTokens.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  )
}

// ================================================================
// GameSettingsModal — 主弹窗
// ================================================================

export default function GameSettingsModal({ open, onClose }: GameSettingsModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          {/* 遮罩层 */}
          <motion.div
            className="fixed inset-0 z-50"
            style={{ background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(6px)' }}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />

          {/* 弹窗 */}
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            initial={{ opacity: 0, scale: 0.92, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 16 }}
            transition={{ type: 'spring', damping: 28, stiffness: 350 }}
          >
            <div
              className="model-config-modal w-full max-w-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="model-config-modal-inner flex flex-col max-h-[80vh]">
                {/* Title bar */}
                <div className="flex items-center justify-between px-5 py-4 border-b model-config-divider flex-shrink-0">
                  <h2 className="text-lg font-semibold text-white" style={{ fontFamily: 'var(--font-display)' }}>
                    游戏设置
                  </h2>
                  <button
                    onClick={onClose}
                    className="text-[#a0b0c8] hover:text-white text-xl transition-colors cursor-pointer leading-none"
                  >
                    ✕
                  </button>
                </div>

                {/* Body — single scrollable panel */}
                <div className="flex-1 p-5 overflow-y-auto model-list-scroll">
                  <SettingsPanel />
                </div>

                {/* Footer */}
                <div className="px-5 py-3 border-t model-config-divider flex-shrink-0 flex items-center justify-between">
                  <p className="text-[10px] text-[#8090a0] leading-relaxed">
                    设置仅存储在内存中，刷新页面或重启服务后恢复默认。
                  </p>
                  <button
                    onClick={onClose}
                    className="px-5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer
                               border border-[rgba(0,212,255,0.3)] text-[#c0d8f0] hover:text-white
                               hover:border-[rgba(0,212,255,0.5)] bg-[rgba(0,212,255,0.06)]
                               hover:bg-[rgba(0,212,255,0.12)] hover:shadow-[0_0_15px_rgba(0,212,255,0.15)]"
                  >
                    完成
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
