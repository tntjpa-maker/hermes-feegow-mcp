import json
import sqlite3
from dataclasses import asdict
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
                CREATE TABLE IF NOT EXISTS pending_bookings (
                    cal_uid TEXT PRIMARY KEY,
                    cal_booking_id INTEGER,
                    booking_json TEXT NOT NULL,
                    pagbank_checkout_id TEXT NOT NULL,
                    payment_url TEXT NOT NULL,
                    payment_status TEXT NOT NULL DEFAULT 'WAITING',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            self._ensure_transaction_column(db)

    def _ensure_transaction_column(self, db):
        existentes = {row["name"] for row in db.execute("PRAGMA table_info(booking_map)")}
        if "pagbank_transaction_id" not in existentes:
            db.execute("ALTER TABLE booking_map ADD COLUMN pagbank_transaction_id TEXT")

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

    def save_mapping(
        self,
        uid: str,
        booking_id,
        appointment_id: int,
        status: str,
        pagbank_transaction_id: str = None,
    ):
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO booking_map(cal_uid, cal_booking_id, feegow_appointment_id, status, pagbank_transaction_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cal_uid) DO UPDATE SET
                    cal_booking_id=excluded.cal_booking_id,
                    feegow_appointment_id=excluded.feegow_appointment_id,
                    status=excluded.status,
                    pagbank_transaction_id=COALESCE(excluded.pagbank_transaction_id, booking_map.pagbank_transaction_id),
                    updated_at=CURRENT_TIMESTAMP
                """,
                (uid, booking_id, appointment_id, status, pagbank_transaction_id),
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

    def save_pending_booking(
        self,
        booking,
        checkout_id: str,
        payment_url: str,
        payment_status: str = "WAITING",
    ):
        booking_json = json.dumps(asdict(booking), ensure_ascii=False)
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO pending_bookings(
                    cal_uid, cal_booking_id, booking_json,
                    pagbank_checkout_id, payment_url, payment_status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(cal_uid) DO UPDATE SET
                    cal_booking_id=excluded.cal_booking_id,
                    booking_json=excluded.booking_json,
                    pagbank_checkout_id=excluded.pagbank_checkout_id,
                    payment_url=excluded.payment_url,
                    payment_status=excluded.payment_status,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    booking.uid,
                    booking.booking_id,
                    booking_json,
                    checkout_id,
                    payment_url,
                    payment_status,
                ),
            )

    def get_pending_booking(self, uid: str):
        if not uid:
            return None
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM pending_bookings WHERE cal_uid = ?",
                (uid,),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["booking"] = json.loads(result.pop("booking_json"))
        return result

    def update_pending_status(self, uid: str, status: str):
        with self._connect() as db:
            db.execute(
                """
                UPDATE pending_bookings
                SET payment_status=?, updated_at=CURRENT_TIMESTAMP
                WHERE cal_uid=?
                """,
                (status, uid),
            )

    def list_pending_expirados(self, minutos: int):
        # Reservas que continuam "WAITING" (nunca foram pagas nem canceladas)
        # há mais de `minutos` minutos, contando a partir da última mudança
        # de status (updated_at). SQLite guarda CURRENT_TIMESTAMP em UTC,
        # então a comparação abaixo também usa UTC - consistente.
        with self._connect() as db:
            rows = db.execute(
                """
                SELECT * FROM pending_bookings
                WHERE payment_status = 'WAITING'
                  AND updated_at <= datetime('now', ?)
                """,
                (f"-{int(minutos)} minutes",),
            ).fetchall()
        resultados = []
        for row in rows:
            item = dict(row)
            item["booking"] = json.loads(item.pop("booking_json"))
            resultados.append(item)
        return resultados
