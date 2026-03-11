# Golden Flower Poker AI - 技术设计文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   Browser (React)                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ 游戏大厅  │  │ 牌桌 UI  │  │  心路历程查看器   │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
│                      │ WebSocket + REST              │
└──────────────────────┼──────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────┐
│              FastAPI Backend (Python)                │
│  ┌──────────────────────────────────────────────┐   │
│  │              Game Engine (核心)               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │   │
│  │  │ 发牌系统 │ │ 规则引擎 │ │  结算系统    │  │   │
│  │  └──────────┘ └──────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │            AI Agent Manager                  │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │   │
│  │  │ Agent 1 │ │ Agent 2 │ │ Agent N │  ...    │   │
│  │  │(OpenAI) │ │(Claude) │ │(Gemini) │        │   │
│  │  └─────────┘ └─────────┘ └─────────┘        │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │          Thought Recorder (心路历程)          │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │              WebSocket Manager               │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
     ┌─────┴─────┐ ┌───┴───┐ ┌────┴────┐
     │  OpenAI   │ │Claude │ │ Gemini  │
     │   API     │ │  API  │ │   API   │
     └───────────┘ └───────┘ └─────────┘
```

### 1.1 技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | React 18 + TypeScript | SPA 单页应用 |
| 构建工具 | Vite | 快速开发体验 |
| UI 组件 | Tailwind CSS + 自定义组件 | 灵活的样式控制 |
| 动画 | Framer Motion | 翻牌、发牌动画 |
| 状态管理 | Zustand | 轻量级，适合游戏状态 |
| 通信 | WebSocket + REST API | 实时状态推送 + 常规请求 |
| 后端框架 | FastAPI (Python 3.11+) | 异步支持好，WebSocket 内置 |
| AI 集成 | LiteLLM | 统一多模型 API 调用 |
| 数据存储 | SQLite | 轻量级，游戏状态持久化 |
| ORM | SQLAlchemy | 数据库操作 |

### 1.2 为什么选择这些技术

- **LiteLLM**: 统一了 OpenAI / Anthropic / Gemini 等多家模型的调用接口，新增模型只需配置无需改代码
- **Zustand**: 比 Redux 轻量得多，API 简洁，游戏状态管理足够用
- **SQLite**: 单用户场景无需 PostgreSQL，部署简单，零配置
- **WebSocket**: 游戏状态变化需要实时推送到前端，HTTP 轮询太浪费

---

## 2. 目录结构

```
Golden_Flower_Poker_AI/
├── docs/
│   ├── PRD.md                    # 需求文档
│   └── TECH_DESIGN.md            # 技术设计文档（本文件）
├── backend/
│   ├── pyproject.toml            # Python 项目配置
│   ├── app/
│   │   ├── main.py               # FastAPI 入口
│   │   ├── config.py             # 配置管理
│   │   ├── models/               # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── card.py           # 扑克牌模型
│   │   │   ├── player.py         # 玩家模型
│   │   │   ├── game.py           # 游戏状态模型
│   │   │   ├── chat.py           # 聊天消息模型
│   │   │   └── thought.py        # 心路历程模型
│   │   ├── engine/               # 游戏引擎
│   │   │   ├── __init__.py
│   │   │   ├── deck.py           # 牌组管理
│   │   │   ├── evaluator.py      # 牌型评估
│   │   │   ├── game_manager.py   # 游戏流程控制
│   │   │   └── rules.py          # 规则判定
│   │   ├── agents/               # AI Agent
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py     # Agent 基类
│   │   │   ├── agent_manager.py  # Agent 生命周期管理
│   │   │   ├── chat_engine.py    # 聊天引擎（发言/回应逻辑）
│   │   │   ├── experience.py     # 经验回顾系统
│   │   │   ├── personalities.py  # 性格预设
│   │   │   └── prompts.py        # Prompt 模板
│   │   ├── thought/              # 心路历程
│   │   │   ├── __init__.py
│   │   │   ├── recorder.py       # 记录器
│   │   │   └── reporter.py       # 报告生成器
│   │   ├── api/                  # API 路由
│   │   │   ├── __init__.py
│   │   │   ├── game.py           # 游戏相关接口
│   │   │   ├── chat.py           # 聊天相关接口
│   │   │   ├── thought.py        # 心路历程接口
│   │   │   └── websocket.py      # WebSocket 处理
│   │   └── db/                   # 数据库
│   │       ├── __init__.py
│   │       ├── database.py       # 数据库连接
│   │       └── schemas.py        # SQLAlchemy 模型
│   └── tests/
│       ├── test_evaluator.py
│       ├── test_game_engine.py
│       └── test_agents.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── index.html
│   ├── public/
│   │   └── cards/                # 扑克牌图片资源
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── stores/               # Zustand 状态管理
│       │   ├── gameStore.ts      # 游戏状态
│       │   └── uiStore.ts        # UI 状态
│       ├── components/           # React 组件
│       │   ├── Lobby/            # 大厅
│       │   ├── Table/            # 牌桌
│       │   ├── Cards/            # 扑克牌
│       │   ├── Player/           # 玩家位
│       │   ├── Actions/          # 操作按钮
│       │   ├── Thought/          # 心路历程查看器
│       │   └── Settlement/       # 结算界面
│       ├── hooks/                # 自定义 Hooks
│       │   ├── useWebSocket.ts
│       │   └── useGame.ts
│       ├── services/             # API 调用
│       │   └── api.ts
│       ├── types/                # TypeScript 类型
│       │   └── game.ts
│       └── styles/               # 样式
│           └── cards.css         # 扑克牌样式
└── docker-compose.yml            # 可选的容器化部署
```

---

## 3. 数据模型

### 3.1 核心模型

```python
# ---- Card 扑克牌 ----
class Suit(Enum):
    HEARTS = "hearts"       # 红心 ♥
    DIAMONDS = "diamonds"   # 方块 ♦
    CLUBS = "clubs"         # 梅花 ♣
    SPADES = "spades"       # 黑桃 ♠

