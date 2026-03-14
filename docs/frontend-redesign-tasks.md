# Frontend Redesign Tasks - 暗黑科技风

> 本文档包含前端 UI 重设计的所有分步骤任务。
> 每个 Task 可以在独立的 session 中由 AI 完成。
> **执行前必须先阅读 `docs/design-system.md` 了解完整的设计规范。**

---

## 如何使用本文档

1. 按 Task 编号顺序执行（Task 之间有依赖关系）
2. 每个 Task 开始时，告诉 AI：
   - "请先阅读 `docs/design-system.md` 和 `docs/frontend-redesign-tasks.md` 中的 Task X"
   - "参考图在 `docs/design-refs/` 目录下"
3. 每个 Task 完成后，建议做一次 `git commit`
4. 可以并行执行的 Task 会在文档中标注

---

## 依赖关系图

```
Task 0 (基础设施)
  ├── Task 1 (大厅页)
  ├── Task 2 (牌桌页 - 布局 + 座位)
  │     ├── Task 3 (牌桌页 - 操作面板 + 聊天)
  │     └── Task 4 (牌桌页 - 动画 + 日志)
  ├── Task 5 (结算页)
  └── Task 6 (思维面板)
```

- **Task 0** 是所有 Task 的前置依赖，必须最先完成
- **Task 1, 2, 5, 6** 互相独立，可以并行执行（都只依赖 Task 0）
- **Task 3, 4** 依赖 Task 2 的牌桌基础布局

---

## Task 0: 基础设施 — 设计系统搭建

**优先级**：最高（所有其他 Task 依赖此 Task）

**设计参考图**：无（本 Task 是基础设施，不涉及页面视觉）

### 目标

建立统一的设计 Token 系统（CSS 自定义属性 + 字体加载 + 共用工具函数），让所有后续 Task 可以引用统一的颜色、字体和效果。

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/index.html` | 修改 | 添加 Google Fonts 引入 |
| `frontend/src/index.css` | 修改 | 添加 CSS 自定义属性 + 全局样式类 |
| `frontend/src/utils/theme.ts` | 新建 | 提取共用常量和工具函数 |

### 详细要求

#### 0.1 修改 `index.html`

在 `<head>` 中添加 Google Fonts：

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
```

#### 0.2 修改 `index.css`

保留现有的 `@import "tailwindcss";`，在其后添加：

1. **CSS 自定义属性**（完整色板定义，详见 `design-system.md` 第 1 节）
2. **全局 body 样式**：
   - `font-family: 'Inter', 'Noto Sans SC', sans-serif;`
   - `background-color: var(--bg-deepest);`
   - `color: var(--text-primary);`
3. **Tailwind `@theme` 扩展**（如果 Tailwind v4 支持），或者通过 CSS 变量让 Tailwind 可用
4. **全局工具类**：
   - `.glass-panel` — 标准玻璃态面板样式
   - `.glass-panel-accent` — 强调玻璃态面板样式
   - `.neon-text-primary` — 青色霓虹文字发光
   - `.neon-text-gold` — 金色发光文字
   - `.neon-border-gradient` — 霓虹渐变边框（用于按钮）
   - `.glow-pulse` — 脉冲发光动画
   - `.perspective-grid` — 透视网格背景
   - `.radial-glow` — 径向渐变光晕背景

完整的 CSS 类定义请参考 `design-system.md` 第 3、4、10 节。

#### 0.3 新建 `src/utils/theme.ts`

提取以下内容到共用模块中（目前在 6 个文件中重复定义）：

```typescript
// 头像渐变色列表
export const AVATAR_COLORS = [
  'from-rose-500 to-pink-600',
  'from-violet-500 to-purple-600',
  'from-blue-500 to-indigo-600',
  'from-cyan-500 to-teal-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
]

// 根据 ID 哈希获取头像颜色
export function getAvatarColor(id: string): string {
  let hash = 0
  for (let i = 0; i < id.length; i++) {
    hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

// 获取头像显示文字（首字符）
export function getAvatarText(name: string): string {
  const firstChar = name.charAt(0)
  if (/[\u4e00-\u9fff]/.test(firstChar)) return firstChar
  return firstChar.toUpperCase()
}

// 操作按钮的主题色映射
export const ACTION_THEME_COLORS: Record<string, { border: string; glow: string; text: string }> = {
  check_cards: { border: 'rgba(0, 170, 255, 0.4)', glow: 'rgba(0, 170, 255, 0.3)', text: '#00aaff' },
  call:        { border: 'rgba(0, 212, 255, 0.4)', glow: 'rgba(0, 212, 255, 0.3)', text: '#00d4ff' },
  raise:       { border: 'rgba(255, 215, 0, 0.4)', glow: 'rgba(255, 215, 0, 0.3)',  text: '#ffd700' },
  compare:     { border: 'rgba(139, 92, 246, 0.4)', glow: 'rgba(139, 92, 246, 0.3)', text: '#8b5cf6' },
  fold:        { border: 'rgba(255, 68, 68, 0.4)', glow: 'rgba(255, 68, 68, 0.3)',  text: '#ff4444' },
}
```

然后，到以下 6 个文件中删除本地的 `AVATAR_COLORS` 和 `getAvatarColor()` 定义，改为从 `utils/theme` 导入：

- `src/components/Player/PlayerSeat.tsx`（还有 `getAvatarText`）
- `src/components/Thought/ThoughtDrawer.tsx`
- `src/components/Settlement/Leaderboard.tsx`
- `src/components/Settlement/AgentSummaryCard.tsx`
- `src/components/Table/ChatPanel.tsx`（如有）
- `src/components/Table/GameLog.tsx`（如有）

### 验证方式

1. 运行 `npm run dev`，页面应正常加载（不报错）
2. 字体加载正常（浏览器 DevTools → Network → 搜索 fonts.googleapis.com）
3. 在浏览器 DevTools 的元素面板中，html/body 元素上能看到 CSS 自定义属性
4. `import { getAvatarColor } from '../utils/theme'` 不报 TypeScript 错误

