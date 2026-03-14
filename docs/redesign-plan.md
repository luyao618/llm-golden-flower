# 前端 UI 重设计计划 — 赛博朋克科技风

> 本文档是前端 UI 重设计（T8.3）的总纲。提供全局概览和执行指南。
> 详细设计规范见 `docs/design-system.md`，详细任务列表见 `docs/frontend-redesign-tasks.md`。

---

## 1. 项目背景

**炸金花 AI** 项目当前使用"绿色赌场毡布"主题（green-700 ~ green-950 + amber 金色强调），所有颜色以 Tailwind 工具类硬编码在 30+ 个组件文件中，且没有任何主题变量或集中管理。

本次重设计将视觉风格从"绿色赌场风"全面转向 **赛博朋克科技风（Cyberpunk Tech Theme）**：深蓝黑背景、霓虹灯发光文字、多色霓虹分区、毛玻璃面板、渐变光边框。

**范围限定**：
- **只改视觉**，不改游戏逻辑、WebSocket 通信、状态管理
- **所有 UI 文字保持简体中文**
- 对应 TASKS.md 中的 T8.3

---

## 2. 设计方向

**风格关键词**：赛博朋克科技风、霓虹灯发光、毛玻璃态、渐变光边框、多色霓虹分区

### 风格基准：欢迎页 (WelcomePage)

欢迎页已实现完整的赛博朋克科技风，是后续所有页面改造的**视觉基准**。所有页面必须统一贯穿以下四个核心视觉要素：

| 核心要素 | 实现方式 | CSS 工具类/变量 |
|---------|---------|----------------|
| **霓虹灯发光文字** | 标题和关键文字带霓虹管闪烁/稳定发光效果，多层 `text-shadow` | `.neon-sign-flicker`、`.neon-sign-steady`、`.neon-text-primary`、`.neon-text-hero` |
| **毛玻璃面板** | 半透明背景 + `backdrop-filter: blur()` + 微弱边框 | `.glass-panel`、`.glass-panel-accent`、`.lobby-card-inner` |
| **渐变光边框** | 青/紫/粉/金四色流动渐变边框线，带 `animation` 位移 | `.welcome-btn::after`、`.lobby-card`、`.neon-btn-wrapper`、`.neon-border-gradient` |
| **多色霓虹分区** | 不同功能模块用不同霓虹色区分（青=主操作、紫=配置、金=筹码/金额、粉=装饰）| `--color-primary`(青)、`--color-secondary`(紫)、`--color-gold`(金)、`--color-accent`(粉) |

> **重要**：后续 Task 2~6 的改造必须以欢迎页的实际效果为视觉参考，而不仅仅是参考图。参考图用于布局参考，欢迎页用于风格参考。

**参考图**（`docs/design-refs/` 目录下 4 张 Ideogram AI 生成图）：

| 页面 | 文件名 | 关键视觉 |
|------|--------|----------|
| 大厅 | `lobby.jpeg` | 深黑背景 + 透视网格 + 玻璃态设置面板 + 霓虹标题 + 渐变边框按钮 |
| 牌桌 | `game-table.jpeg` | 深蓝灰椭圆牌桌 + 青色霓虹描边 + 彩色头像发光环 + 金色底池 |
| 结算 | `result.jpeg` | "GAME OVER" 霓虹大字 + 领奖台 + 盈亏数字 + AI 卡片横排 |
| 思维面板 | `thought-panel.jpeg` | 右侧玻璃态抽屉 + 垂直时间线 + 环形节点 + 彩色 Tab |

> 参考图中的文字是 AI 乱码，只参考视觉/布局/配色/光效。

---

## 3. 技术栈

| 技术 | 版本 | 备注 |
|------|------|------|
| React | 19 | — |
| TypeScript | 5.9 | — |
| Vite | 7 | — |
| Tailwind CSS | 4.2 | **零配置模式**：`@import "tailwindcss"` in CSS，无 `tailwind.config.js` |
| Framer Motion | 12 | 动画库 |
| Zustand | 5 | 状态管理 |
| React Router | 7 | 路由 |

**Tailwind v4 主题扩展方式**：通过 `index.css` 中的 CSS 自定义属性（`--color-primary` 等），而非传统的 `tailwind.config.js`。

---

## 4. 当前代码现状

### 问题
1. **所有颜色硬编码**：`green-700`、`amber-400`、`green-950` 等散落在 30+ 个 `.tsx` 文件中
2. **代码重复**：`AVATAR_COLORS` 数组和 `getAvatarColor()` 函数在 6 个文件中各复制一份
3. **无设计 Token**：没有 CSS 自定义属性、没有集中的主题文件
4. **无自定义字体**：使用浏览器默认字体
5. **无品牌资源**：没有 favicon（仅 Vite 默认 SVG）

### 涉及文件（30 个组件 + 2 个 CSS）

