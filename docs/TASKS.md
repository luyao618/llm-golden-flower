# Golden Flower Poker AI - 任务分解

> 每个任务 = 一次 vibe coding session（1-3 小时）
> 状态: `pending` | `in_progress` | `done`
> `depends_on` 标注前置依赖，无依赖的任务可并行开发

---

## Phase 1: 游戏引擎

### T1.1 项目脚手架 + 扑克牌模型
- **状态**: `done`
- **depends_on**: 无
- **内容**:
  - 创建 `backend/` 目录结构，`pyproject.toml`（FastAPI, LiteLLM, SQLAlchemy, pytest 等依赖）
  - 实现 `app/models/card.py`: `Suit`, `Rank`, `Card` 数据类
  - 实现 `app/models/game.py`: `HandType`, `HandResult`, `PlayerType`, `PlayerStatus`, `Player`, `GamePhase`, `GameAction`, `ActionRecord`, `RoundState`, `GameState`, `GameConfig`
  - 实现 `app/config.py`: 基础配置管理（AI 模型列表、游戏默认参数）
- **验收**: `import app.models.card` 和 `import app.models.game` 正常工作

### T1.2 牌型评估器 + 单元测试
- **状态**: `done`
- **depends_on**: T1.1
- **内容**:
  - 实现 `app/engine/evaluator.py`: 
    - `evaluate_hand(cards: list[Card]) -> HandResult` 
    - 支持全部 6 种牌型判定：豹子、同花顺、同花、顺子、对子、散牌
    - `compare_hands(hand_a, hand_b) -> int` 比较两手牌大小
    - 处理 A-2-3 最小顺子特殊规则
  - 实现 `app/engine/deck.py`: `Deck` 类（洗牌、发牌）
  - 编写 `tests/test_evaluator.py`: 覆盖每种牌型识别、牌型比较、边界情况（A-2-3, Q-K-A）
- **验收**: `pytest tests/test_evaluator.py` 全部通过（55 tests）

### T1.3 规则引擎（操作合法性 + 下注计算）
- **状态**: `done`
- **depends_on**: T1.1
- **内容**:
  - 实现 `app/engine/rules.py`:
    - `get_available_actions(round_state, player) -> list[GameAction]` 
    - `get_call_cost(round_state, player) -> int` 暗注/明注不同费率
    - `get_raise_cost(round_state, player) -> int`
    - `get_compare_cost(round_state, player) -> int`
    - `validate_action(round_state, player, action) -> bool`
  - 编写 `tests/test_rules.py`: 覆盖暗注/明注操作差异、筹码不足时的操作限制、比牌资格校验
- **验收**: `pytest tests/test_rules.py` 全部通过（66 tests）

### T1.4 游戏流程引擎（发牌、轮转、结算）
- **状态**: `done`
- **depends_on**: T1.2, T1.3
- **内容**:
  - 实现 `app/engine/game_manager.py`:
    - `create_game(config) -> GameState`
    - `start_round(game) -> RoundState` 收底注、发牌、确定庄家
    - `apply_action(game, player, action, target?) -> ActionResult` 执行操作、更新状态
    - `advance_turn(game)` 推进到下一个行动玩家
    - `check_round_end(game) -> bool` 判断局是否结束
    - `settle_round(game) -> RoundResult` 结算（处理弃牌胜出、比牌胜出、最大轮数强制比牌）
    - 信息隐藏：`get_visible_state(game, viewer_id)`
  - 编写 `tests/test_game_engine.py`: 模拟完整一局（发牌 → 多轮操作 → 结算）
- **验收**: `pytest tests/test_game_engine.py` 全部通过（54 tests）

---

## Phase 2: AI Agent

