"""Sistema de monitoramento de atividade MCP.

Registra chamadas de tools feitas pelo agente de IA e expoe metricas
para o frontend via API REST.
"""

import json
import logging
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_activity_file = os.getenv("OTRS_ACTIVITY_FILE", "activity.json")
_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_file(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"events": [], "summary": _empty_summary()}
    return {"events": [], "summary": _empty_summary()}


def _empty_summary() -> dict:
    return {
        "total_calls": 0,
        "by_tool": {},
        "by_status": {"success": 0, "error": 0},
        "last_24h": {"calls": 0, "by_tool": {}},
    }


def _rebuild_summary(events: list[dict]) -> dict:
    summary = _empty_summary()
    cutoff_epoch = time.time() - 86400

    for event in events:
        tool = event.get("tool", "unknown")
        status = event.get("status", "error")
        ts_iso = event.get("timestamp_iso", "")

        summary["total_calls"] += 1
        summary["by_tool"][tool] = summary["by_tool"].get(tool, 0) + 1
        summary["by_status"][status] = summary["by_status"].get(status, 0) + 1

        try:
            event_time = datetime.fromisoformat(ts_iso).timestamp()
            if event_time >= cutoff_epoch:
                summary["last_24h"]["calls"] += 1
                summary["last_24h"]["by_tool"][tool] = (
                    summary["last_24h"]["by_tool"].get(tool, 0) + 1
                )
        except (ValueError, TypeError):
            pass

    return summary


def record_tool_call(
    tool: str,
    status: str,
    duration_ms: float,
    params: dict[str, Any] | None = None,
    error: str | None = None,
    ticket_id: str | None = None,
) -> None:
    """Registra uma chamada de tool MCP.

    Falha silenciosamente se o arquivo de atividade não for acessível
    (ex: container MCP sem volume montado).
    """
    path = Path(_activity_file)

    # Se o diretório pai não existe, não tenta escrever (container sem volume)
    if not path.parent.exists():
        return

    event = {
        "tool": tool,
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "timestamp": time.time(),
        "timestamp_iso": _now_iso(),
        "ticket_id": ticket_id,
    }
    if error:
        event["error"] = error
    if params:
        safe_params = {k: v for k, v in params.items() if k not in ("password",)}
        event["params"] = safe_params

    with _lock:
        data = _ensure_file(path)
        data["events"].append(event)

        max_events = int(os.getenv("OTRS_ACTIVITY_MAX_EVENTS", "1000"))
        if len(data["events"]) > max_events:
            data["events"] = data["events"][-max_events:]

        data["summary"] = _rebuild_summary(data["events"])

        try:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, str(path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            logger.error("Erro ao salvar atividade: %s", e)


def get_activity(
    limit: int = 50,
    tool_filter: str | None = None,
    status_filter: str | None = None,
) -> dict:
    """Retorna eventos de atividade com filtros."""
    path = Path(_activity_file)

    with _lock:
        data = _ensure_file(path)

    events = data["events"]

    if tool_filter:
        events = [e for e in events if e.get("tool") == tool_filter]
    if status_filter:
        events = [e for e in events if e.get("status") == status_filter]

    events = events[-limit:]
    events.reverse()

    return {
        "events": events,
        "summary": data["summary"],
    }


def get_summary() -> dict:
    """Retorna resumo de atividade."""
    path = Path(_activity_file)

    with _lock:
        data = _ensure_file(path)

    return data["summary"]


def clear_activity() -> None:
    """Limpa todos os registros de atividade."""
    path = Path(_activity_file)

    with _lock:
        data = {"events": [], "summary": _empty_summary()}
        try:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, str(path))
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except OSError as e:
            logger.error("Erro ao limpar atividade: %s", e)
