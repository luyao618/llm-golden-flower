// ============================================================
// 游戏大厅页面 - 配置并创建游戏
// ============================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import GameConfigForm from '../components/Lobby/GameConfigForm'
import ChipsConfig from '../components/Lobby/ChipsConfig'
import StartButton from '../components/Lobby/StartButton'
import ModelConfigPanel from '../components/Lobby/ModelConfigPanel'

export default function LobbyPage() {
  const navigate = useNavigate()
  const [configOpen, setConfigOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-900 to-green-950 flex flex-col items-center justify-center p-8">
      <h1 className="text-5xl font-bold text-amber-400 mb-4">
        炸金花 AI
      </h1>
      <p className="text-green-300 text-lg mb-10">
        与 AI 驱动的智能对手对战，体验牌桌上的心理博弈
      </p>

      <div className="bg-green-800/60 backdrop-blur rounded-2xl p-8 w-full max-w-lg shadow-2xl border border-green-700/50 space-y-8">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">开始新游戏</h2>
          <button
            onClick={() => setConfigOpen(true)}
            className="px-3 py-1.5 bg-amber-600/80 hover:bg-amber-500 text-white text-xs rounded-md
                       transition-colors cursor-pointer border border-amber-500/30"
          >
            配置模型
          </button>
        </div>

        <GameConfigForm />

        <div className="border-t border-green-700/30" />

        <ChipsConfig />

        <div className="border-t border-green-700/30" />

        <StartButton />

        <button
          onClick={() => navigate('/demo/cards')}
          className="w-full py-3 bg-green-700 hover:bg-green-600 text-white rounded-lg transition-colors text-sm cursor-pointer"
        >
          扑克牌组件预览 (T5.4)
        </button>
      </div>

      <p className="text-green-600 text-sm mt-8">
        Golden Flower Poker AI v0.1
      </p>

      {/* 模型配置面板 */}
      <ModelConfigPanel open={configOpen} onClose={() => setConfigOpen(false)} />
    </div>
  )
}
