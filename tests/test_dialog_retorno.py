import ana_feegow.ana.conversation as conversation_module
import ana_feegow.ana.dialog as dialog_module
from ana_feegow.errors import FeegowAPIError


def _isolar_conversas(monkeypatch, tmp_path):
    monkeypatch.setattr(conversation_module, "BASE", tmp_path)


def _telefones():
    return {"existe": True, "paciente": {"patient_id": 12}}


def test_retorno_elegivel_envia_link_de_retorno_e_finaliza(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "verificar_elegibilidade_retorno",
        lambda telefone: {
            "elegivel": True,
            "motivo": "dentro_do_prazo",
            "ultima_consulta_data": "10-07-2026",
            "dias_desde_ultima": 18,
        },
    )
    monkeypatch.setattr(
        dialog_module, "link_consulta_retorno", lambda: "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno"
    )

    telefone = "21999990000"
    dialog_module.responder(telefone, "oi")  # inicio -> aguardando_motivo
    resposta = dialog_module.responder(telefone, "Quero um retorno")

    assert "18 dia(s)" in resposta
    assert "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"
    assert conv.data["elegibilidade_retorno"]["elegivel"] is True


def test_retorno_fora_do_prazo_envia_link_normal_e_finaliza(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "verificar_elegibilidade_retorno",
        lambda telefone: {
            "elegivel": False,
            "motivo": "fora_do_prazo",
            "ultima_consulta_data": "01-06-2026",
            "dias_desde_ultima": 57,
        },
    )
    monkeypatch.setattr(
        dialog_module,
        "link_consulta_presencial",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/niteroi",
    )

    telefone = "21999990001"
    dialog_module.responder(telefone, "oi")
    resposta = dialog_module.responder(telefone, "retorno")

    assert "https://cal.magnoliasdm.com.br/drathalita/niteroi" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"
    assert conv.data["elegibilidade_retorno"]["elegivel"] is False


def test_retorno_com_falha_no_feegow_nao_quebra_a_conversa(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    def levanta_erro(telefone):
        raise FeegowAPIError(500, "Feegow fora do ar")

    monkeypatch.setattr(dialog_module, "verificar_elegibilidade_retorno", levanta_erro)
    monkeypatch.setattr(
        dialog_module,
        "link_consulta_presencial",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/niteroi",
    )

    telefone = "21999990002"
    dialog_module.responder(telefone, "oi")
    resposta = dialog_module.responder(telefone, "retorno")

    assert "https://cal.magnoliasdm.com.br/drathalita/niteroi" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"


def test_deteccao_de_retorno_e_case_insensitive_e_por_substring(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    chamadas = []
    monkeypatch.setattr(
        dialog_module,
        "verificar_elegibilidade_retorno",
        lambda telefone: chamadas.append(telefone) or {
            "elegivel": True,
            "motivo": "dentro_do_prazo",
            "ultima_consulta_data": "10-07-2026",
            "dias_desde_ultima": 5,
        },
    )
    monkeypatch.setattr(dialog_module, "link_consulta_retorno", lambda: "link")

    telefone = "21999990003"
    dialog_module.responder(telefone, "oi")
    dialog_module.responder(telefone, "Quero fazer meu RETORNO, por favor")

    assert chamadas == [telefone]


def test_primeira_consulta_nao_aciona_checagem_de_retorno(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    chamado = []
    monkeypatch.setattr(
        dialog_module,
        "verificar_elegibilidade_retorno",
        lambda telefone: chamado.append(telefone),
    )

    telefone = "21999990004"
    dialog_module.responder(telefone, "oi")
    resposta = dialog_module.responder(telefone, "primeira consulta")

    assert chamado == []
    assert "dia você prefere" in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "aguardando_data"


def test_identificar_paciente_usa_telefone_real_nao_hardcoded(monkeypatch, tmp_path):
    # Regressão do bug em que o telefone da paciente ficava hardcoded
    # ("21985929056") em vez de usar o telefone real de quem está
    # conversando com a ANA.
    _isolar_conversas(monkeypatch, tmp_path)

    telefones_recebidos = []

    def fake_identificar(telefone):
        telefones_recebidos.append(telefone)
        return _telefones()

    def fake_agendar(**kwargs):
        return {"content": {"agendamento_id": 999}}

    monkeypatch.setattr(dialog_module, "identificar_paciente", fake_identificar)
    monkeypatch.setattr(dialog_module, "agendar_consulta", fake_agendar)
    monkeypatch.setattr(
        dialog_module,
        "consultar_horarios",
        lambda tipo, data, horario: {"content": None},
    )
    monkeypatch.setattr(dialog_module, "identificar_servico", lambda motivo: "consulta_presencial")

    telefone = "21988887777"
    dialog_module.responder(telefone, "oi")
    dialog_module.responder(telefone, "primeira consulta")
    dialog_module.responder(telefone, "20/08/2026")
    dialog_module.responder(telefone, "10:00")

    assert telefones_recebidos == [telefone]
