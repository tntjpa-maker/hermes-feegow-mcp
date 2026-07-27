import pytest

from ana_feegow.webhooks.pagbank_client import PagBankCheckout
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


class FakePaymentServiceOk:
    def __init__(self):
        self.chamadas = 0

    def create_checkout(self, booking):
        self.chamadas += 1
        return PagBankCheckout(checkout_id="CHEC_1", payment_url="https://pagamento.example/pay")


class FakePaymentServiceInvalido:
    """Simula o PagBankClient recusando os dados da paciente (CPF, celular
    etc.) antes de criar o checkout - levanta ValueError, igual o
    PagBankClient real faz em PagBankClient.create_checkout."""

    def __init__(self, mensagem="Celular inválido para o checkout PagBank."):
        self.mensagem = mensagem

    def create_checkout(self, booking):
        raise ValueError(self.mensagem)


class FakeCalComClient:
    def __init__(self, quebrado=False):
        self.quebrado = quebrado
        self.cancelamentos = []

    def cancelar_reserva(self, uid, motivo):
        self.cancelamentos.append((uid, motivo))
        if self.quebrado:
            raise RuntimeError("Cal.com fora do ar")


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


def test_booking_created_com_sucesso_nao_cancela_nada_no_calcom(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    calcom = FakeCalComClient()
    handler = SyncHandler(store, FakeService(), FakePaymentServiceOk(), calcom)

    result = handler.handle(payload("BOOKING_CREATED"))

    assert result["status"] == "processed"
    assert result["payment_url"] == "https://pagamento.example/pay"
    assert calcom.cancelamentos == []
    assert store.get_pending_booking("uid-1") is not None


def test_booking_created_com_dados_invalidos_cancela_reserva_no_calcom(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    calcom = FakeCalComClient()
    handler = SyncHandler(store, FakeService(), FakePaymentServiceInvalido(), calcom)

    with pytest.raises(ValueError, match="Celular inválido"):
        handler.handle(payload("BOOKING_CREATED"))

    # cancela no Cal.com pra liberar o horário - sem isso ele fica preso na
    # agenda sem aparecer em lugar nenhum (o bug real reportado).
    assert calcom.cancelamentos == [
        (
            "uid-1",
            "Dados inválidos no agendamento: Celular inválido para o checkout PagBank.",
        )
    ]
    # a reserva com dado inválido nunca deve ficar salva como pendente
    assert store.get_pending_booking("uid-1") is None


def test_booking_created_com_dados_invalidos_sem_calcom_client_nao_quebra(tmp_path):
    # Sem CALCOM_BASE_URL configurada (calcom_client=None), o comportamento
    # de hoje se mantém: rejeita a reserva, só não cancela automaticamente.
    store = SyncStore(str(tmp_path / "sync.db"))
    handler = SyncHandler(store, FakeService(), FakePaymentServiceInvalido())

    with pytest.raises(ValueError, match="Celular inválido"):
        handler.handle(payload("BOOKING_CREATED"))


def test_booking_created_com_dados_invalidos_falha_ao_cancelar_nao_mascara_erro_original(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    calcom = FakeCalComClient(quebrado=True)
    handler = SyncHandler(store, FakeService(), FakePaymentServiceInvalido(), calcom)

    # mesmo se o cancelamento no Cal.com também falhar, quem chamou continua
    # vendo o erro original (422 CPF/celular inválido), não um 500 genérico.
    with pytest.raises(ValueError, match="Celular inválido"):
        handler.handle(payload("BOOKING_CREATED"))

    assert calcom.cancelamentos  # tentou cancelar, mesmo tendo dado errado
