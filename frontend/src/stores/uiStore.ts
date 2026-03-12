import { create } from 'zustand'

// ---- 动画状态 ----

export interface DealingAnimation {
  /** 正在发牌中 */
  isDealing: boolean
  /** 当前发到第几张 */
  currentCardIndex: number
}

export interface ChipAnimation {
  /** 筹码飞行动画（玩家 → 底池） */
  fromPlayerId: string | null
  /** 筹码数量 */
  amount: number
}

// ---- 赢家动画状态 ----

export interface WinAnimationState {
  /** 赢家玩家 ID */
  winnerId: string
  /** 赢得的筹码数量 */
  amount: number
  /** 是否正在播放 */
  isPlaying: boolean
}

// ---- UI 状态 ----

export interface UIState {
  // 当前选中/高亮的玩家
  selectedPlayerId: string | null
  // 当前行动玩家 ID（高亮边框）
  activePlayerId: string | null

  // 比牌选择模式
  isCompareMode: boolean
  compareTargetId: string | null

  // AI 状态指示
  thinkingPlayerId: string | null
  reviewingPlayerId: string | null

  // 发牌动画
  dealingAnimation: DealingAnimation

  // 筹码动画
  chipAnimation: ChipAnimation | null

  // 赢家筹码飞行动画
  winAnimation: WinAnimationState | null

  // 发牌完毕后是否显示手牌
  showPlayerCards: boolean

  // 人类玩家是否已看牌（触发翻牌动画）
  hasLookedAtCards: boolean

  // 心路历程抽屉
  isThoughtDrawerOpen: boolean
  thoughtDrawerAgentId: string | null

  // 游戏信息面板折叠
  isGameLogExpanded: boolean
  isChatPanelExpanded: boolean

  // Actions
  setSelectedPlayer: (playerId: string | null) => void
  setActivePlayer: (playerId: string | null) => void
  enterCompareMode: () => void
  exitCompareMode: () => void
  setCompareTarget: (playerId: string | null) => void
  setThinkingPlayer: (playerId: string | null) => void
  setReviewingPlayer: (playerId: string | null) => void
  startDealingAnimation: () => void
  stopDealingAnimation: () => void
  advanceDealingCard: () => void
  triggerChipAnimation: (fromPlayerId: string, amount: number) => void
  clearChipAnimation: () => void
  startWinAnimation: (winnerId: string, amount: number) => void
  clearWinAnimation: () => void
  setShowPlayerCards: (show: boolean) => void
  setHasLookedAtCards: (looked: boolean) => void
  toggleThoughtDrawer: (agentId?: string) => void
  toggleGameLog: () => void
  toggleChatPanel: () => void
  resetUI: () => void
}

export const useUIStore = create<UIState>((set) => ({
  // Initial state
  selectedPlayerId: null,
  activePlayerId: null,
  isCompareMode: false,
  compareTargetId: null,
  thinkingPlayerId: null,
  reviewingPlayerId: null,
  dealingAnimation: {
    isDealing: false,
    currentCardIndex: 0,
  },
  chipAnimation: null,
  winAnimation: null,
  showPlayerCards: false,
  hasLookedAtCards: false,
  isThoughtDrawerOpen: false,
  thoughtDrawerAgentId: null,
  isGameLogExpanded: true,
  isChatPanelExpanded: true,

  // Actions
  setSelectedPlayer: (playerId) =>
    set({ selectedPlayerId: playerId }),

  setActivePlayer: (playerId) =>
    set({ activePlayerId: playerId }),

  enterCompareMode: () =>
    set({ isCompareMode: true, compareTargetId: null }),

  exitCompareMode: () =>
    set({ isCompareMode: false, compareTargetId: null }),

  setCompareTarget: (playerId) =>
    set({ compareTargetId: playerId }),

  setThinkingPlayer: (playerId) =>
    set({ thinkingPlayerId: playerId }),

  setReviewingPlayer: (playerId) =>
    set({ reviewingPlayerId: playerId }),

  startDealingAnimation: () =>
    set({
      dealingAnimation: { isDealing: true, currentCardIndex: 0 },
    }),

  stopDealingAnimation: () =>
    set({
      dealingAnimation: { isDealing: false, currentCardIndex: 0 },
    }),

  advanceDealingCard: () =>
    set((state) => ({
      dealingAnimation: {
        ...state.dealingAnimation,
        currentCardIndex: state.dealingAnimation.currentCardIndex + 1,
      },
    })),

  triggerChipAnimation: (fromPlayerId, amount) =>
    set({ chipAnimation: { fromPlayerId, amount } }),

  clearChipAnimation: () =>
    set({ chipAnimation: null }),

  startWinAnimation: (winnerId, amount) =>
    set({ winAnimation: { winnerId, amount, isPlaying: true } }),

  clearWinAnimation: () =>
    set({ winAnimation: null }),

  setShowPlayerCards: (show) =>
    set({ showPlayerCards: show }),

  setHasLookedAtCards: (looked) =>
    set({ hasLookedAtCards: looked }),

  toggleThoughtDrawer: (agentId) =>
    set((state) => ({
      isThoughtDrawerOpen: agentId
        ? true
        : !state.isThoughtDrawerOpen,
      thoughtDrawerAgentId: agentId ?? state.thoughtDrawerAgentId,
    })),

  toggleGameLog: () =>
    set((state) => ({ isGameLogExpanded: !state.isGameLogExpanded })),

  toggleChatPanel: () =>
    set((state) => ({ isChatPanelExpanded: !state.isChatPanelExpanded })),

  resetUI: () =>
    set({
      selectedPlayerId: null,
      activePlayerId: null,
      isCompareMode: false,
      compareTargetId: null,
      thinkingPlayerId: null,
      reviewingPlayerId: null,
      dealingAnimation: { isDealing: false, currentCardIndex: 0 },
      chipAnimation: null,
      winAnimation: null,
      showPlayerCards: false,
      hasLookedAtCards: false,
      isThoughtDrawerOpen: false,
      thoughtDrawerAgentId: null,
    }),
}))