---

## Task 1: 大厅页 (LobbyPage) 重设计

**优先级**：高
**前置依赖**：Task 0

**设计参考图**：`docs/design-refs/lobby.jpeg`

> 请在开始此 Task 前阅读参考图。关键视觉特征：
> - 极深色背景 + 底部透视网格效果
> - 中央玻璃态设置面板（带青色/紫色边缘光晕）
> - "炸金花 AI" 大标题带霓虹青色发光
> - START GAME 按钮双层霓虹边框（青→粉渐变），有脉冲动画
> - 周围装饰性浮动扑克牌和筹码（可选，优先级低）

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/pages/LobbyPage.tsx` | 修改 | 页面布局、背景、标题、面板容器 |
| `frontend/src/components/Lobby/GameConfigForm.tsx` | 修改 | 输入框/下拉框暗色主题 |
| `frontend/src/components/Lobby/ChipsConfig.tsx` | 修改 | 筹码配置区暗色主题 |
| `frontend/src/components/Lobby/StartButton.tsx` | 修改 | 霓虹渐变边框按钮 |
| `frontend/src/components/Lobby/ModelConfigPanel.tsx` | 修改 | 模态弹窗暗色玻璃态 |
| `frontend/src/components/Lobby/CopilotConnect.tsx` | 修改 | Copilot 连接区暗色主题 |

### 详细要求

#### 1.1 LobbyPage.tsx — 页面容器

**当前代码**（需替换的关键行）：
```tsx
// 当前：绿色渐变背景
<div className="min-h-screen bg-gradient-to-b from-green-900 to-green-950 flex flex-col items-center justify-center p-8">
```

**改为**：
```tsx
// 新：深色背景 + 透视网格 + 顶部径向光晕
<div className="min-h-screen bg-[var(--bg-deepest)] flex flex-col items-center justify-center p-8 relative overflow-hidden">
  {/* 背景装饰：径向光晕 */}
  <div className="absolute inset-0 pointer-events-none"
    style={{
      background: 'radial-gradient(ellipse at 50% 20%, rgba(0,212,255,0.06) 0%, transparent 50%), radial-gradient(ellipse at 50% 80%, rgba(139,92,246,0.04) 0%, transparent 50%)'
    }}
  />
  {/* 背景装饰：透视网格 */}
  <div className="absolute bottom-0 left-0 right-0 h-1/3 perspective-grid opacity-30 pointer-events-none" />
```

**标题**：
```tsx
// 当前
<h1 className="text-5xl font-bold text-amber-400 mb-4">炸金花 AI</h1>

// 改为
<h1 className="text-5xl font-bold neon-text-primary mb-4 relative z-10"
    style={{ fontFamily: 'var(--font-display)' }}>
  炸金花 AI
</h1>
```

**副标题**：
```tsx
// 当前：text-green-300
// 改为：text-[var(--text-secondary)]
```

**面板容器**：
```tsx
// 当前
<div className="bg-green-800/60 backdrop-blur rounded-2xl p-8 w-full max-w-lg shadow-2xl border border-green-700/50 space-y-8">

// 改为
<div className="glass-panel-accent p-8 w-full max-w-lg space-y-8 relative z-10">
```

**版本号文字**：
```tsx
// 当前：text-green-600
// 改为：text-[var(--text-muted)]
```

**"配置模型"按钮**：
```tsx
// 当前：bg-amber-600/80 hover:bg-amber-500 ... border-amber-500/30
// 改为：bg-[var(--color-secondary)]/20 hover:bg-[var(--color-secondary)]/30 text-[var(--color-secondary)] border border-[var(--color-secondary)]/30
```

**"扑克牌组件预览"按钮**：
```tsx
// 当前：bg-green-700 hover:bg-green-600
// 改为：bg-white/5 hover:bg-white/10 border border-[var(--border-default)] text-[var(--text-secondary)]
```

**分隔线**：
```tsx
// 当前：border-green-700/30
// 改为：border-[var(--border-default)]
```

#### 1.2 GameConfigForm.tsx — 表单控件

所有表单元素的颜色替换规则：

| 当前 | 替换为 |
|------|--------|
| `text-green-300` (标签) | `text-[var(--text-secondary)]` |
| `text-green-400/70` (小标签) | `text-[var(--text-muted)]` |
| `bg-green-900/60` (输入框背景) | `bg-[var(--bg-surface)]` |
| `border-green-700/50` (输入框边框) | `border-[var(--border-default)]` |
| `placeholder-green-600` | `placeholder-[var(--text-disabled)]` |
| `focus:border-amber-500/50` | `focus:border-[var(--color-primary)]/50` |
| `focus:ring-amber-500/30` | `focus:ring-[var(--color-primary)]/30` |
| `bg-green-900/40` (对手卡片) | `bg-[var(--bg-surface)]/60` |
| `border-green-700/30` (对手卡片边框) | `border-[var(--border-default)]` |
| `text-amber-400` (+ 添加对手) | `text-[var(--color-primary)]` |
| `text-red-400/70` (移除) | `text-[var(--color-danger)]/70` |
| `bg-green-950/60` (下拉框) | `bg-[var(--bg-deep)]` |
| `border-green-700/40` (下拉框边框) | `border-[var(--border-default)]` |

#### 1.3 ChipsConfig.tsx — 筹码配置

同样的颜色替换规则，额外注意：

| 当前 | 替换为 |
|------|--------|
| `bg-amber-500/20 border-amber-500/50 text-amber-400` (选中预设) | `bg-[var(--color-primary)]/10 border-[var(--color-primary)]/40 text-[var(--color-primary)]` |
| `bg-green-900/40 border-green-700/30 text-green-300` (未选预设) | `bg-[var(--bg-surface)]/40 border-[var(--border-default)] text-[var(--text-secondary)]` |
| `text-green-400/60` (收起/展开) | `text-[var(--text-muted)]` |
| `bg-green-900/30 border-green-700/20` (高级配置面板) | `bg-[var(--bg-surface)]/30 border-[var(--border-default)]` |
| `text-green-500` (概览文字) | `text-[var(--text-muted)]` |

#### 1.4 StartButton.tsx — 核心按钮重设计

这是大厅页最重要的视觉元素。参照参考图中 START GAME 按钮的双层霓虹边框效果。

**当前按钮**：
```tsx
className="... bg-amber-500 hover:bg-amber-400 text-green-950 ..."
```

**改为霓虹渐变边框按钮**：
```tsx
<div className="relative group">
  {/* 外层霓虹发光 */}
  <div className="absolute -inset-[2px] rounded-xl bg-gradient-to-r from-[var(--color-primary)] via-[var(--color-secondary)] to-[var(--color-accent)] opacity-70 blur-[2px] group-hover:opacity-100 group-hover:blur-[4px] transition-all duration-300" />
  {/* 按钮本体 */}
  <button className="relative w-full py-3.5 font-bold rounded-xl text-lg bg-[var(--bg-surface)] text-[var(--text-primary)] border border-white/10 transition-all cursor-pointer hover:bg-[var(--bg-elevated)] active:scale-[0.98]"
    style={{ fontFamily: 'var(--font-display)' }}>
    开始游戏
  </button>
