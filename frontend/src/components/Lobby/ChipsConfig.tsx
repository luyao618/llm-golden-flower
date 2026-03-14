// ============================================================
// 筹码配置组件 - 初始筹码、底注、单局上限、最大轮数
// ============================================================

import { useState } from 'react'
import { useGameStore } from '../../stores/gameStore'

/** 预设配置 */
const PRESETS = [
  { label: '休闲局', initial_chips: 500, ante: 5, max_bet: 100, max_turns: 8 },
  { label: '标准局', initial_chips: 1000, ante: 10, max_bet: 200, max_turns: 10 },
  { label: '豪赌局', initial_chips: 5000, ante: 50, max_bet: 1000, max_turns: 15 },
] as const

export default function ChipsConfig() {
  const { gameConfig, setGameConfig } = useGameStore()
  const [showAdvanced, setShowAdvanced] = useState(false)

  const applyPreset = (preset: (typeof PRESETS)[number]) => {
    setGameConfig({
      initial_chips: preset.initial_chips,
      ante: preset.ante,
      max_bet: preset.max_bet,
      max_turns: preset.max_turns,
    })
  }

  return (
    <div className="space-y-2">
      {/* Chips label row with icon */}
      <div className="flex items-center gap-3 px-1">
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-yellow-600 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <span className="text-sm font-medium" style={{ color: '#c8d8e8' }}>筹码配置</span>
      </div>

      {/* 预设选择 — pill buttons */}
      <div className="flex gap-2">
        {PRESETS.map((preset) => {
          const isActive =
            gameConfig.initial_chips === preset.initial_chips &&
            gameConfig.ante === preset.ante
          return (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset)}
              className={`flex-1 py-2 px-3 rounded-xl text-xs font-medium transition-all cursor-pointer border
                ${
                  isActive
                    ? 'bg-[var(--color-primary)]/10 border-[var(--color-primary)]/40 text-[var(--color-primary)] shadow-[0_0_12px_rgba(0,212,255,0.1)]'
                    : 'bg-white/[0.04] border-white/[0.10] text-[#c0c8d8] hover:border-white/[0.18] hover:text-[var(--text-primary)]'
                }`}
            >
              <div>{preset.label}</div>
              <div className="text-[10px] mt-0.5 opacity-80">
                {preset.initial_chips} / {preset.ante}
              </div>
            </button>
          )
        })}
      </div>

      {/* 高级配置展开 */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-xs hover:text-[var(--text-primary)] transition-colors cursor-pointer flex items-center gap-1 px-1 font-medium"
        style={{ color: '#9aa8b8' }}
      >
        {showAdvanced ? '收起高级配置' : '高级配置'}
        <span className="text-[10px]">{showAdvanced ? '▲' : '▼'}</span>
      </button>

      {showAdvanced && (
        <div className="grid grid-cols-2 gap-3 form-row">
          {[
            { label: '初始筹码', key: 'initial_chips' as const, min: 100, max: 100000, step: 100, fallback: 1000 },
            { label: '底注', key: 'ante' as const, min: 1, max: 1000, step: 5, fallback: 10 },
            { label: '单局下注上限', key: 'max_bet' as const, min: 10, max: 10000, step: 50, fallback: 200 },
            { label: '最大轮数', key: 'max_turns' as const, min: 3, max: 50, step: 1, fallback: 10 },
          ].map((field) => (
            <div key={field.key}>
              <label className="block text-[10px] mb-1" style={{ color: '#9aa8b8' }}>
                {field.label}
              </label>
              <input
                type="number"
                value={gameConfig[field.key]}
                onChange={(e) =>
                  setGameConfig({
                    [field.key]: Math.max(
                      field.min,
                      Math.min(field.max, Number(e.target.value) || field.fallback)
                    ),
                  })
                }
                min={field.min}
                max={field.max}
                step={field.step}
                className="w-full px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                           text-white text-xs focus:outline-none focus:border-[var(--color-primary)]/30"
              />
            </div>
          ))}
        </div>
      )}

      {/* 当前配置概览 */}
      <div className="flex items-center gap-3 text-[10px] px-1" style={{ fontFamily: 'var(--font-mono)', color: '#a0b0c0' }}>
        <span>筹码:{gameConfig.initial_chips}</span>
        <span>底注:{gameConfig.ante}</span>
        <span>上限:{gameConfig.max_bet}</span>
        <span>轮数:{gameConfig.max_turns}</span>
      </div>
    </div>
  )
}
