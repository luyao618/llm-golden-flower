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
        <span className="text-[var(--color-secondary)] text-xs font-medium"
          style={{ fontFamily: 'var(--font-display)' }}>
          第 {narrative.round_number} 局叙事
        </span>
      </div>

      {/* 叙事正文 */}
      <div className="bg-[var(--bg-surface)]/50 border border-[var(--border-default)] rounded-xl p-4
        hover:border-[var(--border-hover)] transition-colors">
        {/* 装饰性引号 */}
        <div className="text-[var(--color-primary)]/20 text-3xl font-serif leading-none mb-1">"</div>

        {/* 叙事文本 - 按段落分割 */}
        <div className="space-y-2 pl-2 border-l-2 border-[var(--color-primary)]/15">
          {narrative.narrative
            .split('\n')
            .filter((p) => p.trim())
            .map((paragraph, i) => (
              <p
                key={i}
                className="text-[var(--text-secondary)] text-xs leading-relaxed"
                style={{ fontFamily: 'var(--font-mono)' }}
              >
                {paragraph.trim()}
              </p>
            ))}
        </div>

        {/* 右下角关闭引号 */}
        <div className="text-[var(--color-primary)]/20 text-3xl font-serif leading-none text-right mt-1">"</div>
      </div>

      {/* 结局 */}
      {narrative.outcome && (
        <div className="bg-[var(--bg-deep)]/60 border border-[var(--border-default)] rounded-lg px-3 py-2
          hover:border-[var(--border-hover)] transition-colors">
          <span className="text-[var(--text-muted)] text-[10px] block mb-0.5">结局</span>
          <p className="text-[var(--text-secondary)] text-xs leading-relaxed"
            style={{ fontFamily: 'var(--font-mono)' }}>
            {narrative.outcome}
          </p>
        </div>
      )}
    </motion.div>
  )
}
