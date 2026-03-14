# Design System - 赛博朋克科技风 (Cyberpunk Tech Theme)

> 本文档定义了炸金花 AI 项目前端重设计的完整设计规范。
> 所有 Task 在实现时必须严格遵循本文档中的设计 Token。
>
> **风格基准**：WelcomePage（欢迎页）已完整实现赛博朋克科技风，是所有页面的视觉参考标准。
> 核心四要素：**霓虹灯发光文字**、**毛玻璃面板**、**渐变光边框**、**多色霓虹分区**。

## 设计参考图

以下 4 张 AI 生成的参考图定义了整体视觉方向：

| 页面 | 参考图 |
|------|--------|
| 大厅页 | `docs/design-refs/lobby.jpeg` |
| 牌桌页 | `docs/design-refs/game-table.jpeg` |
| 结算页 | `docs/design-refs/result.jpeg` |
| 思维面板 | `docs/design-refs/thought-panel.jpeg` |

**重要**：参考图中的文字内容是 AI 生成的乱码，不要参考文字内容，只参考视觉风格、布局结构、颜色搭配和光效。

---

## 1. 色板 (Color Palette)

### 背景层级

| Token 名 | 色值 | 用途 |
|-----------|------|------|
| `--bg-deepest` | `#06060f` | 页面最底层背景 |
| `--bg-deep` | `#0a0a1a` | 次深背景、footer/header 底色 |
| `--bg-surface` | `#12122a` | 面板/卡片背景 |
| `--bg-elevated` | `#1a1a35` | 悬浮层/弹窗/抽屉 |
| `--bg-hover` | `#222245` | 元素 hover 状态 |

### 主题色

| Token 名 | 色值 | 用途 |
|-----------|------|------|
| `--color-primary` | `#00d4ff` | 主强调色 - 按钮边框、活跃状态、主要高亮 |
| `--color-primary-soft` | `rgba(0, 212, 255, 0.15)` | 主色低透明度背景 |
| `--color-secondary` | `#8b5cf6` | 辅助色 - 装饰、次要元素、Tab、思维面板 |
| `--color-secondary-soft` | `rgba(139, 92, 246, 0.15)` | 辅助色低透明度背景 |
| `--color-accent` | `#ff66aa` | 霓虹粉 - 装饰性发光、特殊按钮边框 |
| `--color-gold` | `#ffd700` | 金色 - 筹码、金额、冠军标记 |
| `--color-gold-soft` | `rgba(255, 215, 0, 0.15)` | 金色低透明度背景 |

### 语义色

| Token 名 | 色值 | 用途 |
|-----------|------|------|
| `--color-success` | `#00ff88` | 盈利、成功 |
| `--color-danger` | `#ff4444` | 亏损、弃牌、错误 |
| `--color-warning` | `#ffaa00` | 警告、重连中 |
| `--color-info` | `#00aaff` | 信息提示 |

### 文字色

| Token 名 | 色值 | 用途 |
|-----------|------|------|
| `--text-primary` | `#f0f0f5` | 主要文字（标题、关键信息） |
| `--text-secondary` | `#a0a0c0` | 次要文字（描述、标签） |
| `--text-muted` | `#555570` | 弱化文字（提示、占位符） |
| `--text-disabled` | `#333350` | 禁用状态文字 |

### 边框色

| Token 名 | 色值 | 用途 |
|-----------|------|------|
| `--border-default` | `rgba(255, 255, 255, 0.06)` | 默认边框 |
| `--border-hover` | `rgba(0, 212, 255, 0.25)` | hover 状态边框 |
| `--border-active` | `rgba(0, 212, 255, 0.5)` | 活跃/focus 状态边框 |
| `--border-glow` | `rgba(0, 212, 255, 0.15)` | 发光边框 |

---

## 2. 字体 (Typography)

### 字体族

| Token 名 | 字体 | 用途 |
|-----------|------|------|
| `--font-display` | `'Space Grotesk', sans-serif` | 标题、大号文字、品牌文字 |
| `--font-body` | `'Inter', 'Noto Sans SC', sans-serif` | 正文、UI 标签、中文内容 |
| `--font-mono` | `'JetBrains Mono', monospace` | 数字、筹码、ID、代码、思维记录 |

### Google Fonts 引入

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### 字号规范

| 场景 | 字号 | 字重 | 字体 |
|------|------|------|------|
| 页面大标题 | 36-48px | 700 (bold) | Space Grotesk |
| 区块标题 | 20-24px | 600 (semi-bold) | Space Grotesk |
| 正文 | 14-16px | 400 (regular) | Inter |
| 小标签 | 12px | 500 (medium) | Inter |
| 极小提示 | 10px | 400 | Inter |
| 数字/金额 | 根据场景 | 600-700 | JetBrains Mono |

**注意**：禁止使用 8px 或 9px 字号，最小字号为 10px。

---

## 3. 玻璃态 (Glassmorphism)

核心视觉效果，用于面板、卡片、弹窗。

