# 牌桌页 3D 升级计划（混合3D方案）

> **方案**：AI 生成 3D 牌桌俯视图作为背景 + 2D 交互组件叠加  
> **范围**：仅修改 GamePage 和 ActionPanel，不涉及 LobbyPage / WelcomePage / ResultPage  
> **分支**：`UI-Task2-Update1`

---

## Step 1: 安装 lucide-react 图标库

- [ ] `npm install lucide-react`
- [ ] 验证安装成功

**涉及文件**: `frontend/package.json`

---

## Step 2: 集成 3D 牌桌背景到 TableLayout

- [ ] 用 `<img>` 替换 CSS 椭圆渐变绘制的牌桌
- [ ] 图片设为 `object-fit: contain`，居中显示
- [ ] 调整座位位置算法参数（cx/cy/rx/ry）适配新背景
- [ ] 移除旧的 CSS 椭圆相关样式代码
- [ ] 确保 PotDisplay 在桌面中央正确显示

**涉及文件**: `frontend/src/components/Table/TableLayout.tsx`, `frontend/src/assets/table-bg.png`

---

## Step 3: 添加环境氛围光效

- [ ] GamePage 四角添加 CSS radial-gradient 光晕层
- [ ] 颜色对应设计稿：左上绿光、右下红光、微弱紫色点缀
- [ ] 光晕层设为 `pointer-events-none`，不影响交互

**涉及文件**: `frontend/src/pages/GamePage.tsx`

---

## Step 4: 升级 PlayerSeat 霓虹光环

- [ ] 头像尺寸从 48px 放大到 56px
- [ ] 添加 conic-gradient 霓虹光环（基于玩家颜色）
- [ ] 当前行动玩家的光环增加脉冲动画
- [ ] 简化视觉噪音：减少不必要的边框和阴影层

**涉及文件**: `frontend/src/components/Player/PlayerSeat.tsx`

---

## Step 5: 重新设计 ActionPanel 胶囊霓虹按钮

- [ ] 按钮改为胶囊形状（`rounded-full`）
- [ ] 深色半透明背景 + 青色霓虹边框
- [ ] 每个按钮左侧添加 lucide 圆形图标容器
  - 看牌 → `Eye`
  - 跟注 → `ArrowDown`
  - 加注 → `TrendingUp`
  - 弃牌 → `X`
  - 比牌 → `Swords`
- [ ] 移除原有的每按钮独立颜色背景
- [ ] 统一为参考图的暗底 + 绿色/青色霓虹风格

**涉及文件**: `frontend/src/components/Actions/ActionPanel.tsx`, `frontend/src/index.css`

---

## Step 6: GamePage 布局微调

- [ ] 简化/浮动顶部 Header 栏
- [ ] Chat 面板默认收起
- [ ] 调整 GameLog 位置避免遮挡牌桌
- [ ] 整体验证各组件在牌桌背景上的视觉效果

**涉及文件**: `frontend/src/pages/GamePage.tsx`, `frontend/src/components/Table/GameLog.tsx`

---

## 资源清单

| 资源 | 路径 | 状态 |
|------|------|------|
| 3D 牌桌背景图 | `frontend/src/assets/table-bg.png` | ✅ 已就位 |
| 参考设计图 | `docs/design-refs/game-table.jpeg` | ✅ 已有 |
| lucide-react | `package.json` | ⬜ 待安装 |
