"""T2.4 单元测试: ChatEngine + Chat 数据模型

测试覆盖:
- ChatMessage / ChatContext / BystanderReaction 数据模型
- ChatEngine.should_respond 概率逻辑
- ChatEngine.calculate_response_probability 各事件类型和性格组合
- ChatEngine.maybe_react_as_bystander LLM 调用和解析
- ChatEngine.collect_bystander_reactions must_respond 保证
- TriggerEvent 创建工厂函数
- 旁观反应解析（JSON 正常解析、容错、降级）
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.base_agent import BaseAgent
from app.agents.chat_engine import (
    ChatEngine,
    TriggerEvent,
    TriggerEventType,
    EVENT_BASE_PROBABILITIES,
    create_trigger_event_from_action,
    create_player_message_event,
    _get_fallback_reaction,
)
from app.models.chat import (
    BystanderReaction,
    ChatContext,
    ChatMessage,
    ChatMessageType,
)
from app.models.game import GameAction


# ============================================================
# 辅助函数
# ============================================================


def make_agent(
    agent_id: str = "agent-1",
    name: str = "测试AI",
    personality: str = "analytical",
    model_id: str = "openai-gpt4o-mini",
) -> BaseAgent:
    """创建测试用 BaseAgent"""
    return BaseAgent(
        agent_id=agent_id,
        name=name,
        personality=personality,
        model_id=model_id,
    )


def make_trigger_event(
    event_type: TriggerEventType = TriggerEventType.RAISE,
    actor_id: str = "player-1",
    actor_name: str = "张三",
    description: str = "张三 加注到 40 筹码",
    must_respond: bool = False,
) -> TriggerEvent:
    """创建测试用 TriggerEvent"""
    return TriggerEvent(
        event_type=event_type,
        actor_id=actor_id,
        actor_name=actor_name,
        description=description,
        must_respond=must_respond,
    )


# ============================================================
# ChatMessage 数据模型
# ============================================================


class TestChatMessage:
    """ChatMessage 测试"""

    def test_default_creation(self):
        msg = ChatMessage()
        assert msg.id  # 自动生成 UUID
        assert msg.message_type == ChatMessageType.ACTION_TALK
        assert msg.content == ""
        assert msg.timestamp > 0

    def test_custom_creation(self):
        msg = ChatMessage(
            game_id="game-1",
            round_number=3,
            player_id="player-1",
            player_name="张三",
            message_type=ChatMessageType.BYSTANDER_REACT,
            content="有意思！",
            trigger_event="李四 加注了",
            inner_thought="他可能在虚张声势",
        )
        assert msg.game_id == "game-1"
        assert msg.round_number == 3
        assert msg.player_name == "张三"
        assert msg.message_type == ChatMessageType.BYSTANDER_REACT
        assert msg.content == "有意思！"
        assert msg.trigger_event == "李四 加注了"
        assert msg.inner_thought == "他可能在虚张声势"


class TestChatMessageType:
    """ChatMessageType 枚举测试"""

    def test_all_types_defined(self):
        assert ChatMessageType.ACTION_TALK == "action_talk"
        assert ChatMessageType.BYSTANDER_REACT == "bystander_react"
        assert ChatMessageType.PLAYER_MESSAGE == "player_message"
        assert ChatMessageType.SYSTEM_MESSAGE == "system_message"

    def test_type_count(self):
        assert len(ChatMessageType) == 4


# ============================================================
# ChatContext 数据模型
# ============================================================


class TestChatContext:
    """ChatContext 测试"""

    def test_empty_context(self):
        ctx = ChatContext()
        assert len(ctx.messages) == 0
        assert ctx.get_recent() == []

    def test_add_message(self):
        ctx = ChatContext()
        msg = ChatMessage(player_name="张三", content="大家好")
        ctx.add_message(msg)
        assert len(ctx.messages) == 1
        assert ctx.messages[0].content == "大家好"

    def test_max_messages_limit(self):
        ctx = ChatContext(max_messages=5)
        for i in range(10):
            ctx.add_message(ChatMessage(content=f"消息{i}"))
        assert len(ctx.messages) == 5
        assert ctx.messages[0].content == "消息5"
        assert ctx.messages[-1].content == "消息9"

    def test_get_recent_with_count(self):
        ctx = ChatContext()
        for i in range(5):
            ctx.add_message(ChatMessage(content=f"消息{i}"))
        recent = ctx.get_recent(3)
        assert len(recent) == 3
        assert recent[0].content == "消息2"
        assert recent[-1].content == "消息4"

    def test_get_recent_all(self):
        ctx = ChatContext()
        for i in range(3):
            ctx.add_message(ChatMessage(content=f"消息{i}"))
        recent = ctx.get_recent()
        assert len(recent) == 3

    def test_format_for_prompt_empty(self):
        ctx = ChatContext()
        result = ctx.format_for_prompt()
        assert result == "（暂无聊天记录）"

    def test_format_for_prompt_with_messages(self):
        ctx = ChatContext()
        ctx.add_message(
            ChatMessage(
                player_name="张三",
                content="大家好",
                message_type=ChatMessageType.ACTION_TALK,
            )
        )
        ctx.add_message(
            ChatMessage(
                player_name="李四",
                content="你好啊",
                message_type=ChatMessageType.BYSTANDER_REACT,
            )
        )
        result = ctx.format_for_prompt()
        assert "张三" in result
        assert "大家好" in result
        assert "李四" in result
        assert "你好啊" in result
        assert "行动发言" in result
        assert "插嘴" in result

    def test_clear(self):
        ctx = ChatContext()
        ctx.add_message(ChatMessage(content="test"))
        ctx.clear()
        assert len(ctx.messages) == 0


# ============================================================
# BystanderReaction 数据模型
# ============================================================


class TestBystanderReaction:
    """BystanderReaction 测试"""

    def test_default_no_respond(self):
        reaction = BystanderReaction(
            agent_id="agent-1",
            agent_name="AI-1",
            should_respond=False,
        )
        assert reaction.should_respond is False
        assert reaction.message == ""

    def test_to_chat_message_when_responding(self):
        reaction = BystanderReaction(
            agent_id="agent-1",
            agent_name="AI-1",
            should_respond=True,
            message="有意思！",
            inner_thought="他在虚张声势",
            trigger_event="张三 加注了",
        )
        msg = reaction.to_chat_message(game_id="game-1", round_number=2)
        assert msg is not None
        assert msg.player_id == "agent-1"
        assert msg.player_name == "AI-1"
        assert msg.content == "有意思！"
        assert msg.message_type == ChatMessageType.BYSTANDER_REACT
        assert msg.game_id == "game-1"
        assert msg.round_number == 2

    def test_to_chat_message_when_not_responding(self):
        reaction = BystanderReaction(
            agent_id="agent-1",
            agent_name="AI-1",
            should_respond=False,
        )
        msg = reaction.to_chat_message()
        assert msg is None

    def test_to_chat_message_empty_message(self):
        reaction = BystanderReaction(
            agent_id="agent-1",
            agent_name="AI-1",
            should_respond=True,
            message="",
        )
        msg = reaction.to_chat_message()
        assert msg is None


# ============================================================
# ChatEngine - should_respond 概率逻辑
# ============================================================


class TestShouldRespond:
    """should_respond 概率逻辑测试"""

    def test_self_action_never_triggers(self):
        """自己的行动不触发自己的旁观反应"""
        engine = ChatEngine()
        agent = make_agent(agent_id="agent-1")
        event = make_trigger_event(actor_id="agent-1")

        # 多次测试确保一直返回 False
        for _ in range(100):
            assert engine.should_respond(event, agent) is False

    def test_high_talk_frequency_more_likely(self):
        """高发言频率的 AI 更可能回应"""
        engine = ChatEngine()
        aggressive = make_agent(personality="aggressive")  # talk_frequency=0.8
        conservative = make_agent(
            agent_id="agent-2", personality="conservative"
        )  # talk_frequency=0.25

        event = make_trigger_event(event_type=TriggerEventType.RAISE)

        aggressive_prob = engine.calculate_response_probability(event, aggressive)
        conservative_prob = engine.calculate_response_probability(event, conservative)

        assert aggressive_prob > conservative_prob

    def test_big_raise_higher_probability_than_call(self):
        """大幅加注的触发概率高于跟注"""
        engine = ChatEngine()
        agent = make_agent()

        big_raise_event = make_trigger_event(event_type=TriggerEventType.BIG_RAISE)
        call_event = make_trigger_event(event_type=TriggerEventType.CALL)

        big_raise_prob = engine.calculate_response_probability(big_raise_event, agent)
        call_prob = engine.calculate_response_probability(call_event, agent)

        assert big_raise_prob > call_prob


class TestCalculateResponseProbability:
    """calculate_response_probability 详细概率计算测试"""

    def test_self_action_returns_zero(self):
        engine = ChatEngine()
        agent = make_agent(agent_id="agent-1")
        event = make_trigger_event(actor_id="agent-1")
        assert engine.calculate_response_probability(event, agent) == 0.0

    def test_aggressive_big_raise(self):
        """激进型 + 大幅加注 = 高概率"""
        engine = ChatEngine()
        agent = make_agent(personality="aggressive")  # talk_frequency=0.8
        event = make_trigger_event(event_type=TriggerEventType.BIG_RAISE)

        prob = engine.calculate_response_probability(event, agent)
        # base=0.6, factor=0.3+0.8*1.4=1.42, final=0.6*1.42=0.852
        assert 0.8 < prob <= 1.0

    def test_conservative_call(self):
        """保守型 + 跟注 = 低概率"""
        engine = ChatEngine()
        agent = make_agent(personality="conservative")  # talk_frequency=0.25
        event = make_trigger_event(event_type=TriggerEventType.CALL)

        prob = engine.calculate_response_probability(event, agent)
        # base=0.1, factor=0.3+0.25*1.4=0.65, final=0.1*0.65=0.065
        assert prob < 0.1

    def test_analytical_compare(self):
        """分析型 + 比牌"""
        engine = ChatEngine()
        agent = make_agent(personality="analytical")  # talk_frequency=0.45
        event = make_trigger_event(event_type=TriggerEventType.COMPARE)

        prob = engine.calculate_response_probability(event, agent)
        # base=0.55, factor=0.3+0.45*1.4=0.93, final=0.55*0.93=0.5115
        assert 0.4 < prob < 0.6

    def test_must_respond_uses_higher_base(self):
        """must_respond 事件使用更高的基础概率"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event(must_respond=True)

        prob = engine.calculate_response_probability(event, agent)
        # must_respond base=0.7
        assert prob > 0.5

    def test_all_event_types_have_base_probability(self):
        """所有事件类型都有基础概率配置"""
        for event_type in TriggerEventType:
            assert event_type in EVENT_BASE_PROBABILITIES

    def test_probability_capped_at_one(self):
        """概率不超过 1.0"""
        engine = ChatEngine()
        agent = make_agent(personality="aggressive")  # talk_frequency=0.8
        # 用最高概率的事件
        event = make_trigger_event(
            event_type=TriggerEventType.PLAYER_MESSAGE,
            must_respond=True,
        )
        prob = engine.calculate_response_probability(event, agent)
        assert prob <= 1.0

    def test_all_personalities_respond_probability(self):
        """所有性格类型对同一事件的概率都是正数（排除自身行动）"""
        engine = ChatEngine()
        event = make_trigger_event(
            event_type=TriggerEventType.RAISE,
            actor_id="other-player",
        )
        for personality in ["aggressive", "conservative", "analytical", "intuitive", "bluffer"]:
            agent = make_agent(personality=personality, agent_id="test-agent")
            prob = engine.calculate_response_probability(event, agent)
            assert prob > 0, f"Personality {personality} should have positive probability"

    def test_event_probability_ordering(self):
        """事件概率应该符合直觉排序：大幅加注 > 普通加注 > 跟注"""
        engine = ChatEngine()
        agent = make_agent()

        big_raise = engine.calculate_response_probability(
            make_trigger_event(event_type=TriggerEventType.BIG_RAISE), agent
        )
        normal_raise = engine.calculate_response_probability(
            make_trigger_event(event_type=TriggerEventType.RAISE), agent
        )
        call = engine.calculate_response_probability(
            make_trigger_event(event_type=TriggerEventType.CALL), agent
        )
        check = engine.calculate_response_probability(
            make_trigger_event(event_type=TriggerEventType.CHECK_CARDS), agent
        )

        assert big_raise > normal_raise > call
        assert big_raise > check


