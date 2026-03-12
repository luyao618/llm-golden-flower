// ============================================================
// 模型配置面板 (T8.0)
// 模态弹窗：配置 API Key (OpenAI/Anthropic/Google) + Copilot 连接
// ============================================================

import { useCallback, useEffect, useState } from 'react'
import type { ProviderStatus } from '../../types/game'
import {
  getProviders,
  removeProviderKey,
  setProviderKey,
  verifyProviderKey,
} from '../../services/api'
import { useGameStore } from '../../stores/gameStore'
import CopilotConnect from './CopilotConnect'

interface ModelConfigPanelProps {
  open: boolean
  onClose: () => void
}

/** Provider 显示信息 */
const PROVIDER_META: Record<
  string,
  { name: string; color: string; placeholder: string }
> = {
  openai: {
    name: 'OpenAI',
    color: 'text-green-400',
    placeholder: 'sk-...',
  },
  anthropic: {
    name: 'Anthropic',
    color: 'text-orange-400',
    placeholder: 'sk-ant-...',
  },
  google: {
    name: 'Google AI',
    color: 'text-blue-400',
    placeholder: 'AIza...',
  },
}

/** 单个 Provider 的 Key 输入行 */
function ProviderKeyRow({
  provider,
  onUpdate,
}: {
  provider: ProviderStatus
  onUpdate: () => void
}) {
  const [keyInput, setKeyInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [message, setMessage] = useState<{
    text: string
    type: 'success' | 'error'
  } | null>(null)

  const meta = PROVIDER_META[provider.provider] ?? {
    name: provider.name,
    color: 'text-white',
    placeholder: '',
  }

  const handleSave = useCallback(async () => {
    if (!keyInput.trim()) return
    setSaving(true)
    setMessage(null)
    try {
      await setProviderKey(provider.provider, keyInput.trim())
      setKeyInput('')
      setMessage({ text: '已保存', type: 'success' })
      onUpdate()
    } catch (err) {
      setMessage({
        text: err instanceof Error ? err.message : '保存失败',
        type: 'error',
      })
    } finally {
      setSaving(false)
    }
  }, [keyInput, provider.provider, onUpdate])

  const handleVerify = useCallback(async () => {
    setVerifying(true)
    setMessage(null)
    try {
      const res = await verifyProviderKey(
        provider.provider,
        keyInput.trim() || undefined
      )
      setMessage({
        text: res.message,
        type: res.valid ? 'success' : 'error',
      })
    } catch (err) {
      setMessage({
        text: err instanceof Error ? err.message : '验证失败',
        type: 'error',
      })
    } finally {
      setVerifying(false)
    }
  }, [keyInput, provider.provider])

  const handleRemove = useCallback(async () => {
    try {
      await removeProviderKey(provider.provider)
      setKeyInput('')
      setMessage(null)
      onUpdate()
    } catch {
      // 忽略
    }
  }, [provider.provider, onUpdate])

  return (
    <div className="border border-green-700/30 rounded-lg p-3 bg-green-950/20">
      <div className="flex items-center justify-between mb-2">
        <span className={`font-medium text-sm ${meta.color}`}>{meta.name}</span>
        {provider.configured && (
          <span className="text-xs text-green-400 bg-green-900/40 px-2 py-0.5 rounded-full">
            已配置 {provider.key_preview}
          </span>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="password"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          placeholder={
            provider.configured
              ? `已配置 ${provider.key_preview ?? ''}`
              : meta.placeholder
          }
          className="flex-1 px-3 py-1.5 bg-green-900/40 border border-green-700/40 rounded-md
                     text-white text-sm placeholder-green-700 focus:outline-none
                     focus:border-amber-500/40 transition-colors"
        />
        <button
          onClick={handleSave}
          disabled={saving || !keyInput.trim()}
          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:bg-green-800 disabled:text-green-600
                     text-white text-xs rounded-md transition-colors cursor-pointer disabled:cursor-not-allowed"
        >
          {saving ? '...' : '保存'}
        </button>
        <button
          onClick={handleVerify}
          disabled={verifying || (!keyInput.trim() && !provider.configured)}
          className="px-3 py-1.5 bg-green-700 hover:bg-green-600 disabled:bg-green-800 disabled:text-green-600
                     text-white text-xs rounded-md transition-colors cursor-pointer disabled:cursor-not-allowed"
        >
          {verifying ? '...' : '验证'}
        </button>
        {provider.configured && (
          <button
            onClick={handleRemove}
            className="px-3 py-1.5 bg-red-900/40 hover:bg-red-900/60 text-red-300
                       text-xs rounded-md transition-colors cursor-pointer border border-red-800/40"
          >
            移除
          </button>
        )}
      </div>

      {message && (
        <p
          className={`text-xs mt-1.5 ${
            message.type === 'success' ? 'text-green-400' : 'text-red-400'
          }`}
        >
          {message.text}
        </p>
      )}
    </div>
  )
}

export default function ModelConfigPanel({
  open,
  onClose,
}: ModelConfigPanelProps) {
  const [providers, setProviders] = useState<ProviderStatus[]>([])
  const [loading, setLoading] = useState(true)
  const fetchModels = useGameStore((s) => s.fetchModels)

  const loadProviders = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getProviders()
      setProviders(res)
    } catch {
      // 忽略
    } finally {
      setLoading(false)
    }
  }, [])

  // 当面板打开时加载 Provider 状态
  useEffect(() => {
    if (open) {
      loadProviders()
    }
  }, [open, loadProviders])

  // Provider 或 Copilot 状态变更后，刷新 provider 列表 + 模型列表
  const handleStatusChange = useCallback(() => {
    loadProviders()
    fetchModels()
  }, [loadProviders, fetchModels])

  if (!open) return null

  return (
    // 遮罩层
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      {/* 面板 */}
      <div className="bg-green-900/95 border border-green-700/50 rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-5 border-b border-green-700/30">
          <h2 className="text-lg font-semibold text-white">配置模型</h2>
          <button
            onClick={onClose}
            className="text-green-500 hover:text-white text-xl transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* 说明 */}
          <p className="text-green-400 text-xs leading-relaxed">
            配置 API Key 或连接 GitHub Copilot 后，对应的 AI
            模型将出现在对手选择列表中。API Key
            仅存储在内存中，刷新页面或重启服务后需重新配置。
          </p>

          {/* API Key 配置 */}
          <div className="space-y-3">
            <h3 className="text-green-300 text-sm font-medium">API Key 配置</h3>
            {loading ? (
              <div className="text-center text-green-600 text-sm py-4">
                加载中...
              </div>
            ) : (
              providers.map((p) => (
                <ProviderKeyRow
                  key={p.provider}
                  provider={p}
                  onUpdate={handleStatusChange}
                />
              ))
            )}
          </div>

          {/* 分隔线 */}
          <div className="border-t border-green-700/30" />

          {/* Copilot 连接 */}
          <CopilotConnect onStatusChange={handleStatusChange} />
        </div>

        {/* 底部 */}
        <div className="p-5 border-t border-green-700/30">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-green-700 hover:bg-green-600 text-white rounded-lg
                       transition-colors text-sm cursor-pointer"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  )
}
