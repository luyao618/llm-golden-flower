// ===== Design System: Shared Constants & Utilities =====

/** Avatar gradient color list — used across all components */
export const AVATAR_COLORS = [
  'from-rose-500 to-pink-600',
  'from-violet-500 to-purple-600',
  'from-blue-500 to-indigo-600',
  'from-cyan-500 to-teal-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
]

/** Get avatar gradient class by hashing player ID */
export function getAvatarColor(id: string): string {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

/** Get avatar display text (first character of name) */
export function getAvatarText(name: string): string {
  const firstChar = name.charAt(0)
  if (/[\u4e00-\u9fff]/.test(firstChar)) return firstChar
  return firstChar.toUpperCase()
}

/** Action button theme color mapping */
export const ACTION_THEME_COLORS: Record<string, { border: string; glow: string; text: string }> = {
  check_cards: { border: 'rgba(0, 170, 255, 0.4)', glow: 'rgba(0, 170, 255, 0.3)', text: '#00aaff' },
  call:        { border: 'rgba(0, 212, 255, 0.4)', glow: 'rgba(0, 212, 255, 0.3)', text: '#00d4ff' },
  raise:       { border: 'rgba(255, 215, 0, 0.4)', glow: 'rgba(255, 215, 0, 0.3)',  text: '#ffd700' },
  compare:     { border: 'rgba(139, 92, 246, 0.4)', glow: 'rgba(139, 92, 246, 0.3)', text: '#8b5cf6' },
  fold:        { border: 'rgba(255, 68, 68, 0.4)', glow: 'rgba(255, 68, 68, 0.3)',  text: '#ff4444' },
}