# ============================================================
# ChatEngine - maybe_react_as_bystander (mock LLM)
# ============================================================


class TestMaybeReactAsBystander:
    """maybe_react_as_bystander LLM 调用测试"""

    @pytest.mark.asyncio
    async def test_positive_reaction(self):
        """正常 JSON 回应解析"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = json.dumps(
            {
                "should_respond": True,
                "message": "这个加注很有意思啊",
                "inner_thought": "他可能在虚张声势",
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=mock_response):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is True
        assert reaction.message == "这个加注很有意思啊"
        assert reaction.inner_thought == "他可能在虚张声势"
        assert reaction.agent_id == agent.agent_id
        assert reaction.agent_name == agent.name

    @pytest.mark.asyncio
    async def test_negative_reaction(self):
        """AI 选择不回应"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = json.dumps(
            {
                "should_respond": False,
                "message": "",
                "inner_thought": "不值得回应",
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=mock_response):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is False

    @pytest.mark.asyncio
    async def test_llm_failure_with_must_respond(self):
        """LLM 调用失败时，must_respond 返回降级反应"""
        engine = ChatEngine()
        agent = make_agent(personality="aggressive")
        event = make_trigger_event()
        ctx = ChatContext()

        with patch.object(
            agent, "call_llm", new_callable=AsyncMock, side_effect=Exception("API Error")
        ):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is True
        assert reaction.message  # 有降级文本
        assert "LLM 调用失败" in reaction.inner_thought

    @pytest.mark.asyncio
    async def test_llm_failure_without_must_respond(self):
        """LLM 调用失败时，非 must_respond 返回 None"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        with patch.object(
            agent, "call_llm", new_callable=AsyncMock, side_effect=Exception("API Error")
        ):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=False,
            )

        assert reaction is None

    @pytest.mark.asyncio
    async def test_probability_skip(self):
        """概率判断不通过时返回 None"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        # 通过 mock should_respond 始终返回 False
        with patch.object(engine, "should_respond", return_value=False):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=False,
            )

        assert reaction is None

    @pytest.mark.asyncio
    async def test_agent_state_passed_to_prompt(self):
        """agent_state 正确传递到 prompt"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = json.dumps(
            {
                "should_respond": True,
                "message": "好牌啊",
                "inner_thought": "试探他",
            }
        )

        with patch.object(
            agent, "call_llm", new_callable=AsyncMock, return_value=mock_response
        ) as mock_call:
            await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                agent_state={
                    "seen_status": "已看牌",
                    "chips": 500,
                    "actions_summary": "跟注了2次",
                },
                must_respond=True,
            )

            # 验证 LLM 被调用了
            mock_call.assert_awaited_once()
            # 验证 prompt 中包含状态信息
            call_args = mock_call.call_args
            messages = call_args[1].get("messages") or call_args[0][0]
            user_prompt = messages[1]["content"]
            assert "已看牌" in user_prompt
            assert "500" in user_prompt
            assert "跟注了2次" in user_prompt


# ============================================================
# ChatEngine - 旁观反应解析容错
# ============================================================


class TestBystanderResponseParsing:
    """旁观反应解析容错测试"""

    @pytest.mark.asyncio
    async def test_parse_markdown_json(self):
        """解析 markdown 包裹的 JSON"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = '```json\n{"should_respond": true, "message": "好大的胆子", "inner_thought": "让我看看"}\n```'

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=mock_response):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is True
        assert reaction.message == "好大的胆子"

    @pytest.mark.asyncio
    async def test_parse_plain_text_short(self):
        """短文本直接作为回应"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = "哈哈，加得好！"

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=mock_response):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is True
        assert "加得好" in reaction.message

    @pytest.mark.asyncio
    async def test_parse_rejection_text(self):
        """识别拒绝回应的文本"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = "我选择沉默，不说话"

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=mock_response):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is False

    @pytest.mark.asyncio
    async def test_parse_should_respond_true_empty_message(self):
        """should_respond=true 但 message 为空时，改为不回应"""
        engine = ChatEngine()
        agent = make_agent()
        event = make_trigger_event()
        ctx = ChatContext()

        mock_response = json.dumps(
            {
                "should_respond": True,
                "message": "",
                "inner_thought": "算了",
            }
        )

        with patch.object(agent, "call_llm", new_callable=AsyncMock, return_value=mock_response):
            reaction = await engine.maybe_react_as_bystander(
                trigger_event=event,
                agent=agent,
                chat_context=ctx,
                must_respond=True,
            )

        assert reaction is not None
        assert reaction.should_respond is False


