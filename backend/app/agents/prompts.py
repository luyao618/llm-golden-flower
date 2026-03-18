"""Prompt 模板系统

提供 AI Agent 在不同场景下使用的 Prompt 模板：
1. System Prompt - 角色身份 + 规则 + 发言指导（无预设性格，由 LLM 自行决定风格）
2. Decision Prompt - 决策场景（手牌、局面、历史行动、聊天上下文、经验策略）
3. Bystander React Prompt - 旁观插嘴场景
4. Experience Review Prompt - 经验回顾场景
5. Round Narrative Prompt - 单局叙事生成
6. Game Summary Prompt - 整场游戏总结

所有模板使用 Python str.format() 或 f-string 变量占位，
由调用方传入具体值进行渲染。
"""

from __future__ import annotations

# ---- 炸金花规则摘要 ----

RULES_SUMMARY = """\
炸金花（三张牌扑克）规则：
1. 每人发 3 张牌，牌型从大到小：豹子 > 同花顺 > 同花 > 顺子 > 对子 > 散牌
2. 特殊规则：A-2-3 是最小的顺子
3. 开局每人交底注，然后从庄家下家开始轮流行动
4. 可用操作：
   - 看牌：查看自己的手牌（暗注变明注，下注费用翻倍）
   - 跟注：跟上当前注额（暗注 1 倍，明注 2 倍）
   - 加注：加倍当前注额（暗注 2 倍，明注 4 倍）
   - 弃牌：放弃本局
   - 比牌：与另一个玩家比牌（只有已看牌的玩家才能发起），输者出局
5. 达到最大轮数时，剩余玩家强制比牌
6. 最后留在牌桌的玩家赢得底池"""

# ---- LLM 响应的 JSON 输出格式说明 ----

DECISION_OUTPUT_SCHEMA = """\
{
    "action": "fold | call | raise | check_cards | compare",
    "target": "比牌对象的玩家ID（仅当 action 为 compare 时需要，否则为 null）",
    "table_talk": "你在操作时说的话（可以为 null 表示沉默）",
    "thought": {
        "hand_evaluation": "对自己手牌的评估",
        "opponent_analysis": "对对手行为的分析",
        "chat_analysis": "对近期牌桌聊天的分析（可选）",
        "risk_assessment": "风险评估",
        "reasoning": "最终决策理由",
        "confidence": 0.0到1.0之间的数字,
        "emotion": "当前情绪标签，如：紧张、自信、忐忑、兴奋、沮丧、平静"
    }
}"""

# ---- 快速思考模式输出格式（仅保留核心思考字段） ----

FAST_DECISION_OUTPUT_SCHEMA = """\
{
    "action": "fold | call | raise | check_cards | compare",
    "target": "比牌对象的玩家ID（仅当 action 为 compare 时需要，否则为 null）",
    "table_talk": "你在操作时说的话（可以为 null 表示沉默）",
    "thought": {
        "reasoning": "简要决策理由（一两句话）",
        "confidence": 0.0到1.0之间的数字,
        "emotion": "当前情绪标签，如：紧张、自信、忐忑、兴奋、沮丧、平静"
    }
}"""

# ---- 极速决策模式输出格式（无思考过程） ----

TURBO_DECISION_OUTPUT_SCHEMA = """\
{
    "action": "fold | call | raise | check_cards | compare",
    "target": "比牌对象的玩家ID（仅当 action 为 compare 时需要，否则为 null）",
    "table_talk": "你在操作时说的话（可以为 null 表示沉默）"
}"""

BYSTANDER_OUTPUT_SCHEMA = """\
{
    "should_respond": true或false,
    "message": "你的回应内容（如果 should_respond 为 true）",
    "inner_thought": "你的内心真实想法（不会公开）"
}"""

EXPERIENCE_REVIEW_OUTPUT_SCHEMA = """\
{
    "self_analysis": "对自己近期表现的分析",
    "opponent_patterns": {
        "玩家ID": "对该对手行为模式的总结"
    },
    "strategy_adjustment": "接下来的策略调整方向",
    "confidence_shift": -1到1之间的数字（正数表示更自信，负数表示信心下降）
}"""

ROUND_NARRATIVE_OUTPUT_SCHEMA = """\
{
    "narrative": "以第一人称写的本局叙事（200-400字）",
    "outcome": "对本局结果的一句话总结"
}"""

