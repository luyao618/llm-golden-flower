// ============================================================
// 游戏设置弹窗 — 左右分栏布局
// 左侧：设置分类侧边栏（模型设置 等）
// 右侧：选中分类对应的设置内容
// ============================================================

import { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useSettingsStore } from '../../stores/settingsStore'

interface GameSettingsModalProps {
  open: boolean
  onClose: () => void
}

// ---- 侧边栏分类 ----

type SettingsTab = 'model'

interface SettingsTabMeta {
  id: SettingsTab
  name: string
  icon: string
  color: string
  accentBorder: string
  accentBg: string
}

const SETTINGS_TABS: SettingsTabMeta[] = [
  {
    id: 'model',
    name: '模型设置',
    icon: '⚙',
    color: 'text-cyan-400',
    accentBorder: 'border-cyan-500/60',
    accentBg: 'bg-cyan-500/10',
  },
]

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

// ================================================================
// SidebarItem
// ================================================================

function SidebarItem({
  meta,
  isActive,
  onClick,
}: {
  meta: SettingsTabMeta
  isActive: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all cursor-pointer
        ${isActive
          ? `${meta.accentBg} ${meta.accentBorder} border shadow-[0_0_12px_rgba(0,212,255,0.08)]`
          : 'border border-transparent hover:bg-white/[0.06] hover:border-white/[0.10]'
        }`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-sm
        ${isActive ? meta.accentBg + ' ' + meta.color : 'bg-white/[0.08] text-[#a0b0c8]'}`}>
        {meta.icon}
      </div>
      <div className="flex-1 text-left min-w-0">
        <div className={`text-sm font-medium ${isActive ? meta.color : 'text-[#d0dce8]'}`}>
          {meta.name}
        </div>
      </div>
    </button>
  )
}

// ================================================================
// ModelSettingsPanel — 右侧模型设置面板
// ================================================================

function ModelSettingsPanel() {
  const { maxTokens, loading, saving, fetchSettings, setMaxTokens } = useSettingsStore()
  const [selected, setSelected] = useState<number | null>(null)
  const [initialized, setInitialized] = useState(false)

  // 初始化
  useEffect(() => {
    fetchSettings().then(() => setInitialized(true))
  }, [fetchSettings])

  // 同步 store 到本地 selected
  useEffect(() => {
    if (initialized) {
      setSelected(maxTokens)
    }
  }, [maxTokens, initialized])

  const handleSelect = useCallback(async (value: number | null) => {
    setSelected(value)
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
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm bg-cyan-500/10 text-cyan-400">
          ⚙
        </div>
        <h3 className="text-base font-semibold text-cyan-400">模型设置</h3>
      </div>

      {/* Max Tokens */}
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
            const isSelected = selected === preset.value
            return (
              <button
                key={preset.label}
                onClick={() => handleSelect(preset.value)}
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
            {saving ? '保存中...' : selected === null ? '无上限' : selected.toLocaleString()}
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
  const [activeTab, setActiveTab] = useState<SettingsTab>('model')

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
              className="model-config-modal w-full max-w-3xl h-[75vh]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="model-config-modal-inner h-full flex flex-col">
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

                {/* Body — split layout */}
                <div className="flex flex-1 min-h-0">
                  {/* Left sidebar */}
                  <div className="w-52 flex-shrink-0 border-r model-config-divider p-3 space-y-1 overflow-y-auto">
                    {SETTINGS_TABS.map((meta) => (
                      <SidebarItem
                        key={meta.id}
                        meta={meta}
                        isActive={activeTab === meta.id}
                        onClick={() => setActiveTab(meta.id)}
                      />
                    ))}
                  </div>

                  {/* Right panel */}
                  <div className="flex-1 p-5 overflow-y-auto model-list-scroll">
                    {activeTab === 'model' && <ModelSettingsPanel />}
                  </div>
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
