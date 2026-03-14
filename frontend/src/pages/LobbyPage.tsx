// ============================================================
// 游戏大厅页面 — 重定向到首页（游戏配置已改为弹窗形式）
// ============================================================

import { Navigate } from 'react-router-dom'

export default function LobbyPage() {
  return <Navigate to="/" replace />
}
