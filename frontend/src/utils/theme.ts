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

/** Cyberpunk avatar accent colors — subtle neon tints for border/glow */
const AVATAR_ACCENT_COLORS = [
  { border: 'rgba(255, 100, 130, 0.45)', glow: 'rgba(255, 100, 130, 0.15)', text: 'rgba(255, 160, 180, 0.9)' },
  { border: 'rgba(160, 120, 255, 0.45)', glow: 'rgba(160, 120, 255, 0.15)', text: 'rgba(190, 170, 255, 0.9)' },
  { border: 'rgba(80, 140, 255, 0.45)',  glow: 'rgba(80, 140, 255, 0.15)',  text: 'rgba(140, 180, 255, 0.9)' },
  { border: 'rgba(0, 212, 255, 0.45)',   glow: 'rgba(0, 212, 255, 0.15)',   text: 'rgba(120, 220, 255, 0.9)' },
  { border: 'rgba(80, 220, 160, 0.45)',  glow: 'rgba(80, 220, 160, 0.15)',  text: 'rgba(140, 230, 190, 0.9)' },
  { border: 'rgba(255, 185, 50, 0.45)',  glow: 'rgba(255, 185, 50, 0.15)',  text: 'rgba(255, 210, 120, 0.9)' },
]

/** Get cyberpunk avatar accent style by hashing player ID */
export function getAvatarAccent(id: string): { border: string; glow: string; text: string } {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0
  }
  return AVATAR_ACCENT_COLORS[Math.abs(hash) % AVATAR_ACCENT_COLORS.length]
}

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