# ============================================================
# ChatEngine - collect_bystander_reactions
# ============================================================


class TestCollectBystanderReactions:
    """collect_bystander_reactions 批量收集测试"""

    @pytest.mark.asyncio
    async def test_empty_bystanders(self):
        """无旁观者时返回空列表"""
        engine = ChatEngine()
        event = make_trigger_event()
        ctx = ChatContext()

        reactions = await engine.collect_bystander_reactions(
            event=event,
            bystanders=[],
            chat_context=ctx,
        )
        assert reactions == []

    @pytest.mark.asyncio
    async def test_skip_event_actor(self):
        """跳过事件发起者"""
        engine = ChatEngine()
        actor_agent = make_agent(agent_id="actor-id")
        other_agent = make_agent(agent_id="other-id", name="其他AI")

        event = make_trigger_event(actor_id="actor-id")
        ctx = ChatContext()

        respond_json = json.dumps(
            {
                "should_respond": True,
                "message": "有意思",
                "inner_thought": "看着呢",
            }
        )

        # mock 所有 agent 的 LLM 调用
        with (
            patch.object(
                actor_agent, "call_llm", new_callable=AsyncMock, return_value=respond_json
            ),
            patch.object(
                other_agent, "call_llm", new_callable=AsyncMock, return_value=respond_json
            ),
        ):
            # 让 should_respond 始终通过
            with patch.object(engine, "should_respond", return_value=True):
                reactions = await engine.collect_bystander_reactions(
                    event=event,
                    bystanders=[actor_agent, other_agent],
                    chat_context=ctx,
                )

        # 只有 other_agent 的反应，actor_agent 被跳过
        agent_ids = [r.agent_id for r in reactions]
        assert "actor-id" not in agent_ids
        assert "other-id" in agent_ids

    @pytest.mark.asyncio
    async def test_must_respond_guarantee(self):
        """must_respond=True 确保至少一个 AI 回应"""
        engine = ChatEngine()
        agents = [
            make_agent(agent_id="a1", name="AI-1", personality="conservative"),
            make_agent(agent_id="a2", name="AI-2", personality="aggressive"),
        ]

        event = make_trigger_event(
            actor_id="player-1",
            must_respond=True,
        )
        ctx = ChatContext()

        respond_json = json.dumps(
            {
                "should_respond": True,
                "message": "好的我来回应",
                "inner_thought": "收到",
            }
        )

        # 先让所有 should_respond 返回 False，模拟无人回应
        with patch.object(engine, "should_respond", return_value=False):
            for agent in agents:
                with patch.object(
                    agent, "call_llm", new_callable=AsyncMock, return_value=respond_json
                ):
                    pass

            # 需要同时 mock 所有 agent 的 call_llm
            with (
                patch.object(
                    agents[0], "call_llm", new_callable=AsyncMock, return_value=respond_json
                ),
                patch.object(
                    agents[1], "call_llm", new_callable=AsyncMock, return_value=respond_json
                ),
            ):
                reactions = await engine.collect_bystander_reactions(
                    event=event,
                    bystanders=agents,
                    chat_context=ctx,
                )

        # must_respond 保证至少有一个回应
        assert len(reactions) >= 1
        assert any(r.should_respond for r in reactions)

    @pytest.mark.asyncio
    async def test_must_respond_picks_most_talkative(self):
        """must_respond 降级时选择最健谈的 AI"""
        engine = ChatEngine()
        conservative = make_agent(
            agent_id="a1", name="保守者", personality="conservative"
        )  # talk_frequency=0.25
        aggressive = make_agent(
            agent_id="a2", name="激进者", personality="aggressive"
        )  # talk_frequency=0.8

        event = make_trigger_event(
            actor_id="player-1",
            must_respond=True,
        )
        ctx = ChatContext()

        respond_json = json.dumps(
            {
                "should_respond": True,
                "message": "我来说两句",
                "inner_thought": "好吧",
            }
        )

        # 让 should_respond 始终返回 False，触发 must_respond 降级
        with patch.object(engine, "should_respond", return_value=False):
            with (
                patch.object(
                    conservative, "call_llm", new_callable=AsyncMock, return_value=respond_json
                ),
                patch.object(
                    aggressive, "call_llm", new_callable=AsyncMock, return_value=respond_json
                ),
            ):
                reactions = await engine.collect_bystander_reactions(
                    event=event,
                    bystanders=[conservative, aggressive],
                    chat_context=ctx,
                )

        # 应该选择激进者（talk_frequency 更高）
        assert len(reactions) == 1
        assert reactions[0].agent_id == "a2"

    @pytest.mark.asyncio
    async def test_no_must_respond_may_return_empty(self):
        """非 must_respond 事件可能无人回应"""
        engine = ChatEngine()
        agents = [
            make_agent(agent_id="a1", personality="conservative"),
        ]

        event = make_trigger_event(must_respond=False)
        ctx = ChatContext()

        # 让 should_respond 返回 False
        with patch.object(engine, "should_respond", return_value=False):
            reactions = await engine.collect_bystander_reactions(
                event=event,
                bystanders=agents,
                chat_context=ctx,
            )

        assert reactions == []


