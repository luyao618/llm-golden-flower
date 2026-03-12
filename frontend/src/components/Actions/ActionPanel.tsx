import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '../../stores/gameStore'
import { useUIStore } from '../../stores/uiStore'
import type { GameAction, Player, RoundState } from '../../types/game'
import CompareSelector from './CompareSelector'

// ---- 费用计算（前端镜像后端 rules.py 逻辑）----

function getCallCost(round: RoundState, player: Player): number {
  if (player.status === 'active_blind') return round.current_bet
  if (player.status === 'active_seen') return round.current_bet * 2
  return 0
}

function getRaiseCost(round: RoundState, player: Player): number {
  if (player.status === 'active_blind') return round.current_bet * 2
  if (player.status === 'active_seen') return round.current_bet * 4
  return 0
}

function getCompareCost(round: RoundState, player: Player): number {
  if (player.status !== 'active_seen') return 0
  return getCallCost(round, player)
}

// ---- 操作按钮配置 ----

interface ActionButtonConfig {
  action: GameAction
  label: string
  /** 额外描述文本（费用等） */
  costLabel?: string
  /** Tailwind color class set */
  colors: string
  /** 确认前二次确认？ */
  needsConfirm?: boolean
  /** 键盘快捷键提示 */
  hotkey?: string
}

// ---- 操作面板 Props ----

interface ActionPanelProps {
  /** 发送操作的回调 */
  onAction: (action: GameAction, target?: string) => void
}

/**
 * 操作面板组件
 *
 * 根据当前可用操作渲染对应按钮，显示费用信息。
 * 支持比牌模式（进入选择对手流程）。
 * 仅在玩家回合可操作。
 */
