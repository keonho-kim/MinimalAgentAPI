from fastapi import FastAPI
from fastapi.testclient import TestClient

from minial_agent.api.session import router as session_router_module
from minial_agent.api.session import service as session_service_module
from minial_agent.api.session.router import router
from minial_agent.api.session.service import SessionService, clean_session_title


def test_clean_session_title_strips_prefix_quotes_and_limits_length() -> None:
    assert clean_session_title('"제목: 오늘의 작업 계획입니다."', fallback="fallback") == (
        "오늘의 작업 계획입"
    )


def test_session_service_generates_title_with_core_llm(monkeypatch) -> None:
    calls = []

    class FakeMessage:
        content = "제목: 아주 긴 제목입니다"

    class FakeModel:
        def invoke(self, messages):
            calls.append(messages)
            return FakeMessage()

    def fake_llm_client(*, disable_streaming=False):
        assert disable_streaming is True
        return FakeModel()

    monkeypatch.setattr(session_service_module, "llm_client", fake_llm_client)

    title = SessionService().create_title(
        user_id="user",
        uuid="session",
        message="오늘 있었던 일을 정리해줘",
    )

    assert title == "아주 긴 제목입니다"
    assert calls[0][1] == ("user", "오늘 있었던 일을 정리해줘")


def test_session_title_route_returns_generated_title(monkeypatch) -> None:
    class FakeSessionService:
        def create_title(self, *, user_id: str, uuid: str, message: str) -> str:
            assert user_id == "user"
            assert uuid == "session"
            assert message == "README를 작성해줘"
            return "README작성"

    monkeypatch.setattr(
        session_router_module,
        "session_service",
        FakeSessionService(),
    )
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.post(
        "/api/session/title",
        json={
            "user_id": "user",
            "uuid": "session",
            "message": "README를 작성해줘",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"title": "README작성"}