### T2.1 LiteLLM 集成 + BaseAgent 框架
- **状态**: `pending`
- **depends_on**: T1.1
- **内容**:
  - 实现 `app/agents/base_agent.py`:
    - `BaseAgent` 类：agent_id, name, model_id, personality, memory
    - `async call_llm(messages) -> str` 封装 LiteLLM 调用（含重试、超时、错误处理）
    - `build_system_prompt() -> str` 从性格模板构建 system prompt
    - `parse_decision_response(raw) -> Decision` JSON 解析 + 容错
  - 实现 `app/agents/agent_manager.py`: Agent 实例的创建和生命周期管理
  - 配置 LiteLLM 的多模型支持（OpenAI / Anthropic / Gemini）
- **验收**: 能通过 BaseAgent 调用至少一个 LLM API 并获得 JSON 响应

### T2.2 AI 性格系统 + Prompt 模板
- **状态**: `pending`
- **depends_on**: T2.1
- **内容**:
  - 实现 `app/agents/personalities.py`: 5 种性格定义（激进型、保守型、分析型、直觉型、诈唬型），每种包含:
    - 描述文本（用于 system prompt）
    - 行为倾向参数（aggression, bluff_tendency, talk_frequency 等）
    - 发言风格指导
  - 实现 `app/agents/prompts.py`:
    - System prompt 模板（含规则摘要 + 性格注入 + 发言指导）
    - Decision prompt 模板（含聊天上下文和经验上下文占位）
    - Bystander react prompt 模板
    - Experience review prompt 模板
    - Round narrative prompt 模板
    - Game summary prompt 模板
- **验收**: 各模板渲染正确，变量替换无遗漏

### T2.3 AI 决策流程（make_decision 完整实现）
- **状态**: `pending`
- **depends_on**: T2.1, T2.2, T1.3, T1.4
- **内容**:
  - 在 `BaseAgent` 中实现完整的 `make_decision()`:
    - 构建决策 prompt（手牌、局面、历史行动、聊天上下文、经验策略）
    - 调用 LLM
    - 解析响应为 Decision（action + thought + table_talk）
    - 验证操作合法性，非法操作降级处理
  - 实现 `Decision` 和 `ThoughtRecord` 的创建逻辑
  - 编写 `tests/test_agents.py`: mock LLM 响应，测试解析和容错
- **验收**: mock 测试通过，非法操作降级逻辑正确

### T2.4 聊天引擎（行动发言 + 旁观插嘴）
- **状态**: `pending`
- **depends_on**: T2.1, T2.2
- **内容**:
  - 实现 `app/agents/chat_engine.py`:
    - `maybe_react_as_bystander(trigger_event, chat_context, must_respond?) -> BystanderReaction | None`
    - `should_respond(trigger_event, personality) -> bool` 基于性格和事件类型计算回应概率
    - 触发规则：关键操作（大幅加注、弃牌）提高触发概率，性格影响基础概率
    - 玩家消息处理：`must_respond=True` 确保至少一个 AI 回应
  - 实现 `app/models/chat.py`: `ChatMessage`, `ChatMessageType`, `ChatContext`, `BystanderReaction`
- **验收**: 单元测试验证回应概率逻辑和 must_respond 保证

### T2.5 心路历程记录 + 叙事生成
- **状态**: `pending`
- **depends_on**: T2.3
- **内容**:
  - 实现 `app/thought/recorder.py`:
    - `ThoughtRecorder` 类：append_thought(), get_round_thoughts()
  - 实现 `app/thought/reporter.py`:
    - `generate_round_narrative(agent, round_thoughts, chat_messages, result) -> RoundNarrative` 调用 LLM 生成第一人称叙事
    - `generate_game_summary(agent, all_narratives, all_reviews, stats) -> GameSummary` 游戏结束总结
  - 实现 `app/models/thought.py`: `ThoughtRecord`, `RoundNarrative`, `GameSummary`
- **验收**: 能生成合理的叙事文本（手动调用验证）

---

## Phase 3: 经验学习系统

