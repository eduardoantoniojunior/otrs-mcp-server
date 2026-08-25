"""Modulo de banco de dados SQLite para o OTRS MCP Server.

Gerencia a conexao, schema e operacoes CRUD para usuarios, API keys e uso.
"""

import hashlib
import logging
import os
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = os.getenv("OTRS_DB_PATH", "/data/otrs-mcp.db")
_lock = threading.Lock()
_initialized = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db_path() -> str:
    return os.getenv("OTRS_DB_PATH", _DEFAULT_DB_PATH)


def _connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-64000")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Inicializa o schema do banco de dados."""
    global _initialized
    with _lock:
        if _initialized:
            return
        conn = _connect(db_path)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
            _initialized = True
            logger.info("Banco de dados inicializado: %s", db_path or get_db_path())
        finally:
            conn.close()


@contextmanager
def get_db(db_path: str | None = None):
    """Context manager para obter uma conexao ao banco."""
    conn = _connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------


def generate_api_key() -> str:
    """Gera uma chave de API segura. Formato: sk-otrs-{64 hex chars}."""
    random_bytes = secrets.token_hex(32)
    return f"sk-otrs-{random_bytes}"


def hash_api_key(api_key: str) -> str:
    """Gera hash SHA-256 de uma chave de API."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_api_key(
    name: str,
    agent_name: str,
    permissions: list[str] | None = None,
    rate_limit: int = 100,
    expires_in_days: int | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Cria uma nova API key e retorna o valor bruto (mostrado apenas uma vez)."""
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:12]

    expires_at = None
    if expires_in_days:
        from datetime import timedelta

        expires_at = (
            datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        ).isoformat()

    with get_db(db_path) as conn:
        conn.execute(
            """INSERT INTO api_keys (name, key_hash, key_prefix, agent_name, permissions, rate_limit, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                key_hash,
                key_prefix,
                agent_name,
                _json_dumps(permissions or ["read"]),
                rate_limit,
                expires_at,
                _now_iso(),
            ),
        )
        key_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    logger.info("API key criada: id=%d, name=%s, agent=%s", key_id, name, agent_name)
    return {
        "id": key_id,
        "key": raw_key,
        "key_prefix": key_prefix,
        "name": name,
        "agent_name": agent_name,
    }


def verify_api_key(api_key: str, db_path: str | None = None) -> dict[str, Any] | None:
    """Verifica uma API key e retorna o registro se valida, None caso contrario."""
    key_hash = hash_api_key(api_key)
    now = _now_iso()

    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT id, name, agent_name, permissions, rate_limit, expires_at, active
               FROM api_keys WHERE key_hash = ?""",
            (key_hash,),
        ).fetchone()

        if row is None:
            return None

        if not row["active"]:
            return None

        if row["expires_at"] and row["expires_at"] < now:
            return None

        # Atualiza uso
        conn.execute(
            """UPDATE api_keys SET usage_count = usage_count + 1, last_used_at = ? WHERE id = ?""",
            (now, row["id"]),
        )

        return {
            "id": row["id"],
            "name": row["name"],
            "agent_name": row["agent_name"],
            "permissions": _json_loads(row["permissions"]),
            "rate_limit": row["rate_limit"],
        }


