// ============================================================
// GitHub Copilot Device Flow 连接组件 (T8.0)
// 用户点击连接 → 显示 user_code → 等待授权 → 显示已连接
// ============================================================

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  connectCopilot,
  disconnectCopilot,
  getCopilotStatus,
  pollCopilotAuth,
} from '../../services/api'

type CopilotState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | {
      phase: 'awaiting'
      userCode: string
      verificationUri: string
      expiresAt: number
    }
  | { phase: 'connected'; modelCount: number }
  | { phase: 'error'; message: string }

interface CopilotConnectProps {
  /** 当连接状态变化时触发，通知父组件刷新模型列表 */
  onStatusChange?: () => void
}

export default function CopilotConnect({ onStatusChange }: CopilotConnectProps) {
  const [state, setState] = useState<CopilotState>({ phase: 'idle' })
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 清理轮询定时器
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  // 组件挂载时检查现有连接状态
  useEffect(() => {
    let cancelled = false
    getCopilotStatus()
      .then((res) => {
        if (cancelled) return
        if (res.connected) {
          setState({ phase: 'connected', modelCount: res.models.length })
        }
      })
      .catch(() => {
        // 忽略 - 保持 idle
      })
    return () => {
      cancelled = true
      stopPolling()
    }
  }, [stopPolling])

  // 发起 Device Flow
  const handleConnect = useCallback(async () => {
    setState({ phase: 'loading' })
    try {
      const res = await connectCopilot()
      setState({
        phase: 'awaiting',
        userCode: res.user_code,
        verificationUri: res.verification_uri,
        expiresAt: Date.now() + res.expires_in * 1000,
      })

      // 开始轮询
      stopPolling()
      pollTimerRef.current = setInterval(async () => {
        try {
          const pollRes = await pollCopilotAuth()
          if (pollRes.status === 'connected') {
            stopPolling()
            setState({
              phase: 'connected',
              modelCount: pollRes.models?.length ?? 0,
            })
            onStatusChange?.()
          }
        } catch {
          // 轮询失败时停止（如 device code 过期）
          stopPolling()
          setState({
            phase: 'error',
            message: '授权超时或被拒绝，请重试',
          })
        }
      }, 5000)
    } catch (err) {
      setState({
        phase: 'error',
        message: err instanceof Error ? err.message : '连接失败',
      })
    }
  }, [onStatusChange, stopPolling])

  // 断开连接
  const handleDisconnect = useCallback(async () => {
    try {
      await disconnectCopilot()
      setState({ phase: 'idle' })
      onStatusChange?.()
    } catch {
      // 忽略断开错误
    }
  }, [onStatusChange])

  // 复制 user_code 到剪贴板
  const handleCopy = useCallback((text: string) => {
    navigator.clipboard.writeText(text).catch(() => {
      // 剪贴板 API 不可用时忽略
    })
  }, [])

  return (
    <div className="border border-purple-700/40 rounded-lg p-4 bg-purple-950/20">
      <div className="flex items-center gap-2 mb-3">
        <svg
          className="w-5 h-5 text-purple-400"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
        </svg>
        <h3 className="text-purple-300 font-medium text-sm">GitHub Copilot</h3>
        {state.phase === 'connected' && (
          <span className="ml-auto text-xs text-green-400 bg-green-900/40 px-2 py-0.5 rounded-full">
            已连接
          </span>
        )}
      </div>

      {/* idle 状态 */}
      {state.phase === 'idle' && (
        <button
          onClick={handleConnect}
          className="w-full py-2 bg-purple-700 hover:bg-purple-600 text-white rounded-md
                     text-sm transition-colors cursor-pointer"
        >
          连接 GitHub Copilot
        </button>
      )}

      {/* loading 状态 */}
      {state.phase === 'loading' && (
        <div className="text-center text-purple-400 text-sm py-2">
          正在发起授权...
        </div>
      )}

      {/* 等待用户授权 */}
      {state.phase === 'awaiting' && (
        <div className="space-y-3">
          <p className="text-purple-300 text-xs">
            1. 复制下方验证码
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-center text-2xl font-mono font-bold text-white bg-purple-900/50 py-2 rounded-md tracking-widest">
              {state.userCode}
            </code>
            <button
              onClick={() => handleCopy(state.userCode)}
              className="px-3 py-2 bg-purple-800 hover:bg-purple-700 text-purple-200 rounded-md text-xs
                         transition-colors cursor-pointer"
            >
              复制
            </button>
          </div>
          <p className="text-purple-300 text-xs">
            2. 打开{' '}
            <a
              href={state.verificationUri}
              target="_blank"
              rel="noopener noreferrer"
              className="text-purple-200 underline hover:text-white"
            >
              {state.verificationUri}
            </a>{' '}
            并输入验证码
          </p>
          <div className="flex items-center gap-2 text-purple-400 text-xs">
            <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
            等待授权中...
          </div>
        </div>
      )}

      {/* 已连接 */}
      {state.phase === 'connected' && (
        <div className="space-y-2">
          <p className="text-green-400 text-xs">
            {state.modelCount} 个 Copilot 模型可用
          </p>
          <button
            onClick={handleDisconnect}
            className="w-full py-1.5 bg-red-900/40 hover:bg-red-900/60 text-red-300 rounded-md
                       text-xs transition-colors cursor-pointer border border-red-800/40"
          >
            断开连接
          </button>
        </div>
      )}

      {/* 错误状态 */}
      {state.phase === 'error' && (
        <div className="space-y-2">
          <p className="text-red-400 text-xs">{state.message}</p>
          <button
            onClick={handleConnect}
            className="w-full py-2 bg-purple-700 hover:bg-purple-600 text-white rounded-md
                       text-sm transition-colors cursor-pointer"
          >
            重试
          </button>
        </div>
      )}
    </div>
  )
}
