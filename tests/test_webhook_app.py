import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from ana_feegow.webhooks.app import create_app


class FakeHandler:
    def handle(self, envelope):
        return {"status": "processed", "trigger": envelope["triggerEvent"]}


def test_health():
    client = TestClient(create_app(handler=FakeHandler(), secret="segredo"))
    assert client.get("/health").json()["status"] == "ok"


def test_rejeita_sem_assinatura():
    client = TestClient(create_app(handler=FakeHandler(), secret="segredo"))
    response = client.post("/webhooks/calcom", json={"triggerEvent": "BOOKING_PAID"})
    assert response.status_code == 401


def test_aceita_hmac_calcom():
    client = TestClient(create_app(handler=FakeHandler(), secret="segredo"))
    raw = json.dumps({"triggerEvent": "BOOKING_PAID"}).encode()
    signature = hmac.new(b"segredo", raw, hashlib.sha256).hexdigest()
    response = client.post(
        "/webhooks/calcom",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-cal-signature-256": signature,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
