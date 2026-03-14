// ============================================================
// 开始游戏按钮 - 调用 create API 并跳转到牌桌
// ============================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGameStore } from '../../stores/gameStore'

export default function StartButton() {
  const navigate = useNavigate()
  const { status, error, createGame, aiOpponents, playerName } = useGameStore()
  const [localError, setLocalError] = useState<string | null>(null)

  const isCreating = status === 'creating'

  const handleStart = async () => {
    setLocalError(null)

    // 基础验证
    if (aiOpponents.length === 0) {
      setLocalError('至少需要一个 AI 对手')
      return
    }

    // 如果没有输入名称，使用默认昵称
    if (!playerName.trim()) {
      // 临时设置默认名称用于创建游戏
      const { setPlayerName } = useGameStore.getState()
      setPlayerName('人类一败涂地')
    }

    try {
      const response = await createGame()
      // 创建成功，跳转到牌桌页面
      navigate(`/game/${response.game_id}`)
    } catch (err) {
      // createGame 内部已经设置了 store error
      // 这里设置 localError 作为额外提示
      if (err instanceof Error) {
        setLocalError(err.message)
      }
    }
  }

  const displayError = localError || error

  return (
    <div className="space-y-1">
      {displayError && (
        <div className="px-4 py-2 bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/30 rounded-xl text-[var(--color-danger)] text-sm">
          {displayError}
        </div>
      )}

      {/* Neon animated border wrapper */}
      <div className="neon-btn-wrapper">
        <button
          onClick={handleStart}
          disabled={isCreating}
          className="relative w-full py-3 font-bold rounded-[11px] text-base tracking-wider
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
          onMouseEnter={e => (e.currentTarget.style.background = 'rgba(15, 15, 40, 0.50)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'rgba(15, 15, 40, 0.40)')}
        >
          {isCreating ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-5 h-5 border-2 border-[var(--color-primary)]/30 border-t-[var(--color-primary)] rounded-full animate-spin" />
              创建中...
            </span>
          ) : (
            '开始游戏'
          )}
        </button>
      </div>
    </div>
  )
}