class Rank(Enum):
    TWO = 2
    THREE = 3
    # ... 
    KING = 13
    ACE = 14

class Card:
    suit: Suit
    rank: Rank

# ---- HandType 牌型 ----
class HandType(Enum):
    HIGH_CARD = 1       # 散牌
    PAIR = 2            # 对子
    STRAIGHT = 3        # 顺子
    FLUSH = 4           # 同花
    STRAIGHT_FLUSH = 5  # 同花顺
    THREE_OF_A_KIND = 6 # 豹子

class HandResult:
    hand_type: HandType
    ranks: list[Rank]           # 用于同牌型比较的排序后点数
    description: str            # 人类可读描述，如 "一对K"

# ---- Player 玩家 ----
class PlayerType(Enum):
    HUMAN = "human"
    AI = "ai"

class PlayerStatus(Enum):
    ACTIVE_BLIND = "active_blind"   # 未看牌（暗注）
    ACTIVE_SEEN = "active_seen"     # 已看牌（明注）
    FOLDED = "folded"               # 已弃牌
    OUT = "out"                     # 筹码用完，出局

class Player:
    id: str
    name: str
    avatar: str
    player_type: PlayerType
    chips: int
    status: PlayerStatus
    hand: list[Card] | None         # 手牌（对前端隐藏AI的牌）
    total_bet_this_round: int       # 本局累计下注
    model_id: str | None            # AI 使用的模型标识

# ---- Game 游戏状态 ----
class GamePhase(Enum):
    WAITING = "waiting"             # 等待开始
    DEALING = "dealing"             # 发牌中
    BETTING = "betting"             # 下注阶段
    COMPARING = "comparing"         # 比牌中
    SETTLEMENT = "settlement"       # 结算中
    GAME_OVER = "game_over"         # 游戏结束

class GameAction(Enum):
    FOLD = "fold"                   # 弃牌
    CALL = "call"                   # 跟注
    RAISE = "raise"                 # 加注
    CHECK_CARDS = "check_cards"     # 看牌
    COMPARE = "compare"             # 比牌

class ActionRecord:
    player_id: str
    action: GameAction
    amount: int | None              # 下注金额
    target_id: str | None           # 比牌对象
    timestamp: float

class RoundState:
    round_number: int               # 当前是第几局
    pot: int                        # 底池
    current_bet: int                # 当前注额基数
    dealer_index: int               # 庄家位置
    current_player_index: int       # 当前行动玩家
    actions: list[ActionRecord]     # 本局行动历史
    phase: GamePhase
    turn_count: int                 # 当前轮次（一圈为一轮）
    max_turns: int                  # 最大轮次

class GameState:
    game_id: str
    players: list[Player]
    current_round: RoundState | None
    round_history: list[RoundResult]  # 历史局结果
    config: GameConfig

class GameConfig:
    initial_chips: int = 1000
    ante: int = 10
    max_bet: int = 200
    max_turns: int = 10             # 每局最大轮数
```

### 3.2 聊天模型

```python
class ChatMessageType(Enum):
    ACTION_TALK = "action_talk"       # 操作时附带的发言
    BYSTANDER_TALK = "bystander_talk" # 旁观时插嘴
    PLAYER_MESSAGE = "player_message" # 人类玩家发言
    SYSTEM_MESSAGE = "system_message" # 系统消息

class ChatMessage:
    id: str
    game_id: str
    round_number: int
    sender_id: str                    # 发送者 player_id
    sender_name: str
    message_type: ChatMessageType
    content: str                      # 发言内容
    related_action: GameAction | None # 关联的游戏操作（如有）
    timestamp: float

class ChatContext:
    """传递给 AI 决策的聊天上下文"""
    recent_messages: list[ChatMessage]  # 本局最近的聊天记录
    player_message_pending: str | None  # 人类玩家刚刚说的话（需要回应）
```

### 3.3 经验学习模型

```python
class ReviewTrigger(Enum):
    CONSECUTIVE_LOSSES = "consecutive_losses"   # 连续输牌 (>=2局)
    BIG_LOSS = "big_loss"                       # 单局大额损失 (>20%初始筹码)
    PERIODIC = "periodic"                       # 定期回顾 (每5局)
    CHIP_CRISIS = "chip_crisis"                 # 筹码危机 (<30%初始值)
    OPPONENT_SHIFT = "opponent_shift"           # 对手行为突变