```
frontend/
├── index.html                              # Task 0: 加字体
├── src/
│   ├── index.css                           # Task 0: 加 CSS 变量 + 工具类
│   ├── utils/theme.ts                      # Task 0: 新建（共用常量）
│   ├── styles/cards.css                    # Task 4: 微调牌面
│   ├── pages/
│   │   ├── LobbyPage.tsx                   # Task 1
│   │   ├── GamePage.tsx                    # Task 2
│   │   └── ResultPage.tsx                  # Task 5
│   └── components/
│       ├── Lobby/
│       │   ├── GameConfigForm.tsx           # Task 1
│       │   ├── ChipsConfig.tsx             # Task 1
│       │   ├── StartButton.tsx             # Task 1
│       │   ├── ModelConfigPanel.tsx         # Task 1
│       │   └── CopilotConnect.tsx          # Task 1
│       ├── Table/
│       │   ├── TableLayout.tsx             # Task 2
│       │   ├── PotDisplay.tsx              # Task 2
│       │   ├── ChatPanel.tsx               # Task 3
│       │   ├── ChatInput.tsx               # Task 3
│       │   ├── GameLog.tsx                 # Task 4
│       │   ├── DealingAnimation.tsx        # Task 4
│       │   └── ChipFlyAnimation.tsx        # Task 4
│       ├── Player/
│       │   ├── PlayerSeat.tsx              # Task 2
│       │   └── ChatBubble.tsx              # Task 2
│       ├── Cards/
│       │   ├── CardFace.tsx                # Task 2 (微调)
│       │   └── CardHand.tsx                # Task 2 (微调)
│       ├── Actions/
│       │   ├── ActionPanel.tsx             # Task 3
│       │   └── CompareSelector.tsx         # Task 3
│       ├── Settlement/
│       │   ├── Leaderboard.tsx             # Task 5
│       │   └── AgentSummaryCard.tsx        # Task 5
│       └── Thought/
│           ├── ThoughtDrawer.tsx           # Task 6
│           ├── ThoughtTimeline.tsx         # Task 6
│           ├── ThoughtCard.tsx             # Task 6
│           └── NarrativeView.tsx           # Task 6
```

---

## 5. 任务概览

共 **7 个 Task**（编号 0-6），建议按以下顺序执行：

| Task | 名称 | 文件数 | 预计时长 | 依赖 |
|------|------|--------|----------|------|
| **Task 0** | 基础设施 — 设计 Token + 字体 + 共用模块 | 3 (1 新建) | 30 min | 无 |
| **Task 1** | 大厅页重设计 | 6 | 45 min | Task 0 |
| **Task 2** | 牌桌页 — 布局 + 牌桌 + 座位 | 7 | 60 min | Task 0 |
| **Task 3** | 牌桌页 — 操作面板 + 聊天 | 4 | 30 min | Task 0 + 2 |
| **Task 4** | 牌桌页 — 动画 + 日志 | 4 | 20 min | Task 0 + 2 |
| **Task 5** | 结算页重设计 | 3 | 30 min | Task 0 |
| **Task 6** | 思维面板重设计 | 4 | 30 min | Task 0 |

### 依赖关系

```
Task 0 ──┬── Task 1  (可并行)
         ├── Task 2 ──┬── Task 3  (串行)
         │            └── Task 4  (串行)
         ├── Task 5  (可并行)
         └── Task 6  (可并行)
```

**最优执行路径**（4 个并行 session）：
- Session A: Task 0 → Task 1
- Session B: Task 0 完成后 → Task 2 → Task 3
- Session C: Task 0 完成后 → Task 5
- Session D: Task 0 完成后 → Task 6
- Session E: Task 2 完成后 → Task 4

> 实际操作中建议至少串行做 Task 0，之后再并行。

---

## 6. 执行指南

### 给每个 AI Session 的指令模板

```
请先阅读以下文件了解上下文：
1. docs/design-system.md — 完整设计规范（色板、字体、效果）
2. docs/frontend-redesign-tasks.md — 找到 Task X 的详细要求

参考图在 docs/design-refs/ 目录下，请查看对应的参考图。

注意：
- 参考图中的文字内容是 AI 乱码，只参考视觉风格
- 所有 UI 文字使用简体中文
- 只改视觉样式，不改任何游戏逻辑或状态管理代码
- 使用 CSS 自定义属性（如 var(--color-primary)）而非硬编码颜色
- Tailwind v4 无 tailwind.config.js，主题通过 CSS 变量扩展

请开始执行 Task X。
```

### 每个 Task 完成后的检查

1. `npm run dev` — 页面正常加载，无控制台错误
2. 视觉符合参考图方向
3. 所有交互（按钮、输入、切换）正常工作
4. 无残留的绿色系样式
5. 建议做一次 `git commit`

### 全部完成后的终检

见 `docs/frontend-redesign-tasks.md` 底部的"完成检查清单"。

---

## 7. 关键文档索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 设计规范 | `docs/design-system.md` | 色板、字体、玻璃态、发光、间距、动画、头像等完整规范 |
| 任务详单 | `docs/frontend-redesign-tasks.md` | 7 个 Task 的逐文件、逐行修改指南 + 验证方式 |
| 参考图-大厅 | `docs/design-refs/lobby.jpeg` | Ideogram 生成的大厅页参考设计 |
| 参考图-牌桌 | `docs/design-refs/game-table.jpeg` | Ideogram 生成的牌桌页参考设计 |
| 参考图-结算 | `docs/design-refs/result.jpeg` | Ideogram 生成的结算页参考设计 |
| 参考图-思维面板 | `docs/design-refs/thought-panel.jpeg` | Ideogram 生成的思维面板参考设计 |
| 本文档 | `docs/redesign-plan.md` | 重设计总纲（你正在看的这个） |