</div>
```

**错误提示框**：
```tsx
// 当前：bg-red-900/30 border-red-700/40 text-red-300
// 改为：bg-[var(--color-danger)]/10 border-[var(--color-danger)]/30 text-[var(--color-danger)]
```

**底部提示文字**：
```tsx
// 当前：text-green-600
// 改为：text-[var(--text-muted)]
```

#### 1.5 ModelConfigPanel.tsx — 模态弹窗

**遮罩层**：保持不变（`bg-black/60 backdrop-blur-sm` 已经合适）

**面板容器**：
```tsx
// 当前
className="bg-green-900/95 border border-green-700/50 rounded-2xl ..."

// 改为
className="glass-panel-accent w-full max-w-lg max-h-[85vh] overflow-y-auto"
```

**标题栏**：
```tsx
// 当前：border-green-700/30
// 改为：border-[var(--border-default)]
// 标题文字保持 text-white
// 关闭按钮：text-[var(--text-muted)] hover:text-white
```

**ProviderKeyRow 组件**：
```tsx
// 当前：border-green-700/30 bg-green-950/20
// 改为：border-[var(--border-default)] bg-[var(--bg-deep)]/40

// 保存按钮：bg-[var(--color-primary)]/80 hover:bg-[var(--color-primary)]
// 验证按钮：bg-[var(--bg-elevated)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)]
// 移除按钮：保持红色系不变
// 输入框：同 GameConfigForm 的替换规则
```

**底部"完成"按钮**：
```tsx
// 当前：bg-green-700 hover:bg-green-600
// 改为：bg-[var(--bg-elevated)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)]
```

#### 1.6 CopilotConnect.tsx — Copilot 连接

**外框**：
```tsx
// 当前：border-purple-700/40 bg-purple-950/20
// 改为：border-[var(--color-secondary)]/30 bg-[var(--color-secondary)]/5
```

其他紫色元素保持紫色系（因为 Copilot/GitHub 品牌色即紫色，与新主题的 secondary 色一致），只需要替换绿色相关的类。

### 验证方式

1. `npm run dev`，访问 `/`
2. 页面背景为极深色（近乎纯黑）
3. 标题"炸金花 AI"有青色霓虹发光效果
4. 中央面板有玻璃态效果（半透明 + 模糊 + 发光边框）
5. START GAME 按钮有渐变霓虹边框
6. 所有表单控件在暗色背景上清晰可读
7. 点击"配置模型"弹窗正常工作，视觉风格一致

---

## Task 2: 牌桌页 — 布局、牌桌、座位

**优先级**：高
**前置依赖**：Task 0

**设计参考图**：`docs/design-refs/game-table.jpeg`

> 参考图关键视觉特征：
> - 深蓝黑背景，牌桌为深蓝灰色椭圆
> - 牌桌边缘有青色霓虹发光描边（非木质边框）
> - 每个玩家座位有彩色发光圆环头像
> - "Pot: 500" 金色发光文字在桌面中央
> - 活跃玩家有脉冲发光效果

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/pages/GamePage.tsx` | 修改 | 页面整体布局、顶部栏、底部栏 |
| `frontend/src/components/Table/TableLayout.tsx` | 修改 | 椭圆牌桌颜色和边框 |
| `frontend/src/components/Player/PlayerSeat.tsx` | 修改 | 玩家座位视觉、发光环 |
| `frontend/src/components/Player/ChatBubble.tsx` | 修改 | 聊天气泡暗色主题 |
| `frontend/src/components/Table/PotDisplay.tsx` | 修改 | 底池显示暗色主题 |
| `frontend/src/components/Cards/CardFace.tsx` | 微调 | 牌面在深色背景上的阴影 |
| `frontend/src/components/Cards/CardHand.tsx` | 微调 | 手牌容器适配 |

### 详细要求

#### 2.1 GamePage.tsx — 整体布局

**页面背景**：
```tsx
// 当前（出现在多处）
bg-gradient-to-b from-green-950 via-green-900 to-green-950

// 全部改为
bg-[var(--bg-deepest)]
```

**加载状态页面**（line 121）：同上，加上加载指示器颜色改为 `border-[var(--color-primary)]/30 border-t-[var(--color-primary)]`

**顶部 header**：
```tsx
// 当前
className="flex items-center justify-between px-4 py-2 bg-black/30 border-b border-green-800/50"

// 改为
className="flex items-center justify-between px-4 py-2 bg-[var(--bg-deep)]/80 backdrop-blur-md border-b border-[var(--border-default)]"
```