class ExperienceReview:
    """经验回顾记录"""
    agent_id: str
    game_id: str
    trigger: ReviewTrigger
    triggered_at_round: int               # 在第几局前触发
    rounds_reviewed: list[int]            # 回顾了哪几局
    
    # AI 的回顾输出
    self_analysis: str                    # 自我分析
    opponent_patterns: dict[str, str]     # 对各对手的行为模式总结
    strategy_adjustment: str              # 策略调整方向
    confidence_shift: float               # 信心变化 (-1 到 1)
    
    # 生成的策略注入 prompt
    strategy_context: str                 # 注入后续决策的策略摘要
```

### 3.4 AI 心路历程模型

```python
class ThoughtRecord:
    """单次决策的思考记录"""
    agent_id: str
    round_number: int
    turn_number: int
    
    # 结构化数据
    hand_evaluation: str            # 手牌评估
    opponent_analysis: str          # 对手分析
    risk_assessment: str            # 风险评估
    chat_analysis: str | None       # 对近期聊天内容的分析（"他说他很自信，但我觉得……"）
    decision: GameAction            # 最终决策
    decision_target: str | None     # 比牌对象（如有）
    reasoning: str                  # 决策理由
    confidence: float               # 信心值 0-1
    emotion: str                    # 情绪标签
    table_talk: str | None          # 操作时附带的发言（可为空 = 沉默）
    
    # 原始 LLM 输出
    raw_response: str

class RoundNarrative:
    """单局叙事总结"""
    agent_id: str
    round_number: int
    narrative: str                  # 第一人称叙事
    outcome: str                    # 本局结果

class GameSummary:
    """整场游戏总结"""
    agent_id: str
    
    # 统计数据
    rounds_played: int
    rounds_won: int
    total_chips_won: int
    total_chips_lost: int
    biggest_win: int
    biggest_loss: int
    fold_rate: float
    bluff_count: int
    
    # 叙事报告
    key_moments: list[str]          # 关键时刻回顾
    opponent_impressions: dict[str, str]  # 对各对手的印象
    self_reflection: str            # 自我风格总结
    chat_strategy_summary: str      # 聊天策略总结（"我主要用施压策略，对玩家A效果不错"）
    learning_journey: str           # 学习历程总结（"第7局后我意识到需要更大胆……"）
    narrative_summary: str          # 完整叙事总结
```

---

## 4. AI Agent 设计

### 4.1 Agent 架构

```
┌───────────────────────────────────────────────┐
│                  BaseAgent                    │
│  ┌─────────────────────────────────────────┐  │
│  │         Personality Profile             │  │
│  │  (性格特征 → System Prompt)             │  │
│  │  (影响发言风格和发言频率)                │  │
│  └─────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────┐  │
│  │          Memory (上下文)                 │  │
│  │  - 手牌信息                             │  │
│  │  - 历史行动                             │  │
│  │  - 对手画像                             │  │
│  │  - 筹码变化                             │  │
│  │  - 聊天记录 (本局牌桌对话)              │  │
│  │  - 经验回顾结论 (策略调整摘要)          │  │
│  └─────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────┐  │
│  │       Decision Engine (决策)             │  │
│  │  1. 检查是否触发经验回顾                │  │
│  │  2. 构建 prompt (含聊天上下文+经验)     │  │
│  │  3. 调用 LLM API                        │  │
│  │  4. 解析: 行动 + 心路历程 + 发言        │  │
│  │  5. 验证行动合法性                      │  │
│  │  6. 记录心路历程 + 发送聊天消息         │  │
│  └─────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────┐  │
│  │       Chat Engine (聊天)                 │  │
│  │  - generate_action_talk() 操作时发言     │  │
│  │  - generate_bystander_talk() 旁观插嘴   │  │
│  │  - should_respond() 判断是否需要回应     │  │
│  └─────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────┐  │
│  │    Experience Reviewer (经验回顾)        │  │
│  │  - check_trigger() 检查触发条件         │  │
│  │  - review_past_rounds() 回顾历史局      │  │
│  │  - generate_strategy_context() 生成策略  │  │
│  └─────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────┐  │
│  │      Thought Journal (心路日志)          │  │
│  │  - append_thought(ThoughtRecord)        │  │
│  │  - generate_round_narrative()           │  │
│  │  - generate_game_summary()              │  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

### 4.2 Prompt 设计

#### System Prompt 模板

```
你是一个正在玩炸金花（三张牌扑克）的玩家。

## 你的身份
- 名字: {agent_name}
- 性格: {personality_description}

## 炸金花规则摘要
{rules_summary}

## 你的决策原则
- 根据你的性格特征做出符合角色的决策
- 仔细分析对手的行为模式
- 权衡风险与收益
- 记录你的真实想法

## 牌桌交流
- 你可以在做出操作时说一句话（也可以选择沉默）
- 你的发言应该符合你的性格特征
- 你可以利用言语来施压、虚张声势、试探对手、回应挑衅
- 注意：你说的话对手能看到，不要泄露自己的真实策略
- 牌桌上的对话也是博弈的一部分，对手的话可能是真话也可能是烟雾弹

## 输出格式
你必须以 JSON 格式输出，包含以下字段:
{output_schema}
```

#### Decision Prompt 模板

