import ana_feegow.ana.conversation as conversation_module
import ana_feegow.ana.dialog as dialog_module


def _isolar_conversas(monkeypatch, tmp_path):
    monkeypatch.setattr(conversation_module, "BASE", tmp_path)


def test_pergunta_informativa_na_primeira_mensagem_responde_e_convida_a_agendar(
    monkeypatch, tmp_path
):
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880001"
    resposta = dialog_module.responder(telefone, "Oi, boa tarde! Queria saber onde fica a clinica.")

    assert "Av. Sete de Setembro" in resposta
    assert "posso te ajudar a agendar" in resposta.lower()
    # A pergunta fixa "primeira consulta ou retorno" logo após uma resposta
    # informativa soava como um menu de atendimento automático - a ANA não
    # deve mais emendar essa pergunta (ver dialog.responder, estado
    # "inicio", e SOUL.md seções 1 e 5).
    assert "primeira consulta ou retorno" not in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "aguardando_motivo"


def test_pergunta_de_preco_nao_derruba_agendamento_em_andamento(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880002"

    dialog_module.responder(telefone, "oi")  # inicio -> aguardando_motivo

    conv_antes = conversation_module.Conversation(telefone)
    assert conv_antes.state == "aguardando_motivo"

    resposta = dialog_module.responder(telefone, "quanto custa a consulta?")

    assert "R$ 350,00" in resposta

    conv_depois = conversation_module.Conversation(telefone)
    # Uma pergunta informativa no meio do fluxo não altera o estado - a
    # próxima mensagem da paciente ainda é tratada normalmente como o
    # motivo da consulta (primeira consulta ou retorno).
    assert conv_depois.state == "aguardando_motivo"


def test_pergunta_de_convenio_nao_e_confundida_com_pedido_de_agendamento(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880003"
    resposta = dialog_module.responder(telefone, "voces atendem convenio?")

    assert "particular" in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    # A mensagem também avança o estado (mesma regra da mensagem "inicio"),
    # mas não deve ter sido tratada como "AGENDAR".
    assert conv.state == "aguardando_motivo"


def test_pergunta_sobre_consulta_hibrida_e_respondida_como_faq(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880007"
    resposta = dialog_module.responder(telefone, "oi, o que é a consulta híbrida?")

    assert "presencial" in resposta.lower()
    assert "online" in resposta.lower()
    # Pergunta explicativa não deve ser confundida com pedido de
    # agendamento (ver decision.py: bloco "o que é" / "como funciona").
    assert "sinal de 20%" not in resposta.lower()


def test_consulta_presencial_nova_envia_link_presencial_e_explica_sinal(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "link_consulta_presencial",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/niteroi",
    )

    telefone = "21988880004"

    dialog_module.responder(telefone, "oi")  # inicio -> aguardando_motivo
    resposta = dialog_module.responder(telefone, "quero marcar minha primeira consulta")

    assert "https://cal.magnoliasdm.com.br/drathalita/niteroi" in resposta
    assert "sinal de 20%" in resposta.lower()
    # A ANA nunca pergunta data nem horário - ela só envia o link do
    # Cal.com para a paciente escolher por conta própria.
    assert "que dia" not in resposta.lower()
    assert "que horário" not in resposta.lower()
    assert "qual horário" not in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"
    assert conv.data.get("tipo_consulta") == "consulta_presencial"


def test_consulta_online_nova_envia_link_online(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "link_consulta_online",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/online",
    )

    telefone = "21988880005"

    dialog_module.responder(telefone, "oi")
    resposta = dialog_module.responder(telefone, "quero uma consulta online, primeira vez")

    assert "https://cal.magnoliasdm.com.br/drathalita/online" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"
    assert conv.data.get("tipo_consulta") == "consulta_online"


def test_consulta_hibrida_nova_usa_link_presencial(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "link_consulta_presencial",
        lambda: "https://cal.magnoliasdm.com.br/drathalita/niteroi",
    )

    telefone = "21988880006"

    dialog_module.responder(telefone, "oi")
    resposta = dialog_module.responder(telefone, "quero a consulta hibrida, primeira vez")

    # Híbrida não tem link de agenda próprio - é uma etiqueta de
    # serviço/preço no Feegow (pacote presencial + online), então usa o
    # mesmo link presencial.
    assert "https://cal.magnoliasdm.com.br/drathalita/niteroi" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.data.get("tipo_consulta") == "consulta_hibrida"