Header 内部的所有文字颜色替换：
| 当前 | 替换为 |
|------|--------|
| `text-green-400` (返回大厅) | `text-[var(--color-primary)]` |
| `hover:text-green-300` | `hover:text-[var(--color-primary)]` 增强亮度 |
| `text-green-500/60` (ID文字) | `text-[var(--text-muted)]` |
| `text-green-500/70` (心路历程) | `text-[var(--color-secondary)]/70 hover:text-[var(--color-secondary)]` |
| `text-amber-500` (结束游戏) | `text-[var(--color-gold)]` |

**ConnectionIndicator 组件**的颜色映射：
```tsx
const colorMap: Record<ConnectionStatus, string> = {
  connected: 'bg-[var(--color-success)]',
  connecting: 'bg-[var(--color-warning)] animate-pulse',
  reconnecting: 'bg-[var(--color-warning)] animate-pulse',
  disconnected: 'bg-[var(--color-danger)]',
}
```

**底部 footer**：
```tsx
// 当前
className="shrink-0 bg-black/40 border-t border-green-800/50 relative z-20"

// 改为
className="shrink-0 bg-[var(--bg-deep)]/80 backdrop-blur-md border-t border-[var(--border-default)] relative z-20"
```

Footer 内部文字颜色替换：
| 当前 | 替换为 |
|------|--------|
| `text-amber-400/70` (点击看牌) | `text-[var(--color-gold)]/70` |
| `bg-amber-500 text-green-950` (开始按钮) | 使用与 StartButton 类似的霓虹按钮样式 |
| `text-amber-400` (游戏已结束) | `text-[var(--color-gold)]` |
| `text-red-400` (连接断开) | `text-[var(--color-danger)]` |
| `text-yellow-400` (连接中) | `text-[var(--color-warning)]` |
| `text-green-600/50` (等待对手) | `text-[var(--text-muted)]` |

**聊天面板侧栏**：
```tsx
// 当前
className="... border-l border-green-800/50 bg-black/20 ..."

// 改为
className="... border-l border-[var(--border-default)] bg-[var(--bg-deep)]/40 ..."
```

折叠按钮：
```tsx
// 当前：bg-green-900/80 border-green-700/50 text-green-400
// 改为：bg-[var(--bg-surface)] border-[var(--border-default)] text-[var(--color-primary)]
```

聊天标题栏：
```tsx
// 当前：border-green-800/40, text-green-400/80, text-green-700/50
// 改为：border-[var(--border-default)], text-[var(--color-primary)]/80, text-[var(--text-muted)]
```

#### 2.2 TableLayout.tsx — 牌桌椭圆

这是视觉变化最大的部分。参照参考图，牌桌从绿色赌场风格改为深蓝灰 + 青色霓虹描边。

**当前牌桌三层结构**（line 172-193）：

```tsx
{/* 外层 - 木质色 */}
<div className="... bg-gradient-to-b from-amber-900 to-amber-950 p-[6px] shadow-2xl">
  {/* 中层 - 牌桌边缘 */}
  <div className="... bg-gradient-to-b from-green-800 to-green-900 p-[3px]">
    {/* 内层 - 牌桌毡面 */}
    <div className="... bg-gradient-to-br from-green-700 via-green-800 to-green-900 ...">
```

**改为**：

```tsx
{/* 牌桌 - 霓虹发光边框 */}
<div className="w-full h-full rounded-[50%] p-[2px] shadow-2xl"
  style={{
    background: 'linear-gradient(135deg, rgba(0,212,255,0.5), rgba(139,92,246,0.3), rgba(0,212,255,0.5))',
    boxShadow: '0 0 40px rgba(0,212,255,0.15), 0 0 80px rgba(0,212,255,0.05)'
  }}>
  {/* 内层 - 深蓝灰毡面 */}
  <div className="w-full h-full rounded-[50%] flex items-center justify-center relative overflow-hidden"
    style={{
      background: 'linear-gradient(135deg, #0d1b2a, #162035, #0d1b2a)'
    }}>
    {/* 微妙的桌面纹理/光泽 */}
    <div className="absolute inset-0 rounded-[50%] opacity-20"
      style={{
        backgroundImage: 'radial-gradient(circle at 30% 40%, rgba(0,212,255,0.05) 0%, transparent 50%), radial-gradient(circle at 70% 60%, rgba(139,92,246,0.03) 0%, transparent 40%)'
      }}
    />
    <PotDisplay ... />
  </div>
</div>
```

**等待提示**：
```tsx
// 当前：text-green-400/50
// 改为：text-[var(--text-muted)]
```

#### 2.3 PlayerSeat.tsx — 玩家座位

**STATUS_COLORS 映射**：
```tsx
const STATUS_COLORS: Record<PlayerStatus, string> = {
  active_blind: 'text-[var(--color-info)] bg-[var(--color-info)]/10 border-[var(--color-info)]/30',
  active_seen: 'text-[var(--color-gold)] bg-[var(--color-gold)]/10 border-[var(--color-gold)]/30',
  folded: 'text-[var(--text-muted)] bg-white/5 border-white/10',
  out: 'text-[var(--color-danger)] bg-[var(--color-danger)]/10 border-[var(--color-danger)]/30',
}
```

**头像外圈发光环**（参照参考图中每个座位的发光圆环）：

当前头像是普通圆形，改为带发光环效果：

```tsx
<div className={`
  w-12 h-12 rounded-full flex items-center justify-center
  text-white font-bold text-lg
  bg-gradient-to-br ${getAvatarColor(player.id)}
  ${isDimmed ? 'grayscale' : ''}
  ${isMe ? 'ring-2 ring-[var(--color-gold)] shadow-[0_0_12px_rgba(255,215,0,0.3)]' : 'ring-2 ring-white/15'}
`}>
```

**活跃玩家发光环** — 改为青色霓虹脉冲：
```tsx
{isActive && (
  <motion.div
    className="absolute -inset-1 rounded-xl border-2 border-[var(--color-primary)]/70 shadow-[0_0_15px_var(--color-primary)/30]"
    animate={{
      boxShadow: [
        '0 0 10px rgba(0,212,255,0.2)',
        '0 0 25px rgba(0,212,255,0.5)',
        '0 0 10px rgba(0,212,255,0.2)',
      ],
    }}
    transition={{ duration: 1.5, repeat: Infinity }}
  />
)}
```

