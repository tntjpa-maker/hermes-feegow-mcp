import hashlib
import json

from ana_feegow.webhooks.cal_parser import parse_booking


class SyncHandler:
    def __init__(self, store, service, payment_service=None):
        self.store = store
        self.service = service
        self.payment_service = payment_service

    @staticmethod
    def event_key(envelope: dict) -> str:
        canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _create_checkout(self, booking):
        if self.payment_service is None:
            raise RuntimeError("Serviço de pagamento PagBank não configurado.")
        checkout = self.payment_service.create_checkout(booking)
        self.store.save_pending_booking(
            booking,
            checkout.checkout_id,
            checkout.payment_url,
        )
        return checkout

    def handle(self, envelope: dict):
        trigger = envelope.get("triggerEvent")
        if trigger not in {
            "BOOKING_CREATED",
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

        response = {"status": "processed", "trigger": trigger, "uid": uid}

        if trigger == "BOOKING_CREATED":
            booking = parse_booking(envelope)
            existing = self.store.get_pending_booking(booking.uid)
            if existing:
                self.store.mark_event(key, trigger, booking.uid)
                return {
                    "status": "duplicate",
                    "trigger": trigger,
                    "uid": booking.uid,
                    "payment_url": existing["payment_url"],
                }
            checkout = self._create_checkout(booking)
            response["payment_url"] = checkout.payment_url

        elif trigger == "BOOKING_PAID":
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
            if mapping:
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
                pending = self.store.get_pending_booking(previous_uid or booking.uid)
                if not pending:
                    raise LookupError("Reserva Cal.com sem vínculo com o Feegow.")
                checkout = self._create_checkout(booking)
                if previous_uid and previous_uid != booking.uid:
                    self.store.update_pending_status(previous_uid, "REPLACED")
                response["payment_url"] = checkout.payment_url

        else:
            related_uid = str(payload.get("rescheduleUid") or "")
            mapping = self.store.get_mapping(uid, related_uid)
            if mapping:
                self.service.cancel_booking(mapping["feegow_appointment_id"])
                self.store.update_status(mapping["cal_uid"], "cancelled")
            else:
                pending_uid = uid or related_uid
                pending = self.store.get_pending_booking(pending_uid)
                if not pending:
                    raise LookupError("Reserva Cal.com sem vínculo com o Feegow.")
                self.store.update_pending_status(pending_uid, "CANCELED")

        self.store.mark_event(key, trigger, uid)
        return response
