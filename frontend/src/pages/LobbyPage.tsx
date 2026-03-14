// ============================================================
// 游戏大厅页面 - 配置并创建游戏
// ============================================================

import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import GameConfigForm from '../components/Lobby/GameConfigForm'
import ChipsConfig from '../components/Lobby/ChipsConfig'
import StartButton from '../components/Lobby/StartButton'
import ModelConfigPanel from '../components/Lobby/ModelConfigPanel'
import lobbyBg from '../assets/lobby-bg.jpeg'

export default function LobbyPage() {
  const navigate = useNavigate()
  const [modelConfigOpen, setModelConfigOpen] = useState(false)

  const handleNeedModelConfig = useCallback(() => {
    setModelConfigOpen(true)
  }, [])

  return (
    <div className="h-screen bg-[var(--bg-deepest)] flex flex-col items-center p-4 relative overflow-hidden">
      {/* 背景图 — 与欢迎页保持一致 */}
      <div className="absolute inset-0 pointer-events-none">
        <img
          src={lobbyBg}
          alt=""
          className="w-full h-full object-cover"
          style={{ objectPosition: 'center 80%', filter: 'brightness(1.0) contrast(1.12) saturate(1.1)' }}
        />
        {/* 暗色叠加层 — 与欢迎页一致的极轻压暗 */}
        <div className="absolute inset-0"
          style={{
            background: `
              linear-gradient(to bottom, rgba(5,5,15,0.06) 0%, rgba(5,5,15,0.10) 50%, rgba(5,5,15,0.25) 100%)
            `
          }}
        />
      </div>

      {/* 标题区域 — 与欢迎页完全一致的位置（mt-10 固定） */}
      <div className="relative z-10 flex flex-col items-center mt-10 mb-0">
        <h1 className="text-7xl font-black neon-sign-steady tracking-widest mb-3"
            style={{ fontFamily: 'var(--font-display)' }}>
          AI 炸金花
        </h1>
        <p className="text-[var(--text-secondary)] text-base tracking-[0.3em] uppercase mb-4"
           style={{ fontFamily: 'var(--font-display)' }}>
          Golden Flower Poker AI
        </p>
        <div className="title-deco-line w-64 rounded-full" />
      </div>

      {/* 弹性间距 — 把卡片推到标题下方适当位置 */}
      <div className="h-0" />

      {/* 主面板 — 渐变边框卡片 */}
      <div className="w-full max-w-2xl relative z-10 mb-auto">
        {/* 返回按钮 — 主面板卡片左上方 */}
        <button
          onClick={() => navigate('/')}
          className="lobby-back-btn flex items-center gap-2.5 px-5 py-2.5 rounded-2xl mb-3
                     transition-all cursor-pointer group"
        >
          <svg className="w-5 h-5 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"
               style={{ color: '#00d4ff', filter: 'drop-shadow(0 0 4px rgba(0,212,255,0.6))' }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M15 19l-7-7 7-7" />
          </svg>
          <span className="text-sm font-semibold tracking-wider"
                style={{
                  fontFamily: 'var(--font-display)',
                  color: '#d5fbff',
                  textShadow: '0 0 8px rgba(0,212,255,0.5), 0 0 20px rgba(0,212,255,0.25)',
                }}>
            返回
          </span>
        </button>

        <div className="lobby-card">
        <div className="lobby-card-inner p-5 space-y-4 relative">

          <GameConfigForm />

          {/* 分隔线 */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

          <ChipsConfig />

          {/* 分隔线 */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

          {/* 底部操作区：只有开始游戏 */}
          <StartButton onNeedModelConfig={handleNeedModelConfig} />
        </div>
        </div>
      </div>

      {/* 模型配置面板 — 由 StartButton 触发打开 */}
      <ModelConfigPanel open={modelConfigOpen} onClose={() => setModelConfigOpen(false)} />
    </div>
  )
}
