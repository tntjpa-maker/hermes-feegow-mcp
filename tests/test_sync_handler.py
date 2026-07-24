from ana_feegow.webhooks.cal_parser import CalBooking
from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore


class FakeService:
    def __init__(self):
        self.created = self.rescheduled = self.cancelled = 0

    def create_booking(self, booking):
        self.created += 1
        return 321

    def reschedule_booking(self, appointment_id, booking):
        self.rescheduled += 1
        return {"success": True}

    def cancel_booking(self, appointment_id):
        self.cancelled += 1
        return {"success": True}


def payload(trigger):
    return {
        "triggerEvent": trigger,
        "createdAt": f"2026-07-24T09:55:2{len(trigger)}Z",
        "payload": {
            "uid": "uid-1",
            "bookingId": 10,
            "eventTypeId": 7,
            "type": "niteroi",
            "startTime": "2026-07-29T19:30:00Z",
            "responses": {
                "name": {"value": "Paciente Teste"},
                "email": {"value": "paciente@example.com"},
                "cpf": {"value": "11767993714"},
                "data_nascimento": {"value": "27051988"},
                "celular": {"value": "21985929056"},
            },
        },
    }


def test_fluxo_pago_remarcado_cancelado_e_idempotente(tmp_path):
    service = FakeService()
    handler = SyncHandler(SyncStore(str(tmp_path / "sync.db")), service)

    paid = payload("BOOKING_PAID")
    assert handler.handle(paid)["status"] == "processed"
    assert handler.handle(paid)["status"] == "duplicate"

    assert handler.handle(payload("BOOKING_RESCHEDULED"))["status"] == "processed"
    assert handler.handle(payload("BOOKING_CANCELLED"))["status"] == "processed"
    assert (service.created, service.rescheduled, service.cancelled) == (1, 1, 1)
