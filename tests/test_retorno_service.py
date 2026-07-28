from datetime import datetime

import pytest

from ana_feegow.errors import FeegowAPIError
from ana_feegow.services.retorno_service import (
    link_consulta_presencial,
    link_consulta_retorno,
    verificar_elegibilidade_retorno,
)


class FakeFeegowClient:
    """Fake mínimo que imita as duas chamadas feitas pela checagem de
    elegibilidade: GET /patient/list (via identificar_paciente) e
    GET /appoints/search (via buscar_agendamentos)."""

    def __init__(self, patient_list_response, agendamentos_response=None):
        self.patient_list_response = patient_list_response
        self.agendamentos_response = agendamentos_response or {"content": []}
        self.chamadas = []

    def get(self, endpoint, params=None):
        self.chamadas.append((endpoint, params))
        if endpoint == "/patient/list":
            return self.patient_list_response
        if endpoint == "/appoints/search":
            return self.agendamentos_response
        raise AssertionError(f"endpoint inesperado: {endpoint}")


def paciente_encontrado(patient_id=12, celular="21985929056"):
    return {
        "total": 1,
        "content": [{"patient_id": patient_id, "nome": "Paciente Teste", "celular": celular}],
    }


def paciente_nao_encontrado():
    return {"total": 0, "content": []}


def agendamento(data, status_id):
    return {"data": data, "status_id": status_id}


HOJE = datetime(2026, 7, 28)


def test_paciente_nao_encontrado_nao_e_elegivel():
    client = FakeFeegowClient(paciente_nao_encontrado())

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado == {
        "elegivel": False,
        "motivo": "paciente_nao_encontrado",
        "ultima_consulta_data": None,
        "dias_desde_ultima": None,
    }
    # não deve nem tentar buscar agendamentos sem paciente
    assert all(endpoint != "/appoints/search" for endpoint, _ in client.chamadas)


def test_sem_consulta_atendida_recente_nao_e_elegivel():
    agendamentos = {
        "content": [
            agendamento("20-07-2026", status_id=1),  # marcado, não atendido
            agendamento("15-07-2026", status_id=11),  # cancelado pelo paciente
        ]
    }
    client = FakeFeegowClient(paciente_encontrado(), agendamentos)

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado["elegivel"] is False
    assert resultado["motivo"] == "sem_consulta_atendida_recente"


def test_consulta_atendida_dentro_do_prazo_e_elegivel():
    agendamentos = {
        "content": [
            agendamento("10-07-2026", status_id=3),  # atendido há 18 dias
        ]
    }
    client = FakeFeegowClient(paciente_encontrado(), agendamentos)

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado["elegivel"] is True
    assert resultado["motivo"] == "dentro_do_prazo"
    assert resultado["dias_desde_ultima"] == 18
    assert resultado["ultima_consulta_data"] == "10-07-2026"


def test_consulta_atendida_fora_do_prazo_nao_e_elegivel():
    agendamentos = {
        "content": [
            agendamento("01-06-2026", status_id=3),  # atendido há 57 dias
        ]
    }
    client = FakeFeegowClient(paciente_encontrado(), agendamentos)

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado["elegivel"] is False
    assert resultado["motivo"] == "fora_do_prazo"
    assert resultado["dias_desde_ultima"] == 57


def test_exatamente_no_limite_e_elegivel():
    agendamentos = {"content": [agendamento("28-06-2026", status_id=3)]}  # exatos 30 dias
    client = FakeFeegowClient(paciente_encontrado(), agendamentos)

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado["dias_desde_ultima"] == 30
    assert resultado["elegivel"] is True


def test_usa_a_consulta_atendida_mais_recente_entre_varias():
    agendamentos = {
        "content": [
            agendamento("01-06-2026", status_id=3),  # mais antiga
            agendamento("15-07-2026", status_id=3),  # mais recente -> deve ser usada
            agendamento("20-07-2026", status_id=1),  # marcado (ignorado)
        ]
    }
    client = FakeFeegowClient(paciente_encontrado(), agendamentos)

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado["ultima_consulta_data"] == "15-07-2026"
    assert resultado["dias_desde_ultima"] == 13


def test_ignora_agendamentos_de_outros_status_incluindo_aguardando_pagamento():
    agendamentos = {
        "content": [
            agendamento("27-07-2026", status_id=208),  # aguardando pagamento
            agendamento("26-07-2026", status_id=6),  # não compareceu
            agendamento("10-07-2026", status_id=3),  # única atendida de fato
        ]
    }
    client = FakeFeegowClient(paciente_encontrado(), agendamentos)

    resultado = verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    assert resultado["ultima_consulta_data"] == "10-07-2026"
    assert resultado["elegivel"] is True


def test_busca_agendamentos_usa_paciente_id_correto():
    agendamentos = {"content": [agendamento("10-07-2026", status_id=3)]}
    client = FakeFeegowClient(paciente_encontrado(patient_id=99), agendamentos)

    verificar_elegibilidade_retorno("21985929056", client=client, hoje=HOJE)

    endpoint, params = next(c for c in client.chamadas if c[0] == "/appoints/search")
    assert params["paciente_id"] == 99


def test_erro_feegow_propaga(monkeypatch):
    class ClientQuebrado:
        def get(self, endpoint, params=None):
            raise FeegowAPIError(500, "fora do ar")

    with pytest.raises(FeegowAPIError):
        verificar_elegibilidade_retorno("21985929056", client=ClientQuebrado(), hoje=HOJE)


def test_links_usam_calcom_base_url(monkeypatch):
    from ana_feegow.config import settings

    monkeypatch.setattr(settings, "CALCOM_BASE_URL", "https://cal.magnoliasdm.com.br")

    assert link_consulta_retorno() == "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno"
    assert link_consulta_presencial() == "https://cal.magnoliasdm.com.br/drathalita/niteroi"