### T3.1 经验回顾触发 + 执行
- **状态**: `pending`
- **depends_on**: T2.3, T2.5
- **内容**:
  - 实现 `app/agents/experience.py`:
    - `ExperienceReviewer` 类
    - `check_trigger(game, round_result) -> ReviewTrigger | None` 5 种触发条件
    - `perform_review(trigger, recent_narratives, recent_thoughts, opponent_stats) -> ExperienceReview` 调用 LLM
    - `generate_strategy_context(review) -> str` 生成注入后续决策的策略摘要
  - 将经验回顾集成到 AI 回合流程中（每局第一次行动前检查）
  - 实现 `app/models/thought.py` 中的 `ExperienceReview`, `ReviewTrigger`（如未在 T2.5 中实现）
- **验收**: mock 测试验证各触发条件和策略注入逻辑

---

## Phase 4: 后端 API

### T4.1 FastAPI 搭建 + 数据库初始化
- **状态**: `pending`
- **depends_on**: T1.1
- **内容**:
  - 实现 `app/main.py`: FastAPI 应用入口，CORS 配置，路由注册
  - 实现 `app/db/database.py`: SQLite 连接、session 管理
  - 实现 `app/db/schemas.py`: SQLAlchemy ORM 模型（games, players, rounds, thought_records, chat_messages, experience_reviews, round_narratives, game_summaries — 8 张表）
  - 数据库初始化和迁移脚本
- **验收**: `uvicorn app.main:app` 能启动，数据库表创建成功

### T4.2 游戏管理 REST API
- **状态**: `pending`
- **depends_on**: T4.1, T1.4
- **内容**:
  - 实现 `app/api/game.py`:
    - `POST /api/game/create` 创建新游戏（参数：AI数量、各AI模型、筹码配置）
    - `GET /api/game/{game_id}` 获取游戏状态
    - `POST /api/game/{game_id}/start` 开始游戏
    - `POST /api/game/{game_id}/end` 结束游戏
    - `POST /api/game/{game_id}/action` 玩家执行操作
    - `GET /api/models` 获取可用 AI 模型列表
- **验收**: 用 curl/httpie 能创建游戏并获取状态

### T4.3 WebSocket + AI 回合调度
- **状态**: `pending`
- **depends_on**: T4.2, T2.3, T2.4, T3.1
- **内容**:
  - 实现 `app/api/websocket.py`:
    - WebSocket 连接管理（`WebSocketManager`）
    - 客户端事件处理（`player_action`, `chat_message`, `start_round`）
    - 服务端事件推送（全部 11 种事件类型）
  - 实现 `process_ai_turns()`: AI 回合的完整调度循环（经验回顾检查 → 决策 → 发言 → 旁观反应）
  - 实现 `handle_player_chat()`: 玩家消息处理 + AI 回应调度
- **验收**: WebSocket 连接测试，能完成一个完整的人机对弈回合

### T4.4 心路历程 + 聊天 REST API + 持久化
- **状态**: `pending`
- **depends_on**: T4.1, T2.5, T3.1
- **内容**:
  - 实现 `app/api/thought.py`:
    - `GET /api/game/{game_id}/thoughts/{agent_id}` 
    - `GET /api/game/{game_id}/thoughts/{agent_id}/round/{round_num}`
    - `GET /api/game/{game_id}/narrative/{agent_id}/round/{round_num}`
    - `GET /api/game/{game_id}/summary/{agent_id}`
    - `GET /api/game/{game_id}/reviews/{agent_id}`
  - 实现 `app/api/chat.py`:
    - `GET /api/game/{game_id}/chat`
    - `GET /api/game/{game_id}/chat/round/{round_num}`
  - 将游戏状态、心路历程、聊天记录、经验回顾写入 SQLite
- **验收**: API 返回正确的存储数据

---

## Phase 5: 前端基础

