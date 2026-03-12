// ============================================================
// 聊天气泡组件 (T6.4)
//
// 显示在玩家头顶的聊天气泡，带入场动画和自动渐隐。
// 新消息到来时替换旧气泡，短暂显示后自动消失。
// ============================================================

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { ChatMessage } from '../../types/game'

/** 气泡显示时长（毫秒） */
const BUBBLE_DURATION = 4000

/** 气泡最大字符数（超出截断） */
const MAX_CHARS = 50

interface ChatBubbleProps {
  /** 最新的聊天消息（用于显示气泡） */
  message: ChatMessage | null
  /** 气泡位置：玩家在牌桌上半部还是下半部（影响气泡朝向） */
  position?: 'above' | 'below'
}

/**
 * 玩家头顶聊天气泡
 * 短暂显示后自动渐隐，新消息会重置计时器
 */
export default function ChatBubble({
  message,
  position = 'above',
}: ChatBubbleProps) {
  const [visible, setVisible] = useState(false)
  const [currentMsg, setCurrentMsg] = useState<ChatMessage | null>(null)

  // 当新消息到来时，显示气泡并启动定时器
  useEffect(() => {
    if (!message) return

    setCurrentMsg(message)
    setVisible(true)

    const timer = setTimeout(() => {
      setVisible(false)
    }, BUBBLE_DURATION)

    return () => clearTimeout(timer)
  }, [message])

  const isAbove = position === 'above'

  // 截断过长消息
  const displayText =
    currentMsg && currentMsg.content.length > MAX_CHARS
      ? currentMsg.content.slice(0, MAX_CHARS) + '...'
      : currentMsg?.content ?? ''

  return (
    <AnimatePresence>
      {visible && currentMsg && (
        <motion.div
          key={currentMsg.id}
          className={`
            absolute left-1/2 -translate-x-1/2 z-20
            pointer-events-none
            ${isAbove ? 'bottom-full mb-2' : 'top-full mt-2'}
          `}
          initial={{ opacity: 0, y: isAbove ? 8 : -8, scale: 0.85 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: isAbove ? -4 : 4, scale: 0.9 }}
          transition={{ duration: 0.25, ease: 'easeOut' }}
        >
          {/* 气泡主体 */}
          <div className="relative max-w-[180px] min-w-[40px]">
            <div
              className={`
                px-2.5 py-1.5 rounded-xl text-xs leading-relaxed
                text-white/95 shadow-lg
                ${getBubbleBg(currentMsg.message_type)}
              `}
            >
              {displayText}
            </div>

            {/* 气泡小三角 */}
            <div
              className={`
                absolute left-1/2 -translate-x-1/2
                w-0 h-0
                ${
                  isAbove
                    ? 'top-full border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-t-[5px] border-t-green-800/90'
                    : 'bottom-full border-l-[5px] border-l-transparent border-r-[5px] border-r-transparent border-b-[5px] border-b-green-800/90'
                }
              `}
            />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

/** 根据消息类型返回气泡背景色 */
function getBubbleBg(messageType: string): string {
  switch (messageType) {
    case 'action_talk':
      return 'bg-gradient-to-br from-blue-800/90 to-blue-900/90 border border-blue-600/30'
    case 'bystander_react':
      return 'bg-gradient-to-br from-purple-800/90 to-purple-900/90 border border-purple-600/30'
    case 'player_message':
      return 'bg-gradient-to-br from-green-700/90 to-green-800/90 border border-green-500/30'
    default:
      return 'bg-green-800/90 border border-green-600/30'
  }
}