### 标准玻璃态面板

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(0, 212, 255, 0.12);
  border-radius: 16px;
  box-shadow: 
    0 0 20px rgba(0, 212, 255, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.03);
}
```

### 强调玻璃态面板（用于主面板/活跃状态）

```css
.glass-panel-accent {
  background: rgba(0, 212, 255, 0.04);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 16px;
  box-shadow: 
    0 0 30px rgba(0, 212, 255, 0.1),
    0 0 60px rgba(0, 212, 255, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}
```

---

## 4. 发光效果 (Glow Effects)

### 文字发光

```css
/* 主标题霓虹效果 */
.neon-text-primary {
  color: #00d4ff;
  text-shadow: 
    0 0 7px rgba(0, 212, 255, 0.6),
    0 0 20px rgba(0, 212, 255, 0.4),
    0 0 40px rgba(0, 212, 255, 0.2);
}

/* 金色发光 */
.neon-text-gold {
  color: #ffd700;
  text-shadow:
    0 0 7px rgba(255, 215, 0, 0.5),
    0 0 20px rgba(255, 215, 0, 0.3);
}
```

### 边框发光

```css
/* 按钮/元素 hover 发光 */
.glow-border {
  box-shadow: 0 0 15px rgba(0, 212, 255, 0.3);
}

/* 活跃元素脉冲发光 */
.glow-pulse {
  animation: glow-pulse 2s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 10px rgba(0, 212, 255, 0.2); }
  50% { box-shadow: 0 0 25px rgba(0, 212, 255, 0.5); }
}
```

### 渐变边框

```css
/* 霓虹渐变边框（用于 START GAME 按钮等） */
.neon-border-gradient {
  position: relative;
  background: var(--bg-surface);
  border-radius: 12px;
}
.neon-border-gradient::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 14px;
  background: linear-gradient(135deg, #00d4ff, #8b5cf6, #ff66aa);
  z-index: -1;
  opacity: 0.8;
  filter: blur(1px);
}
```

---

## 5. 圆角 (Border Radius)

| 元素 | 圆角 |
|------|------|
| 按钮（标准） | 8px (`rounded-lg`) |
| 按钮（胶囊型） | 9999px (`rounded-full`) |
| 卡片/面板 | 16px (`rounded-2xl`) |
| 输入框 | 10px (`rounded-[10px]`) |
| 小标签/badge | 6px (`rounded-md`) |
| 头像 | 50% (`rounded-full`) |
| 牌桌 | 50% (椭圆) |

---

## 6. 间距 (Spacing)

遵循 Tailwind 的 4px 倍数系统：

| 场景 | 间距 |
|------|------|
| 面板内边距 | 24-32px (`p-6` / `p-8`) |
| 元素间距 | 12-16px (`gap-3` / `gap-4`) |
| 紧凑间距 | 8px (`gap-2`) |
| 区块间距 | 32-40px (`space-y-8` / `space-y-10`) |

---

## 7. 动画 (Animation)

### 过渡时间

| 场景 | 时长 | 缓动 |
|------|------|------|
| hover 变色 | 200ms | `ease` |
| 面板展开/收起 | 300ms | `spring (damping: 30)` |
| 发光渐变 | 300ms | `ease-in-out` |
| 入场动画 | 400-500ms | `ease-out` |

### Framer Motion 标准动画

```tsx
// 页面入场
const pageVariants = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, ease: 'easeOut' }
}

// 卡片入场（带错开）
const staggerChildren = {
  animate: { transition: { staggerChildren: 0.1 } }
}
```

---

## 8. 头像系统 (Avatar)

### 颜色列表

统一在 `src/utils/theme.ts` 中定义，所有组件引用同一份：

```typescript
export const AVATAR_COLORS = [
  'from-rose-500 to-pink-600',
  'from-violet-500 to-purple-600',
  'from-blue-500 to-indigo-600',
  'from-cyan-500 to-teal-600',
  'from-emerald-500 to-green-600',
  'from-amber-500 to-orange-600',
]
```

### 头像发光环

- 默认：`ring-2 ring-white/10`
- 活跃玩家：`ring-2 ring-[var(--color-primary)]` + `shadow-[0_0_15px_rgba(0,212,255,0.4)]`
- 人类玩家：`ring-2 ring-[var(--color-gold)]`

---

## 9. 牌桌专用规范

### 牌桌颜色

- **毡面**：`#0d1b2a` → `#162035` 深蓝灰渐变（替换原来的 green-700/800/900）
- **边框**：1px `rgba(0, 212, 255, 0.4)` + `box-shadow: 0 0 30px rgba(0, 212, 255, 0.15)`
- **去掉**：原来的琥珀色木质外框

### 操作按钮

底部操作按钮改为暗底 + 发光边框胶囊风格：

```
背景: rgba(255, 255, 255, 0.04)
边框: 1px solid rgba(颜色, 0.3)
hover: border-color 增强 + box-shadow 发光
active: scale(0.95)
```

每个操作按钮有自己的主题色：
- 看牌: `#00aaff` (蓝)
- 跟注: `#00d4ff` (青)
- 加注: `#ffd700` (金)
- 比牌: `#8b5cf6` (紫)
- 弃牌: `#ff4444` (红)

---

## 10. 背景装饰

### 透视网格 (用于大厅页、结算页)

```css
.perspective-grid {
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  perspective: 500px;
}
```

### 径向渐变光晕 (用于牌桌页背景)

```css
.radial-glow {
  background: 
    radial-gradient(ellipse at 50% 0%, rgba(0, 212, 255, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 100%, rgba(139, 92, 246, 0.06) 0%, transparent 50%),
    var(--bg-deepest);
}
```