GAME_SUMMARY_OUTPUT_SCHEMA = """\
{
    "key_moments": ["关键时刻1的描述", "关键时刻2的描述", ...],
    "opponent_impressions": {
        "玩家ID或名字": "对该对手的印象评价"
    },
    "self_reflection": "自我风格总结",
    "chat_strategy_summary": "聊天策略总结（我用了什么样的话术，效果如何）",
    "learning_journey": "学习历程总结（我在什么时候做了策略调整，原因是什么）",
    "narrative_summary": "完整的回顾叙事（300-600字，第一人称）"
}"""


# =============================================
# 1. System Prompt 模板
# =============================================

SYSTEM_PROMPT_TEMPLATE = """\
你是一个正在玩炸金花（三张牌扑克）的玩家。

## 你的身份
- 名字: {agent_name}

## 你的目标
赢。你要尽一切办法在牌桌上赢得更多筹码。

## 你的风格
你自行决定自己的打牌风格和说话方式。你可以激进、保守、善于诈唬、善于分析——
一切由你自己判断当前局面后决定。没有人给你设定性格，你就是你自己。

## 炸金花规则摘要
{rules_summary}

## 你的决策原则
- 根据你对局面的判断自主做出最有利的决策
- 仔细分析对手的行为模式
- 权衡风险与收益
- 记录你的真实想法

## 牌桌交流
- 你可以在做出操作时说一句话（也可以选择沉默）
- 你自行决定什么时候说话、说什么、用什么语气
- 你可以利用言语来施压、虚张声势、试探对手、回应挑衅
- 注意：你说的话对手能看到，不要泄露自己的真实策略
- 牌桌上的对话也是博弈的一部分，对手的话可能是真话也可能是烟雾弹

## 输出格式
你必须以 JSON 格式输出，包含以下字段:
{output_schema}"""

# ---- 快速思考模式 System Prompt（精简版） ----

FAST_SYSTEM_PROMPT_TEMPLATE = """\
你是炸金花玩家 {agent_name}，目标是赢得更多筹码。

## 规则摘要
{rules_summary}

## 决策要求
- 根据局面做出最有利的决策
- 分析对手行为模式，权衡风险与收益
- 可以在操作时说一句话（也可以沉默），利用言语施压或试探

## 输出格式（JSON）
{output_schema}"""

# ---- 极速决策模式 System Prompt（最精简） ----

TURBO_SYSTEM_PROMPT_TEMPLATE = """\
你是炸金花玩家 {agent_name}。根据局面快速做出最有利的决策。

## 规则
{rules_summary}

## 输出格式（JSON，直接输出决策）
{output_schema}"""


# =============================================
# 2. Decision Prompt 模板
# =============================================

DECISION_PROMPT_TEMPLATE = """\
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

请做出你的决策，记录你的心路历程，并决定是否要说点什么。"""


# =============================================
# 3. Bystander React Prompt 模板
# =============================================

BYSTANDER_REACT_PROMPT_TEMPLATE = """\
## 当前情况

{trigger_event_description}

## 最近的聊天记录
{recent_chat}

## 你的当前状态
- 手牌状态: {seen_status}
- 筹码: {your_chips}
- 你在这一局的表现: {your_actions_so_far}

你可以选择回应，也可以选择沉默。
如果回应，简短有力，一两句话即可。

输出格式:
{output_schema}"""


# =============================================
# 4. Experience Review Prompt 模板
# =============================================

EXPERIENCE_REVIEW_PROMPT_TEMPLATE = """\
## 经验回顾

你刚刚经历了几局不太顺利的牌局，现在花点时间回顾一下。

### 触发原因
{trigger_reason}

### 最近几局的回顾
{past_rounds_narratives}

### 你的统计数据
- 最近 {review_round_count} 局胜率: {win_rate}
- 筹码变化: {chips_change}
- 弃牌率: {fold_rate}

### 各对手的近期行为
{opponent_recent_behaviors}

请分析你的表现，找出问题，并制定调整策略。

输出格式:
{output_schema}"""


# =============================================
# 5. Round Narrative Prompt 模板
# =============================================