### T5.1 React 项目搭建
- **状态**: `pending`
- **depends_on**: 无
- **内容**:
  - 创建 `frontend/` 目录：Vite + React 18 + TypeScript
  - 安装依赖：Tailwind CSS, Framer Motion, Zustand, react-router-dom
  - 配置 Vite 代理到后端 API
  - 实现 `src/types/game.ts`: 前端 TypeScript 类型定义（对应后端数据模型）
  - 实现 `src/services/api.ts`: REST API 调用封装
  - 基础路由：`/` (大厅) → `/game/:id` (牌桌) → `/result/:id` (结果)
- **验收**: `npm run dev` 能启动，路由切换正常

### T5.2 游戏大厅页面
- **状态**: `pending`
- **depends_on**: T5.1
- **内容**:
  - 实现 `src/components/Lobby/`:
    - `GameConfigForm`: AI 对手数量选择 (1-5)、各 AI 的模型选择下拉菜单
    - `ChipsConfig`: 初始筹码和底注配置
    - `StartButton`: 调用 create + start API，跳转到牌桌
  - 实现 `src/stores/gameStore.ts`: 基础游戏状态 store（gameId, phase, players, createGame action）
- **验收**: 能配置并创建游戏，成功跳转到牌桌页面

### T5.3 牌桌布局 + 玩家座位
- **状态**: `pending`
- **depends_on**: T5.1
- **内容**:
  - 实现 `src/components/Table/TableLayout.tsx`: 椭圆形牌桌布局
  - 实现 `src/components/Player/PlayerSeat.tsx`: 玩家座位组件（头像、名字、筹码、状态标记）
  - 实现 `src/components/Table/PotDisplay.tsx`: 底池筹码显示
  - 实现座位的动态排列算法（2-6 人环形布局）
  - 实现 `src/stores/uiStore.ts`: UI 状态管理（动画状态、选中状态等）
- **验收**: 牌桌显示正确的玩家座位布局，筹码和状态正确渲染

### T5.4 拟物风格扑克牌组件
- **状态**: `pending`
- **depends_on**: T5.1
- **内容**:
  - 实现 `src/components/Cards/CardFace.tsx`: 单张扑克牌渲染
    - SVG 花色（♥♦♣♠）
    - 经典扑克牌布局（角落数字+花色、中央花色排列）
    - 牌背设计（CSS 渐变图案）
  - 实现 `src/components/Cards/CardHand.tsx`: 三张手牌组合展示
  - 实现 `src/styles/cards.css`: 扑克牌样式（圆角、阴影、尺寸）
  - 支持正面/背面状态切换
- **验收**: 52 张牌全部正确渲染，正反面切换正常

---

## Phase 6: 前端交互

### T6.1 WebSocket 通信 + 状态同步
- **状态**: `pending`
- **depends_on**: T5.2, T5.3, T4.3
- **内容**:
  - 实现 `src/hooks/useWebSocket.ts`: WebSocket 连接管理 Hook（连接、断线重连、消息分发）
  - 实现 `src/hooks/useGame.ts`: 游戏逻辑 Hook（整合 store 操作和 WebSocket 消息处理）
  - 更新 `gameStore.ts`: 处理全部 11 种服务端事件，更新对应状态
  - 实现客户端事件发送（player_action, chat_message, start_round）
- **验收**: 能通过 WebSocket 收到游戏状态更新并正确渲染

### T6.2 操作面板 + 玩家行动交互
- **状态**: `pending`
- **depends_on**: T6.1
- **内容**:
  - 实现 `src/components/Actions/ActionPanel.tsx`: 根据可用操作显示按钮
  - 实现各操作按钮：跟注（显示金额）、加注、看牌、弃牌、比牌
  - 实现 `src/components/Actions/CompareSelector.tsx`: 比牌时选择对手（点击对手座位或下拉菜单）
  - 操作按钮状态管理（仅在自己回合且有可用操作时可点击）
  - 操作确认后通过 WebSocket 发送事件
- **验收**: 玩家能完成一个完整的操作回合（看牌 → 跟注 → 比牌等）

