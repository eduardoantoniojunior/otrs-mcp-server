"""Testes para o sistema de atividade (activity.py)."""

import json
from pathlib import Path

import pytest

from otrs_mcp import activity


@pytest.fixture(autouse=True)
def isolated_activity_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Cada teste opera sobre um activity.json unico no tmp_path."""
    file_path = tmp_path / "activity.json"
    monkeypatch.setattr(activity, "_activity_file", str(file_path))
    return file_path


def _read_events(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["events"]


class TestRecordToolCallBlocklist:
    """record_tool_call deve filtrar campos sensiveis dos params gravados."""

    def test_password_is_dropped(self, isolated_activity_file: Path) -> None:
        activity.record_tool_call(
            tool="dummy",
            status="success",
            duration_ms=1.0,
            params={"user": "eve", "password": "s3cret"},
        )

        events = _read_events(isolated_activity_file)
        assert events[0]["params"] == {"user": "eve"}

    def test_body_is_dropped(self, isolated_activity_file: Path) -> None:
        """Body de ticket/artigo nao pode vazar para o log."""
        activity.record_tool_call(
            tool="create_ticket",
            status="success",
            duration_ms=1.0,
            params={"title": "T", "body": "conteudo sensivel do cliente"},
        )

        events = _read_events(isolated_activity_file)
        assert "body" not in events[0]["params"]
        assert events[0]["params"] == {"title": "T"}

    def test_articles_are_dropped(self, isolated_activity_file: Path) -> None:
        """Chaves article/articles (qualquer case) sao removidas."""
        activity.record_tool_call(
            tool="get_ticket",
            status="success",
            duration_ms=1.0,
            params={
                "ticket_id": "1",
                "Article": [{"Body": "x"}],
                "articles": [{"Body": "y"}],
            },
        )

        events = _read_events(isolated_activity_file)
        assert events[0]["params"] == {"ticket_id": "1"}

    def test_article_prefix_keys_are_kept(self, isolated_activity_file: Path) -> None:
        """Chaves como article_limit/article_order nao sao mascaradas."""
        activity.record_tool_call(
            tool="get_ticket",
            status="success",
            duration_ms=1.0,
            params={
                "ticket_id": "1",
                "include_articles": True,
                "article_limit": 5,
                "article_order": "desc",
                "article_sender_type": "customer",
            },
        )

        events = _read_events(isolated_activity_file)
        assert events[0]["params"] == {
            "ticket_id": "1",
            "include_articles": True,
            "article_limit": 5,
            "article_order": "desc",
            "article_sender_type": "customer",
        }
