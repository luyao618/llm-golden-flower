// ============================================================
// 游戏设置弹窗 — 居中弹窗形式的游戏配置
// 复用 GameConfigForm + ChipsConfig，底部右下角放返回 + 开始游戏
// ============================================================

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import GameConfigForm from './GameConfigForm'
import ChipsConfig from './ChipsConfig'
import ModelConfigPanel from './ModelConfigPanel'
import { useGameStore } from '../../stores/gameStore'

interface GameSetupModalProps {
  open: boolean
  onClose: () => void
}

export default function GameSetupModal({ open, onClose }: GameSetupModalProps) {
  const navigate = useNavigate()
  const [modelConfigOpen, setModelConfigOpen] = useState(false)
  const { status, error, createGame, aiOpponents, playerName, availableModels } = useGameStore()
  const [localError, setLocalError] = useState<string | null>(null)
  const [showModelAlert, setShowModelAlert] = useState(false)

  const isCreating = status === 'creating'

  const handleNeedModelConfig = useCallback(() => {
    setShowModelAlert(false)
    setModelConfigOpen(true)
  }, [])

  const handleStart = async () => {
    setLocalError(null)

    if (aiOpponents.length === 0) {
      setLocalError('至少需要一个 AI 对手')
      return
    }

    if (availableModels.length === 0) {
      setShowModelAlert(true)
      return
    }

    if (!playerName.trim()) {
      const { setPlayerName } = useGameStore.getState()
      setPlayerName('人类一败涂地')
    }

    try {
      const response = await createGame()
      navigate(`/game/${response.game_id}`)
    } catch (err) {
      if (err instanceof Error) {
        setLocalError(err.message)
      }
    }
  }

  const displayError = localError || error

  return (
    <>
      <AnimatePresence>
        {open && !modelConfigOpen && (
          <>
            {/* 遮罩层 */}
            <motion.div
              className="fixed inset-0 z-40"
              style={{ background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(6px)' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onClose}
            />

            {/* 弹窗 */}
            <motion.div
              className="fixed inset-0 z-40 flex items-center justify-center p-4"
              initial={{ opacity: 0, scale: 0.92, y: 16 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 16 }}
              transition={{ type: 'spring', damping: 28, stiffness: 350 }}
            >
              <div
                className="model-config-modal w-full max-w-3xl h-[75vh]"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="model-config-modal-inner relative flex flex-col h-full">

                  {/* 标题栏 */}
                  <div className="flex items-center justify-between px-6 pt-5 pb-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-full flex items-center justify-center"
                        style={{
                          background: 'rgba(0, 212, 255, 0.08)',
                          border: '1px solid rgba(0, 212, 255, 0.25)',
                          boxShadow: '0 0 16px rgba(0, 212, 255, 0.12)',
                        }}
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                             style={{ color: '#00d4ff', filter: 'drop-shadow(0 0 4px rgba(0,212,255,0.5))' }}>
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <h2
                        className="text-lg font-bold tracking-wider"
                        style={{
                          fontFamily: 'var(--font-display)',
                          color: '#e0faff',
                          textShadow: '0 0 12px rgba(0, 212, 255, 0.4)',
                        }}
                      >
                        配置游戏
                      </h2>
                    </div>

                    {/* 关闭按钮 */}
                    <button
                      onClick={onClose}
                      className="w-8 h-8 rounded-lg flex items-center justify-center transition-all cursor-pointer"
                      style={{
                        color: '#6a7a8a',
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.06)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.color = '#c0d0e0'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = '#6a7a8a'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)'
                      }}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>

                  {/* 分隔线 */}
                  <div className="mx-6 h-px model-config-divider" style={{ borderTopWidth: 1, borderTopStyle: 'solid' }} />

                  {/* 内容区域 — 整体可滚动 */}
                  <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4 min-h-0 model-list-scroll">
                    <GameConfigForm />

                    {/* 分隔线 */}
                    <div className="h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

                    <ChipsConfig />
                  </div>

                  {/* 底部操作栏 — 分隔线 + 按钮右对齐 */}
                  <div className="px-6 pb-5 pt-3">
                    {/* 分隔线 */}
                    <div className="h-px bg-gradient-to-r from-transparent via-white/15 to-transparent mb-4" />

                    {/* 错误提示 */}
                    {displayError && (
                      <div className="px-4 py-2 mb-3 rounded-xl text-sm"
                           style={{
                             background: 'rgba(239, 68, 68, 0.08)',
                             border: '1px solid rgba(239, 68, 68, 0.25)',
                             color: '#f87171',
                           }}>
                        {displayError}
                      </div>
                    )}

                    {/* 按钮组 — 右对齐 */}
                    <div className="flex items-center justify-end gap-3">
                      {/* 返回按钮 — 与开始游戏同尺寸 */}
                      <button
                        onClick={onClose}
                        className="py-2.5 rounded-[11px] text-sm font-bold tracking-wider transition-all cursor-pointer"
                        style={{
                          minWidth: 160,
                          fontFamily: 'var(--font-display)',
                          color: '#a0b0c8',
                          background: 'rgba(255, 255, 255, 0.04)',
                          border: '1px solid rgba(255, 255, 255, 0.10)',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                          e.currentTarget.style.color = '#e0f0ff'
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.18)'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)'
                          e.currentTarget.style.color = '#a0b0c8'
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.10)'
                        }}
                      >
                        返回
                      </button>

                      {/* 开始游戏按钮 — 流光效果 */}
                      <div className="neon-btn-wrapper" style={{ minWidth: 160 }}>
                        <button
                          onClick={handleStart}
                          disabled={isCreating}
                          className="relative w-full py-2.5 font-bold rounded-[11px] text-sm tracking-wider
                                     text-white
                                     transition-all cursor-pointer
                                     active:scale-[0.98]
                                     disabled:cursor-wait disabled:opacity-60"
                          style={{
                            fontFamily: 'var(--font-display)',
                            background: 'rgba(15, 15, 40, 0.40)',
                            backdropFilter: 'blur(20px) saturate(1.3)',
                            WebkitBackdropFilter: 'blur(20px) saturate(1.3)',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(15, 15, 40, 0.50)')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(15, 15, 40, 0.40)')}
                        >
                          {isCreating ? (
                            <span className="flex items-center justify-center gap-2">
                              <span className="inline-block w-4 h-4 border-2 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
                              创建中...
                            </span>
                          ) : (
                            '开始游戏'
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* 模型未配置提示弹框 */}
      <AnimatePresence>
        {showModelAlert && (
          <>
            <motion.div
              className="fixed inset-0 z-50"
              style={{ background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(4px)' }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowModelAlert(false)}
            />
            <motion.div
              className="fixed inset-0 z-50 flex items-center justify-center p-4"
              initial={{ opacity: 0, scale: 0.92, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.92, y: 10 }}
              transition={{ type: 'spring', damping: 28, stiffness: 350 }}
            >
              <div
                className="w-full max-w-sm rounded-2xl p-[1px] overflow-hidden"
                style={{
                  background: 'linear-gradient(135deg, rgba(0,212,255,0.5), rgba(139,92,246,0.4), rgba(0,212,255,0.2))',
                }}
              >
                <div
                  className="rounded-2xl p-6 space-y-5"
                  style={{
                    background: 'rgba(10, 10, 30, 0.92)',
                    backdropFilter: 'blur(24px) saturate(1.3)',
                    WebkitBackdropFilter: 'blur(24px) saturate(1.3)',
                    boxShadow: '0 0 40px rgba(0, 212, 255, 0.12), 0 0 80px rgba(139, 92, 246, 0.06)',
                  }}
                >
                  <div className="flex flex-col items-center text-center space-y-3">
                    <div
                      className="w-14 h-14 rounded-full flex items-center justify-center"
                      style={{
                        background: 'rgba(0, 212, 255, 0.08)',
                        border: '1px solid rgba(0, 212, 255, 0.25)',
                        boxShadow: '0 0 20px rgba(0, 212, 255, 0.15)',
                      }}
                    >
                      <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                           style={{ color: '#00d4ff', filter: 'drop-shadow(0 0 6px rgba(0,212,255,0.5))' }}>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <h3
                      className="text-lg font-bold tracking-wide"
                      style={{
                        fontFamily: 'var(--font-display)',
                        color: '#e0faff',
                        textShadow: '0 0 12px rgba(0, 212, 255, 0.4)',
                      }}
                    >
                      尚未配置 AI 模型
                    </h3>
                  </div>
                  <p
                    className="text-sm leading-relaxed text-center"
                    style={{ color: '#a0b8d0', fontFamily: 'var(--font-body)' }}
                  >
                    需要先配置至少一个 AI 模型的 API Key 或连接 GitHub Copilot，才能开始游戏。
                  </p>
                  <div className="flex gap-3 pt-1">
                    <button
                      onClick={() => setShowModelAlert(false)}
                      className="flex-1 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer"
                      style={{
                        fontFamily: 'var(--font-display)',
                        color: '#8090a0',
                        background: 'rgba(255, 255, 255, 0.04)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                        e.currentTarget.style.color = '#c0d0e0'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.04)'
                        e.currentTarget.style.color = '#8090a0'
                      }}
                    >
                      取消
                    </button>
                    <button
                      onClick={handleNeedModelConfig}
                      className="flex-1 py-2.5 rounded-xl text-sm font-bold transition-all cursor-pointer"
                      style={{
                        fontFamily: 'var(--font-display)',
                        color: '#ffffff',
                        background: 'linear-gradient(135deg, rgba(0,212,255,0.25), rgba(139,92,246,0.2))',
                        border: '1px solid rgba(0, 212, 255, 0.35)',
                        textShadow: '0 0 8px rgba(0,212,255,0.4)',
                        boxShadow: '0 0 16px rgba(0, 212, 255, 0.12)',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(0,212,255,0.35), rgba(139,92,246,0.3))'
                        e.currentTarget.style.boxShadow = '0 0 24px rgba(0, 212, 255, 0.2)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(0,212,255,0.25), rgba(139,92,246,0.2))'
                        e.currentTarget.style.boxShadow = '0 0 16px rgba(0, 212, 255, 0.12)'
                      }}
                    >
                      去配置
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* 模型配置面板 */}
      <ModelConfigPanel open={modelConfigOpen} onClose={() => setModelConfigOpen(false)} />
    </>
  )
}