# ============================================================
# TriggerEvent 工厂函数
# ============================================================


class TestCreateTriggerEvent:
    """create_trigger_event_from_action 工厂函数测试"""

    def test_raise_event(self):
        event = create_trigger_event_from_action(
            action=GameAction.RAISE,
            actor_id="p1",
            actor_name="张三",
            amount=40,
            current_bet=20,
        )
        assert event.event_type == TriggerEventType.RAISE
        assert "张三" in event.description
        assert "40" in event.description

    def test_big_raise_event(self):
        event = create_trigger_event_from_action(
            action=GameAction.RAISE,
            actor_id="p1",
            actor_name="张三",
            amount=100,
            current_bet=20,
        )
        assert event.event_type == TriggerEventType.BIG_RAISE

    def test_fold_event(self):
        event = create_trigger_event_from_action(
            action=GameAction.FOLD,
            actor_id="p1",
            actor_name="张三",
        )
        assert event.event_type == TriggerEventType.FOLD
        assert "弃牌" in event.description

    def test_compare_event_with_winner(self):
        event = create_trigger_event_from_action(
            action=GameAction.COMPARE,
            actor_id="p1",
            actor_name="张三",
            target_name="李四",
            compare_winner="p1",
        )
        assert event.event_type == TriggerEventType.COMPARE_WIN
        assert "赢了" in event.description

    def test_compare_event_with_loser(self):
        event = create_trigger_event_from_action(
            action=GameAction.COMPARE,
            actor_id="p1",
            actor_name="张三",
            target_name="李四",
            compare_winner="p2",
        )
        assert event.event_type == TriggerEventType.COMPARE_LOSE
        assert "输了" in event.description

    def test_compare_event_no_result(self):
        event = create_trigger_event_from_action(
            action=GameAction.COMPARE,
            actor_id="p1",
            actor_name="张三",
            target_name="李四",
        )
        assert event.event_type == TriggerEventType.COMPARE

    def test_check_cards_event(self):
        event = create_trigger_event_from_action(
            action=GameAction.CHECK_CARDS,
            actor_id="p1",
            actor_name="张三",
        )
        assert event.event_type == TriggerEventType.CHECK_CARDS
        assert "看" in event.description

    def test_call_event(self):
        event = create_trigger_event_from_action(
            action=GameAction.CALL,
            actor_id="p1",
            actor_name="张三",
            amount=20,
        )
        assert event.event_type == TriggerEventType.CALL
        assert "跟注" in event.description


