from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore


class FakeService:
    def __init__(self):
        self.created_bookings = []
        self.rescheduled = self.cancelled = 0

    def create_booking(self, booking):
        self.created_bookings.append(booking)
        return 321

    def reschedule_booking(self, appointment_id, booking):
        self.rescheduled += 1
        return {"success": True}

    def cancel_booking(self, appointment_id):
        self.cancelled += 1
        return {"success": True}


class FakePaymentServiceQuebrado:
    """Não deve nunca ser chamado no fluxo de consulta_retorno - se for,
    o teste falha (ver assert em create_checkout)."""

    def create_checkout(self, booking):
        raise AssertionError(
            "Consulta de retorno não deve passar pelo checkout do PagBank."
        )


def payload_retorno(trigger, uid="uid-retorno-1", reschedule_uid=None):
    dados_payload = {
        "uid": uid,
        "bookingId": 20,
        "eventTypeId": 9,
        "type": "consulta-retorno",
        "startTime": "2026-08-05T14:00:00Z",
        # O formulário real do evento "Consulta Retorno" no Cal.com só
        # coleta nome/email/celular (sem CPF nem data de nascimento) - ver
        # cal_parser.parse_booking() e feegow_sync_service.ensure_patient(),
        # que tratam retorno como paciente já cadastrada na Feegow.
        "responses": {
            "name": {"value": "Paciente Retorno"},
            "email": {"value": "retorno@example.com"},
            "celular": {"value": "21985929056"},
        },
    }
    if reschedule_uid:
        dados_payload["rescheduleUid"] = reschedule_uid
    return {
        "triggerEvent": trigger,
        "createdAt": f"2026-07-28T09:00:0{len(trigger) % 10}Z",
        "payload": dados_payload,
    }


def test_booking_created_de_retorno_nao_cria_checkout_e_registra_direto_no_feegow(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    service = FakeService()
    handler = SyncHandler(store, service, FakePaymentServiceQuebrado())

    resultado = handler.handle(payload_retorno("BOOKING_CREATED"))

    assert resultado["status"] == "processed"
    assert "payment_url" not in resultado
    assert len(service.created_bookings) == 1
    assert service.created_bookings[0].tipo_consulta == "consulta_retorno"

    mapping = store.get_mapping("uid-retorno-1")
    assert mapping is not None
    assert mapping["feegow_appointment_id"] == 321
    assert mapping["status"] == "scheduled"
    # não deve sobrar nenhuma reserva pendente de pagamento
    assert store.get_pending_booking("uid-retorno-1") is None


def test_booking_created_de_retorno_e_idempotente(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    service = FakeService()
    handler = SyncHandler(store, service, FakePaymentServiceQuebrado())

    primeiro = handler.handle(payload_retorno("BOOKING_CREATED"))
    segundo = handler.handle(payload_retorno("BOOKING_CREATED"))

    assert primeiro["status"] == "processed"
    assert segundo["status"] == "duplicate"
    assert len(service.created_bookings) == 1


def test_cancelamento_de_consulta_retorno_funciona_normalmente(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    service = FakeService()
    handler = SyncHandler(store, service, FakePaymentServiceQuebrado())

    handler.handle(payload_retorno("BOOKING_CREATED", uid="uid-retorno-2"))
    resultado = handler.handle(payload_retorno("BOOKING_CANCELLED", uid="uid-retorno-2"))

    assert resultado["status"] == "processed"
    assert service.cancelled == 1


def test_remarcacao_de_consulta_retorno_funciona_normalmente(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    service = FakeService()
    handler = SyncHandler(store, service, FakePaymentServiceQuebrado())

    handler.handle(payload_retorno("BOOKING_CREATED", uid="uid-retorno-3"))
    resultado = handler.handle(payload_retorno("BOOKING_RESCHEDULED", uid="uid-retorno-3"))

    assert resultado["status"] == "processed"
    assert service.rescheduled == 1