**名字颜色**：
```tsx
// 当前：isMe ? 'text-amber-300' : 'text-white'
// 改为：isMe ? 'text-[var(--color-gold)]' : 'text-[var(--text-primary)]'
```

**筹码颜色**：
```tsx
// 当前：text-amber-400, bg-amber-500, border-amber-300/50
// 改为：text-[var(--color-gold)], 筹码圆点也用金色
```

**AI 标记、庄家标记**：
```tsx
// AI badge: bg-green-600 → bg-[var(--color-primary)]/80, border-green-400 → border-[var(--color-primary)]
// Dealer badge: 保持金色系 (bg-amber-500 即可)
```

**ThinkingDots**：
```tsx
// 当前：bg-amber-400
// 改为：bg-[var(--color-primary)]
```

**经验回顾指示器**：
```tsx
// 当前：bg-purple-500/80
// 改为：bg-[var(--color-secondary)]/80
```

**本局下注额**：
```tsx
// 当前：text-green-400/70
// 改为：text-[var(--color-primary)]/60
```

**引入共用 theme**：
```tsx
import { getAvatarColor, getAvatarText } from '../../utils/theme'
```
删除本文件中的 `AVATAR_COLORS`, `getAvatarColor`, `getAvatarText` 定义。

#### 2.4 PotDisplay.tsx — 底池显示

参照参考图中 "Pot: 500" 的金色发光效果。

```tsx
// 底池数字容器
// 当前：bg-black/60 border-amber-500/40
// 改为：bg-[var(--bg-deep)]/80 backdrop-blur border-[var(--color-gold)]/30 shadow-[0_0_20px_rgba(255,215,0,0.1)]

// 底池金额文字
// 当前：text-amber-400
// 改为：neon-text-gold (使用 className)

// 局信息文字
// 当前：text-green-400/70, text-green-300, text-green-700, text-amber-400/80
// 改为：text-[var(--text-muted)], text-[var(--text-secondary)], text-[var(--text-disabled)], text-[var(--color-gold)]/80
```

#### 2.5 ChatBubble.tsx

```tsx
// 气泡背景改为暗色半透明
// 当前可能有绿色系，统一改为：bg-[var(--bg-surface)]/90 border border-[var(--border-default)] 
// 文字：text-[var(--text-primary)]
```

#### 2.6 CardFace.tsx / CardHand.tsx

牌面组件主要使用 `cards.css` 中的自定义样式，不用大改。仅微调：
- 确保牌面在深色背景上有足够的阴影/对比度
- 牌背设计可保持不变（已有拟物风格）
- 如果牌面白色区域在深色背景上太刺眼，可加微弱的 `brightness(0.95)` 滤镜

### 验证方式

1. `npm run dev`，创建游戏进入牌桌页
2. 牌桌为深蓝灰色椭圆 + 青色霓虹边框发光
3. 玩家头像有彩色环效果
4. 活跃玩家有青色脉冲光效
5. 底池金额有金色发光
6. 顶部栏/底部栏为暗色玻璃态

---

## Task 3: 牌桌页 — 操作面板 + 聊天

**优先级**：高
**前置依赖**：Task 0, Task 2

**设计参考图**：`docs/design-refs/game-table.jpeg`

> 参考图关键视觉特征（底部区域）：
> - 底部操作按钮为圆角胶囊形，每个带图标 + 文字
> - 按钮暗底 + 发光边框风格，不是实心色块
> - 每个操作按钮有不同的主题色

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/Actions/ActionPanel.tsx` | 修改 | 操作按钮重设计 |
| `frontend/src/components/Actions/CompareSelector.tsx` | 修改 | 比牌选择器暗色主题 |
| `frontend/src/components/Table/ChatPanel.tsx` | 修改 | 聊天面板暗色主题 |
| `frontend/src/components/Table/ChatInput.tsx` | 修改 | 输入框暗色主题 |

### 详细要求

#### 3.1 ActionPanel.tsx — 操作按钮重设计

这是操作体验最关键的组件。参照参考图底部的按钮栏。

**按钮样式从实心色块改为发光边框胶囊**：

当前每个按钮的 `colors` 字段定义了实心背景色。改为透明底 + 发光边框：

```tsx
// 导入主题
import { ACTION_THEME_COLORS } from '../../utils/theme'

// 替换 switch 中的 colors 字段
case 'check_cards':
  buttons.push({
    action: 'check_cards',
    label: '看牌',
    colors: `bg-white/[0.03] hover:bg-[${ACTION_THEME_COLORS.check_cards.text}]/10 
             border-[${ACTION_THEME_COLORS.check_cards.border}] 
             text-[${ACTION_THEME_COLORS.check_cards.text}]
             hover:shadow-[0_0_15px_${ACTION_THEME_COLORS.check_cards.glow}]`,
    hotkey: 'Q',
  })
  break
```

**注意**：由于 Tailwind 不支持动态插值，建议改用 `style` 属性来设置这些动态颜色，或者把每个按钮的颜色类硬编码为具体值：

```tsx
case 'check_cards':
  buttons.push({
    action: 'check_cards',
    label: '看牌',
    colors: 'bg-white/[0.03] hover:bg-sky-500/10 border-sky-400/40 text-sky-400 hover:shadow-[0_0_15px_rgba(0,170,255,0.3)]',
    hotkey: 'Q',
  })
  break

case 'call':
  buttons.push({
    action: 'call',
    label: '跟注',
    costLabel: `${getCallCost(currentRound, myPlayer)}`,
    colors: 'bg-white/[0.03] hover:bg-cyan-500/10 border-cyan-400/40 text-cyan-400 hover:shadow-[0_0_15px_rgba(0,212,255,0.3)]',
    hotkey: 'W',
  })
  break