class TestCreatePlayerMessageEvent:
    """create_player_message_event 测试"""

    def test_player_message_event(self):
        event = create_player_message_event(
            player_id="p1",
            player_name="玩家",
            message="你们谁最厉害？",
        )
        assert event.event_type == TriggerEventType.PLAYER_MESSAGE
        assert event.must_respond is True
        assert "玩家" in event.description
        assert "你们谁最厉害？" in event.description


# ============================================================
# 降级反应测试
# ============================================================


class TestFallbackReaction:
    """_get_fallback_reaction 降级反应测试"""

    def test_each_personality_has_fallback(self):
        """每种性格都有降级反应文本"""
        for personality in ["aggressive", "conservative", "analytical", "intuitive", "bluffer"]:
            agent = make_agent(personality=personality)
            event = make_trigger_event()
            fallback = _get_fallback_reaction(event, agent)
            assert isinstance(fallback, str)
            assert len(fallback) > 0

    def test_unknown_personality_fallback(self):
        """未知性格也能返回降级反应"""
        agent = make_agent()
        agent.personality = "unknown_type"
        event = make_trigger_event()
        fallback = _get_fallback_reaction(event, agent)
        assert isinstance(fallback, str)
        assert len(fallback) > 0


# ============================================================
# _pick_most_talkative 测试
# ============================================================


