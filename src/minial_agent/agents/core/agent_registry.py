import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from .agent_builder import AgentBuilder


@dataclass
class _AgentEntry:
    agent: Any
    created_at: float
    last_used_at: float


class AgentRegistry:
    def __init__(
        self,
        builder: AgentBuilder | None = None,
        max_agents: int = 128,
        ttl_seconds: int = 60 * 60,
    ) -> None:
        self.builder = builder or AgentBuilder()
        self.max_agents = max_agents
        self.ttl_seconds = ttl_seconds
        self._agents: OrderedDict[str, _AgentEntry] = OrderedDict()

    def get_agent(self, user_id: str, uuid: str) -> Any:
        self._cleanup_expired()

        key = self._key(user_id=user_id, uuid=uuid)
        now = time.monotonic()

        if key in self._agents:
            entry = self._agents.pop(key)
            entry.last_used_at = now
            self._agents[key] = entry
            return entry.agent

        agent = self.builder.get_agent(user_id=user_id, uuid=uuid)
        self._agents[key] = _AgentEntry(
            agent=agent,
            created_at=now,
            last_used_at=now,
        )
        self._cleanup_overflow()
        return agent

    def delete_agent(self, user_id: str, uuid: str) -> None:
        self._agents.pop(self._key(user_id=user_id, uuid=uuid), None)

    def _cleanup_expired(self) -> None:
        if self.ttl_seconds <= 0:
            return

        now = time.monotonic()
        expired_keys = [
            key
            for key, entry in self._agents.items()
            if now - entry.last_used_at > self.ttl_seconds
        ]

        for key in expired_keys:
            self._agents.pop(key, None)

    def _cleanup_overflow(self) -> None:
        while len(self._agents) > self.max_agents:
            self._agents.popitem(last=False)

    def _key(self, user_id: str, uuid: str) -> str:
        return f"{user_id}:{uuid}"