ROUND_NARRATIVE_PROMPT_TEMPLATE = """\
## 请以第一人称写一段本局的叙事回顾

你是 {agent_name}。

### 本局基本信息
- 第 {round_number} 局
- 你的手牌: {hand_description}
- 本局结果: {round_outcome}

### 你在本局的思考过程
{round_thoughts}

### 本局的聊天记录
{chat_messages}

### 本局的行动记录
{action_history}

请用第一人称（"我"）写一段 200-400 字的叙事，生动地描述你这局的心路历程。
包括你的牌力判断、对对手的分析、关键决策点、以及你在聊天中的策略。

输出格式:
{output_schema}"""


# =============================================
# 6. Game Summary Prompt 模板
# =============================================

GAME_SUMMARY_PROMPT_TEMPLATE = """\
## 请写一份整场游戏的总结报告

你是 {agent_name}。

### 统计数据
- 总共打了 {rounds_played} 局
- 赢了 {rounds_won} 局
- 总共赢得 {total_chips_won} 筹码
- 总共输掉 {total_chips_lost} 筹码
- 最大单局赢利: {biggest_win}
- 最大单局亏损: {biggest_loss}
- 弃牌率: {fold_rate}

### 各局叙事回顾
{all_narratives}

### 经验回顾记录
{all_reviews}

### 对手列表
{opponents_info}

请从以下几个方面写总结：
1. **关键时刻**: 回顾 2-4 个最令你印象深刻的关键时刻
2. **对手印象**: 对每个对手的评价和印象
3. **自我反思**: 总结自己的打牌风格和优缺点
4. **聊天策略**: 总结你在聊天中使用的策略和效果
5. **学习历程**: 你在游戏过程中是否做了策略调整？转折点是什么？
6. **总结叙事**: 用第一人称写一段 300-600 字的完整回顾

输出格式:
{output_schema}"""


# =============================================
# 模板渲染函数
# =============================================


def render_system_prompt(
    agent_name: str,
    thinking_mode: str = "fast",
) -> str:
    """渲染 System Prompt

    根据 thinking_mode 选择对应的模板和输出 Schema。

    Args:
        agent_name: Agent 显示名称
        thinking_mode: AI 思考模式 ("detailed" / "fast" / "turbo")

    Returns:
        渲染后的 system prompt 文本
    """
    if thinking_mode == "turbo":
        template = TURBO_SYSTEM_PROMPT_TEMPLATE
        schema = TURBO_DECISION_OUTPUT_SCHEMA
    elif thinking_mode == "fast":
        template = FAST_SYSTEM_PROMPT_TEMPLATE
        schema = FAST_DECISION_OUTPUT_SCHEMA
    else:
        # detailed（默认完整版）
        template = SYSTEM_PROMPT_TEMPLATE
        schema = DECISION_OUTPUT_SCHEMA

    return template.format(
        agent_name=agent_name,
        rules_summary=RULES_SUMMARY,
        output_schema=schema,
    )


def render_decision_prompt(
    hand_description: str,
    seen_status: str,
    pot: int,
    your_chips: int,
    current_bet: int,
    players_status_table: str,
    action_history: str,
    chat_history: str,
    available_actions: str,
    experience_context: str = "",
) -> str:
    """渲染 Decision Prompt

    Args:
        hand_description: 手牌描述（如 "红心K, 黑桃K, 方块3（一对K）"）
        seen_status: 看牌状态（"看牌" 或 "未看牌"）
        pot: 底池筹码数
        your_chips: 自己的筹码数
        current_bet: 当前注额基数
        players_status_table: 各玩家状态表格文本
        action_history: 本局行动历史文本
        chat_history: 本局聊天记录文本
        available_actions: 可用操作列表文本
        experience_context: 经验回顾策略上下文（可为空）

    Returns:
        渲染后的 decision prompt 文本
    """
    # 格式化经验上下文（如果有的话）
    exp_section = ""
    if experience_context:
        exp_section = f"## 你最近的策略调整\n{experience_context}"

    return DECISION_PROMPT_TEMPLATE.format(
        hand_description=hand_description,
        seen_status=seen_status,
        pot=pot,
        your_chips=your_chips,
        current_bet=current_bet,
        players_status_table=players_status_table,
        action_history=action_history,
        chat_history=chat_history,
        experience_context=exp_section,
        available_actions=available_actions,
    )