case 'raise':
  buttons.push({
    action: 'raise',
    label: '加注',
    costLabel: `${getRaiseCost(currentRound, myPlayer)}`,
    colors: 'bg-white/[0.03] hover:bg-yellow-500/10 border-yellow-400/40 text-yellow-400 hover:shadow-[0_0_15px_rgba(255,215,0,0.3)]',
    hotkey: 'E',
  })
  break

case 'compare':
  buttons.push({
    action: 'compare',
    label: '比牌',
    costLabel: `${getCompareCost(currentRound, myPlayer)}`,
    colors: 'bg-white/[0.03] hover:bg-purple-500/10 border-purple-400/40 text-purple-400 hover:shadow-[0_0_15px_rgba(139,92,246,0.3)]',
    hotkey: 'R',
  })
  break

case 'fold':
  buttons.push({
    action: 'fold',
    label: '弃牌',
    colors: 'bg-white/[0.03] hover:bg-red-500/10 border-red-400/40 text-red-400 hover:shadow-[0_0_15px_rgba(255,68,68,0.3)]',
    needsConfirm: true,
    hotkey: 'F',
  })
  break
```

**按钮基础样式**（替换 line 256-262 的 className）：
```tsx
className={`
  relative px-5 py-2.5 rounded-full font-bold border
  transition-all duration-200 cursor-pointer
  disabled:opacity-30 disabled:cursor-not-allowed
  active:scale-95 backdrop-blur-sm
  ${btn.colors}
`}
```

注意改为 `rounded-full`（胶囊型）。

**快捷键提示**：
```tsx
// 当前：bg-black/40 text-white/50
// 改为：bg-[var(--bg-deep)] text-[var(--text-muted)] border border-[var(--border-default)]
```

**费用标签**：
```tsx
// 当前：opacity-80
// 保持不变，颜色随父按钮
```

**确认弹出**：
```tsx
// 确认按钮保持红色实心：bg-[var(--color-danger)] text-white
// 取消按钮：text-[var(--text-muted)] hover:text-[var(--text-secondary)]
```

**游戏信息提示**（左右两侧）：
```tsx
// 当前：text-green-400/60, text-amber-400/60, text-amber-400
// 改为：text-[var(--text-muted)], text-[var(--color-gold)]/60, text-[var(--color-gold)]
```

#### 3.2 CompareSelector.tsx

适配暗色主题。所有绿色系 → CSS 变量引用。

#### 3.3 ChatPanel.tsx

**消息列表区域**：
```tsx
// 所有绿色系颜色替换为 CSS 变量
// 系统消息：text-[var(--text-muted)] italic
// 玩家消息：text-[var(--text-primary)]
// 玩家名：text-[var(--color-primary)]
// 时间戳：text-[var(--text-disabled)]
```

如果有 `AVATAR_COLORS` / `getAvatarColor()` 的本地定义，替换为从 `utils/theme` 导入。

#### 3.4 ChatInput.tsx

```tsx
// 输入框
// 当前可能有 green 系
// 改为：bg-[var(--bg-surface)] border-[var(--border-default)] text-[var(--text-primary)]
//       placeholder-[var(--text-disabled)]
//       focus:border-[var(--color-primary)]/50 focus:ring-[var(--color-primary)]/20

// 发送按钮
// 改为：bg-[var(--color-primary)]/20 hover:bg-[var(--color-primary)]/30 text-[var(--color-primary)]
```

### 验证方式

1. 在牌桌页等到轮到自己行动
2. 底部按钮为胶囊形 + 发光边框风格
3. hover 时有对应颜色的辉光效果
4. 聊天面板消息可正常显示和发送

---

## Task 4: 牌桌页 — 动画组件 + 日志

**优先级**：中
**前置依赖**：Task 0, Task 2

**设计参考图**：`docs/design-refs/game-table.jpeg`（左上角日志区域）

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/Table/GameLog.tsx` | 修改 | 行动日志暗色主题 |
| `frontend/src/components/Table/DealingAnimation.tsx` | 微调 | 发牌动画颜色适配 |
| `frontend/src/components/Table/ChipFlyAnimation.tsx` | 微调 | 筹码飞行动画适配 |
| `frontend/src/styles/cards.css` | 微调 | 牌面/牌背在深色背景上的适配 |

### 详细要求

#### 4.1 GameLog.tsx

**面板容器**：
```tsx
// 改为暗色半透明玻璃面板
className="glass-panel p-3 max-h-48 overflow-y-auto"
```

**日志条目颜色**：
- 所有绿色 → CSS 变量
- 玩家名 → `text-[var(--color-primary)]`
- 操作文字 → `text-[var(--text-secondary)]`
- 金额/筹码 → `text-[var(--color-gold)]` (JetBrains Mono 字体)
- 时间 → `text-[var(--text-disabled)]`

如果有 `ACTION_LABELS` 的本地定义，考虑提取到 `utils/theme.ts`。

如果有 `AVATAR_COLORS` 的本地定义，改为从 `utils/theme` 导入。

#### 4.2 DealingAnimation.tsx

发牌动画的核心逻辑和 Framer Motion 动画不需要修改。仅调整：
- 飞行中的牌背颜色/边框确保在深色背景上可见
- 如果有绿色相关的样式类，替换为 CSS 变量

#### 4.3 ChipFlyAnimation.tsx

筹码飞行动画主要使用绝对定位和 Framer Motion，核心逻辑不改。仅调整：
- 筹码颜色如果有绿色系，保留金色/红色/蓝色/紫色即可
- 可以给飞行中的筹码加微弱的发光拖尾效果（可选）

#### 4.4 cards.css

可能需要的微调：
- 牌面白色区域可能在纯黑背景上太突兀，加 `box-shadow: 0 2px 8px rgba(0,0,0,0.5)` 增加融合感
- 牌背可加微弱的发光边框效果
- 确保牌面翻转动画的背景透明度正确

### 验证方式

1. 左上角日志面板为暗色玻璃态
2. 发牌动画正常播放
3. 筹码飞行动画正常
4. 扑克牌在深色背景上视觉效果好

---

