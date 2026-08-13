import ana_feegow.ana.conversation as conversation_module
import ana_feegow.ana.dialog as dialog_module
from ana_feegow.services import twenty_service as twenty_service_module


def _isolar_conversas(monkeypatch, tmp_path):
    monkeypatch.setattr(conversation_module, "BASE", tmp_path)


def test_resposta_de_origem_grava_categoria_e_texto_literal(monkeypatch, tmp_path):
    # Cobre o pedido do cliente: alem de classificar a resposta da paciente
    # em uma categoria (origemDoLead), o texto literal que ela escreveu
    # tambem deve ser guardado (como Nota, via registrar_origem_lead_texto_livre)
    # para uso em direcionamento de campanhas de marketing.
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880099"

    # Deixa a conversa exatamente no estado que segue a pergunta "como
    # voce conheceu a Dra. Thalita?", sem depender do restante do fluxo de
    # agendamento (testado em outros arquivos).
    conv = conversation_module.Conversation(telefone)
    conv.update("tipo_consulta", "consulta_presencial")
    conv.update("twenty_opportunity_id", "opp-1")
    conv.update("twenty_person_id", "person-1")
    conv.next("aguardando_origem")

    monkeypatch.setattr(
        dialog_module, "link_consulta_presencial", lambda: "https://cal.example/link"
    )

    chamadas_categoria = []
    chamadas_texto = []
    monkeypatch.setattr(
        twenty_service_module,
        "registrar_origem_lead",
        lambda opportunity_id, origem: chamadas_categoria.append((opportunity_id, origem)),
    )
    monkeypatch.setattr(
        twenty_service_module,
        "registrar_origem_lead_texto_livre",
        lambda opportunity_id, person_id, texto: chamadas_texto.append(
            (opportunity_id, person_id, texto)
        ),
    )

    resposta_literal = "vi minha prima comentando no Instagram sobre a experiencia dela"
    resposta = dialog_module.responder(telefone, resposta_literal)

    assert "https://cal.example/link" in resposta

    # A categoria continua sendo gravada normalmente.
    assert chamadas_categoria == [("opp-1", "INSTAGRAM")]

    # E agora o texto literal da paciente tambem e gravado, sem alteracao -
    # e o dado bruto (nao a categoria) que serve para direcionamento de
    # campanhas de marketing.
    assert chamadas_texto == [("opp-1", "person-1", resposta_literal)]

    conv_depois = conversation_module.Conversation(telefone)
    assert conv_depois.state == "finalizado"
