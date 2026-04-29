from minial_agent.agents.core.agent_registry import AgentRegistry


class FakeBuilder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get_agent(self, user_id: str, uuid: str) -> object:
        self.calls.append((user_id, uuid))
        return object()


def test_agent_registry_reuses_same_session() -> None:
    builder = FakeBuilder()
    registry = AgentRegistry(builder=builder)

    first = registry.get_agent(user_id="user", uuid="session")
    second = registry.get_agent(user_id="user", uuid="session")

    assert first is second
    assert builder.calls == [("user", "session")]


def test_agent_registry_creates_different_sessions() -> None:
    builder = FakeBuilder()
    registry = AgentRegistry(builder=builder)

    first = registry.get_agent(user_id="user", uuid="one")
    second = registry.get_agent(user_id="user", uuid="two")

    assert first is not second
    assert builder.calls == [("user", "one"), ("user", "two")]


def test_agent_registry_cleans_up_expired_sessions() -> None:
    builder = FakeBuilder()
    registry = AgentRegistry(builder=builder, ttl_seconds=1)

    first = registry.get_agent(user_id="user", uuid="session")
    registry._agents["user:session"].last_used_at -= 2
    second = registry.get_agent(user_id="user", uuid="session")

    assert first is not second
    assert builder.calls == [("user", "session"), ("user", "session")]


def test_agent_registry_evicts_oldest_session() -> None:
    builder = FakeBuilder()
    registry = AgentRegistry(builder=builder, max_agents=1)

    first = registry.get_agent(user_id="user", uuid="one")
    second = registry.get_agent(user_id="user", uuid="two")
    third = registry.get_agent(user_id="user", uuid="one")

    assert first is not second
    assert third is not first
    assert builder.calls == [("user", "one"), ("user", "two"), ("user", "one")]
