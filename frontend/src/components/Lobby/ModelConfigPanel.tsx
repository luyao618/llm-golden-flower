// ============================================================
// 模型配置面板 — 左右分栏布局
// 左侧：Provider 列表 (OpenRouter / Azure OpenAI / Copilot / SiliconFlow)
// 右侧：选中 Provider 的配置（API Key + 额外配置 + 模型管理）
// ============================================================

import { useCallback, useEffect, useMemo, useState } from 'react'
import type {
  AzureOpenAIAddedModel,
  AzureOpenAIModel,
  OpenRouterAddedModel,
  OpenRouterModel,
  ProviderExtraConfig,
  ProviderStatus,
  SiliconFlowAddedModel,
  SiliconFlowModel,
} from '../../types/game'
import {
  addAzureOpenAIModel,
  addOpenRouterModel,
  addSiliconFlowModel,
  fetchAzureOpenAIModels,
  fetchOpenRouterModels,
  fetchSiliconFlowModels,
  getAddedAzureOpenAIModels,
  getAddedOpenRouterModels,
  getAddedSiliconFlowModels,
  getCopilotStatus,
  getProviders,
  removeAzureOpenAIModel,
  removeOpenRouterModel,
  removeProviderKey,
  removeSiliconFlowModel,
  setProviderConfig,
  setProviderKey,
  verifyProviderKey,
} from '../../services/api'
import { useGameStore } from '../../stores/gameStore'
import CopilotConnect from './CopilotConnect'

interface ModelConfigPanelProps {
  open: boolean
  onClose: () => void
}

// ---- Provider 元数据 ----

type ProviderTab = 'openrouter' | 'azure_openai' | 'github_copilot' | 'siliconflow'

interface ProviderMeta {
  id: ProviderTab
  name: string
  icon: string  // emoji / short text for the sidebar icon
  color: string // tailwind text color class
  accentBorder: string // border color for active state
  accentBg: string     // bg color for active state
  placeholder: string  // API Key placeholder
  needsExtraConfig?: {
    api_host?: { label: string; placeholder: string; default?: string }
    api_version?: { label: string; placeholder: string; default?: string }
  }
}

const PROVIDERS_META: ProviderMeta[] = [
  {
    id: 'openrouter',
    name: 'OpenRouter',
    icon: 'OR',
    color: 'text-cyan-400',
    accentBorder: 'border-cyan-500/60',
    accentBg: 'bg-cyan-500/10',
    placeholder: 'sk-or-...',
  },
  {
    id: 'azure_openai',
    name: 'Azure OpenAI',
    icon: 'Az',
    color: 'text-blue-400',
    accentBorder: 'border-blue-500/60',
    accentBg: 'bg-blue-500/10',
    placeholder: 'your-azure-api-key',
    needsExtraConfig: {
      api_host: {
        label: 'API Host (Endpoint)',
        placeholder: 'https://your-resource.openai.azure.com',
      },
      api_version: {
        label: 'API Version',
        placeholder: '2024-10-21',
        default: '2024-10-21',
      },
    },
  },
  {
    id: 'github_copilot',
    name: 'GitHub Copilot',
    icon: 'GH',
    color: 'text-purple-400',
    accentBorder: 'border-purple-500/60',
    accentBg: 'bg-purple-500/10',
    placeholder: '',
  },
  {
    id: 'siliconflow',
    name: 'SiliconFlow',
    icon: 'SF',
    color: 'text-emerald-400',
    accentBorder: 'border-emerald-500/60',
    accentBg: 'bg-emerald-500/10',
    placeholder: 'sk-...',
    needsExtraConfig: {
      api_host: {
        label: 'API Host',
        placeholder: 'https://api.siliconflow.cn',
        default: 'https://api.siliconflow.cn',
      },
    },
  },
]

// ---- 通用模型类型 (统一 OpenRouter / SiliconFlow / Azure 的模型列表) ----

interface GenericModel {
  id: string
  name: string
  context_length: number | null
}

interface GenericAddedModel {
  id: string
  display_name: string
  original_id: string
}

// ================================================================
// ProviderSidebarItem — 左侧单个 Provider 项
// ================================================================