def list_api_keys(
    include_inactive: bool = False, db_path: str | None = None
) -> list[dict[str, Any]]:
    """Lista todas as API keys (sem expor hashes)."""
    with get_db(db_path) as conn:
        if include_inactive:
            rows = conn.execute(
                """SELECT id, name, key_prefix, agent_name, permissions, active,
                          usage_count, last_used_at, created_at, expires_at
                   FROM api_keys ORDER BY created_at DESC"""
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, name, key_prefix, agent_name, permissions, active,
                          usage_count, last_used_at, created_at, expires_at
                   FROM api_keys WHERE active = 1 ORDER BY created_at DESC"""
            ).fetchall()

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "key_prefix": r["key_prefix"],
            "agent_name": r["agent_name"],
            "permissions": _json_loads(r["permissions"]),
            "active": bool(r["active"]),
            "usage_count": r["usage_count"],
            "last_used_at": r["last_used_at"],
            "created_at": r["created_at"],
            "expires_at": r["expires_at"],
        }
        for r in rows
    ]


def revoke_api_key(key_id: int, db_path: str | None = None) -> bool:
    """Revoga (desativa) uma API key."""
    with get_db(db_path) as conn:
        cursor = conn.execute("UPDATE api_keys SET active = 0 WHERE id = ?", (key_id,))
        return cursor.rowcount > 0


def delete_api_key(key_id: int, db_path: str | None = None) -> bool:
    """Remove permanentemente uma API key."""
    with get_db(db_path) as conn:
        cursor = conn.execute("DELETE FROM api_keys WHERE id = ?", (key_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Admin Users
# ---------------------------------------------------------------------------


def create_admin_user(
    username: str, password: str, db_path: str | None = None
) -> dict[str, Any]:
    """Cria um usuario administrador. Senha armazenada com hash."""
    from passlib.hash import bcrypt

    password_hash = bcrypt.hash(password)
    with get_db(db_path) as conn:
        try:
            conn.execute(
                """INSERT INTO admin_users (username, password_hash, created_at)
                   VALUES (?, ?, ?)""",
                (username, password_hash, _now_iso()),
            )
            user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        except sqlite3.IntegrityError:
            raise ValueError(f"Usuario '{username}' ja existe")

    logger.info("Usuario admin criado: id=%d, username=%s", user_id, username)
    return {"id": user_id, "username": username}


def verify_admin_user(
    username: str, password: str, db_path: str | None = None
) -> dict[str, Any] | None:
    """Verifica credenciais de um usuario admin. Retorna dict com id/username ou None."""
    from passlib.hash import bcrypt

    with get_db(db_path) as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, active FROM admin_users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None or not row["active"]:
        return None

    if not bcrypt.verify(password, row["password_hash"]):
        return None

    return {"id": row["id"], "username": row["username"]}


def list_admin_users(db_path: str | None = None) -> list[dict[str, Any]]:
    """Lista usuarios administradores (sem hashes)."""
    with get_db(db_path) as conn:
        rows = conn.execute(
            "SELECT id, username, active, created_at FROM admin_users ORDER BY created_at"
        ).fetchall()

    return [
        {
            "id": r["id"],
            "username": r["username"],
            "active": bool(r["active"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def delete_admin_user(user_id: int, db_path: str | None = None) -> bool:
    """Remove um usuario admin."""
    with get_db(db_path) as conn:
        cursor = conn.execute("DELETE FROM admin_users WHERE id = ?", (user_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Activity Tracking (SQLite-based, supplementing activity.json)
# ---------------------------------------------------------------------------


def record_activity(
    tool: str,
    status: str,
    duration_ms: float,
    api_key_id: int | None = None,
    agent_name: str | None = None,
    params: dict[str, Any] | None = None,
    error: str | None = None,
    ticket_id: str | None = None,
    db_path: str | None = None,
) -> None:
    """Registra uma chamada de tool no banco de dados."""
    safe_params = {k: v for k, v in (params or {}).items() if k not in ("password",)}
    with get_db(db_path) as conn:
        conn.execute(
            """INSERT INTO api_usage (api_key_id, agent_name, tool, status, duration_ms, params, error, ticket_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                api_key_id,
                agent_name,
                tool,
                status,
                round(duration_ms, 2),
                _json_dumps(safe_params),
                error,
                ticket_id,
                _now_iso(),
            ),
        )


def get_activity_log(
    limit: int = 50,
    tool_filter: str | None = None,
    status_filter: str | None = None,
    agent_filter: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """Retorna log de atividade com filtros."""
    conditions = []
    params: list[Any] = []

    if tool_filter:
        conditions.append("tool = ?")
        params.append(tool_filter)
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if agent_filter:
        conditions.append("agent_name = ?")
        params.append(agent_filter)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with get_db(db_path) as conn:
        rows = conn.execute(
            f"""SELECT id, api_key_id, agent_name, tool, status, duration_ms,
                       params, error, ticket_id, created_at
                FROM api_usage {where}
                ORDER BY created_at DESC LIMIT ?""",
            (*params, limit),
        ).fetchall()

        summary = conn.execute("""SELECT
                 COUNT(*) as total,
                 SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                 SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
               FROM api_usage""").fetchone()

    return {
        "events": [
            {
                "id": r["id"],
                "api_key_id": r["api_key_id"],
                "agent_name": r["agent_name"],
                "tool": r["tool"],
                "status": r["status"],
                "duration_ms": r["duration_ms"],
                "params": _json_loads(r["params"]),
                "error": r["error"],
                "ticket_id": r["ticket_id"],
                "created_at": r["created_at"],
            }
            for r in rows
        ],
        "summary": {
            "total": summary["total"],
            "success_count": summary["success_count"] or 0,
            "error_count": summary["error_count"] or 0,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_dumps(obj: Any) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: str | None) -> Any:
    if not s:
        return None
    import json

    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    key_hash TEXT UNIQUE NOT NULL,
    key_prefix TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    permissions TEXT NOT NULL DEFAULT '["read"]',
    rate_limit INTEGER NOT NULL DEFAULT 100,
    active INTEGER NOT NULL DEFAULT 1,
    expires_at TEXT,
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS api_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key_id INTEGER,
    agent_name TEXT,
    tool TEXT NOT NULL,
    status TEXT NOT NULL,
    duration_ms REAL NOT NULL DEFAULT 0,
    params TEXT,
    error TEXT,
    ticket_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(active);
CREATE INDEX IF NOT EXISTS idx_api_usage_tool ON api_usage(tool);
CREATE INDEX IF NOT EXISTS idx_api_usage_created ON api_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_agent ON api_usage(agent_name);
"""
