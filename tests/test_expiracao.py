from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from ana_feegow.webhooks.app import create_app
from ana_feegow.webhooks.calcom_client import CalComClient
from ana_feegow.webhooks.expiracao import expirar_reservas_pendentes
from ana_feegow.webhooks.sync_store import SyncStore


@dataclass(frozen=True)
class FakeBooking:
    uid: str
    booking_id: int


def _envelhecer_pending(store, uid: str, minutos: int):
    with store._connect() as db:
        db.execute(
            "UPDATE pending_bookings SET updated_at = datetime('now', ?) WHERE cal_uid = ?",
            (f"-{minutos} minutes", uid),
        )


def test_list_pending_expirados_retorna_so_waiting_vencidos(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))

    store.save_pending_booking(FakeBooking("uid-velho", 1), "CHEC_1", "https://pay/1")
    _envelhecer_pending(store, "uid-velho", 31)

    store.save_pending_booking(FakeBooking("uid-recente", 2), "CHEC_2", "https://pay/2")

    store.save_pending_booking(FakeBooking("uid-pago", 3), "CHEC_3", "https://pay/3")
    store.update_pending_status("uid-pago", "PAID")
    _envelhecer_pending(store, "uid-pago", 31)

    expirados = store.list_pending_expirados(30)
    uids = {item["cal_uid"] for item in expirados}
    assert uids == {"uid-velho"}


def test_list_pending_expirados_vazio_quando_nada_vencido(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    store.save_pending_booking(FakeBooking("uid-1", 1), "CHEC_1", "https://pay/1")
    assert store.list_pending_expirados(30) == []


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


class FakeCalSession:
    def __init__(self, csrf_response=None, cancel_response=None):
        self.csrf_response = csrf_response or FakeResponse(json_data={"csrfToken": "token-123"})
        self.cancel_response = cancel_response or FakeResponse(status_code=200)
        self.chamadas = []

    def get(self, url, **kwargs):
        self.chamadas.append(("GET", url))
        return self.csrf_response

    def post(self, url, **kwargs):
        self.chamadas.append(("POST", url, kwargs.get("json")))
        return self.cancel_response


def test_cancelar_reserva_sucesso():
    session = FakeCalSession()
    client = CalComClient(base_url="https://cal.example.com", session=session)

    client.cancelar_reserva("uid-1", "Sinal não pago no prazo.")

    assert session.chamadas[0] == ("GET", "https://cal.example.com/api/csrf")
    metodo, url, payload = session.chamadas[1]
    assert metodo == "POST"
    assert url == "https://cal.example.com/api/cancel"
    assert payload == {
        "csrfToken": "token-123",
        "uid": "uid-1",
        "cancellationReason": "Sinal não pago no prazo.",
        "allRemainingBookings": False,
    }


def test_cancelar_reserva_falha_ao_obter_csrf():
    session = FakeCalSession(csrf_response=FakeResponse(status_code=500))
    client = CalComClient(base_url="https://cal.example.com", session=session)

    with pytest.raises(RuntimeError, match="csrfToken"):
        client.cancelar_reserva("uid-1", "motivo")


def test_cancelar_reserva_sem_csrf_token_no_corpo():
    session = FakeCalSession(csrf_response=FakeResponse(json_data={}))
    client = CalComClient(base_url="https://cal.example.com", session=session)

    with pytest.raises(RuntimeError, match="csrfToken"):
        client.cancelar_reserva("uid-1", "motivo")


def test_cancelar_reserva_falha_no_cancelamento():
    session = FakeCalSession(cancel_response=FakeResponse(status_code=404, text="uid não encontrado"))
    client = CalComClient(base_url="https://cal.example.com", session=session)

    with pytest.raises(RuntimeError, match="404"):
        client.cancelar_reserva("uid-1", "motivo")


def test_calcom_client_exige_base_url(monkeypatch):
    monkeypatch.delenv("CALCOM_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="CALCOM_BASE_URL"):
        CalComClient()


class FakeCalComClient:
    def __init__(self, falhar_para=None):
        self.cancelamentos = []
        self.falhar_para = falhar_para or set()

    def cancelar_reserva(self, uid, motivo):
        self.cancelamentos.append((uid, motivo))
        if uid in self.falhar_para:
            raise RuntimeError("Cal.com fora do ar")


def test_expira_reserva_vencida_e_marca_expired(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    store.save_pending_booking(FakeBooking("uid-1", 1), "CHEC_1", "https://pay/1")
    _envelhecer_pending(store, "uid-1", 31)

    calcom = FakeCalComClient()
    resultado = expirar_reservas_pendentes(store, calcom, minutos=30)

    assert resultado == [{"uid": "uid-1", "status": "expirado"}]
    assert calcom.cancelamentos == [("uid-1", expirar_reservas_pendentes.__globals__["MOTIVO_PADRAO"])]
    assert store.get_pending_booking("uid-1")["payment_status"] == "EXPIRED"


def test_expira_ignora_reserva_paga_entre_a_varredura_e_o_cancelamento(tmp_path, monkeypatch):
    store = SyncStore(str(tmp_path / "sync.db"))
    store.save_pending_booking(FakeBooking("uid-1", 1), "CHEC_1", "https://pay/1")
    _envelhecer_pending(store, "uid-1", 31)

    original_get = store.get_pending_booking

    def get_pending_booking_simulando_corrida(uid):
        store.update_pending_status(uid, "PAID")
        return original_get(uid)

    monkeypatch.setattr(store, "get_pending_booking", get_pending_booking_simulando_corrida)

    calcom = FakeCalComClient()
    resultado = expirar_reservas_pendentes(store, calcom, minutos=30)

    assert resultado == []
    assert calcom.cancelamentos == []
    assert store.get_pending_booking("uid-1")["payment_status"] == "PAID"


def test_expira_registra_falha_e_continua_sem_marcar_expired(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    store.save_pending_booking(FakeBooking("uid-1", 1), "CHEC_1", "https://pay/1")
    _envelhecer_pending(store, "uid-1", 31)

    calcom = FakeCalComClient(falhar_para={"uid-1"})
    resultado = expirar_reservas_pendentes(store, calcom, minutos=30)

    assert len(resultado) == 1
    assert resultado[0]["uid"] == "uid-1"
    assert resultado[0]["status"] == "falha"
    assert store.get_pending_booking("uid-1")["payment_status"] == "WAITING"


def test_expira_nao_afeta_reservas_recentes(tmp_path):
    store = SyncStore(str(tmp_path / "sync.db"))
    store.save_pending_booking(FakeBooking("uid-1", 1), "CHEC_1", "https://pay/1")

    calcom = FakeCalComClient()
    resultado = expirar_reservas_pendentes(store, calcom, minutos=30)

    assert resultado == []
    assert store.get_pending_booking("uid-1")["payment_status"] == "WAITING"


class FakeHandler:
    def handle(self, envelope):
        return {"status": "processed"}


def test_app_sobe_normalmente_sem_calcom_base_url(monkeypatch, tmp_path):
    monkeypatch.delenv("CALCOM_BASE_URL", raising=False)
    store = SyncStore(str(tmp_path / "sync.db"))
    app = create_app(handler=FakeHandler(), secret="segredo", store=store)

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