function ProviderSidebarItem({
  meta,
  isActive,
  isConfigured,
  onClick,
}: {
  meta: ProviderMeta
  isActive: boolean
  isConfigured: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all cursor-pointer
        ${isActive
          ? `${meta.accentBg} ${meta.accentBorder} border`
          : 'border border-transparent hover:bg-white/[0.04] hover:border-white/[0.08]'
        }`}
    >
      {/* Icon circle */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold
        ${isActive ? meta.accentBg + ' ' + meta.color : 'bg-white/[0.06] text-[#8090a0]'}`}>
        {meta.icon}
      </div>
      {/* Name + status */}
      <div className="flex-1 text-left min-w-0">
        <div className={`text-sm font-medium ${isActive ? meta.color : 'text-[#c8d8e8]'}`}>
          {meta.name}
        </div>
      </div>
      {/* Status dot */}
      {isConfigured && (
        <div className="w-2 h-2 rounded-full bg-[var(--color-success)] flex-shrink-0" />
      )}
    </button>
  )
}

// ================================================================
// ExtraConfigSection — 额外配置（api_host / api_version）
// ================================================================

function ExtraConfigSection({
  meta,
  currentConfig,
  onSave,
}: {
  meta: ProviderMeta
  currentConfig: ProviderExtraConfig
  onSave: (config: Partial<ProviderExtraConfig>) => Promise<void>
}) {
  const fields = meta.needsExtraConfig
  if (!fields) return null

  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // Initialize values from currentConfig
  useEffect(() => {
    const init: Record<string, string> = {}
    if (fields.api_host) init.api_host = currentConfig.api_host || fields.api_host.default || ''
    if (fields.api_version) init.api_version = currentConfig.api_version || fields.api_version.default || ''
    setValues(init)
  }, [currentConfig, fields])

  const handleSave = useCallback(async () => {
    setSaving(true)
    setMessage(null)
    try {
      const config: Partial<ProviderExtraConfig> = {}
      if (values.api_host !== undefined) config.api_host = values.api_host.trim()
      if (values.api_version !== undefined) config.api_version = values.api_version.trim()
      await onSave(config)
      setMessage({ text: '配置已保存', type: 'success' })
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : '保存失败', type: 'error' })
    } finally {
      setSaving(false)
    }
  }, [values, onSave])

  return (
    <div className="space-y-2">
      {fields.api_host && (
        <div>
          <label className="text-xs text-[#8090a0] mb-1 block">{fields.api_host.label}</label>
          <input
            type="text"
            value={values.api_host || ''}
            onChange={(e) => setValues((v) => ({ ...v, api_host: e.target.value }))}
            placeholder={fields.api_host.placeholder}
            className="w-full px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                       text-white text-sm placeholder-[#606a78] focus:outline-none
                       focus:border-[var(--color-primary)]/40 transition-colors"
          />
        </div>
      )}
      {fields.api_version && (
        <div>
          <label className="text-xs text-[#8090a0] mb-1 block">{fields.api_version.label}</label>
          <input
            type="text"
            value={values.api_version || ''}
            onChange={(e) => setValues((v) => ({ ...v, api_version: e.target.value }))}
            placeholder={fields.api_version.placeholder}
            className="w-full px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                       text-white text-sm placeholder-[#606a78] focus:outline-none
                       focus:border-[var(--color-primary)]/40 transition-colors"
          />
        </div>
      )}
      <button
        onClick={handleSave}
        disabled={saving}
        className="px-4 py-1.5 bg-white/[0.08] hover:bg-white/[0.12] border border-white/[0.10]
                   text-white text-xs rounded-lg transition-colors cursor-pointer
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? '保存中...' : '保存配置'}
      </button>
      {message && (
        <p className={`text-xs ${message.type === 'success' ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
          {message.text}
        </p>
      )}
    </div>
  )
}

// ================================================================
// APIKeySection — API Key 输入 + 保存 + 验证 + 移除
// ================================================================

function APIKeySection({
  meta,
  providerStatus,
  onUpdate,
}: {
  meta: ProviderMeta
  providerStatus: ProviderStatus | null
  onUpdate: () => void
}) {
  const [keyInput, setKeyInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  const isConfigured = providerStatus?.configured ?? false

  const handleSave = useCallback(async () => {
    if (!keyInput.trim()) return
    setSaving(true)
    setMessage(null)
    try {
      await setProviderKey(meta.id, keyInput.trim())
      setKeyInput('')
      setMessage({ text: 'API Key 已保存', type: 'success' })
      onUpdate()
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : '保存失败', type: 'error' })
    } finally {
      setSaving(false)
    }
  }, [keyInput, meta.id, onUpdate])

  const handleVerify = useCallback(async () => {
    setVerifying(true)
    setMessage(null)
    try {
      const res = await verifyProviderKey(meta.id, keyInput.trim() || undefined)
      setMessage({ text: res.message, type: res.valid ? 'success' : 'error' })
    } catch (err) {
      setMessage({ text: err instanceof Error ? err.message : '验证失败', type: 'error' })
    } finally {
      setVerifying(false)
    }
  }, [keyInput, meta.id])

  const handleRemove = useCallback(async () => {
    try {
      await removeProviderKey(meta.id)
      setKeyInput('')
      setMessage(null)
      onUpdate()
    } catch {
      // ignore
    }
  }, [meta.id, onUpdate])

  return (
    <div className="space-y-2">
      <label className="text-xs text-[#8090a0] block">API Key</label>
      <div className="flex gap-2">
        <input
          type="password"
          value={keyInput}
          onChange={(e) => setKeyInput(e.target.value)}
          placeholder={isConfigured ? `已配置 ${providerStatus?.key_preview ?? ''}` : meta.placeholder}
          className="flex-1 px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                     text-white text-sm placeholder-[#606a78] focus:outline-none
                     focus:border-[var(--color-primary)]/40 transition-colors"
        />
        <button
          onClick={handleSave}
          disabled={saving || !keyInput.trim()}
          className={`px-3 py-1.5 text-white text-xs rounded-lg transition-colors cursor-pointer
                     disabled:opacity-40 disabled:cursor-not-allowed
                     ${meta.accentBg} hover:brightness-125 border ${meta.accentBorder}`}
        >
          {saving ? '...' : '保存'}
        </button>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleVerify}
          disabled={verifying || (!keyInput.trim() && !isConfigured)}
          className="px-3 py-1.5 bg-white/[0.06] hover:bg-white/[0.10] border border-white/[0.10]
                     text-white text-xs rounded-lg transition-colors cursor-pointer
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {verifying ? '验证中...' : 'Check'}
        </button>
        {isConfigured && (
          <button
            onClick={handleRemove}
            className="px-3 py-1.5 bg-red-900/30 hover:bg-red-900/50 text-red-300
                       text-xs rounded-lg transition-colors cursor-pointer border border-red-800/30"
          >
            移除 Key
          </button>
        )}
      </div>
      {message && (
        <p className={`text-xs ${message.type === 'success' ? 'text-[var(--color-success)]' : 'text-[var(--color-danger)]'}`}>
          {message.text}
        </p>
      )}
    </div>
  )
}

// ================================================================
// ModelManager — 通用模型搜索/添加/移除组件
// ================================================================

function ModelManager({
  providerLabel,
  accentColor,
  fetchModels,
  fetchAddedModels,
  addModel,
  removeModel,
  getOriginalId,
  onModelsChange,
}: {
  providerLabel: string
  accentColor: string
  fetchModels: () => Promise<{ models: GenericModel[]; total: number }>
  fetchAddedModels: () => Promise<{ models: GenericAddedModel[] }>
  addModel: (id: string, name: string) => Promise<unknown>
  removeModel: (id: string) => Promise<unknown>
  getOriginalId: (m: GenericAddedModel) => string
  onModelsChange: () => void
}) {
  const [allModels, setAllModels] = useState<GenericModel[]>([])
  const [addedModels, setAddedModels] = useState<GenericAddedModel[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [adding, setAdding] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadModels = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [available, added] = await Promise.all([
        fetchModels(),
        fetchAddedModels(),
      ])
      setAllModels(available.models)
      setAddedModels(added.models)
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载模型列表失败')
    } finally {
      setLoading(false)
    }
  }, [fetchModels, fetchAddedModels])

  useEffect(() => {
    loadModels()
  }, [loadModels])

  const addedIds = useMemo(
    () => new Set(addedModels.map((m) => getOriginalId(m))),
    [addedModels, getOriginalId]
  )

  const filteredModels = useMemo(() => {
    if (!search.trim()) return allModels.slice(0, 50)
    const q = search.toLowerCase()
    return allModels
      .filter((m) => m.id.toLowerCase().includes(q) || m.name.toLowerCase().includes(q))
      .slice(0, 50)
  }, [allModels, search])

  const handleAdd = useCallback(
    async (model: GenericModel) => {
      setAdding(model.id)
      try {
        await addModel(model.id, model.name)
        const added = await fetchAddedModels()
        setAddedModels(added.models)
        onModelsChange()
      } catch (err) {
        setError(err instanceof Error ? err.message : '添加失败')
      } finally {
        setAdding(null)
      }
    },
    [addModel, fetchAddedModels, onModelsChange]
  )

  const handleRemove = useCallback(
    async (modelId: string) => {
      setRemoving(modelId)
      try {
        await removeModel(modelId)
        const added = await fetchAddedModels()
        setAddedModels(added.models)
        onModelsChange()
      } catch (err) {
        setError(err instanceof Error ? err.message : '移除失败')
      } finally {
        setRemoving(null)
      }
    },
    [removeModel, fetchAddedModels, onModelsChange]
  )

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className={`text-sm font-medium ${accentColor}`}>
          {providerLabel} 模型
        </h4>
        <button
          onClick={loadModels}
          disabled={loading}
          className={`text-xs ${accentColor} hover:brightness-125 transition-colors cursor-pointer disabled:opacity-50`}
        >
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-900/20 px-3 py-1.5 rounded-lg">
          {error}
        </p>
      )}

      {/* 已添加的模型 */}
      {addedModels.length > 0 && (
        <div className="border border-white/[0.08] rounded-lg p-3 bg-white/[0.02]">
          <p className="text-xs text-[#8090a0] mb-2">
            已添加 ({addedModels.length})
          </p>
          <div className="space-y-1.5">
            {addedModels.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between bg-white/[0.04] px-3 py-1.5 rounded-md"
              >
                <div className="flex-1 min-w-0">
                  <span className="text-white text-xs truncate block">{m.display_name}</span>
                  <span className="text-[#606a78] text-[10px] truncate block">{m.original_id}</span>
                </div>
                <button
                  onClick={() => handleRemove(m.id)}
                  disabled={removing === m.id}
                  className="ml-2 px-2 py-0.5 text-xs text-red-300 hover:text-red-200 bg-red-900/20
                             hover:bg-red-900/40 rounded transition-colors cursor-pointer
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
      <div className="border border-white/[0.08] rounded-lg p-3 bg-white/[0.02]">
        <p className="text-xs text-[#8090a0] mb-2">搜索并添加模型</p>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索模型名称..."
          className="w-full px-3 py-1.5 bg-white/[0.06] border border-white/[0.10] rounded-lg
                     text-white text-sm placeholder-[#606a78] focus:outline-none
                     focus:border-[var(--color-primary)]/40 transition-colors mb-2"
        />
        {loading ? (
          <div className="text-center text-[#606a78] text-xs py-4">
            正在获取模型列表...
          </div>
        ) : (
          <div className="max-h-48 overflow-y-auto space-y-1 model-list-scroll">
            {filteredModels.length === 0 ? (
              <p className="text-[#606a78] text-xs text-center py-2">
                {search ? '未找到匹配的模型' : '暂无可用模型'}
              </p>
            ) : (
              filteredModels.map((m) => {
                const isAdded = addedIds.has(m.id)
                return (
                  <div
                    key={m.id}
                    className="flex items-center justify-between bg-white/[0.03] hover:bg-white/[0.06]
                               px-3 py-1.5 rounded-md transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <span className="text-white text-xs truncate block">{m.name}</span>
                      <span className="text-[#606a78] text-[10px] truncate block">
                        {m.id}
                        {m.context_length ? ` | ctx: ${(m.context_length / 1000).toFixed(0)}k` : ''}
                      </span>
                    </div>
                    {isAdded ? (
                      <span className="ml-2 px-2 py-0.5 text-[10px] text-[#8090a0] bg-white/[0.06] rounded flex-shrink-0">
                        已添加
                      </span>
                    ) : (
                      <button
                        onClick={() => handleAdd(m)}
                        disabled={adding === m.id}
                        className={`ml-2 px-2 py-0.5 text-xs ${accentColor} hover:brightness-125
                                   bg-white/[0.06] hover:bg-white/[0.10] rounded transition-colors
                                   cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed flex-shrink-0`}
                      >
                        {adding === m.id ? '...' : '添加'}
                      </button>
                    )}
                  </div>
                )
              })
            )}
            {filteredModels.length === 50 && (
              <p className="text-[#606a78] text-[10px] text-center py-1">
                {search ? '显示前 50 个结果，请缩小搜索范围' : '显示前 50 个模型，使用搜索查找更多'}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ================================================================
// RightPanel — 右侧内容面板（根据选中 Provider 切换）
// ================================================================

function RightPanel({
  activeTab,
  providers,
  onUpdate,
}: {
  activeTab: ProviderTab
  providers: ProviderStatus[]
  onUpdate: () => void
}) {
  const fetchModels = useGameStore((s) => s.fetchModels)
  const meta = PROVIDERS_META.find((m) => m.id === activeTab)!

  // Find the provider status for the active tab (API-based providers only)
  const providerStatus = providers.find((p) => p.provider === activeTab) ?? null

  const handleModelsChange = useCallback(() => {
    fetchModels()
  }, [fetchModels])

  const handleConfigSave = useCallback(
    async (config: Partial<ProviderExtraConfig>) => {
      await setProviderConfig(activeTab, config)
      onUpdate()
    },
    [activeTab, onUpdate]
  )

  // GitHub Copilot — special handling (no API Key, uses Device Flow)
  if (activeTab === 'github_copilot') {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${meta.accentBg} ${meta.color}`}>
            {meta.icon}
          </div>
          <h3 className={`text-base font-semibold ${meta.color}`}>{meta.name}</h3>
        </div>
        <p className="text-xs text-[#8090a0] leading-relaxed">
          通过 GitHub Device Flow OAuth 连接 Copilot，无需手动输入 API Key。
          连接成功后可使用 GPT-4o、Claude Sonnet 等模型。
        </p>
        <CopilotConnect onStatusChange={onUpdate} />
      </div>
    )
  }

  // API Key based providers (OpenRouter / Azure OpenAI / SiliconFlow)
  const isConfigured = providerStatus?.configured ?? false
  const extraConfig: ProviderExtraConfig = providerStatus?.extra_config ?? {}

  // Model manager per provider
  const renderModelManager = () => {
    if (!isConfigured) return null

    if (activeTab === 'openrouter') {
      return (
        <ModelManager
          providerLabel="OpenRouter"
          accentColor="text-cyan-400"
          fetchModels={async () => {
            const res = await fetchOpenRouterModels()
            return {
              models: res.models.map((m: OpenRouterModel) => ({
                id: m.id,
                name: m.name,
                context_length: m.context_length,
              })),
              total: res.total,
            }
          }}
          fetchAddedModels={async () => {
            const res = await getAddedOpenRouterModels()
            return {
              models: res.models.map((m: OpenRouterAddedModel) => ({
                id: m.id,
                display_name: m.display_name,
                original_id: m.openrouter_id,
              })),
            }
          }}
          addModel={addOpenRouterModel}
          removeModel={removeOpenRouterModel}
          getOriginalId={(m) => m.original_id}
          onModelsChange={handleModelsChange}
        />
      )
    }

    if (activeTab === 'siliconflow') {
      return (
        <ModelManager
          providerLabel="SiliconFlow"
          accentColor="text-emerald-400"
          fetchModels={async () => {
            const res = await fetchSiliconFlowModels()
            return {
              models: res.models.map((m: SiliconFlowModel) => ({
                id: m.id,
                name: m.name,
                context_length: m.context_length,
              })),
              total: res.total,
            }
          }}
          fetchAddedModels={async () => {
            const res = await getAddedSiliconFlowModels()
            return {
              models: res.models.map((m: SiliconFlowAddedModel) => ({
                id: m.id,
                display_name: m.display_name,
                original_id: m.siliconflow_id,
              })),
            }
          }}
          addModel={addSiliconFlowModel}
          removeModel={removeSiliconFlowModel}
          getOriginalId={(m) => m.original_id}
          onModelsChange={handleModelsChange}
        />
      )
    }

    if (activeTab === 'azure_openai') {
      return (
        <ModelManager
          providerLabel="Azure OpenAI"
          accentColor="text-blue-400"
          fetchModels={async () => {
            const res = await fetchAzureOpenAIModels()
            return {
              models: res.models.map((m: AzureOpenAIModel) => ({
                id: m.id,
                name: m.name,
                context_length: m.context_length,
              })),
              total: res.total,
            }
          }}
          fetchAddedModels={async () => {
            const res = await getAddedAzureOpenAIModels()
            return {
              models: res.models.map((m: AzureOpenAIAddedModel) => ({
                id: m.id,
                display_name: m.display_name,
                original_id: m.azure_id,
              })),
            }
          }}
          addModel={addAzureOpenAIModel}
          removeModel={removeAzureOpenAIModel}
          getOriginalId={(m) => m.original_id}
          onModelsChange={handleModelsChange}
        />
      )
    }

    return null
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold ${meta.accentBg} ${meta.color}`}>
          {meta.icon}
        </div>
        <h3 className={`text-base font-semibold ${meta.color}`}>{meta.name}</h3>
        {isConfigured && (
          <span className="ml-auto text-[10px] text-[var(--color-success)] bg-[var(--color-success)]/10 px-2 py-0.5 rounded-full">
            已配置
          </span>
        )}
      </div>

      {/* Extra config (api_host, api_version) — show BEFORE api key for Azure */}
      {meta.needsExtraConfig && (
        <ExtraConfigSection meta={meta} currentConfig={extraConfig} onSave={handleConfigSave} />
      )}

      {/* API Key */}
      <APIKeySection meta={meta} providerStatus={providerStatus} onUpdate={onUpdate} />

      {/* Divider + Model Manager */}
      {isConfigured && (
        <>
          <div className="border-t border-white/[0.06]" />
          {renderModelManager()}
        </>
      )}
    </div>
  )
}

// ================================================================
// ModelConfigPanel — 主面板
// ================================================================

export default function ModelConfigPanel({ open, onClose }: ModelConfigPanelProps) {
  const [providers, setProviders] = useState<ProviderStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<ProviderTab>('openrouter')
  const fetchModels = useGameStore((s) => s.fetchModels)

  const loadProviders = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getProviders()
      setProviders(res)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (open) {
      loadProviders()
    }
  }, [open, loadProviders])

  const handleStatusChange = useCallback(() => {
    loadProviders()
    fetchModels()
  }, [loadProviders, fetchModels])

  // Check if each provider is configured
  const configuredSet = useMemo(() => {
    const s = new Set<string>()
    for (const p of providers) {
      if (p.configured) s.add(p.provider)
    }
    return s
  }, [providers])

  // Check Copilot status separately (it's not in the providers list)
  const [copilotConnected, setCopilotConnected] = useState(false)
  useEffect(() => {
    if (open) {
      getCopilotStatus()
        .then((res) => setCopilotConnected(res.connected))
        .catch(() => setCopilotConnected(false))
    }
  }, [open, providers]) // re-check when providers refresh

  if (!open) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="glass-panel-accent w-full max-w-3xl h-[75vh] flex flex-col">
        {/* Title bar */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.06] flex-shrink-0">
          <h2 className="text-lg font-semibold text-white" style={{ fontFamily: 'var(--font-display)' }}>
            配置模型
          </h2>
          <button
            onClick={onClose}
            className="text-[#8090a0] hover:text-white text-xl transition-colors cursor-pointer leading-none"
          >
            ✕
          </button>
        </div>

        {/* Body — split layout */}
        <div className="flex flex-1 min-h-0">
          {/* Left sidebar */}
          <div className="w-52 flex-shrink-0 border-r border-white/[0.06] p-3 space-y-1 overflow-y-auto">
            {PROVIDERS_META.map((meta) => (
              <ProviderSidebarItem
                key={meta.id}
                meta={meta}
                isActive={activeTab === meta.id}
                isConfigured={
                  meta.id === 'github_copilot'
                    ? copilotConnected
                    : configuredSet.has(meta.id)
                }
                onClick={() => setActiveTab(meta.id)}
              />
            ))}
          </div>

          {/* Right panel */}
          <div className="flex-1 p-5 overflow-y-auto model-list-scroll">
            {loading ? (
              <div className="flex items-center justify-center h-32 text-[#606a78] text-sm">
                加载中...
              </div>
            ) : (
              <RightPanel
                activeTab={activeTab}
                providers={providers}
                onUpdate={handleStatusChange}
              />
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/[0.06] flex-shrink-0 flex items-center justify-between">
          <p className="text-[10px] text-[#606a78] leading-relaxed">
            API Key 仅存储在内存中，刷新页面或重启服务后需重新配置。
          </p>
          <button
            onClick={onClose}
            className="px-5 py-1.5 rounded text-sm font-medium transition-all cursor-pointer border border-white/[0.12] text-[#8090a0] hover:text-white hover:border-white/[0.25] bg-white/[0.04] hover:bg-white/[0.08]"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  )
}
