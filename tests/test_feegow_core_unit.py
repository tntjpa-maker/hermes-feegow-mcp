from ana_feegow.errors import FeegowAPIError
from ana_feegow.services.agendamento_service import agendar_consulta
from ana_feegow.services.cancelamento_service import cancelar_consulta
from ana_feegow.services.remarcacao_service import remarcar_consulta


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, endpoint, payload):
        self.calls.append((endpoint, payload))
        return {"success": True, "content": {"agendamento_id": 321}}


def test_criacao_normaliza_data_e_horario_sem_rede():
    client = FakeClient()

    result = agendar_consulta(
        paciente_id=68,
        tipo_consulta="consulta_presencial",
        data="2026-07-29",
        horario="14:30",
        celular="21999999999",
        email="teste@example.com",
        client=client,
    )

    endpoint, payload = client.calls[0]
    assert result["success"] is True
    assert endpoint == "/appoints/new-appoint"
    assert payload["data"] == "29-07-2026"
    assert payload["horario"] == "14:30:00"
    assert payload["procedimento_id"] == 35


def test_remarcacao_usa_endpoint_nativo_sem_rede():
    client = FakeClient()

    remarcar_consulta(
        agendamento_id=321,
        data="2026-07-30",
        horario="15:00",
        client=client,
    )

    endpoint, payload = client.calls[0]
    assert endpoint == "/appoints/reschedule"
    assert payload["agendamento_id"] == 321
    assert payload["data"] == "30-07-2026"
    assert payload["horario"] == "15:00:00"


def test_cancelamento_atualiza_status_sem_rede():
    client = FakeClient()

    cancelar_consulta(agendamento_id=321, client=client)

    endpoint, payload = client.calls[0]
    assert endpoint == "/appoints/statusUpdate"
    assert payload["AgendamentoID"] == 321
    assert payload["StatusID"] == 11


def test_erro_mantem_alias_body():
    error = FeegowAPIError(422, "erro de validação")
    assert error.body == "erro de validação"