## Task 5: 结算页 (ResultPage) 重设计

**优先级**：高
**前置依赖**：Task 0

**设计参考图**：`docs/design-refs/result.jpeg`

> 参考图关键视觉特征：
> - "GAME OVER" 霓虹发光大标题 + 下方青→紫渐变横线
> - 3D 领奖台效果（金银铜），中间最高
> - "+250" 大字绿色盈利数字
> - 底部 AI 角色横排卡片（彩色头像 + 边框）
> - "Back to Lobby" 霓虹边框按钮

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/pages/ResultPage.tsx` | 修改 | 页面布局、标题、背景 |
| `frontend/src/components/Settlement/Leaderboard.tsx` | 修改 | 排行榜暗色主题 + 发光效果 |
| `frontend/src/components/Settlement/AgentSummaryCard.tsx` | 修改 | AI 总结卡暗色主题 |

### 详细要求

#### 5.1 ResultPage.tsx

**页面背景**：
```tsx
// 当前（多处）：bg-gradient-to-b from-green-950 via-green-900 to-green-950
// 全部改为：bg-[var(--bg-deepest)]
```

**顶部 header**：
```tsx
// 当前：bg-black/40 backdrop-blur border-b border-green-800/50
// 改为：bg-[var(--bg-deep)]/80 backdrop-blur-md border-b border-[var(--border-default)]
```

Header 内部按钮颜色替换：
```tsx
// 返回大厅：text-[var(--color-primary)]
// 再来一局按钮：霓虹边框样式（与 StartButton 类似）
// ID 文字：text-[var(--text-muted)] font-mono
```

**标题区域**（motion.div）：
```tsx
// 当前
<h1 className="text-3xl font-bold text-amber-400 mb-2">游戏结束</h1>

// 改为
<h1 className="text-4xl font-bold neon-text-primary mb-3"
    style={{ fontFamily: 'var(--font-display)' }}>
  GAME OVER
</h1>
{/* 渐变分隔线 */}
<div className="mx-auto w-48 h-[2px] bg-gradient-to-r from-transparent via-[var(--color-primary)] to-transparent mb-2" />
```

**副标题**：
```tsx
// 当前：text-green-400/60
// 改为：text-[var(--text-muted)]
```

**AI 总结报告标题**：
```tsx
// 当前：text-amber-400
// 改为：text-[var(--color-primary)] 或 text-[var(--text-primary)]
```

**底部"再来一局"按钮**：霓虹边框样式。

**加载/无数据状态**：统一替换绿色系为 CSS 变量。

#### 5.2 Leaderboard.tsx

**导入共用 theme**：
```tsx
import { getAvatarColor } from '../../utils/theme'
```
删除本文件中的 `AVATAR_COLORS` 和 `getAvatarColor()` 定义。

**排行榜标题**：
```tsx
// 当前：text-amber-400
// 改为：text-[var(--text-primary)]
```

**排名行**：
```tsx
// 第一名行
// 当前：bg-amber-500/10 border-amber-500/40 shadow-amber-500/10
// 改为：bg-[var(--color-gold)]/5 border-[var(--color-gold)]/30 shadow-[0_0_20px_rgba(255,215,0,0.1)]

// 其他行
// 当前：bg-green-900/30 border-green-700/30 hover:bg-green-900/50
// 改为：bg-[var(--bg-surface)]/30 border-[var(--border-default)] hover:bg-[var(--bg-hover)]/30
```

**RankBadge**：
```tsx
// 第一名保持金色渐变
// 第二名保持银色
// 第三名保持铜色
// 第4+：bg-[var(--bg-surface)] border-[var(--border-default)], text-[var(--text-muted)]
```

**名字颜色**：
```tsx
// 第一名：text-[var(--color-gold)]
// 其他：text-[var(--text-primary)]
```

**标签**：
```tsx
// "你" 标签：bg-[var(--color-primary)]/10 text-[var(--color-primary)] border-[var(--color-primary)]/20
// personality 标签：bg-[var(--bg-elevated)] text-[var(--text-muted)] border-[var(--border-default)]
```

**筹码变化**：
```tsx
// 正：text-[var(--color-success)]
// 负：text-[var(--color-danger)]
// 零：text-[var(--text-muted)]
```

#### 5.3 AgentSummaryCard.tsx

**导入共用 theme**：
```tsx
import { getAvatarColor } from '../../utils/theme'
```
删除本文件中的 `AVATAR_COLORS` 和 `getAvatarColor()` 定义。

**卡片容器**：
```tsx
// 当前：bg-green-900/20 border-green-700/30
// 改为：bg-[var(--bg-surface)]/20 border-[var(--border-default)] hover:border-[var(--border-hover)]
```

**CollapsibleSection**：
```tsx
// 外框：border-[var(--border-default)]
// 头部背景：bg-[var(--bg-surface)]/30 hover:bg-[var(--bg-hover)]/30
// 标题：text-[var(--text-secondary)]
// badge：bg-[var(--bg-elevated)] text-[var(--text-muted)]
// 展开箭头：text-[var(--text-muted)]
// 内容文字：text-[var(--text-secondary)]
```

**StatBar**：
```tsx
// 标签：text-[var(--text-muted)]
// 值：text-[var(--text-primary)]
```

**骨架屏 loading 状态**：
```tsx
// bg-green-800/40 → bg-[var(--bg-elevated)]/40
```

**经验回顾区域**：
```tsx
// 左边框线：border-[var(--color-gold)]/30
// 触发条件标签：text-[var(--color-gold)]/80
// 局数标签：text-[var(--text-muted)]
```

### 验证方式

1. 在结算页看到 "GAME OVER" 霓虹标题 + 渐变分隔线
2. 排行榜行有暗色主题 + 第一名有金色发光
3. AI 总结卡片在暗色背景上清晰可读
4. 折叠/展开动画正常
5. "再来一局"按钮有霓虹边框

---

## Task 6: 思维面板 (ThoughtDrawer) 重设计

**优先级**：中
**前置依赖**：Task 0

**设计参考图**：`docs/design-refs/thought-panel.jpeg`

> 参考图关键视觉特征：
> - 右侧滑出的玻璃态面板
> - 顶部有 AI 头像 + 模型名（GPT-4）
> - 三个 Tab 按钮，选中状态用青色填充
> - 垂直时间线（青色线）+ 圆形节点（内含数字 + 环形进度条）
> - 不同节点用不同颜色（青、紫、粉）

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/components/Thought/ThoughtDrawer.tsx` | 修改 | 面板容器、Tab 样式 |
| `frontend/src/components/Thought/ThoughtTimeline.tsx` | 修改 | 时间线节点重设计 |
| `frontend/src/components/Thought/ThoughtCard.tsx` | 修改 | 思考卡片暗色主题 |
| `frontend/src/components/Thought/NarrativeView.tsx` | 修改 | 叙事视图暗色主题 |