```
## 当前局面

你的手牌: {hand_description}（你已{seen_status}）
底池: {pot} 筹码
你的筹码: {your_chips}
当前注额: {current_bet}

## 各玩家状态
{players_status_table}

## 本局行动历史
{action_history}

## 本局牌桌聊天
{chat_history}

{experience_context}

## 你的可用操作
{available_actions}

请做出你的决策，记录你的心路历程，并决定是否要说点什么。
```

#### Bystander React Prompt（旁观插嘴）

当非自己回合时，AI 被触发回应：

```
## 当前情况

{trigger_event_description}
（例如: "玩家A刚刚加注到 80 筹码"）
（例如: "玩家B说: '你们谁敢跟我比牌？'"）

## 最近的聊天记录
{recent_chat}

## 你的当前状态
- 手牌状态: {seen_status}
- 筹码: {your_chips}
- 你在这一局的表现: {your_actions_so_far}

你可以选择回应，也可以选择沉默。
如果回应，请符合你的性格。简短有力，一两句话即可。

输出格式:
{
    "should_respond": true/false,
    "message": "你的回应内容（如果 should_respond 为 true）",
    "inner_thought": "你的内心真实想法（不会公开）"
}
```

#### Experience Review Prompt（经验回顾）

```
## 经验回顾

你刚刚经历了几局不太顺利的牌局，现在花点时间回顾一下。

### 触发原因
{trigger_reason}

### 最近几局的回顾
{past_rounds_narratives}

### 你的统计数据
- 最近 {n} 局胜率: {win_rate}
- 筹码变化: {chips_change}
- 弃牌率: {fold_rate}

### 各对手的近期行为
{opponent_recent_behaviors}

请分析你的表现，找出问题，并制定调整策略。

输出格式:
{
    "self_analysis": "对自己近期表现的分析",
    "opponent_patterns": {
        "player_id": "对该对手行为模式的总结"
    },
    "strategy_adjustment": "接下来的策略调整方向",
    "confidence_shift": 0.1  // -1到1，正数表示更自信
}
```

### 4.3 LLM 响应解析

AI 的响应需要被解析为结构化的决策 + 心路历程：

```python
# 期望的 LLM JSON 输出格式
{
    "action": "call",                           # 必须是合法操作之一
    "target": null,                             # 比牌时指定对手
    "table_talk": "哦？你加注了？那我就跟着看看", # 可选，null 表示沉默
    "thought": {
        "hand_evaluation": "一对9，中等偏下的牌力",
        "opponent_analysis": "小明连续两轮加注，可能有大牌或在诈唬",
        "chat_analysis": "小明刚才说'你们小心点'，语气很自信，但他之前诈唬过，不一定可信",
        "risk_assessment": "底池已有 120，跟注只需 20，赔率不错",
        "reasoning": "虽然牌力一般，但底池赔率值得一跟。小明的话可能是虚张声势",
        "confidence": 0.45,
        "emotion": "忐忑"
    }
}
```

**容错处理**:
- LLM 返回非 JSON 时，尝试从文本中提取关键信息
- 返回非法操作时，降级为最安全的合法操作（跟注或弃牌）
- API 超时时，自动弃牌并记录异常
- 设置 3 次重试，重试失败则默认弃牌

### 4.4 多模型支持 (via LiteLLM)

```python
# 配置示例
AI_MODELS = {
    "openai-gpt4": {
        "model": "gpt-4o",
        "display_name": "GPT-4o",
        "provider": "openai",
    },
    "anthropic-claude": {
        "model": "claude-sonnet-4-20250514",
        "display_name": "Claude Sonnet",
        "provider": "anthropic",
    },
    "google-gemini": {
        "model": "gemini/gemini-2.0-flash",
        "display_name": "Gemini 2.0 Flash",
        "provider": "google",
    },
}

# 统一调用接口 (使用 litellm)
async def call_llm(model_id: str, messages: list[dict]) -> str:
    config = AI_MODELS[model_id]
    response = await litellm.acompletion(
        model=config["model"],
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    return response.choices[0].message.content
```

---

## 5. API 设计

### 5.1 REST API

#### 游戏管理

```
POST   /api/game/create          创建新游戏
GET    /api/game/{game_id}       获取游戏状态
POST   /api/game/{game_id}/start 开始游戏（开始第一局）
POST   /api/game/{game_id}/end   结束游戏
```

#### 玩家操作

```
POST   /api/game/{game_id}/action    玩家执行操作
```

#### 心路历程

```
GET    /api/game/{game_id}/thoughts/{agent_id}                   获取某AI的所有思考记录
GET    /api/game/{game_id}/thoughts/{agent_id}/round/{round_num} 获取某AI某局的思考记录
GET    /api/game/{game_id}/narrative/{agent_id}/round/{round_num} 获取某AI某局的叙事
GET    /api/game/{game_id}/summary/{agent_id}                    获取某AI的游戏总结
GET    /api/game/{game_id}/reviews/{agent_id}                    获取某AI的所有经验回顾记录
```

#### 聊天

```
GET    /api/game/{game_id}/chat                                  获取聊天历史
GET    /api/game/{game_id}/chat/round/{round_num}                获取某局聊天历史
```

#### 配置

```
GET    /api/models                获取可用的 AI 模型列表
```

