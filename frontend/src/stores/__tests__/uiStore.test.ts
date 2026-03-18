/**
 * uiStore 单元测试
 *
 * 覆盖：
 * - 初始状态
 * - 玩家选择 / 高亮
 * - 比牌模式
 * - AI 思考 / 经验回顾指示
 * - 发牌动画
 * - 筹码动画
 * - 赢家动画
 * - 手牌显示状态
 * - 错误弹窗队列（push / dismiss / clearAll）
 * - Copilot 错误
 * - 心路历程抽屉
 * - 面板折叠切换
 * - 比牌亮牌
 * - resetUI
 */

import { beforeEach, describe, expect, it } from 'vitest'
import { useUIStore } from '../uiStore'

function resetUI() {
  useUIStore.getState().resetUI()
}

describe('useUIStore', () => {
  beforeEach(resetUI)

  // ---- Initial state ----

  describe('initial state', () => {
    it('starts with all null/false/empty', () => {
      const s = useUIStore.getState()
      expect(s.selectedPlayerId).toBeNull()
      expect(s.activePlayerId).toBeNull()
      expect(s.isCompareMode).toBe(false)
      expect(s.thinkingPlayerId).toBeNull()
      expect(s.dealingAnimation.isDealing).toBe(false)
      expect(s.chipAnimation).toBeNull()
      expect(s.winAnimation).toBeNull()
      expect(s.showPlayerCards).toBe(false)
      expect(s.hasLookedAtCards).toBe(false)
      expect(s.errorPopups).toEqual([])
      expect(s.copilotError).toBeNull()
      expect(s.isThoughtDrawerOpen).toBe(false)
      expect(s.isGameLogExpanded).toBe(true)
      expect(s.isChatPanelExpanded).toBe(false)
      expect(s.compareRevealedCards).toEqual({})
    })
  })

  // ---- Player selection / active ----

  describe('player selection', () => {
    it('setSelectedPlayer', () => {
      useUIStore.getState().setSelectedPlayer('p1')
      expect(useUIStore.getState().selectedPlayerId).toBe('p1')
    })

    it('setActivePlayer', () => {
      useUIStore.getState().setActivePlayer('p2')
      expect(useUIStore.getState().activePlayerId).toBe('p2')
    })
  })

  // ---- Compare mode ----

  describe('compare mode', () => {
    it('enterCompareMode sets flag and clears target', () => {
      useUIStore.getState().setCompareTarget('p1') // pre-set
      useUIStore.getState().enterCompareMode()
      expect(useUIStore.getState().isCompareMode).toBe(true)
      expect(useUIStore.getState().compareTargetId).toBeNull()
    })

    it('setCompareTarget sets target', () => {
      useUIStore.getState().enterCompareMode()
      useUIStore.getState().setCompareTarget('p2')
      expect(useUIStore.getState().compareTargetId).toBe('p2')
    })

    it('exitCompareMode clears both', () => {
      useUIStore.getState().enterCompareMode()
      useUIStore.getState().setCompareTarget('p2')
      useUIStore.getState().exitCompareMode()
      expect(useUIStore.getState().isCompareMode).toBe(false)
      expect(useUIStore.getState().compareTargetId).toBeNull()
    })
  })

  // ---- AI thinking / reviewing ----

  describe('AI status indicators', () => {
    it('setThinkingPlayer / setReviewingPlayer', () => {
      useUIStore.getState().setThinkingPlayer('p3')
      expect(useUIStore.getState().thinkingPlayerId).toBe('p3')

      useUIStore.getState().setReviewingPlayer('p4')
      expect(useUIStore.getState().reviewingPlayerId).toBe('p4')

      useUIStore.getState().setThinkingPlayer(null)
      expect(useUIStore.getState().thinkingPlayerId).toBeNull()
    })
  })

  // ---- Dealing animation ----

  describe('dealing animation', () => {
    it('start -> advance -> stop', () => {
      useUIStore.getState().startDealingAnimation()
      expect(useUIStore.getState().dealingAnimation.isDealing).toBe(true)
      expect(useUIStore.getState().dealingAnimation.currentCardIndex).toBe(0)

      useUIStore.getState().advanceDealingCard()
      expect(useUIStore.getState().dealingAnimation.currentCardIndex).toBe(1)

      useUIStore.getState().advanceDealingCard()
      expect(useUIStore.getState().dealingAnimation.currentCardIndex).toBe(2)

      useUIStore.getState().stopDealingAnimation()
      expect(useUIStore.getState().dealingAnimation.isDealing).toBe(false)
      expect(useUIStore.getState().dealingAnimation.currentCardIndex).toBe(0)
    })
  })

  // ---- Chip animation ----

  describe('chip animation', () => {
    it('triggerChipAnimation / clearChipAnimation', () => {
      useUIStore.getState().triggerChipAnimation('p1', 50)
      expect(useUIStore.getState().chipAnimation).toEqual({
        fromPlayerId: 'p1',
        amount: 50,
      })

      useUIStore.getState().clearChipAnimation()
      expect(useUIStore.getState().chipAnimation).toBeNull()
    })
  })

  // ---- Win animation ----

  describe('win animation', () => {
    it('startWinAnimation / clearWinAnimation', () => {
      useUIStore.getState().startWinAnimation('p2', 200)
      expect(useUIStore.getState().winAnimation).toEqual({
        winnerId: 'p2',
        amount: 200,
        isPlaying: true,
      })

      useUIStore.getState().clearWinAnimation()
      expect(useUIStore.getState().winAnimation).toBeNull()
    })
  })

  // ---- Show cards / looked at cards ----

  describe('card visibility', () => {
    it('setShowPlayerCards / setHasLookedAtCards', () => {
      useUIStore.getState().setShowPlayerCards(true)
      expect(useUIStore.getState().showPlayerCards).toBe(true)

      useUIStore.getState().setHasLookedAtCards(true)
      expect(useUIStore.getState().hasLookedAtCards).toBe(true)
    })
  })

  // ---- Error popups ----

  describe('error popups', () => {
    it('pushErrorPopup appends to queue', () => {
      useUIStore.getState().pushErrorPopup({ message: 'err1' })
      useUIStore.getState().pushErrorPopup({ message: 'err2', source: 'src' })
      const popups = useUIStore.getState().errorPopups
      expect(popups).toHaveLength(2)
      expect(popups[0].message).toBe('err1')
      expect(popups[1].source).toBe('src')
    })

    it('dismissErrorPopup removes by index', () => {
      useUIStore.getState().pushErrorPopup({ message: 'a' })
      useUIStore.getState().pushErrorPopup({ message: 'b' })
      useUIStore.getState().pushErrorPopup({ message: 'c' })

      useUIStore.getState().dismissErrorPopup(1) // remove 'b'
      const popups = useUIStore.getState().errorPopups
      expect(popups).toHaveLength(2)
      expect(popups[0].message).toBe('a')
      expect(popups[1].message).toBe('c')
    })

    it('clearAllErrorPopups empties', () => {
      useUIStore.getState().pushErrorPopup({ message: 'x' })
      useUIStore.getState().clearAllErrorPopups()
      expect(useUIStore.getState().errorPopups).toEqual([])
    })
  })

  // ---- Copilot error ----

  describe('copilot error', () => {
    it('setCopilotError sets and clears', () => {
      useUIStore.getState().setCopilotError({
        message: 'forbidden',
        errorCode: '403',
      })
      expect(useUIStore.getState().copilotError?.errorCode).toBe('403')

      useUIStore.getState().setCopilotError(null)
      expect(useUIStore.getState().copilotError).toBeNull()
    })
  })

  // ---- Thought drawer ----

  describe('thought drawer', () => {
    it('toggleThoughtDrawer with agentId opens and sets agent', () => {
      useUIStore.getState().toggleThoughtDrawer('agent-1')
      expect(useUIStore.getState().isThoughtDrawerOpen).toBe(true)
      expect(useUIStore.getState().thoughtDrawerAgentId).toBe('agent-1')
    })

    it('toggleThoughtDrawer without agentId toggles', () => {
      // closed -> open
      useUIStore.getState().toggleThoughtDrawer()
      expect(useUIStore.getState().isThoughtDrawerOpen).toBe(true)

      // open -> closed
      useUIStore.getState().toggleThoughtDrawer()
      expect(useUIStore.getState().isThoughtDrawerOpen).toBe(false)
    })
  })

  // ---- Panel toggles ----

  describe('panel toggles', () => {
    it('toggleGameLog flips', () => {
      expect(useUIStore.getState().isGameLogExpanded).toBe(true)
      useUIStore.getState().toggleGameLog()
      expect(useUIStore.getState().isGameLogExpanded).toBe(false)
    })

    it('toggleChatPanel flips', () => {
      expect(useUIStore.getState().isChatPanelExpanded).toBe(false)
      useUIStore.getState().toggleChatPanel()
      expect(useUIStore.getState().isChatPanelExpanded).toBe(true)
    })
  })

  // ---- Compare revealed cards ----

  describe('compare revealed cards', () => {
    it('setCompareRevealedCards / clearCompareRevealedCards', () => {
      const cards = {
        p1: [{ suit: 'hearts' as const, rank: 14 as const }],
        p2: [{ suit: 'spades' as const, rank: 10 as const }],
      }
      useUIStore.getState().setCompareRevealedCards(cards)
      expect(useUIStore.getState().compareRevealedCards).toEqual(cards)

      useUIStore.getState().clearCompareRevealedCards()
      expect(useUIStore.getState().compareRevealedCards).toEqual({})
    })
  })

  // ---- resetUI ----

  describe('resetUI', () => {
    it('restores to initial state', () => {
      useUIStore.getState().setActivePlayer('p1')
      useUIStore.getState().enterCompareMode()
      useUIStore.getState().pushErrorPopup({ message: 'err' })
      useUIStore.getState().startDealingAnimation()

      useUIStore.getState().resetUI()

      const s = useUIStore.getState()
      expect(s.activePlayerId).toBeNull()
      expect(s.isCompareMode).toBe(false)
      expect(s.errorPopups).toEqual([])
      expect(s.dealingAnimation.isDealing).toBe(false)
    })
  })
})
