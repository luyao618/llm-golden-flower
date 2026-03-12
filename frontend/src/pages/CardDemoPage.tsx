import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CardFace, CardHand } from '../components/Cards'
import type { Card, Suit, Rank } from '../types/game'
import { SUIT_SYMBOLS, SUIT_NAMES, RANK_DISPLAY } from '../types/game'

const ALL_SUITS: Suit[] = ['spades', 'hearts', 'clubs', 'diamonds']
const ALL_RANKS: Rank[] = [14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]

/** 生成全部 52 张牌 */
function generateDeck(): Card[] {
  const deck: Card[] = []
  for (const suit of ALL_SUITS) {
    for (const rank of ALL_RANKS) {
      deck.push({ suit, rank })
    }
  }
  return deck
}

/** 示例手牌组合 */
const SAMPLE_HANDS: { label: string; cards: Card[] }[] = [
  {
    label: '豹子 (AAA)',
    cards: [
      { suit: 'spades', rank: 14 },
      { suit: 'hearts', rank: 14 },
      { suit: 'diamonds', rank: 14 },
    ],
  },
  {
    label: '同花顺 (黑桃 J-Q-K)',
    cards: [
      { suit: 'spades', rank: 11 },
      { suit: 'spades', rank: 12 },
      { suit: 'spades', rank: 13 },
    ],
  },
  {
    label: '同花 (红心 3-7-J)',
    cards: [
      { suit: 'hearts', rank: 3 },
      { suit: 'hearts', rank: 7 },
      { suit: 'hearts', rank: 11 },
    ],
  },
  {
    label: '顺子 (5-6-7)',
    cards: [
      { suit: 'clubs', rank: 5 },
      { suit: 'hearts', rank: 6 },
      { suit: 'spades', rank: 7 },
    ],
  },
  {
    label: '对子 (KK-5)',
    cards: [
      { suit: 'spades', rank: 13 },
      { suit: 'hearts', rank: 13 },
      { suit: 'diamonds', rank: 5 },
    ],
  },
  {
    label: '散牌 (2-7-J)',
    cards: [
      { suit: 'diamonds', rank: 2 },
      { suit: 'clubs', rank: 7 },
      { suit: 'hearts', rank: 11 },
    ],
  },
]

export default function CardDemoPage() {
  const navigate = useNavigate()
  const [showFace, setShowFace] = useState(true)
  const deck = generateDeck()

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-900 to-green-950 p-8">
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-white">T5.4 - 扑克牌组件验收</h1>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-green-700 hover:bg-green-600 text-white rounded-lg transition-colors cursor-pointer"
          >
            返回大厅
          </button>
        </div>

        {/* Toggle */}
        <div className="mb-8 flex items-center gap-4">
          <button
            onClick={() => setShowFace(!showFace)}
            className="px-6 py-2 bg-amber-500 hover:bg-amber-400 text-green-950 font-semibold rounded-lg transition-colors cursor-pointer"
          >
            {showFace ? '翻到背面' : '翻到正面'}
          </button>
          <span className="text-green-300 text-sm">
            当前: {showFace ? '正面' : '背面'} | 点击按钮切换正反面
          </span>
        </div>

        {/* Section 1: 手牌组合展示 */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-amber-400 mb-4">手牌组合（CardHand）</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8">
            {SAMPLE_HANDS.map((hand) => (
              <div key={hand.label} className="bg-green-800/30 rounded-xl p-6 flex flex-col items-center gap-4">
                <span className="text-green-300 text-sm">{hand.label}</span>
                <CardHand
                  cards={hand.cards}
                  faceUp={showFace}
                  size="lg"
                  clickable
                  onClick={() => setShowFace(!showFace)}
                />
              </div>
            ))}
          </div>
        </section>

        {/* Section 2: Size comparison */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-amber-400 mb-4">尺寸对比</h2>
          <div className="flex items-end gap-6 bg-green-800/30 rounded-xl p-6">
            {(['sm', 'md', 'lg', 'xl'] as const).map((sz) => (
              <div key={sz} className="flex flex-col items-center gap-2">
                <CardFace
                  card={{ suit: 'spades', rank: 14 }}
                  faceUp={showFace}
                  size={sz}
                />
                <span className="text-green-400 text-xs">{sz}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Section 3: Card back */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-amber-400 mb-4">牌背设计</h2>
          <div className="flex items-end gap-6 bg-green-800/30 rounded-xl p-6">
            {(['sm', 'md', 'lg', 'xl'] as const).map((sz) => (
              <div key={sz} className="flex flex-col items-center gap-2">
                <CardFace
                  card={null}
                  faceUp={false}
                  size={sz}
                />
                <span className="text-green-400 text-xs">{sz}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Section 4: Special effects */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-amber-400 mb-4">特殊效果</h2>
          <div className="flex items-end gap-6 bg-green-800/30 rounded-xl p-6">
            <div className="flex flex-col items-center gap-2">
              <CardFace
                card={{ suit: 'hearts', rank: 14 }}
                faceUp={true}
                size="lg"
                highlighted
              />
              <span className="text-green-400 text-xs">高亮</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <CardFace
                card={{ suit: 'spades', rank: 14 }}
                faceUp={true}
                size="lg"
                glowing
              />
              <span className="text-green-400 text-xs">发光</span>
            </div>
            <div className="flex flex-col items-center gap-2">
              <CardHand
                cards={[
                  { suit: 'spades', rank: 14 },
                  { suit: 'hearts', rank: 14 },
                  { suit: 'diamonds', rank: 14 },
                ]}
                faceUp={true}
                size="lg"
                glowing
                highlightedIndices={[0, 1, 2]}
              />
              <span className="text-green-400 text-xs">赢牌手牌</span>
            </div>
          </div>
        </section>

        {/* Section 5: Full deck, 52 cards */}
        <section className="mb-12">
          <h2 className="text-xl font-semibold text-amber-400 mb-4">
            52 张牌全览 (共 {deck.length} 张)
          </h2>
          {ALL_SUITS.map((suit) => (
            <div key={suit} className="mb-6">
              <h3 className="text-lg text-green-300 mb-3 flex items-center gap-2">
                <span className={SUIT_NAMES[suit] === '红心' || SUIT_NAMES[suit] === '方块' ? 'text-red-400' : 'text-white'}>
                  {SUIT_SYMBOLS[suit]}
                </span>
                {SUIT_NAMES[suit]}
              </h3>
              <div className="flex flex-wrap gap-2 bg-green-800/20 rounded-xl p-4">
                {ALL_RANKS.map((rank) => (
                  <div key={`${suit}-${rank}`} className="flex flex-col items-center gap-1">
                    <CardFace
                      card={{ suit, rank }}
                      faceUp={showFace}
                      size="md"
                      clickable
                      onClick={() => setShowFace(!showFace)}
                    />
                    <span className="text-green-500 text-xs">
                      {RANK_DISPLAY[rank]}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>
      </div>
    </div>
  )
}
