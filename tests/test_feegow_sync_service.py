import pytest

from ana_feegow.webhooks.cal_parser import CalBooking
from ana_feegow.webhooks.feegow_sync_service import FeegowSyncService


class FakeFeegowClient:
    """Fake mínimo pra testar reschedule_booking/cancel_booking sem bater na
    API real do Feegow - só grava as chamadas e devolve a resposta que o
    teste configurar (imitando o formato real: HTTP 200 com "success" no
    corpo, mesmo quando o Feegow recusa a operação)."""

    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = []

    def post(self, endpoint, payload):
        self.chamadas.append((endpoint, payload))
        return self.resposta


def booking(**overrides):
    dados = dict(
        uid="uid-1",
        booking_id=10,
        event_type_id=7,
        tipo_consulta="consulta_presencial",
        data="2026-08-12",
        horario="16:30:00",
        nome="Paciente Teste",
        email="paciente@example.com",
        cpf="11767993714",
        nascimento="1988-05-27",
        celular="21985929056",
        notas="",
    )
    dados.update(overrides)
    return CalBooking(**dados)


def test_reschedule_booking_sucesso_retorna_resultado():
    client = FakeFeegowClient({"success": True, "content": {}})
    service = FeegowSyncService(client=client)

    resultado = service.reschedule_booking(31, booking())

    assert resultado["success"] is True
    assert client.chamadas[0][0] == "/appoints/reschedule"


def test_reschedule_booking_recusado_pelo_feegow_levanta_runtime_error():
    # O Feegow recusa (agenda ocupada, agendamento já cancelado etc.) mas
    # responde HTTP 200 com success:false - sem checar isso, o handler
    # marcaria a reserva como remarcada no nosso banco sem nada ter mudado
    # de fato na agenda da clínica.
    client = FakeFeegowClient({"success": False, "status_code": 409, "message": "Horário ocupado"})
    service = FeegowSyncService(client=client)

    with pytest.raises(RuntimeError, match="Falha ao remarcar agendamento Feegow"):
        service.reschedule_booking(31, booking())


def test_cancel_booking_sucesso_retorna_resultado():
    client = FakeFeegowClient({"success": True})
    service = FeegowSyncService(client=client)

    resultado = service.cancel_booking(31)

    assert resultado["success"] is True
    assert client.chamadas[0][0] == "/appoints/statusUpdate"


def test_cancel_booking_recusado_pelo_feegow_levanta_runtime_error():
    client = FakeFeegowClient({"success": False, "message": "Agendamento já cancelado"})
    service = FeegowSyncService(client=client)

    with pytest.raises(RuntimeError, match="Falha ao cancelar agendamento Feegow"):
        service.cancel_booking(31)