### T6.3 发牌/翻牌动画
- **状态**: `pending`
- **depends_on**: T5.4, T6.1
- **内容**:
  - 使用 Framer Motion 实现发牌动画：卡牌从牌堆飞向各玩家位置
  - 实现翻牌动画：3D 翻转效果（CSS perspective + rotateY）
  - 实现看牌交互：点击自己的牌触发翻牌动画
  - AI 思考状态动画：头像旁显示思考指示器（loading dots 或类似效果）
  - 筹码变化动画：筹码飞入底池 / 飞到赢家
- **验收**: 动画流畅自然，不影响游戏操作

### T6.4 聊天面板 + 气泡
- **状态**: `pending`
- **depends_on**: T6.1
- **内容**:
  - 实现 `src/components/Table/ChatPanel.tsx`:
    - 消息列表（带头像、名字、时间戳）
    - 区分消息类型（行动发言、旁观插嘴、玩家消息、系统消息）用不同样式
    - 自动滚动到最新消息
  - 实现 `src/components/Table/ChatInput.tsx`: 玩家输入框 + 发送按钮
  - 实现 `src/components/Player/ChatBubble.tsx`: 玩家头顶气泡（短暂显示后渐隐）
  - 气泡与聊天面板消息联动
- **验收**: 聊天消息实时显示，气泡动画正常

### T6.5 行动日志 + 游戏信息显示
- **状态**: `pending`
- **depends_on**: T6.1
- **内容**:
  - 实现 `src/components/Table/GameLog.tsx`: 行动历史日志（谁做了什么操作，简洁文字格式）
  - 显示当前轮次、当前注额、底池金额
  - 显示当前行动玩家高亮（座位边框或指示箭头）
  - AI 经验回顾状态提示（"XX 正在回顾经验..."）
- **验收**: 游戏信息清晰可读，当前行动者明确标识

---

## Phase 7: 心路历程前端

### T7.1 心路历程查看器组件
- **状态**: `pending`
- **depends_on**: T6.1, T4.4
- **内容**:
  - 实现 `src/components/Thought/ThoughtDrawer.tsx`: 侧边抽屉组件（局结束后可展开）
  - 实现 `src/components/Thought/ThoughtTimeline.tsx`: 以时间线形式展示单局内每步决策的结构化思考
  - 实现 `src/components/Thought/NarrativeView.tsx`: 叙事视图（第一人称叙事文本展示）
  - 每个 AI 有独立的 tab 切换
  - 经验回顾记录也在时间线中展示（标记为"策略调整"节点）
- **验收**: 能查看每个 AI 每局的思考记录和叙事

### T7.2 游戏结束页面 + 总结报告
- **状态**: `pending`
- **depends_on**: T7.1
- **内容**:
  - 实现 `src/components/Settlement/ResultPage.tsx`: 游戏结束主页面
  - 实现 `src/components/Settlement/Leaderboard.tsx`: 最终排名（头像 + 名字 + 筹码）
  - 实现 `src/components/Settlement/AgentSummaryCard.tsx`: 每个 AI 的总结卡片
    - 统计数据（胜率、弃牌率、最大赢/输）
    - 关键时刻回顾
    - 对各对手的印象评价
    - 自我风格总结
    - 聊天策略总结 + 学习历程
  - 支持展开/折叠各部分内容
- **验收**: 游戏结束后能看到完整的排名和 AI 总结报告

---

## Phase 8: 打磨与联调

### T8.1 端到端联调
- **状态**: `pending`
- **depends_on**: T4.3, T6.2, T6.4
- **内容**:
  - 完整的端到端游戏流程测试：大厅 → 创建游戏 → 多局对弈 → 游戏结束
  - 修复前后端数据格式不匹配问题
  - 修复 WebSocket 事件遗漏或时序问题
  - 修复游戏流程中的边界情况（最大轮数、筹码归零、所有对手弃牌等）
  - 确保聊天消息时序正确（行动先于发言、旁观反应有适当间隔）