class TestPickMostTalkative:
    """_pick_most_talkative 选择最健谈 AI 测试"""

    def test_picks_highest_talk_frequency(self):
        engine = ChatEngine()
        agents = [
            make_agent(agent_id="a1", personality="conservative"),  # 0.25
            make_agent(agent_id="a2", personality="aggressive"),  # 0.8
            make_agent(agent_id="a3", personality="analytical"),  # 0.45
        ]
        result = engine._pick_most_talkative(agents)
        assert result is not None
        assert result.agent_id == "a2"

    def test_excludes_specified_id(self):
        engine = ChatEngine()
        agents = [
            make_agent(agent_id="a1", personality="aggressive"),  # 0.8 (excluded)
            make_agent(agent_id="a2", personality="analytical"),  # 0.45
            make_agent(agent_id="a3", personality="conservative"),  # 0.25
        ]
        result = engine._pick_most_talkative(agents, exclude_id="a1")
        assert result is not None
        assert result.agent_id == "a2"

    def test_empty_list_returns_none(self):
        engine = ChatEngine()
        result = engine._pick_most_talkative([])
        assert result is None

    def test_all_excluded_returns_none(self):
        engine = ChatEngine()
        agents = [make_agent(agent_id="a1")]
        result = engine._pick_most_talkative(agents, exclude_id="a1")
        assert result is None


# ============================================================
# 统计：should_respond 在多次调用中的概率分布
# ============================================================


class TestShouldRespondDistribution:
    """验证 should_respond 的概率分布大致正确"""

    def test_aggressive_big_raise_mostly_responds(self):
        """激进型对大幅加注应该大多数情况回应"""
        engine = ChatEngine()
        agent = make_agent(personality="aggressive")
        event = make_trigger_event(event_type=TriggerEventType.BIG_RAISE)

        responses = sum(1 for _ in range(1000) if engine.should_respond(event, agent))
        # 期望概率约 0.85，允许偏差
        assert responses > 700, f"Expected >700 responses, got {responses}"

    def test_conservative_call_rarely_responds(self):
        """保守型对跟注应该很少回应"""
        engine = ChatEngine()
        agent = make_agent(personality="conservative")
        event = make_trigger_event(event_type=TriggerEventType.CALL)

        responses = sum(1 for _ in range(1000) if engine.should_respond(event, agent))
        # 期望概率约 0.065，允许偏差
        assert responses < 150, f"Expected <150 responses, got {responses}"
