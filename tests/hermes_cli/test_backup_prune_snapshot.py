import sqlite3
import time
import zipfile
from argparse import Namespace
from pathlib import Path


def test_prune_older_than_drops_old_sessions_from_the_archived_copy_only(tmp_path, monkeypatch):
    from hermes_cli import backup as backup_mod
    from hermes_state import SessionDB

    home = tmp_path / ".hermes"
    home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    old = time.time() - 200 * 86400
    with SessionDB(db_path=home / "state.db") as db:
        for sid in ("old", "new"):
            db.create_session(sid, source="cli")
            db.append_message(sid, role="user", content="x")
            db.end_session(sid, "user_exit")
        db._conn.execute("UPDATE sessions SET started_at=?, ended_at=? WHERE id='old'", (old, old))
        db._conn.execute("UPDATE messages SET timestamp=? WHERE session_id='old'", (old,))
        db._conn.commit()

    out = tmp_path / "b.zip"
    assert backup_mod.run_backup(Namespace(output=str(out), keep=0, prune_older_than=90))

    archived = tmp_path / "archived.db"
    with zipfile.ZipFile(out) as zf:
        archived.write_bytes(zf.read("state.db"))
    with sqlite3.connect(archived) as conn:
        assert [r[0] for r in conn.execute("SELECT id FROM sessions")] == ["new"]
    with sqlite3.connect(home / "state.db") as conn:
        assert sorted(r[0] for r in conn.execute("SELECT id FROM sessions")) == ["new", "old"]
