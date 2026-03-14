// ============================================================
// 模型配置面板 (T8.0 + OpenRouter)
// 模态弹窗：配置 API Key (OpenAI/Anthropic/Google/OpenRouter)
// + Copilot 连接 + OpenRouter 动态模型管理
// ============================================================

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { OpenRouterAddedModel, OpenRouterModel, ProviderStatus } from '../../types/game'
import {
  addOpenRouterModel,
  fetchOpenRouterModels,
  getAddedOpenRouterModels,
  getProviders,
  removeOpenRouterModel,
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
  openrouter: {
    name: 'OpenRouter',
    color: 'text-cyan-400',
    placeholder: 'sk-or-...',
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
    <div className="border border-[var(--border-default)] rounded-lg p-3 bg-[var(--bg-deep)]/40">
      <div className="flex items-center justify-between mb-2">
        <span className={`font-medium text-sm ${meta.color}`}>{meta.name}</span>
        {provider.configured && (
          <span className="text-xs text-[var(--color-success)] bg-[var(--color-success)]/10 px-2 py-0.5 rounded-full">
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
          className="flex-1 px-3 py-1.5 bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-md
                     text-white text-sm placeholder-[var(--text-disabled)] focus:outline-none
                     focus:border-[var(--color-primary)]/40 transition-colors"
        />
        <button
          onClick={handleSave}
          disabled={saving || !keyInput.trim()}
          className="px-3 py-1.5 bg-[var(--color-primary)]/80 hover:bg-[var(--color-primary)]
                     disabled:bg-[var(--bg-elevated)] disabled:text-[var(--text-disabled)]
                     text-white text-xs rounded-md transition-colors cursor-pointer disabled:cursor-not-allowed"
        >
          {saving ? '...' : '保存'}
        </button>
        <button
          onClick={handleVerify}
          disabled={verifying || (!keyInput.trim() && !provider.configured)}
          className="px-3 py-1.5 bg-[var(--bg-elevated)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)]
                     disabled:bg-[var(--bg-elevated)] disabled:text-[var(--text-disabled)]
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
            message.type === 'success' ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'
          }`}
        >
          {message.text}
        </p>
      )}
    </div>
  )
}

/** OpenRouter 模型管理面板 */
function OpenRouterModelManager({
  onModelsChange,
}: {
  onModelsChange: () => void
}) {
  const [allModels, setAllModels] = useState<OpenRouterModel[]>([])
  const [addedModels, setAddedModels] = useState<OpenRouterAddedModel[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 加载可用模型列表和已添加模型
  const loadModels = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [available, added] = await Promise.all([
        fetchOpenRouterModels(),
        getAddedOpenRouterModels(),
      ])
      setAllModels(available.models)
      setAddedModels(added.models)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载模型列表失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadModels()
  }, [loadModels])

  // 已添加模型的 openrouter_id 集合（用于快速查找）
  const addedIds = useMemo(
    () => new Set(addedModels.map((m) => m.openrouter_id)),
    [addedModels]
  )

  // 搜索过滤
  const filteredModels = useMemo(() => {
    if (!search.trim()) return allModels.slice(0, 50) // 默认显示前 50 个
    const q = search.toLowerCase()
    return allModels
      .filter(
        (m) =>
          m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q)
      )
      .slice(0, 50)
  }, [allModels, search])

  // 添加模型
  const handleAdd = useCallback(
    async (model: OpenRouterModel) => {
      setAdding(model.id)
      try {
        await addOpenRouterModel(model.id, model.name)
        // 刷新已添加列表
        const added = await getAddedOpenRouterModels()
        setAddedModels(added.models)
        onModelsChange()
      } catch (err) {
        setError(err instanceof Error ? err.message : '添加失败')
      } finally {
        setAdding(null)
      }
    },
    [onModelsChange]
  )

  // 移除模型
  const handleRemove = useCallback(
    async (modelId: string) => {
      setRemoving(modelId)
      try {
        await removeOpenRouterModel(modelId)
        const added = await getAddedOpenRouterModels()
        setAddedModels(added.models)
        onModelsChange()
      } catch (err) {
        setError(err instanceof Error ? err.message : '移除失败')
      } finally {
        setRemoving(null)
      }
    },
    [onModelsChange]
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-cyan-400 text-sm font-medium">
          OpenRouter 模型管理
        </h3>
        <button
          onClick={loadModels}
          disabled={loading}
          className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors cursor-pointer disabled:text-green-600"
        >
          {loading ? '加载中...' : '刷新列表'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-900/20 px-3 py-1.5 rounded-md">
          {error}
        </p>
      )}

      {/* 已添加的模型 */}
      {addedModels.length > 0 && (
        <div className="border border-cyan-700/30 rounded-lg p-3 bg-cyan-950/10">
          <p className="text-xs text-cyan-400/70 mb-2">
            已添加 ({addedModels.length})
          </p>
          <div className="space-y-1.5">
            {addedModels.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between bg-green-900/30 px-3 py-1.5 rounded-md"
              >
                <div className="flex-1 min-w-0">
                  <span className="text-white text-xs truncate block">
                    {m.display_name}
                  </span>
                  <span className="text-green-600 text-[10px] truncate block">
                    {m.openrouter_id}
                  </span>
                </div>
                <button
                  onClick={() => handleRemove(m.id)}
                  disabled={removing === m.id}
                  className="ml-2 px-2 py-0.5 text-xs text-red-300 hover:text-red-200 bg-red-900/30
                             hover:bg-red-900/50 rounded transition-colors cursor-pointer
                             disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0"
                >
                  {removing === m.id ? '...' : '移除'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 搜索和添加模型 */}
      <div className="border border-cyan-700/30 rounded-lg p-3 bg-cyan-950/10">
        <p className="text-xs text-cyan-400/70 mb-2">搜索并添加模型</p>

        {/* 搜索框 */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索模型 (如 gpt, claude, gemini, llama...)"
          className="w-full px-3 py-1.5 bg-green-900/40 border border-green-700/40 rounded-md
                     text-white text-sm placeholder-green-700 focus:outline-none
                     focus:border-cyan-500/40 transition-colors mb-2"
        />

        {/* 模型列表 */}
        {loading ? (
          <div className="text-center text-green-600 text-xs py-4">
            正在从 OpenRouter 获取模型列表...
          </div>
        ) : (
          <div className="max-h-48 overflow-y-auto space-y-1">
            {filteredModels.length === 0 ? (
              <p className="text-green-600 text-xs text-center py-2">
                {search ? '未找到匹配的模型' : '暂无可用模型'}
              </p>
            ) : (
              filteredModels.map((m) => {
                const isAdded = addedIds.has(m.id)
                return (
                  <div
                    key={m.id}
                    className="flex items-center justify-between bg-green-900/20 hover:bg-green-900/30
                               px-3 py-1.5 rounded-md transition-colors group"
                  >
                    <div className="flex-1 min-w-0">
                      <span className="text-white text-xs truncate block">
                        {m.name}
                      </span>
                      <span className="text-green-600 text-[10px] truncate block">
                        {m.id}
                        {m.context_length
                          ? ` | ctx: ${(m.context_length / 1000).toFixed(0)}k`
                          : ''}
                      </span>
                    </div>
                    {isAdded ? (
                      <span className="ml-2 px-2 py-0.5 text-[10px] text-cyan-400 bg-cyan-900/30 rounded flex-shrink-0">
                        已添加
                      </span>
                    ) : (
                      <button
                        onClick={() => handleAdd(m)}
                        disabled={adding === m.id}
                        className="ml-2 px-2 py-0.5 text-xs text-cyan-300 hover:text-cyan-200
                                   bg-cyan-900/30 hover:bg-cyan-900/50 rounded transition-colors
                                   cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed
                                   flex-shrink-0"
                      >
                        {adding === m.id ? '...' : '添加'}
                      </button>
                    )}
                  </div>
                )
              })
            )}
            {filteredModels.length === 50 && (
              <p className="text-green-600 text-[10px] text-center py-1">
                {search
                  ? '显示前 50 个结果，请缩小搜索范围'
                  : '显示前 50 个模型，使用搜索查找更多'}
              </p>
            )}
          </div>
        )}
      </div>
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

  // 检查 OpenRouter 是否已配置
  const openrouterConfigured = providers.some(
    (p) => p.provider === 'openrouter' && p.configured
  )

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
      <div className="glass-panel-accent w-full max-w-lg max-h-[85vh] overflow-y-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between p-5 border-b border-[var(--border-default)]">
          <h2 className="text-lg font-semibold text-white">配置模型</h2>
          <button
            onClick={onClose}
            className="text-[var(--text-muted)] hover:text-white text-xl transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* 说明 */}
          <p className="text-[var(--text-secondary)] text-xs leading-relaxed">
            配置 API Key 或连接 GitHub Copilot 后，对应的 AI
            模型将出现在对手选择列表中。API Key
            仅存储在内存中，刷新页面或重启服务后需重新配置。
          </p>

          {/* API Key 配置 */}
          <div className="space-y-3">
            <h3 className="text-[var(--text-secondary)] text-sm font-medium">API Key 配置</h3>
            {loading ? (
              <div className="text-center text-[var(--text-muted)] text-sm py-4">
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

          {/* OpenRouter 模型管理（仅在 OpenRouter 已配置 key 时显示） */}
          {openrouterConfigured && (
            <>
              <div className="border-t border-green-700/30" />
              <OpenRouterModelManager onModelsChange={fetchModels} />
            </>
          )}

          {/* 分隔线 */}
          <div className="border-t border-[var(--border-default)]" />

          {/* Copilot 连接 */}
          <CopilotConnect onStatusChange={handleStatusChange} />
        </div>

        {/* 底部 */}
        <div className="p-5 border-t border-[var(--border-default)]">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-[var(--bg-elevated)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)]
                       text-white rounded-lg transition-colors text-sm cursor-pointer"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  )
}
