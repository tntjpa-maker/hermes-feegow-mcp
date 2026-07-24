import sqlite3
from pathlib import Path


class SyncStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self):
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS booking_map (
                    cal_uid TEXT PRIMARY KEY,
                    cal_booking_id INTEGER,
                    feegow_appointment_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS processed_events (
                    event_key TEXT PRIMARY KEY,
                    trigger_event TEXT NOT NULL,
                    cal_uid TEXT,
                    processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def event_processed(self, event_key: str) -> bool:
        with self._connect() as db:
            row = db.execute(
                "SELECT 1 FROM processed_events WHERE event_key = ?",
                (event_key,),
            ).fetchone()
        return row is not None

    def mark_event(self, event_key: str, trigger: str, uid: str):
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO processed_events(event_key, trigger_event, cal_uid) VALUES (?, ?, ?)",
                (event_key, trigger, uid),
            )

    def save_mapping(self, uid: str, booking_id, appointment_id: int, status: str):
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO booking_map(cal_uid, cal_booking_id, feegow_appointment_id, status)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(cal_uid) DO UPDATE SET
                    cal_booking_id=excluded.cal_booking_id,
                    feegow_appointment_id=excluded.feegow_appointment_id,
                    status=excluded.status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (uid, booking_id, appointment_id, status),
            )

    def get_mapping(self, *uids: str):
        candidates = [uid for uid in uids if uid]
        if not candidates:
            return None
        placeholders = ",".join("?" for _ in candidates)
        with self._connect() as db:
            row = db.execute(
                f"SELECT * FROM booking_map WHERE cal_uid IN ({placeholders}) ORDER BY updated_at DESC LIMIT 1",
                candidates,
            ).fetchone()
        return dict(row) if row else None

    def update_status(self, uid: str, status: str):
        with self._connect() as db:
            db.execute(
                "UPDATE booking_map SET status=?, updated_at=CURRENT_TIMESTAMP WHERE cal_uid=?",
                (status, uid),
            )