### 详细要求

#### 6.1 ThoughtDrawer.tsx — 面板容器

**导入共用 theme**：
```tsx
import { getAvatarColor } from '../../utils/theme'
```
删除本文件中的 `AVATAR_COLORS` 和 `getAvatarColor()` 定义。

**面板背景**：
```tsx
// 当前
className="fixed top-0 right-0 h-full w-[420px] max-w-[90vw] z-50
  bg-gradient-to-b from-gray-950 via-gray-900 to-gray-950
  border-l border-green-800/50 shadow-2xl
  flex flex-col"

// 改为
className="fixed top-0 right-0 h-full w-[420px] max-w-[90vw] z-50
  bg-[var(--bg-elevated)]/95 backdrop-blur-xl
  border-l border-[var(--color-primary)]/15
  shadow-[−20px_0_60px_rgba(0,212,255,0.05)]
  flex flex-col"
```

注意左边缘使用青色微弱发光边框，参照参考图。

**头部**：
```tsx
// 当前：border-green-800/40 bg-black/30
// 改为：border-[var(--border-default)] bg-[var(--bg-deep)]/50

// 标题：text-[var(--color-primary)]/80
// AI 名字：text-[var(--text-muted)]
// 关闭按钮：text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-white/5
```

**AgentTab 组件**：
```tsx
// Tab 容器：border-[var(--border-default)]
// 选中 Tab：bg-[var(--color-primary)]/15 border-[var(--color-primary)]/40
// 未选 Tab：hover:bg-white/5 border-transparent
// 选中 Tab 文字：text-[var(--color-primary)]
// 未选 Tab 文字：text-[var(--text-muted)]
```

**无内容提示**：
```tsx
// text-green-600/50 → text-[var(--text-muted)]
```

#### 6.2 ThoughtTimeline.tsx — 时间线

这是视觉变化最大的子组件。参照参考图中的垂直时间线：

**时间线线条**：
```tsx
// 垂直连接线颜色
// 当前可能是绿色系
// 改为：bg-[var(--color-primary)]/20 (细线) 或 bg-gradient-to-b from-[var(--color-primary)]/40 to-[var(--color-secondary)]/40
```

**时间线节点**（如果当前是简单的圆点，改为参考图中的环形进度风格）：
```tsx
// 每个节点：一个带数字的圆形
// 不同局数用不同颜色：
//   偶数局 → cyan (#00d4ff)
//   奇数局 → purple (#8b5cf6)
//   关键局 → pink (#ff66aa)
// 或简单地按序轮换颜色
```

可选的增强效果（如果参考图中有环形进度条）：
```tsx
// 用 SVG 圆形实现环形进度条
// 圆心数字显示局数或置信度
```

**Tab 切换**（如果时间线内部有 Tab）：
```tsx
// 决策过程 Tab → 选中态用 var(--color-primary) 背景
// 内心独白 Tab → 选中态用 var(--color-secondary) 背景
// 经验复盘 Tab → 选中态用 var(--color-accent) 背景
```

#### 6.3 ThoughtCard.tsx — 思考卡片

```tsx
// 卡片容器
// 当前可能有 green 系
// 改为：bg-[var(--bg-surface)] border-[var(--border-default)] rounded-xl

// 决策操作标签
// call → text-cyan-400
// raise → text-yellow-400
// fold → text-red-400
// compare → text-purple-400
// check_cards → text-sky-400

// 置信度条
// 进度条颜色随置信度变化：低 → 红色，中 → 黄色，高 → 青色

// 推理文字
// 改为 font-mono (JetBrains Mono)，text-[var(--text-secondary)]
```

#### 6.4 NarrativeView.tsx — 叙事视图

```tsx
// 容器背景：bg-[var(--bg-surface)]/50
// 叙事文字：text-[var(--text-secondary)] leading-relaxed
// 强调文字/引用：border-l-2 border-[var(--color-primary)]/30 pl-4
// 标题：text-[var(--text-primary)]
```

### 验证方式

1. 在牌桌页点击 AI 头像或"心路历程"按钮
2. 面板从右侧滑出，有玻璃态效果
3. Tab 切换正常，选中态有青色高亮
4. 时间线节点显示正常
5. 思考卡片内容可读

---

## 完成检查清单

所有 Task 完成后，做一次全面检查：

- [ ] 所有页面背景为深色（无残留绿色）
- [ ] 所有文字在深色背景上清晰可读
- [ ] 所有交互元素（按钮、链接、输入框）有明确的 hover/focus 视觉反馈
- [ ] 所有动画正常工作（发牌、翻牌、筹码飞行、面板滑出）
- [ ] WebSocket 连接和游戏流程不受影响（只改视觉，不改逻辑）
- [ ] 字体正确加载（Inter, Space Grotesk, JetBrains Mono, Noto Sans SC）
- [ ] 无 TypeScript 编译错误
- [ ] 无残留的 `AVATAR_COLORS` 或 `getAvatarColor()` 重复定义
- [ ] 无残留的 `green-` 系 Tailwind 类（除非是 avatar 渐变色或语义色）
- [ ] `npm run build` 能正常完成
