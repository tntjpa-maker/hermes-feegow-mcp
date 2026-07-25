import hashlib
import json

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
        def handle(self, payload):
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
