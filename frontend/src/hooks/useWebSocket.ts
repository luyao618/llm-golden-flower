// ============================================================
// WebSocket 连接管理 Hook (T6.1)
//
// 功能：
// - 建立/断开 WebSocket 连接
// - 自动断线重连（指数退避）
// - 消息分发（通过回调）
// - 客户端事件发送
// ============================================================

import { useCallback, useEffect, useRef, useState } from 'react'
import type { ClientEvent, GameAction, ServerEvent } from '../types/game'

// ---- 连接状态 ----

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting'

// ---- 配置 ----

interface WebSocketConfig {
  /** 游戏 ID */
  gameId: string
  /** 玩家 ID */
  playerId: string
  /** 收到服务端事件时的回调 */
  onMessage: (event: ServerEvent) => void
  /** 连接建立时的回调 */
  onConnected?: () => void
  /** 连接断开时的回调 */
  onDisconnected?: () => void
  /** 连接出错时的回调 */
  onError?: (error: string) => void
  /** 是否自动重连（默认 true） */
  autoReconnect?: boolean
  /** 最大重连次数（默认 10） */
  maxReconnectAttempts?: number
}

// ---- Hook 返回值 ----

interface UseWebSocketReturn {
  /** 当前连接状态 */
  status: ConnectionStatus
  /** 发送玩家操作 */
  sendAction: (action: GameAction, target?: string) => void
  /** 发送聊天消息 */
  sendChatMessage: (content: string) => void
  /** 发送开始新局 */
  sendStartRound: () => void
  /** 手动断开连接 */
  disconnect: () => void
  /** 手动重连 */
  reconnect: () => void
}

// ---- 常量 ----

/** 初始重连延迟（毫秒） */
const BASE_RECONNECT_DELAY = 1000
/** 最大重连延迟（毫秒） */
const MAX_RECONNECT_DELAY = 30000

/**
 * 构建 WebSocket URL
 */
function buildWsUrl(gameId: string, playerId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return `${protocol}//${host}/ws/${gameId}?player_id=${playerId}`
}

// ---- Hook ----

export function useWebSocket(config: WebSocketConfig | null): UseWebSocketReturn {
  const {
    gameId = '',
    playerId = '',
    onMessage,
    onConnected,
    onDisconnected,
    onError,
    autoReconnect = true,
    maxReconnectAttempts = 10,
  } = config ?? {}

  const [status, setStatus] = useState<ConnectionStatus>('disconnected')

  // Refs for mutable state that shouldn't trigger re-renders
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const intentionalClose = useRef(false)

  // Stable refs for callbacks (avoid re-creating the WebSocket on callback changes)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage
  const onConnectedRef = useRef(onConnected)
  onConnectedRef.current = onConnected
  const onDisconnectedRef = useRef(onDisconnected)
  onDisconnectedRef.current = onDisconnected
  const onErrorRef = useRef(onError)
  onErrorRef.current = onError

  // ---- Internal: clear reconnect timer ----
  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimer.current !== null) {
      clearTimeout(reconnectTimer.current)
      reconnectTimer.current = null
    }
  }, [])

  // ---- Internal: connect ----
  const connect = useCallback(() => {
    if (!gameId || !playerId) return

    // Close existing connection if any
    if (wsRef.current) {
      intentionalClose.current = true
      wsRef.current.close()
      wsRef.current = null
    }

    const url = buildWsUrl(gameId, playerId)
    setStatus('connecting')
    intentionalClose.current = false

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      reconnectAttempts.current = 0
      clearReconnectTimer()
      onConnectedRef.current?.()
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ServerEvent
        onMessageRef.current?.(data)
      } catch (err) {
        console.error('[WebSocket] Failed to parse message:', err)
      }
    }

    ws.onerror = (event) => {
      console.error('[WebSocket] Error:', event)
      onErrorRef.current?.('WebSocket 连接错误')
    }

    ws.onclose = (event) => {
      wsRef.current = null

      if (intentionalClose.current) {
        setStatus('disconnected')
        onDisconnectedRef.current?.()
        return
      }

      // Unexpected close — attempt reconnect
      if (autoReconnect && reconnectAttempts.current < maxReconnectAttempts) {
        const delay = Math.min(
          BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts.current),
          MAX_RECONNECT_DELAY,
        )
        console.log(
          `[WebSocket] Connection closed (code=${event.code}). Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${maxReconnectAttempts})`,
        )
        setStatus('reconnecting')
        reconnectAttempts.current += 1
        reconnectTimer.current = setTimeout(() => {
          connect()
        }, delay)
      } else {
        setStatus('disconnected')
        onDisconnectedRef.current?.()
        if (reconnectAttempts.current >= maxReconnectAttempts) {
          onErrorRef.current?.('WebSocket 重连失败，已达最大重试次数')
        }
      }
    }
  }, [gameId, playerId, autoReconnect, maxReconnectAttempts, clearReconnectTimer])

  // ---- Send helpers ----

  const sendRaw = useCallback((event: ClientEvent) => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(event))
    } else {
      console.warn('[WebSocket] Cannot send, not connected')
    }
  }, [])

  const sendAction = useCallback(
    (action: GameAction, target?: string) => {
      sendRaw({
        type: 'player_action',
        data: { action, ...(target ? { target } : {}) },
      })
    },
    [sendRaw],
  )

  const sendChatMessage = useCallback(
    (content: string) => {
      sendRaw({
        type: 'chat_message',
        data: { content },
      })
    },
    [sendRaw],
  )

  const sendStartRound = useCallback(() => {
    sendRaw({ type: 'start_round' })
  }, [sendRaw])

  // ---- Disconnect ----

  const disconnect = useCallback(() => {
    intentionalClose.current = true
    clearReconnectTimer()
    reconnectAttempts.current = 0
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setStatus('disconnected')
  }, [clearReconnectTimer])

  // ---- Reconnect ----

  const reconnect = useCallback(() => {
    reconnectAttempts.current = 0
    connect()
  }, [connect])

  // ---- Lifecycle: connect on mount, disconnect on unmount ----

  useEffect(() => {
    if (!config) return

    connect()
    return () => {
      intentionalClose.current = true
      clearReconnectTimer()
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
    // Only re-connect when gameId or playerId changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameId, playerId])

  return {
    status,
    sendAction,
    sendChatMessage,
    sendStartRound,
    disconnect,
    reconnect,
  }
}
