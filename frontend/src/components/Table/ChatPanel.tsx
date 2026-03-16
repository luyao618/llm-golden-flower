// ============================================================
// 聊天面板组件 (T6.4)
//
// 显示所有聊天消息，区分 4 种消息类型样式：
// - action_talk:     AI 操作时附带的发言（蓝色标记）
// - bystander_react: AI 旁观时的插嘴（紫色标记）
// - player_message:  人类玩家发的消息（绿色标记）
// - system_message:  系统消息（灰色，居中）
//
// 功能：头像、名字、时间戳、自动滚动到最新消息
// ============================================================

import { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ChatMessage, ChatMessageType } from '../../types/game'
import { getAvatarColor, getAvatarText } from '../../utils/theme'

// ---- 消息类型样式配置 ----

interface MessageTypeStyle {
  /** 标签文字 */
  label: string
  /** 标签 CSS 类 */
  badgeClass: string
  /** 消息文字颜色 */
  textClass: string
  /** 消息容器背景 */
  bgClass: string
}

const MESSAGE_TYPE_STYLES: Record<ChatMessageType, MessageTypeStyle> = {
  action_talk: {
    label: '发言',
    badgeClass: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    textClass: 'text-white/90',
    bgClass: 'bg-blue-500/5',
  },
  bystander_react: {
    label: '插嘴',
    badgeClass: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    textClass: 'text-white/80',
    bgClass: 'bg-purple-500/5',
  },
  player_message: {
    label: '',
    badgeClass: '',
    textClass: 'text-green-200',
    bgClass: 'bg-green-500/5',
  },
  system_message: {
    label: '系统',
    badgeClass: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
    textClass: 'text-gray-400',
    bgClass: '',
  },
}

/** 格式化时间戳为 HH:MM:SS */
function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

// ---- 组件 ----

interface ChatPanelProps {
  messages: ChatMessage[]
  className?: string
}

/**
 * 聊天面板
 * 显示聊天消息列表，支持多种消息类型区分样式，自动滚动到最新消息
 */
export default function ChatPanel({ messages, className = '' }: ChatPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 新消息到来时自动滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  return (
    <div
      ref={scrollRef}
      className={`flex flex-col gap-1 overflow-y-auto pr-1 chat-panel-scroll ${className}`}
    >
      {messages.length === 0 && (
        <div className="flex items-center justify-center h-full">
          <p className="text-green-700/40 text-xs italic">暂无消息</p>
        </div>
      )}

      <AnimatePresence initial={false}>
        {messages.map((msg) => (
          <ChatMessageItem key={msg.id} message={msg} />
        ))}
      </AnimatePresence>

      {/* 滚动锚点 */}
      <div ref={bottomRef} />
    </div>
  )
}

// ---- 单条消息组件 ----

function ChatMessageItem({ message }: { message: ChatMessage }) {
  const style = MESSAGE_TYPE_STYLES[message.message_type]

  // 系统消息使用居中样式
  if (message.message_type === 'system_message') {
    return (
      <motion.div
        className="flex justify-center px-2 py-1"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        <div className="flex items-center gap-1.5 max-w-[90%]">
          <span className={`text-[10px] px-1.5 py-0.5 rounded border ${style.badgeClass}`}>
            {style.label}
          </span>
          <span className={`text-xs ${style.textClass}`}>{message.content}</span>
          <span className="text-gray-600 text-[10px] ml-1 shrink-0">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </motion.div>
    )
  }

  // 普通消息（带头像和名字）
  return (
    <motion.div
      className={`flex gap-2 px-2 py-1.5 rounded-lg ${style.bgClass}`}
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12 }}
      transition={{ duration: 0.2 }}
    >
      {/* 头像 */}
      <div
        className={`
          w-7 h-7 rounded-full flex items-center justify-center
          text-white text-[10px] font-bold shrink-0
          bg-gradient-to-br ${getAvatarColor(message.player_id)}
        `}
      >
        {getAvatarText(message.player_name)}
      </div>

      {/* 内容区 */}
      <div className="flex-1 min-w-0">
        {/* 名字 + 类型标签 + 时间 */}
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-xs font-medium text-amber-400/90 truncate max-w-[80px]">
            {message.player_name}
          </span>
          {style.label && (
            <span className={`text-[9px] px-1 py-0 rounded border leading-tight ${style.badgeClass}`}>
              {style.label}
            </span>
          )}
          <span className="text-gray-600 text-[10px] ml-auto shrink-0">
            {formatTime(message.timestamp)}
          </span>
        </div>
        {/* 消息内容 */}
        <p className={`text-xs leading-relaxed break-words ${style.textClass}`}>
          {message.content}
        </p>
      </div>
    </motion.div>
  )
}
