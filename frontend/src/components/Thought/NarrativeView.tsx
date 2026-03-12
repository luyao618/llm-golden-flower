import { motion } from 'framer-motion'
import type { RoundNarrative } from '../../types/game'

interface NarrativeViewProps {
  narrative: RoundNarrative
}

/**
 * 叙事视图组件
 *
 * 展示 AI 的第一人称叙事文本，描述它在某一局中的心理活动和故事。
 * 以卡片式排版展示，带有引号样式，营造"日记"或"独白"的感觉。
 */
export default function NarrativeView({ narrative }: NarrativeViewProps) {
  return (
    <motion.div
      className="space-y-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* 标题 */}
      <div className="flex items-center gap-2">
        <span className="text-green-500/60 text-xs font-medium">
          第 {narrative.round_number} 局叙事
        </span>
      </div>

      {/* 叙事正文 */}
      <div className="bg-green-900/15 border border-green-800/30 rounded-lg p-4">
        {/* 装饰性引号 */}
        <div className="text-green-700/30 text-3xl font-serif leading-none mb-1">"</div>

        {/* 叙事文本 - 按段落分割 */}
        <div className="space-y-2 pl-2">
          {narrative.narrative
            .split('\n')
            .filter((p) => p.trim())
            .map((paragraph, i) => (
              <p
                key={i}
                className="text-green-300/80 text-xs leading-relaxed"
              >
                {paragraph.trim()}
              </p>
            ))}
        </div>

        {/* 右下角关闭引号 */}
        <div className="text-green-700/30 text-3xl font-serif leading-none text-right mt-1">"</div>
      </div>

      {/* 结局 */}
      {narrative.outcome && (
        <div className="bg-black/20 border border-green-800/25 rounded-md px-3 py-2">
          <span className="text-green-500/50 text-[10px] block mb-0.5">结局</span>
          <p className="text-green-300/70 text-xs leading-relaxed">
            {narrative.outcome}
          </p>
        </div>
      )}
    </motion.div>
  )
}