- **验收**: 能完整玩完一场 3 人游戏（1人类 + 2AI），无崩溃或卡死

### T8.2 AI 性格调优 + 聊天质量
- **状态**: `pending`
- **depends_on**: T8.1
- **内容**:
  - 调优各性格的 system prompt，确保决策风格有明显差异
  - 调优聊天 prompt，确保发言自然且符合性格（激进型爱挑衅、保守型少说话等）
  - 调整旁观插嘴的触发概率参数
  - 测试不同模型（GPT-4o, Claude, Gemini）的响应质量差异
  - 优化 LLM 响应解析的容错能力（处理各模型的 JSON 格式差异）
- **验收**: 3 种不同性格的 AI 在决策和聊天上有明显可感知的差异

### T8.3 UI/UX 优化
- **状态**: `pending`
- **depends_on**: T8.1
- **内容**:
  - 响应式布局适配（桌面端为主，适配不同窗口尺寸）
  - 操作按钮的禁用/加载状态打磨
  - 局结算界面的过渡动画
  - 颜色方案和视觉一致性检查
  - 错误提示 UI（API 超时、WebSocket 断连等用户可见的错误场景）
- **验收**: UI 在常见窗口尺寸下无布局问题，交互顺畅

### T8.4 错误处理 + 鲁棒性
- **状态**: `pending`
- **depends_on**: T8.1
- **内容**:
  - 后端：LLM API 超时/失败的全面降级处理（弃牌 + 记录异常）
  - 后端：WebSocket 异常断连后的游戏状态恢复
  - 前端：WebSocket 断线自动重连 + 状态重新同步
  - 前端：API 调用失败时的 toast 提示
  - 游戏状态持久化：确保刷新浏览器后能恢复进行中的游戏
- **验收**: 模拟网络断连和 API 超时场景，游戏能恢复正常

---

## 依赖关系总览

```
T1.1 ──┬── T1.2 ──┐
       ├── T1.3 ──┼── T1.4
       ├── T2.1 ──┤
       └── T4.1   │
                   │
T2.1 ──┬── T2.2 ──┤
       ├── T2.4   │
       └──────────┼── T2.3 ── T2.5 ── T3.1
                   │
T4.1 ──── T4.2 ───┼──────────────────── T4.3
                   │                      │
T4.1 ──────────── T4.4                   │
                                          │
T5.1 ──┬── T5.2 ──┐                      │
       ├── T5.3 ──┼── T6.1 ─┬── T6.2 ───┼── T8.1 ──┬── T8.2
       └── T5.4 ──┘         ├── T6.3     │          ├── T8.3
                             ├── T6.4 ───┘          └── T8.4
                             └── T6.5
                             │
                             └── T7.1 ── T7.2
```

**可并行的关键路径**:
- **后端路径**: T1.1 → T1.2/T1.3 → T1.4 → T4.2 → T4.3
- **AI 路径**: T1.1 → T2.1 → T2.2/T2.4 → T2.3 → T2.5 → T3.1
- **前端路径**: T5.1 → T5.2/T5.3/T5.4 → T6.x
- T5.x 系列与 T1.x/T2.x 完全独立，可从项目开始就并行开发

---

## 进度统计

| 阶段 | 任务数 | 完成数 | 状态 |
|------|--------|--------|------|
| Phase 1: 游戏引擎 | 4 | 1 | 进行中 |
| Phase 2: AI Agent | 5 | 0 | 未开始 |
| Phase 3: 经验学习 | 1 | 0 | 未开始 |
| Phase 4: 后端 API | 4 | 0 | 未开始 |
| Phase 5: 前端基础 | 4 | 0 | 未开始 |
| Phase 6: 前端交互 | 5 | 0 | 未开始 |
| Phase 7: 心路历程前端 | 2 | 0 | 未开始 |
| Phase 8: 打磨联调 | 4 | 0 | 未开始 |
| **总计** | **29** | **1** | **进行中** |