### 5.2 WebSocket 协议

**连接**: `ws://localhost:8000/ws/{game_id}`

#### 服务端推送事件

```typescript
// 事件类型定义
type ServerEvent =
  | { type: "game_started"; data: GameState }
  | { type: "round_started"; data: { round_number: number; dealer: string } }
  | { type: "cards_dealt"; data: { your_cards: Card[] } }
  | { type: "turn_changed"; data: { current_player: string; available_actions: Action[] } }
  | { type: "player_acted"; data: { player_id: string; action: ActionRecord } }
  | { type: "chat_message"; data: ChatMessage }
  | { type: "round_ended"; data: RoundResult }
  | { type: "game_ended"; data: GameResult }
  | { type: "ai_thinking"; data: { player_id: string } }
  | { type: "ai_reviewing"; data: { player_id: string; trigger: string } }
  | { type: "error"; data: { message: string } }
```

#### 客户端发送事件

```typescript
type ClientEvent =
  | { type: "player_action"; data: { action: GameAction; target?: string } }
  | { type: "chat_message"; data: { content: string } }
  | { type: "start_round" }
```

---

## 6. 前端组件设计

### 6.1 页面结构

```
App
├── LobbyPage                    # 游戏大厅
│   ├── GameConfigForm            # 游戏配置表单
│   │   ├── PlayerCountSelector   # 对手数量选择
│   │   ├── ModelSelector         # 每个 AI 的模型选择
│   │   └── ChipsConfig          # 筹码配置
│   └── StartButton
│
├── TablePage                    # 牌桌主页面
│   ├── TableLayout              # 牌桌布局（椭圆形）
│   │   ├── PotDisplay           # 底池显示
│   │   └── PlayerSeat × N      # 玩家座位
│   │       ├── Avatar           # 头像
│   │       ├── PlayerInfo       # 名字、筹码
│   │       ├── CardHand         # 手牌（3张）
│   │       │   └── CardFace     # 单张扑克牌
│   │       ├── StatusBadge      # 状态标记
│   │       └── ChatBubble       # 玩家头顶的聊天气泡
│   ├── ActionPanel              # 操作面板
│   │   ├── ActionButton × N     # 操作按钮
│   │   └── CompareSelector      # 比牌对手选择
│   ├── ChatPanel                # 聊天面板
│   │   ├── ChatMessageList      # 消息列表
│   │   │   └── ChatMessageItem  # 单条消息（头像+名字+内容）
│   │   └── ChatInput            # 玩家输入框
│   ├── GameLog                  # 行动日志
│   └── ThoughtDrawer            # 心路历程侧边栏
│       ├── ThoughtTimeline      # 思考时间线
│       └── NarrativeView        # 叙事视图
│
└── ResultPage                   # 游戏结束页面
    ├── Leaderboard              # 排名榜
    ├── ChipsChart               # 筹码变化图（P1）
    └── AgentSummaryCard × N     # 每个AI的总结卡片
```

### 6.2 状态管理 (Zustand Store)

```typescript
interface GameStore {
  // 游戏状态
  gameId: string | null;
  phase: GamePhase;
  players: Player[];
  currentRound: RoundState | null;
  myCards: Card[];
  
  // 聊天
  chatMessages: ChatMessage[];
  
  // 操作
  createGame: (config: GameConfig) => Promise<void>;
  performAction: (action: GameAction, target?: string) => Promise<void>;
  sendChatMessage: (content: string) => void;
  
  // WebSocket
  connect: (gameId: string) => void;
  disconnect: () => void;
}
```

### 6.3 扑克牌渲染

使用 CSS 实现拟物风格扑克牌：
- 牌面使用 SVG 花色 + CSS 布局实现经典扑克牌样式
- 牌背使用 CSS 渐变图案
- 翻牌动画使用 CSS 3D transform + Framer Motion
- 发牌动画：从牌堆飞向各玩家位置

---

## 7. 游戏流程时序图

### 7.1 单局完整流程（含聊天和经验回顾）

