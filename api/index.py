"""
Vercel entrypoint.

Vercel's filesystem is read-only at runtime (only /tmp is writable), so the
bundled, pre-seeded nutrients.db can't be opened directly in place — SQLite
needs to create rollback-journal files next to it for any write transaction,
and app.main's lifespan calls Base.metadata.create_all() on startup. Copying
it into /tmp once per cold start sidesteps that entirely; the app is
read-only at request time, so every cold start serves the same seeded data.
"""
import os
import shutil

_SRC_DB = os.path.join(os.path.dirname(__file__), "..", "nutrients.db")
_TMP_DB = "/tmp/nutrients.db"

if not os.path.exists(_TMP_DB):
    shutil.copy(_SRC_DB, _TMP_DB)

os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

from app.main import app  # noqa: E402
