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


class FakeFeegowClientCompleto:
    """Fake que atende tanto GET (busca de paciente) quanto POST (criação de
    agendamento), pra testar create_booking/ensure_patient de ponta a ponta
    sem bater na API real do Feegow."""

    def __init__(self, paciente_id=42, agendamento_resposta=None):
        self.paciente_id = paciente_id
        self.agendamento_resposta = agendamento_resposta or {
            "success": True,
            "content": {"agendamento_id": 555},
        }
        self.posts = []

    def get(self, endpoint, params=None):
        if endpoint == "/patient/list":
            return {
                "total": 1,
                "content": [{"patient_id": self.paciente_id}],
            }
        raise AssertionError(f"GET inesperado: {endpoint}")

    def post(self, endpoint, payload):
        self.posts.append((endpoint, payload))
        return self.agendamento_resposta


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


def test_create_booking_consulta_retorno_e_registrada_com_retorno_true():
    client = FakeFeegowClientCompleto()
    service = FeegowSyncService(client=client)

    appointment_id = service.create_booking(booking(tipo_consulta="consulta_retorno"))

    assert appointment_id == 555
    endpoint, payload = client.posts[0]
    assert endpoint == "/appoints/new-appoint"
    assert payload["retorno"] is True
    # consulta de retorno não é cobrada
    assert payload["valor"] == 0


def test_create_booking_consulta_presencial_nao_marca_retorno():
    client = FakeFeegowClientCompleto()
    service = FeegowSyncService(client=client)

    service.create_booking(booking(tipo_consulta="consulta_presencial"))

    _, payload = client.posts[0]
    assert payload["retorno"] is False


def test_create_booking_consulta_online_marca_telemedicina_true():
    # Consulta online é feita por Google Meet - o agendamento no Feegow
    # precisa ser sinalizado como telemedicina para diferenciar da consulta
    # presencial (ver agendamento_service.agendar_consulta()).
    client = FakeFeegowClientCompleto()
    service = FeegowSyncService(client=client)

    service.create_booking(booking(tipo_consulta="consulta_online"))

    _, payload = client.posts[0]
    assert payload["telemedicina"] is True
    assert payload["retorno"] is False
    # SERVICES["consulta_online"]["valor"] = 25000 (R$250,00) -> sinal de
    # 20% cobrado via PagBank = R$50,00 (ver test_pagbank_flow.py).
    assert payload["valor"] == 25000


def test_create_booking_consulta_presencial_nao_marca_telemedicina():
    client = FakeFeegowClientCompleto()
    service = FeegowSyncService(client=client)

    service.create_booking(booking(tipo_consulta="consulta_presencial"))

    _, payload = client.posts[0]
    assert payload["telemedicina"] is False


class FakeFeegowClientBuscaPorTelefone:
    """Fake que só localiza a paciente por telefone via /patient/list (não
    tem CPF nenhum cadastrado) - reproduz o payload real do evento
    "Consulta Retorno", que só coleta nome/email/celular."""

    def __init__(self, celular_cadastrado, paciente_id=42):
        self.celular_cadastrado = celular_cadastrado
        self.paciente_id = paciente_id
        self.posts = []

    def get(self, endpoint, params=None):
        assert endpoint == "/patient/list"
        offset = params.get("offset", 0)
        limit = params.get("limit", 200)
        pacientes = [
            {"patient_id": self.paciente_id, "celular": self.celular_cadastrado}
        ]
        pagina = pacientes[offset : offset + limit]
        return {"total": len(pacientes), "content": pagina}

    def post(self, endpoint, payload):
        self.posts.append((endpoint, payload))
        return {"success": True, "content": {"agendamento_id": 555}}


def test_ensure_patient_de_retorno_localiza_paciente_so_por_telefone_sem_cpf():
    # Bug real observado em produção em 28/07/2026: o formulário do evento
    # "Consulta Retorno" não coleta CPF nem data de nascimento, então o
    # booking chega com cpf="" e nascimento="". Antes do fix, isso quebrava
    # (buscar_paciente(cpf="") levantava ValueError, ou o código caía em
    # criar_paciente com dados vazios e a Feegow recusava por "Data de
    # nascimento inválida").
    client = FakeFeegowClientBuscaPorTelefone(celular_cadastrado="21985929056")
    service = FeegowSyncService(client=client)
    reserva = booking(
        tipo_consulta="consulta_retorno",
        cpf="",
        nascimento="",
        celular="21985929056",
    )

    appointment_id = service.create_booking(reserva)

    assert appointment_id == 555


def test_ensure_patient_de_retorno_sem_paciente_encontrada_nao_cria_paciente_nova():
    # Sem CPF/nascimento reais, não faz sentido cadastrar uma paciente nova
    # na Feegow para um retorno - se ela não for localizada por telefone,
    # o correto é falhar com um erro claro (que o sync_handler já trata
    # cancelando a reserva no Cal.com automaticamente).
    client = FakeFeegowClientBuscaPorTelefone(celular_cadastrado="21999999999")
    service = FeegowSyncService(client=client)
    reserva = booking(
        tipo_consulta="consulta_retorno",
        cpf="",
        nascimento="",
        celular="21985929056",
    )

    with pytest.raises(ValueError, match="Paciente não encontrada"):
        service.create_booking(reserva)

    # nunca deve tentar criar uma paciente nova nesse fluxo
    assert client.posts == []
