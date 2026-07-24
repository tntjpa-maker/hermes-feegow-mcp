import hashlib
import json

from ana_feegow.webhooks.cal_parser import parse_booking


class SyncHandler:
    def __init__(self, store, service):
        self.store = store
        self.service = service

    @staticmethod
    def event_key(envelope: dict) -> str:
        canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def handle(self, envelope: dict):
        trigger = envelope.get("triggerEvent")
        if trigger not in {
            "BOOKING_PAID",
            "BOOKING_RESCHEDULED",
            "BOOKING_CANCELLED",
        }:
            return {"status": "ignored", "trigger": trigger}

        payload = envelope.get("payload") or {}
        uid = str(payload.get("uid") or "")
        key = self.event_key(envelope)
        if self.store.event_processed(key):
            return {"status": "duplicate", "trigger": trigger, "uid": uid}

        if trigger == "BOOKING_PAID":
            booking = parse_booking(envelope)
            existing = self.store.get_mapping(booking.uid)
            if existing:
                self.store.mark_event(key, trigger, booking.uid)
                return {"status": "duplicate", "trigger": trigger, "uid": booking.uid}
            appointment_id = self.service.create_booking(booking)
            self.store.save_mapping(
                booking.uid,
                booking.booking_id,
                appointment_id,
                "scheduled",
            )

        elif trigger == "BOOKING_RESCHEDULED":
            booking = parse_booking(envelope)
            previous_uid = str(
                payload.get("rescheduleUid")
                or payload.get("rescheduledFromUid")
                or payload.get("previousBookingUid")
                or ""
            )
            mapping = self.store.get_mapping(booking.uid, previous_uid)
            if not mapping:
                raise LookupError("Reserva Cal.com sem vínculo com o Feegow.")
            self.service.reschedule_booking(
                mapping["feegow_appointment_id"],
                booking,
            )
            self.store.save_mapping(
                booking.uid,
                booking.booking_id,
                mapping["feegow_appointment_id"],
                "rescheduled",
            )

        else:
            mapping = self.store.get_mapping(
                uid,
                str(payload.get("rescheduleUid") or ""),
            )
            if not mapping:
                raise LookupError("Reserva Cal.com sem vínculo com o Feegow.")
            self.service.cancel_booking(mapping["feegow_appointment_id"])
            self.store.update_status(mapping["cal_uid"], "cancelled")

        self.store.mark_event(key, trigger, uid)
        return {"status": "processed", "trigger": trigger, "uid": uid}
