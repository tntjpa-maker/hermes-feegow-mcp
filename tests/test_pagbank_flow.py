import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from ana_feegow.webhooks.app import create_app
from ana_feegow.webhooks.cal_parser import parse_booking
from ana_feegow.webhooks.pagbank_client import PagBankClient
from ana_feegow.webhooks.pagbank_handler import PagBankHandler
from ana_feegow.webhooks.sync_handler import SyncHandler
from ana_feegow.webhooks.sync_store import SyncStore

# eventTypeId=7 / type="niteroi" -> consulta_presencial (SERVICES["consulta_presencial"]["valor"] = 35000)
# Sinal = 20% -> 7000 centavos (R$70,00).
SINAL_CONSULTA_PRESENCIAL_CENTAVOS = 7000


def cal_payload(trigger="BOOKING_CREATED"):
    return {
        "triggerEvent": trigger,
        "createdAt": "2026-07-25T12:00:00Z",
        "payload": {
            "uid": "cal-uid-pagbank-1",
            "bookingId": 900001,
            "eventTypeId": 7,
            "type": "niteroi",
            "startTime": "2026-07-29T12:00:00Z",
            "responses": {
                "name": {"value": "Paciente Teste"},
                "email": {"value": "paciente@example.com"},
                "cpf": {"value": "11767993714"},
                "data_nascimento": {"value": "27051988"},
                "celular": {"value": "21985929056"},
            },
        },
    }


class FakeResponse:
    status_code = 200

    def json(self):
        return {
            "id": "CHEC_123",
            "links": [{"rel": "PAY", "href": "https://sandbox.pagbank.test/pay"}],
        }


class FakeSession:
    def __init__(self):
        self.payload = None

    def post(self, url, **kwargs):
        self.payload = kwargs["json"]
        return FakeResponse()


class FakePaymentClient:
    """Simula o PagBankClient só para o método usado na reconfirmação."""

    def __init__(self, pedido):
        self.pedido = pedido
        self.consultas = []

    def consultar_pedido(self, order_id):
        self.consultas.append(order_id)
        return self.pedido


class FakeFeegow:
    def __init__(self):
        self.created = 0

    def create_booking(self, booking):
        self.created += 1
        return 54

    def reschedule_booking(self, appointment_id, booking):
        return {"success": True}

    def cancel_booking(self, appointment_id):
        return {"success": True}