```
Browser                FastAPI              AI Agent           LLM API
  │                      │                     │                  │
  │  start_round         │                     │                  │
  │─────────────────────>│                     │                  │
  │                      │                     │                  │
  │                      │  check_review()     │                  │
  │                      │────────────────────>│                  │
  │                      │  [如果触发经验回顾]  │  review prompt   │
  │  ai_reviewing        │                     │─────────────────>│
  │<─────────────────────│                     │  strategy adj.   │
  │                      │                     │<─────────────────│
  │                      │  strategy_context   │                  │
  │                      │<────────────────────│                  │
  │                      │                     │                  │
  │                      │  shuffle & deal     │                  │
  │  cards_dealt(cards)  │                     │                  │
  │<─────────────────────│                     │                  │
  │                      │                     │                  │
  │  turn_changed(you)   │                     │                  │
  │<─────────────────────│                     │                  │
  │                      │                     │                  │
  │  chat_msg("加油!")   │                     │                  │
  │─────────────────────>│  [保存+广播]        │                  │
  │  chat_message        │                     │                  │
  │<─────────────────────│  react_bystander()  │                  │
  │                      │────────────────────>│  bystander prompt│
  │                      │                     │─────────────────>│
  │                      │                     │  response        │
  │                      │                     │<─────────────────│
  │  chat_message(AI回应)│                     │                  │
  │<─────────────────────│                     │                  │
  │                      │                     │                  │
  │  player_action(call) │                     │                  │
  │─────────────────────>│                     │                  │
  │  player_acted        │                     │                  │
  │<─────────────────────│                     │                  │
  │                      │                     │                  │
  │  ai_thinking(agent1) │                     │                  │
  │<─────────────────────│  make_decision()    │                  │
  │                      │  (含chat_context    │  decision prompt │
  │                      │   + strategy_ctx)   │─────────────────>│
  │                      │────────────────────>│  action+talk+    │
  │                      │                     │  thought         │
  │                      │                     │<─────────────────│
  │                      │  action + thought   │                  │
  │                      │  + table_talk       │                  │
  │                      │<────────────────────│                  │
  │  player_acted        │                     │                  │
  │<─────────────────────│                     │                  │
  │  chat_message(发言)  │                     │                  │
  │<─────────────────────│                     │                  │
  │                      │                     │                  │
  │                      │  [其他AI旁观反应]    │                  │
  │  chat_message(插嘴)  │  react_bystander()  │                  │
  │<─────────────────────│────────────────────>│                  │
  │                      │                     │                  │
  │  ... (继续轮转) ...   │                     │                  │
  │                      │                     │                  │
  │  round_ended(result) │                     │                  │
  │<─────────────────────│  gen_narrative()    │  narrative prompt│
  │                      │────────────────────>│─────────────────>│
  │                      │                     │<─────────────────│
  │                      │<────────────────────│                  │
```

---

## 8. 关键实现细节

### 8.1 信息隐藏

这是游戏公平性的核心：

```python
def get_visible_state(game: GameState, viewer_id: str) -> dict:
    """根据观察者身份过滤游戏状态"""
    state = game.model_dump()
    for player in state["players"]:
        if player["id"] != viewer_id:
            # 其他玩家的手牌对当前查看者不可见
            player["hand"] = None
    return state
```

- 前端永远不会收到其他玩家的手牌数据
- 只有在比牌或局结束亮牌时才发送
- AI Agent 也只能看到自己的手牌

### 8.2 操作合法性校验

```python
def get_available_actions(game: RoundState, player: Player) -> list[GameAction]:
    """获取当前玩家可用的操作"""
    actions = [GameAction.FOLD]  # 弃牌永远可用
    
    if player.status == PlayerStatus.ACTIVE_BLIND:
        actions.extend([GameAction.CALL, GameAction.RAISE, GameAction.CHECK_CARDS])
    elif player.status == PlayerStatus.ACTIVE_SEEN:
        actions.extend([GameAction.CALL, GameAction.RAISE])
        # 只有已看牌的玩家可以发起比牌
        if count_active_players(game) >= 2:
            actions.append(GameAction.COMPARE)
    
    # 筹码不足时不能加注
    if player.chips < get_raise_cost(game, player):
        actions = [a for a in actions if a != GameAction.RAISE]
    
    return actions
```

### 8.3 AI 决策的并发控制

多个 AI 的决策是顺序执行的（遵循轮转顺序），但 API 调用本身是异步的：

