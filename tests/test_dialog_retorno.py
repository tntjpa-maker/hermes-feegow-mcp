import ana_feegow.ana.conversation as conversation_module
import ana_feegow.ana.dialog as dialog_module
from ana_feegow.errors import FeegowAPIError


def _isolar_conversas(monkeypatch, tmp_path):
    monkeypatch.setattr(conversation_module, "BASE", tmp_path)


def test_retorno_elegivel_pergunta_modalidade_antes_de_enviar_link(monkeypatch, tmp_path):
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
    monkeypatch.setattr(
        dialog_module,
        "link_consulta_retorno_online",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno-online",
    )

    telefone = "21999990000"
    dialog_module.responder(telefone, "oi")  # inicio -> aguardando_motivo
    resposta = dialog_module.responder(telefone, "Quero um retorno")

    assert "18 dia(s)" in resposta
    assert "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno" not in resposta
    assert "online ou presencial" in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "aguardando_modalidade_retorno"
    assert conv.data["elegibilidade_retorno"]["elegivel"] is True


def test_retorno_elegivel_online_envia_link_online_e_finaliza(monkeypatch, tmp_path):
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
    monkeypatch.setattr(
        dialog_module,
        "link_consulta_retorno_online",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno-online",
    )

    telefone = "21999990010"
    dialog_module.responder(telefone, "oi")
    dialog_module.responder(telefone, "quero um retorno")
    resposta = dialog_module.responder(telefone, "online")

    assert "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno-online" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"


def test_retorno_elegivel_presencial_envia_link_presencial_e_finaliza(monkeypatch, tmp_path):
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
    monkeypatch.setattr(
        dialog_module,
        "link_consulta_retorno_online",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno-online",
    )

    telefone = "21999990011"
    dialog_module.responder(telefone, "oi")
    dialog_module.responder(telefone, "quero um retorno")
    resposta = dialog_module.responder(telefone, "presencial")

    assert "https://cal.magnoliasdm.com.br/drathalita/consulta-retorno" in resposta
    assert "consulta-retorno-online" not in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"


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
    monkeypatch.setattr(
        dialog_module,
        "link_consulta_presencial",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/niteroi",
    )

    telefone = "21999990004"
    dialog_module.responder(telefone, "oi")
    resposta = dialog_module.responder(telefone, "primeira consulta")

    assert chamado == []
    # Consulta nova (não é retorno): a ANA não pergunta data nem horário -
    # ela envia direto o link do Cal.com correspondente.
    assert "dia você prefere" not in resposta.lower()
    assert "https://cal.magnoliasdm.com.br/drathalita/niteroi" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"


def test_telefone_real_e_usado_na_checagem_de_elegibilidade_de_retorno(monkeypatch, tmp_path):
    # Regressão do bug em que o telefone da paciente ficava hardcoded
    # ("21985929056") em vez de usar o telefone real de quem está
    # conversando com a ANA. Como o agendamento em si agora é feito pelo
    # webhook do Cal.com (FeegowSyncService), a única chamada que ainda
    # recebe o telefone diretamente do dialog.py é a checagem de
    # elegibilidade de retorno.
    _isolar_conversas(monkeypatch, tmp_path)

    telefones_recebidos = []

    def fake_verificar(telefone):
        telefones_recebidos.append(telefone)
        return {
            "elegivel": True,
            "motivo": "dentro_do_prazo",
            "ultima_consulta_data": "10-07-2026",
            "dias_desde_ultima": 5,
        }

    monkeypatch.setattr(dialog_module, "verificar_elegibilidade_retorno", fake_verificar)
    monkeypatch.setattr(dialog_module, "link_consulta_retorno", lambda: "link")

    telefone = "21988887777"
    dialog_module.responder(telefone, "oi")
    dialog_module.responder(telefone, "quero um retorno")

    assert telefones_recebidos == [telefone]
