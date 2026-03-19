"""AI Agent 管理器

负责 Agent 实例的创建、获取、销毁等生命周期管理。
在游戏创建时根据配置批量创建 Agent，游戏结束时清理资源。
"""

from __future__ import annotations

import logging
import random
from typing import Any

from app.agents.base_agent import BaseAgent
from app.config import (
    AI_AVATARS,
    AI_NAMES,
    ALL_MODELS,
)

logger = logging.getLogger(__name__)


class AgentManager:
    """Agent 实例的生命周期管理器

    维护 game_id -> {agent_id -> BaseAgent} 的两级映射，
    支持多场游戏同时进行。

    Usage:
        manager = AgentManager()
        agents = manager.create_agents_for_game(
            game_id="game-1",
            agent_configs=[
                {"model_id": "copilot-gpt4o"},
                {"model_id": "copilot-claude-sonnet"},
            ],
        )
        agent = manager.get_agent("game-1", agents[0].agent_id)
        manager.remove_game("game-1")
    """

    def __init__(self) -> None:
        # game_id -> {agent_id -> BaseAgent}
        self._agents: dict[str, dict[str, BaseAgent]] = {}

    def create_agents_for_game(
        self,
        game_id: str,
        agent_configs: list[dict[str, Any]],
    ) -> list[BaseAgent]:
        """为一场游戏创建多个 AI Agent

        Args:
            game_id: 游戏 ID
            agent_configs: 每个 Agent 的配置列表，每项可包含:
                - agent_id: 指定 ID（可选，不指定则自动生成）
                - name: 显示名称（可选，不指定则随机分配）
                - model_id: 模型标识（可选，未指定则使用默认模型）

        Returns:
            创建的 BaseAgent 列表
        """
        if game_id in self._agents:
            logger.warning("Game '%s' already has agents, clearing old ones", game_id)
            self._agents[game_id] = {}

        agents: list[BaseAgent] = []
        used_names: set[str] = set()

        for i, config in enumerate(agent_configs):
            # 分配名字
            name = config.get("name")
            if not name:
                name = self._pick_name(used_names)
            used_names.add(name)

            # 分配头像
            _avatar = config.get("avatar", AI_AVATARS[i % len(AI_AVATARS)])

            # 模型 — 使用动态回退逻辑
            model_id = config.get("model_id")
            if model_id and model_id not in ALL_MODELS:
                from app.config import get_default_model_id

                default = get_default_model_id()
                logger.warning("Unknown model '%s', using '%s'", model_id, default or "None")
                model_id = default
            elif not model_id:
                from app.config import get_default_model_id

                model_id = get_default_model_id()

            agent = BaseAgent(
                agent_id=config.get("agent_id"),
                name=name,
                model_id=model_id,
            )

            if game_id not in self._agents:
                self._agents[game_id] = {}
            self._agents[game_id][agent.agent_id] = agent
            agents.append(agent)

            logger.info(
                "Created agent: %s (model=%s) for game %s",
                agent.name,
                agent.model_id,
                game_id,
            )

        return agents

    def get_agent(self, game_id: str, agent_id: str) -> BaseAgent | None:
        """获取指定游戏中的指定 Agent

        Args:
            game_id: 游戏 ID
            agent_id: Agent ID

        Returns:
            BaseAgent 实例，不存在则返回 None
        """
        game_agents = self._agents.get(game_id)
        if game_agents is None:
            return None
        return game_agents.get(agent_id)

    def get_agents_for_game(self, game_id: str) -> list[BaseAgent]:
        """获取指定游戏的所有 Agent

        Args:
            game_id: 游戏 ID

        Returns:
            该游戏的所有 BaseAgent 列表
        """
        game_agents = self._agents.get(game_id, {})
        return list(game_agents.values())

    def remove_agent(self, game_id: str, agent_id: str) -> bool:
        """移除指定 Agent

        Args:
            game_id: 游戏 ID
            agent_id: Agent ID

        Returns:
            是否成功移除
        """
        game_agents = self._agents.get(game_id)
        if game_agents and agent_id in game_agents:
            removed = game_agents.pop(agent_id)
            logger.info("Removed agent '%s' from game '%s'", removed.name, game_id)
            return True
        return False

    def remove_game(self, game_id: str) -> bool:
        """移除整场游戏的所有 Agent，释放资源

        Args:
            game_id: 游戏 ID

        Returns:
            是否成功移除
        """
        if game_id in self._agents:
            count = len(self._agents[game_id])
            del self._agents[game_id]
            logger.info("Removed %d agents for game '%s'", count, game_id)
            return True
        return False

    def reset_agents_for_game(self, game_id: str) -> None:
        """重置指定游戏所有 Agent 的状态（用于新游戏）"""
        for agent in self.get_agents_for_game(game_id):
            agent.reset_for_new_game()
        logger.info("Reset all agents for game '%s'", game_id)

    def set_api_keys_for_game(self, game_id: str, api_keys: dict[str, str]) -> None:
        """为指定游戏的所有 Agent 设置 API Keys

        Args:
            game_id: 游戏 ID
            api_keys: provider -> key 的字典，如 {"openrouter": "sk-xxx"}
        """
        agents = self.get_agents_for_game(game_id)
        for agent in agents:
            agent.set_api_keys(api_keys)
        logger.info(
            "Set API keys for %d agents in game '%s' (providers: %s)",
            len(agents),
            game_id,
            list(api_keys.keys()),
        )

    @property
    def active_game_count(self) -> int:
        """当前活跃的游戏数量"""
        return len(self._agents)

    @property
    def total_agent_count(self) -> int:
        """当前所有游戏中的 Agent 总数"""
        return sum(len(agents) for agents in self._agents.values())

    @staticmethod
    def _pick_name(used_names: set[str]) -> str:
        """从预设名字库中选择一个未使用的名字"""
        available = [n for n in AI_NAMES if n not in used_names]
        if available:
            return random.choice(available)

        # 兜底
        return f"AI-{random.randint(1000, 9999)}"

    def __repr__(self) -> str:
        return f"AgentManager(games={self.active_game_count}, agents={self.total_agent_count})"


# 全局单例
_global_agent_manager: AgentManager | None = None


def get_agent_manager() -> AgentManager:
    """获取全局 AgentManager 单例"""
    global _global_agent_manager
    if _global_agent_manager is None:
        _global_agent_manager = AgentManager()
    return _global_agent_manager