export default function ActionPanel({ onAction }: ActionPanelProps) {
  const availableActions = useGameStore((s) => s.availableActions)
  const currentRound = useGameStore((s) => s.currentRound)
  const getMyPlayer = useGameStore((s) => s.getMyPlayer)
  const players = useGameStore((s) => s.players)
  const myPlayerId = useGameStore((s) => s.myPlayerId)

  const isCompareMode = useUIStore((s) => s.isCompareMode)
  const enterCompareMode = useUIStore((s) => s.enterCompareMode)
  const exitCompareMode = useUIStore((s) => s.exitCompareMode)

  const [confirmAction, setConfirmAction] = useState<GameAction | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  const myPlayer = getMyPlayer()
  const isMyTurn = availableActions.length > 0

  // 执行操作
  const executeAction = useCallback(
    (action: GameAction, target?: string) => {
      if (isProcessing) return
      setIsProcessing(true)
      setConfirmAction(null)
      exitCompareMode()
      onAction(action, target)
      // 短暂延迟后恢复（等待服务器响应后 availableActions 会被清空）
      setTimeout(() => setIsProcessing(false), 500)
    },
    [isProcessing, onAction, exitCompareMode],
  )

  // 点击操作按钮
  const handleActionClick = useCallback(
    (action: GameAction, needsConfirm?: boolean) => {
      if (action === 'compare') {
        enterCompareMode()
        return
      }
      if (needsConfirm && confirmAction !== action) {
        setConfirmAction(action)
        return
      }
      executeAction(action)
    },
    [enterCompareMode, confirmAction, executeAction],
  )

  // 比牌目标选中
  const handleCompareTarget = useCallback(
    (targetId: string) => {
      executeAction('compare', targetId)
    },
    [executeAction],
  )

  // 取消确认
  const handleCancelConfirm = useCallback(() => {
    setConfirmAction(null)
  }, [])

  // 不是我的回合 - 显示等待提示
  if (!isMyTurn || !myPlayer || !currentRound) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="text-green-600/50 text-sm">等待对手行动...</span>
      </div>
    )
  }

  // 构建操作按钮配置
  const buttons: ActionButtonConfig[] = []

  for (const action of availableActions) {
    switch (action) {
      case 'check_cards':
        buttons.push({
          action: 'check_cards',
          label: '看牌',
          colors:
            'bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white border-blue-400/30',
          hotkey: 'Q',
        })
        break

      case 'call':
        buttons.push({
          action: 'call',
          label: '跟注',
          costLabel: `${getCallCost(currentRound, myPlayer)}`,
          colors:
            'bg-green-600 hover:bg-green-500 active:bg-green-700 text-white border-green-400/30',
          hotkey: 'W',
        })
        break

      case 'raise':
        buttons.push({
          action: 'raise',
          label: '加注',
          costLabel: `${getRaiseCost(currentRound, myPlayer)}`,
          colors:
            'bg-amber-600 hover:bg-amber-500 active:bg-amber-700 text-white border-amber-400/30',
          hotkey: 'E',
        })
        break

      case 'compare':
        buttons.push({
          action: 'compare',
          label: '比牌',
          costLabel: `${getCompareCost(currentRound, myPlayer)}`,
          colors:
            'bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-white border-purple-400/30',
          hotkey: 'R',
        })
        break

      case 'fold':
        buttons.push({
          action: 'fold',
          label: '弃牌',
          colors:
            'bg-red-700 hover:bg-red-600 active:bg-red-800 text-white border-red-400/30',
          needsConfirm: true,
          hotkey: 'F',
        })
        break
    }
  }

  // ---- 比牌选择模式 ----
  if (isCompareMode) {
    // 获取可比牌的对手列表
    const compareTargets = players.filter(
      (p) =>
        p.id !== myPlayerId &&
        p.status !== 'folded' &&
        p.status !== 'out',
    )

    return (
      <CompareSelector
        targets={compareTargets}
        cost={getCompareCost(currentRound, myPlayer)}
        onSelect={handleCompareTarget}
        onCancel={exitCompareMode}
      />
    )
  }

  // ---- 正常操作按钮 ----
  return (
    <div className="flex items-center justify-center gap-2 h-full px-4">
      {/* 游戏信息提示 */}
      <div className="flex flex-col items-end mr-2 shrink-0">
        <span className="text-green-400/60 text-[10px]">
          底池 {currentRound.pot}
        </span>
        <span className="text-green-400/60 text-[10px]">
          注额 {currentRound.current_bet} ·{' '}
          {myPlayer.status === 'active_blind' ? '暗注' : '明注'}
        </span>
      </div>

      {/* 操作按钮 */}
      <AnimatePresence mode="popLayout">
        {buttons.map((btn) => {
          const isConfirming = confirmAction === btn.action

          return (
            <motion.div
              key={btn.action}
              layout
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            >
              {isConfirming ? (
                // 确认弹出
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => executeAction(btn.action)}
                    disabled={isProcessing}
                    className="px-3 py-2 rounded-lg text-sm font-bold bg-red-600 hover:bg-red-500 text-white border border-red-400/30 transition-all cursor-pointer disabled:opacity-50"
                  >
                    确认{btn.label}
                  </button>
                  <button
                    onClick={handleCancelConfirm}
                    className="px-2 py-2 rounded-lg text-xs text-green-400/60 hover:text-green-300 transition-colors cursor-pointer"
                  >
                    取消
                  </button>
                </div>
              ) : (
                // 普通按钮
                <button
                  onClick={() => handleActionClick(btn.action, btn.needsConfirm)}
                  disabled={isProcessing}
                  className={`
                    relative px-4 py-2 rounded-lg font-bold border
                    transition-all cursor-pointer
                    disabled:opacity-50 disabled:cursor-not-allowed
                    shadow-lg hover:shadow-xl active:scale-95
                    ${btn.colors}
                  `}
                >
                  <div className="flex flex-col items-center leading-tight">
                    <span className="text-sm">{btn.label}</span>
                    {btn.costLabel && (
                      <span className="text-[10px] opacity-80">
                        {btn.costLabel} 筹码
                      </span>
                    )}
                  </div>
                  {/* 快捷键提示 */}
                  {btn.hotkey && (
                    <span className="absolute -top-1 -right-1 text-[8px] bg-black/40 text-white/50 rounded px-1">
                      {btn.hotkey}
                    </span>
                  )}
                </button>
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>

      {/* 筹码信息 */}
      <div className="flex flex-col items-start ml-2 shrink-0">
        <span className="text-amber-400/60 text-[10px]">
          你的筹码
        </span>
        <span className="text-amber-400 text-xs font-mono font-semibold">
          {myPlayer.chips.toLocaleString()}
        </span>
      </div>
    </div>
  )
}