def render_bystander_react_prompt(
    trigger_event_description: str,
    recent_chat: str,
    seen_status: str,
    your_chips: int,
    your_actions_so_far: str,
) -> str:
    """渲染 Bystander React Prompt

    Args:
        trigger_event_description: 触发事件描述
        recent_chat: 最近的聊天记录
        seen_status: 看牌状态
        your_chips: 自己的筹码数
        your_actions_so_far: 自己本局的行动概述

    Returns:
        渲染后的 bystander react prompt 文本
    """
    return BYSTANDER_REACT_PROMPT_TEMPLATE.format(
        trigger_event_description=trigger_event_description,
        recent_chat=recent_chat,
        seen_status=seen_status,
        your_chips=your_chips,
        your_actions_so_far=your_actions_so_far,
        output_schema=BYSTANDER_OUTPUT_SCHEMA,
    )


def render_experience_review_prompt(
    trigger_reason: str,
    past_rounds_narratives: str,
    review_round_count: int,
    win_rate: str,
    chips_change: str,
    fold_rate: str,
    opponent_recent_behaviors: str,
) -> str:
    """渲染 Experience Review Prompt

    Args:
        trigger_reason: 触发原因描述
        past_rounds_narratives: 最近几局的叙事回顾文本
        review_round_count: 回顾的局数
        win_rate: 胜率文本（如 "33%"）
        chips_change: 筹码变化文本（如 "-200"）
        fold_rate: 弃牌率文本（如 "40%"）
        opponent_recent_behaviors: 对手近期行为描述

    Returns:
        渲染后的 experience review prompt 文本
    """
    return EXPERIENCE_REVIEW_PROMPT_TEMPLATE.format(
        trigger_reason=trigger_reason,
        past_rounds_narratives=past_rounds_narratives,
        review_round_count=review_round_count,
        win_rate=win_rate,
        chips_change=chips_change,
        fold_rate=fold_rate,
        opponent_recent_behaviors=opponent_recent_behaviors,
        output_schema=EXPERIENCE_REVIEW_OUTPUT_SCHEMA,
    )


def render_round_narrative_prompt(
    agent_name: str,
    round_number: int,
    hand_description: str,
    round_outcome: str,
    round_thoughts: str,
    chat_messages: str,
    action_history: str,
) -> str:
    """渲染 Round Narrative Prompt

    Args:
        agent_name: Agent 显示名称
        round_number: 局数
        hand_description: 手牌描述
        round_outcome: 本局结果描述
        round_thoughts: 本局思考过程文本
        chat_messages: 本局聊天记录文本
        action_history: 本局行动记录文本

    Returns:
        渲染后的 round narrative prompt 文本
    """
    return ROUND_NARRATIVE_PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        round_number=round_number,
        hand_description=hand_description,
        round_outcome=round_outcome,
        round_thoughts=round_thoughts,
        chat_messages=chat_messages,
        action_history=action_history,
        output_schema=ROUND_NARRATIVE_OUTPUT_SCHEMA,
    )


def render_game_summary_prompt(
    agent_name: str,
    rounds_played: int,
    rounds_won: int,
    total_chips_won: int,
    total_chips_lost: int,
    biggest_win: int,
    biggest_loss: int,
    fold_rate: str,
    all_narratives: str,
    all_reviews: str,
    opponents_info: str,
) -> str:
    """渲染 Game Summary Prompt

    Args:
        agent_name: Agent 显示名称
        rounds_played: 总局数
        rounds_won: 赢的局数
        total_chips_won: 总赢得筹码
        total_chips_lost: 总输掉筹码
        biggest_win: 最大单局赢利
        biggest_loss: 最大单局亏损
        fold_rate: 弃牌率文本
        all_narratives: 所有局的叙事回顾文本
        all_reviews: 所有经验回顾记录文本
        opponents_info: 对手信息列表文本

    Returns:
        渲染后的 game summary prompt 文本
    """
    return GAME_SUMMARY_PROMPT_TEMPLATE.format(
        agent_name=agent_name,
        rounds_played=rounds_played,
        rounds_won=rounds_won,
        total_chips_won=total_chips_won,
        total_chips_lost=total_chips_lost,
        biggest_win=biggest_win,
        biggest_loss=biggest_loss,
        fold_rate=fold_rate,
        all_narratives=all_narratives,
        all_reviews=all_reviews,
        opponents_info=opponents_info,
        output_schema=GAME_SUMMARY_OUTPUT_SCHEMA,
    )