```python
async def process_ai_turns(game: GameState):
    """处理所有连续的 AI 回合"""
    while is_ai_turn(game):
        current_player = get_current_player(game)
        agent = agent_manager.get_agent(current_player.id)
        
        # 1. 检查是否需要经验回顾（仅在每局第一次行动前）
        if is_first_action_this_round(game, current_player):
            review = await agent.check_and_review(game)
            if review:
                await ws_manager.broadcast(game.game_id, {
                    "type": "ai_reviewing",
                    "data": {"player_id": current_player.id, "trigger": review.trigger}
                })
        
        # 2. 通知前端 AI 正在思考
        await ws_manager.broadcast(game.game_id, {
            "type": "ai_thinking",
            "data": {"player_id": current_player.id}
        })
        
        # 3. AI 决策（含聊天上下文 + 经验策略）
        decision = await agent.make_decision(
            game_state=get_visible_state(game, current_player.id),
            chat_context=get_chat_context(game),
            strategy_context=agent.get_strategy_context(),
        )
        
        # 4. 执行决策
        apply_action(game, current_player, decision.action, decision.target)
        
        # 5. 广播行动结果
        await ws_manager.broadcast(game.game_id, {
            "type": "player_acted",
            "data": format_action_record(current_player, decision)
        })
        
        # 6. 如果 AI 有话要说，发送聊天消息
        if decision.table_talk:
            chat_msg = ChatMessage(
                sender_id=current_player.id,
                sender_name=current_player.name,
                message_type=ChatMessageType.ACTION_TALK,
                content=decision.table_talk,
                related_action=decision.action,
            )
            save_chat_message(game.game_id, chat_msg)
            await ws_manager.broadcast(game.game_id, {
                "type": "chat_message",
                "data": chat_msg.to_dict()
            })
        
        # 7. 其他 AI 是否要"旁观插嘴"
        await process_bystander_reactions(game, current_player, decision)


async def process_bystander_reactions(
    game: GameState, 
    acting_player: Player, 
    decision: Decision
):
    """处理其他 AI 对当前操作的旁观反应"""
    other_agents = [
        agent_manager.get_agent(p.id)
        for p in game.players
        if p.id != acting_player.id 
        and p.player_type == PlayerType.AI
        and p.status not in (PlayerStatus.FOLDED, PlayerStatus.OUT)
    ]
    
    responses = 0
    for agent in other_agents:
        if responses >= 2:  # 最多 2 个旁观回应，避免刷屏
            break
        
        reaction = await agent.maybe_react_as_bystander(
            trigger_event=format_trigger_event(acting_player, decision),
            chat_context=get_chat_context(game),
        )
        
        if reaction and reaction.should_respond:
            responses += 1
            chat_msg = ChatMessage(
                sender_id=agent.player_id,
                sender_name=agent.name,
                message_type=ChatMessageType.BYSTANDER_TALK,
                content=reaction.message,
            )
            save_chat_message(game.game_id, chat_msg)
            await ws_manager.broadcast(game.game_id, {
                "type": "chat_message",
                "data": chat_msg.to_dict()
            })


async def handle_player_chat(game: GameState, player_id: str, content: str):
    """处理人类玩家发送的聊天消息"""
    # 1. 保存并广播玩家消息
    chat_msg = ChatMessage(
        sender_id=player_id,
        sender_name=get_player_name(game, player_id),
        message_type=ChatMessageType.PLAYER_MESSAGE,
        content=content,
    )
    save_chat_message(game.game_id, chat_msg)
    await ws_manager.broadcast(game.game_id, {
        "type": "chat_message",
        "data": chat_msg.to_dict()
    })
    
    # 2. 至少一个 AI 回应玩家的话
    active_agents = [
        agent_manager.get_agent(p.id)
        for p in game.players
        if p.player_type == PlayerType.AI
        and p.status not in (PlayerStatus.FOLDED, PlayerStatus.OUT)
    ]
    
    # 随机打乱，让不同 AI 有机会先回应
    random.shuffle(active_agents)
    
    responded = False
    for agent in active_agents[:2]:  # 最多 2 个 AI 回应
        reaction = await agent.maybe_react_as_bystander(
            trigger_event=f"玩家说: '{content}'",
            chat_context=get_chat_context(game),
            must_respond=(not responded),  # 确保至少一个回应
        )
        if reaction and reaction.should_respond:
            responded = True
            reply_msg = ChatMessage(
                sender_id=agent.player_id,
                sender_name=agent.name,
                message_type=ChatMessageType.BYSTANDER_TALK,
                content=reaction.message,
            )
            save_chat_message(game.game_id, reply_msg)
            await ws_manager.broadcast(game.game_id, {
                "type": "chat_message",
                "data": reply_msg.to_dict()
            })
```

### 8.4 心路历程生成流程

```
每步决策时:
  1. Agent 调用 LLM → 返回 action + thought + table_talk (一次调用)
  2. ThoughtRecorder 记录 ThoughtRecord (含 chat_analysis 和 table_talk)
  3. 如果有 table_talk，作为 ChatMessage 存储并广播
  4. 继续游戏

经验回顾触发时 (新局开始前):
  1. ExperienceReviewer 检查触发条件
  2. 如果触发，收集最近 3-5 局的 ThoughtRecord + RoundNarrative
  3. 调用 LLM 生成经验分析和策略调整
  4. 将 strategy_context 注入 Agent 内存，影响后续决策
  5. 存储 ExperienceReview 记录

每局结束时:
  1. 收集该局所有 ThoughtRecord + ChatMessage
  2. 构建叙事生成 prompt（包含思考记录 + 聊天内容 + 本局结果）
  3. 调用 LLM 生成第一人称叙事（含聊天策略的反思）
  4. 存储 RoundNarrative

游戏结束时:
  1. 收集所有局的 ThoughtRecord + RoundNarrative + ExperienceReview
  2. 汇总统计数据（含聊天相关统计）
  3. 构建总结生成 prompt
  4. 调用 LLM 生成完整 GameSummary (含 chat_strategy_summary + learning_journey)
  5. 存储并推送给前端
```

### 8.5 经验回顾触发逻辑

```python
class ExperienceReviewer:
    def __init__(self, agent_id: str, initial_chips: int):
        self.agent_id = agent_id
        self.initial_chips = initial_chips
        self.consecutive_losses = 0
        self.rounds_since_review = 0
        self.last_review_round = 0
    
    def check_trigger(self, game: GameState, round_result: RoundResult) -> ReviewTrigger | None:
        """检查是否应该触发经验回顾"""
        self.rounds_since_review += 1
        
        # 更新连败计数
        if round_result.winner_id != self.agent_id:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        current_chips = get_player_chips(game, self.agent_id)
        
        # 按优先级检查触发条件
        if current_chips <= self.initial_chips * 0.3:
            return ReviewTrigger.CHIP_CRISIS
        
        if self.consecutive_losses >= 2:
            return ReviewTrigger.CONSECUTIVE_LOSSES
        
        if round_result.winner_id != self.agent_id:
            loss = round_result.player_losses.get(self.agent_id, 0)
            if loss > self.initial_chips * 0.2:
                return ReviewTrigger.BIG_LOSS
        
        if self.rounds_since_review >= 5:
            return ReviewTrigger.PERIODIC
        
        return None
    
    async def perform_review(
        self, trigger: ReviewTrigger, recent_narratives: list[RoundNarrative],
        recent_thoughts: list[ThoughtRecord], opponent_stats: dict
    ) -> ExperienceReview:
        """执行经验回顾，调用 LLM 生成策略调整"""
        self.rounds_since_review = 0
        # ... 构建 prompt 并调用 LLM ...
```