def test_booking_created_checkout_paid_feegow_e_idempotencia(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    session = FakeSession()
    pagbank = PagBankClient(
        token="token",
        webhook_url="https://integracao.example/webhooks/pagbank",
        public_base_url="https://integracao.example",
        session=session,
    )
    feegow = FakeFeegow()
    cal_handler = SyncHandler(store, feegow, pagbank)

    result = cal_handler.handle(cal_payload())
    assert result["status"] == "processed"
    assert result["payment_url"] == "https://sandbox.pagbank.test/pay"
    assert session.payload["reference_id"] == "cal-uid-pagbank-1"
    assert session.payload["items"][0]["unit_amount"] == SINAL_CONSULTA_PRESENCIAL_CENTAVOS
    assert store.get_mapping("cal-uid-pagbank-1") is None

    notification = {
        "id": "ORDE_123",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_123", "status": "PAID"}],
    }
    handler = PagBankHandler(store, feegow)
    assert handler.handle(notification)["status"] == "processed"
    assert handler.handle(notification)["status"] == "duplicate"
    assert feegow.created == 1
    assert store.get_mapping("cal-uid-pagbank-1")["feegow_appointment_id"] == 54


def test_webhook_pagbank_valida_assinatura_e_redireciona(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(
        booking,
        "CHEC_123",
        "https://sandbox.pagbank.test/pay",
    )

    class FakePagBankHandler:
        def handle(self, payload, assinatura_confiavel=True):
            return {"status": "processed", "uid": payload["reference_id"]}

    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=FakePagBankHandler(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )
    raw = json.dumps(
        {"reference_id": "cal-uid-pagbank-1", "status": "PAID"},
        separators=(",", ":"),
    ).encode()
    signature = hashlib.sha256(b"pagbank-token-" + raw).hexdigest()

    response = client.post(
        "/webhooks/pagbank",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-authenticity-token": signature,
        },
    )
    assert response.status_code == 200

    redirect = client.get(
        "/pagamento/iniciar?uid=cal-uid-pagbank-1",
        follow_redirects=False,
    )
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "https://sandbox.pagbank.test/pay"


def test_pagbank_reconfirma_via_api_quando_assinatura_ausente(tmp_path):
    # Simula o bug conhecido do PagBank Sandbox: a notificação chega sem o
    # header x-authenticity-token. O handler não deve confiar no corpo
    # recebido - só cria a consulta se a API do PagBank confirmar o
    # pagamento de verdade quando consultada com o token da clínica.
    store = SyncStore(str(tmp_path / "sync.db"))
    booking = parse_booking(cal_payload())
    store.save_pending_booking(booking, "CHEC_999", "https://sandbox.pagbank.test/pay")

    pedido_confirmado_pela_api = {
        "id": "ORDE_999",
        "reference_id": "cal-uid-pagbank-1",
        "charges": [{"id": "CHAR_999", "status": "PAID"}],
    }
    feegow = FakeFeegow()
    payment_client = FakePaymentClient(pedido_confirmado_pela_api)
    handler = PagBankHandler(store, feegow, payment_client)

    # Payload "cru" da notificação, sem assinatura confiável - mesmo se
    # viesse adulterado, só usamos o "id" para buscar o pedido de verdade.
    payload_nao_confiavel = {"id": "ORDE_999", "reference_id": "cal-uid-pagbank-1"}

    result = handler.handle(payload_nao_confiavel, assinatura_confiavel=False)

    assert result["status"] == "processed"
    assert result["feegow_appointment_id"] == 54
    assert payment_client.consultas == ["ORDE_999"]
    assert feegow.created == 1
    assert store.get_mapping("cal-uid-pagbank-1")["pagbank_transaction_id"] == "CHAR_999"


def test_pagbank_sem_assinatura_e_sem_cliente_de_pagamento_e_rejeitado(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    feegow = FakeFeegow()
    handler = PagBankHandler(store, feegow)  # sem payment_client

    with pytest.raises(ValueError):
        handler.handle({"id": "ORDE_999"}, assinatura_confiavel=False)


def test_webhook_pagbank_sem_header_reconfirma_no_handler(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    chamadas = []

    class SpyPagBankHandler:
        def handle(self, payload, assinatura_confiavel=True):
            chamadas.append(assinatura_confiavel)
            return {"status": "processed", "uid": payload.get("reference_id")}

    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=SpyPagBankHandler(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )
    raw = json.dumps(
        {"id": "ORDE_1", "reference_id": "cal-uid-x"},
        separators=(",", ":"),
    ).encode()

    response = client.post(
        "/webhooks/pagbank",
        content=raw,
        headers={"content-type": "application/json"},  # sem x-authenticity-token
    )
    assert response.status_code == 200
    assert chamadas == [False]


def test_webhook_pagbank_assinatura_errada_ainda_rejeita(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    client = TestClient(
        create_app(
            handler=object(),
            secret="cal-secret",
            pagbank_handler=object(),
            pagbank_token="pagbank-token",
            store=store,
        )
    )
    raw = json.dumps({"reference_id": "cal-uid-x"}, separators=(",", ":")).encode()

    response = client.post(
        "/webhooks/pagbank",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-authenticity-token": "assinatura-errada",
        },
    )
    assert response.status_code == 401


def test_create_checkout_rejeita_cpf_com_digito_verificador_invalido(tmp_path):
    # CPFs "de brincadeira" (ex.: 11233223423, usado numa reserva de teste
    # real) têm 11 dígitos mas não passam no cálculo do dígito verificador.
    # O PagBank rejeita esses com HTTP 400 - detectamos isso antes, sem
    # nem chamar a API deles.
    session = FakeSession()
    pagbank = PagBankClient(
        token="token",
        webhook_url="https://integracao.example/webhooks/pagbank",
        public_base_url="https://integracao.example",
        session=session,
    )
    envelope = cal_payload()
    envelope["payload"]["responses"]["cpf"]["value"] = "11233223423"
    booking_cpf_invalido = parse_booking(envelope)

    with pytest.raises(ValueError, match="CPF inválido"):
        pagbank.create_checkout(booking_cpf_invalido)

    assert session.payload is None  # não deve nem tentar chamar a API do PagBank


def test_create_checkout_aceita_cpf_de_teste_oficial_do_pagbank(tmp_path):
    # 01234567890 é o CPF de teste recomendado pela documentação do
    # PagBank para o ambiente Sandbox - precisa continuar passando.
    session = FakeSession()
    pagbank = PagBankClient(
        token="token",
        webhook_url="https://integracao.example/webhooks/pagbank",
        public_base_url="https://integracao.example",
        session=session,
    )
    envelope = cal_payload()
    envelope["payload"]["responses"]["cpf"]["value"] = "01234567890"
    booking = parse_booking(envelope)

    checkout = pagbank.create_checkout(booking)

    assert checkout.checkout_id == "CHEC_123"
    assert session.payload["customer"]["tax_id"] == "01234567890"
