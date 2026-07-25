import hashlib
import json

from ana_feegow.webhooks.cal_parser import CalBooking


class PagBankHandler:
    def __init__(self, store, service):
        self.store = store
        self.service = service

    @staticmethod
    def event_key(payload: dict) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "pagbank:" + hashlib.sha256(canonical.encode()).hexdigest()

    @staticmethod
    def payment_status(payload: dict) -> str:
        charges = payload.get("charges") or []
        for charge in charges:
            if str(charge.get("status", "")).upper() == "PAID":
                return "PAID"
        return str(payload.get("status") or "").upper()

    @staticmethod
    def reference_id(payload: dict) -> str:
        return str(
            payload.get("reference_id")
            or (payload.get("checkout") or {}).get("reference_id")
            or (payload.get("order") or {}).get("reference_id")
            or ""
        )

    def handle(self, payload: dict):
        key = self.event_key(payload)
        uid = self.reference_id(payload)
        status = self.payment_status(payload)

        if self.store.event_processed(key):
            return {"status": "duplicate", "payment_status": status, "uid": uid}

        if not uid:
            raise ValueError("reference_id ausente na notificação PagBank.")

        pending = self.store.get_pending_booking(uid)
        if status != "PAID":
            if pending:
                self.store.update_pending_status(uid, status or "UNKNOWN")
            self.store.mark_event(key, f"PAGBANK_{status or 'UNKNOWN'}", uid)
            return {"status": "recorded", "payment_status": status, "uid": uid}

        mapping = self.store.get_mapping(uid)
        if mapping:
            self.store.update_pending_status(uid, "PAID")
            self.store.mark_event(key, "PAGBANK_PAID", uid)
            return {"status": "duplicate", "payment_status": status, "uid": uid}

        if not pending:
            raise LookupError("Pagamento sem reserva Cal.com pendente.")

        booking = CalBooking(**pending["booking"])
        appointment_id = self.service.create_booking(booking)
        self.store.save_mapping(
            booking.uid,
            booking.booking_id,
            appointment_id,
            "scheduled",
        )
        self.store.update_pending_status(uid, "PAID")
        self.store.mark_event(key, "PAGBANK_PAID", uid)
        return {
            "status": "processed",
            "payment_status": status,
            "uid": uid,
            "feegow_appointment_id": appointment_id,
        }
