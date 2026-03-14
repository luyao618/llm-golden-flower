// ============================================================
// 游戏大厅页面 - 配置并创建游戏
// ============================================================

import { useNavigate } from 'react-router-dom'
import GameConfigForm from '../components/Lobby/GameConfigForm'
import ChipsConfig from '../components/Lobby/ChipsConfig'
import StartButton from '../components/Lobby/StartButton'
import lobbyBg from '../assets/lobby-bg.jpeg'

export default function LobbyPage() {
  const navigate = useNavigate()

  return (
    <div className="h-screen bg-[var(--bg-deepest)] flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* 背景图 — 与欢迎页保持一致 */}
      <div className="absolute inset-0 pointer-events-none">
        <img
          src={lobbyBg}
          alt=""
          className="w-full h-full object-cover"
          style={{ objectPosition: 'center 80%', filter: 'brightness(1.1) contrast(1.12) saturate(1.1)' }}
        />
        {/* 暗色叠加层 — 与欢迎页一致的极轻压暗 */}
        <div className="absolute inset-0"
          style={{
            background: `
              linear-gradient(to bottom, rgba(5,5,15,0.05) 0%, rgba(5,5,15,0.08) 50%, rgba(5,5,15,0.25) 100%)
            `
          }}
        />
      </div>

      {/* 左上角返回按钮 — 霓虹风格 */}
      <button
        onClick={() => navigate('/')}
        className="lobby-back-btn absolute top-6 left-6 z-20 flex items-center gap-2.5 px-5 py-2.5 rounded-2xl
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

      {/* 标题区域 */}
      <div className="relative z-10 flex flex-col items-center mb-4">
        <div className="title-deco-line w-32 mb-4 rounded-full" />
        <h1 className="text-6xl font-black neon-text-hero-ultra tracking-widest mb-2"
            style={{ fontFamily: 'var(--font-display)' }}>
          AI 炸金花
        </h1>
        <div className="flex items-center gap-4">
          <div className="w-12 h-px bg-gradient-to-r from-transparent to-[var(--text-muted)]/50" />
          <p className="text-xs tracking-[0.25em] uppercase"
             style={{ fontFamily: 'var(--font-display)', color: '#a0b8c8' }}>
            Game Setup
          </p>
          <div className="w-12 h-px bg-gradient-to-l from-transparent to-[var(--text-muted)]/50" />
        </div>
      </div>

      {/* 主面板 — 渐变边框卡片 */}
      <div className="lobby-card w-full max-w-2xl relative z-10">
        <div className="lobby-card-inner p-5 space-y-4 relative">

          <GameConfigForm />

          {/* 分隔线 */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

          <ChipsConfig />

          {/* 分隔线 */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" />

          {/* 底部操作区：只有开始游戏 */}
          <StartButton />
        </div>
      </div>
    </div>
  )
}