---

## 9. 数据库设计 (SQLite)

```sql
-- 游戏表
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    config JSON NOT NULL,
    status TEXT NOT NULL,            -- waiting/playing/finished
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP
);

-- 玩家表
CREATE TABLE players (
    id TEXT PRIMARY KEY,
    game_id TEXT REFERENCES games(id),
    name TEXT NOT NULL,
    avatar TEXT,
    player_type TEXT NOT NULL,       -- human/ai
    model_id TEXT,
    personality TEXT,
    initial_chips INTEGER NOT NULL,
    current_chips INTEGER NOT NULL
);

-- 局记录表
CREATE TABLE rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT REFERENCES games(id),
    round_number INTEGER NOT NULL,
    pot INTEGER,
    winner_id TEXT,
    actions JSON,                    -- 完整行动记录
    hands JSON,                      -- 各玩家手牌（局结束后记录）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 心路历程表
CREATE TABLE thought_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT REFERENCES players(id),
    game_id TEXT REFERENCES games(id),
    round_number INTEGER NOT NULL,
    turn_number INTEGER NOT NULL,
    hand_evaluation TEXT,
    opponent_analysis TEXT,
    chat_analysis TEXT,              -- 对聊天内容的分析
    risk_assessment TEXT,
    decision TEXT NOT NULL,
    decision_target TEXT,
    reasoning TEXT,
    confidence REAL,
    emotion TEXT,
    table_talk TEXT,                 -- 操作时的发言（可为空）
    raw_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 聊天记录表
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT REFERENCES games(id),
    round_number INTEGER NOT NULL,
    sender_id TEXT REFERENCES players(id),
    sender_name TEXT NOT NULL,
    message_type TEXT NOT NULL,      -- action_talk/bystander_talk/player_message/system_message
    content TEXT NOT NULL,
    related_action TEXT,             -- 关联的游戏操作（如有）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 经验回顾表
CREATE TABLE experience_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT REFERENCES players(id),
    game_id TEXT REFERENCES games(id),
    trigger TEXT NOT NULL,           -- 触发原因
    triggered_at_round INTEGER NOT NULL,
    rounds_reviewed JSON,            -- 回顾了哪几局
    self_analysis TEXT,
    opponent_patterns JSON,
    strategy_adjustment TEXT,
    confidence_shift REAL,
    strategy_context TEXT,           -- 注入后续决策的策略摘要
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 局叙事表
CREATE TABLE round_narratives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT REFERENCES players(id),
    game_id TEXT REFERENCES games(id),
    round_number INTEGER NOT NULL,
    narrative TEXT NOT NULL,
    outcome TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 游戏总结表
CREATE TABLE game_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT REFERENCES players(id),
    game_id TEXT REFERENCES games(id),
    stats JSON,                      -- 统计数据
    key_moments JSON,
    opponent_impressions JSON,
    self_reflection TEXT,
    narrative_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 10. 开发计划

### Phase 1: 游戏引擎 (3-4 天)
1. 扑克牌模型 + 牌型评估器 + 单元测试
2. 游戏流程引擎（发牌、轮转、结算）
3. 规则校验（操作合法性、下注计算）

### Phase 2: AI Agent (3-4 天)
1. BaseAgent 框架 + LiteLLM 集成
2. Prompt 设计与调优（含聊天 prompt）
3. 心路历程记录系统
4. 响应解析与容错处理
5. 聊天引擎（行动发言 + 旁观插嘴逻辑）

### Phase 3: 经验学习系统 (2 天)
1. 触发条件检测逻辑
2. 经验回顾 Prompt 与 LLM 调用
3. 策略注入机制

### Phase 4: 后端 API (2-3 天)
1. FastAPI 项目搭建
2. REST API 实现（游戏 + 聊天 + 心路历程）
3. WebSocket 实现（含聊天消息推送）
4. SQLite 数据持久化
5. 玩家聊天消息处理与 AI 回应调度

### Phase 5: 前端基础 (3-4 天)
1. React 项目搭建 + 路由
2. 游戏大厅页面
3. 牌桌布局 + 玩家位
4. 拟物风格扑克牌组件

### Phase 6: 前端交互 (3-4 天)
1. WebSocket 通信
2. 操作面板交互
3. 发牌/翻牌动画
4. 聊天面板 + 气泡动画
5. 行动日志

### Phase 7: 心路历程 (2 天)
1. 心路历程查看器组件
2. 叙事报告生成（含聊天策略和经验回顾内容）
3. 游戏总结页面

### Phase 8: 打磨 (2-3 天)
1. AI 个性系统调优（含聊天风格差异化）
2. UI/UX 优化
3. 错误处理与边界情况
4. 整体联调测试

**预估总工期: 20-26 天**
