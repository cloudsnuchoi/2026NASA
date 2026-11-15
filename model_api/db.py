"""Read-only Postgres access (pg8000, BSD licence). The API never writes data tables."""

from __future__ import annotations

import os
import threading
from pathlib import Path

_local = threading.local()


class DBUnavailable(RuntimeError):
    pass


def _pgpass_lookup(host: str, port: str, db: str, user: str) -> str | None:
    path = Path(os.environ.get("PGPASSFILE", Path.home() / ".pgpass"))
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return None
    for line in lines:
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        if len(parts) < 5:
            continue
        h, p, d, u = parts[:4]
        pw = ":".join(parts[4:])
        if all(a in ("*", b) for a, b in ((h, host), (p, port), (d, db), (u, user))):
            return pw
    return None


def conn_params() -> dict:
    host = os.environ.get("PGHOST", "127.0.0.1")
    port = os.environ.get("PGPORT", "5433")
    db = os.environ.get("PGDATABASE", "fieldshift")
    user = os.environ.get("PGUSER", "hk")
    pw = os.environ.get("PGPASSWORD") or _pgpass_lookup(host, port, db, user)
    return {"host": host, "port": int(port), "database": db, "user": user, "password": pw}


def _connect():
    import pg8000.dbapi

    try:
        conn = pg8000.dbapi.connect(timeout=5, **conn_params())
    except Exception as exc:  # network / auth
        raise DBUnavailable(str(exc)) from exc
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY")
    cur.execute("SET statement_timeout = 15000")
    return conn


def query(sql: str, params: tuple | list = ()) -> list[dict]:
    """Run a read-only query; return rows as dicts. Reconnects once on a broken connection."""
    for attempt in (0, 1):
        conn = getattr(_local, "conn", None)
        if conn is None:
            conn = _local.conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute(sql, tuple(params))
            if cur.description is None:
                return []
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception as exc:
            _local.conn = None
            try:
                conn.close()
            except Exception:
                pass
            import pg8000.exceptions

            if attempt == 0 and isinstance(exc, (pg8000.exceptions.InterfaceError, OSError)):
                continue
            raise


def available() -> bool:
    try:
        query("SELECT 1 AS ok")
        return True
    except Exception:
        return False
