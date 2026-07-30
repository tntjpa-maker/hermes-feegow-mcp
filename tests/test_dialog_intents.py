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
    assert "primeira consulta ou retorno" in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "aguardando_motivo"


def test_pergunta_de_preco_nao_derruba_agendamento_em_andamento(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880002"

    dialog_module.responder(telefone, "oi")  # inicio -> aguardando_motivo
    dialog_module.responder(telefone, "primeira consulta")  # -> aguardando_data

    conv_antes = conversation_module.Conversation(telefone)
    assert conv_antes.state == "aguardando_data"

    resposta = dialog_module.responder(telefone, "quanto custa a consulta?")

    assert "R$ 350,00" in resposta

    conv_depois = conversation_module.Conversation(telefone)
    assert conv_depois.state == "aguardando_data"
    assert conv_depois.data.get("data") is None


def test_pergunta_de_convenio_nao_e_confundida_com_pedido_de_agendamento(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    telefone = "21988880003"
    resposta = dialog_module.responder(telefone, "voces atendem convenio?")

    assert "particular" in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    # A mensagem também avança o estado (mesma regra da mensagem "inicio"),
    # mas não deve ter sido tratada como "AGENDAR".
    assert conv.state == "aguardando_motivo"


def test_cadastro_de_paciente_nova_completa_e_agenda(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "consultar_horarios",
        lambda tipo, data, _data2: {"content": []},
    )
    monkeypatch.setattr(
        dialog_module,
        "identificar_paciente",
        lambda telefone: {"existe": False, "paciente": None},
    )
    monkeypatch.setattr(
        dialog_module,
        "criar_paciente",
        lambda nome, cpf, nascimento, celular: {"content": {"patient_id": 999}},
    )
    monkeypatch.setattr(
        dialog_module,
        "agendar_consulta",
        lambda **kwargs: {"content": {"agendamento_id": 4242}},
    )

    telefone = "21988880004"

    dialog_module.responder(telefone, "oi")  # inicio -> aguardando_motivo
    dialog_module.responder(telefone, "primeira consulta")  # -> aguardando_data
    dialog_module.responder(telefone, "20/08/2026")  # -> aguardando_horario
    resposta = dialog_module.responder(telefone, "14:00")  # -> cadastro_nome

    assert "nome completo" in resposta.lower()
    conv = conversation_module.Conversation(telefone)
    assert conv.state == "cadastro_nome"

    resposta = dialog_module.responder(telefone, "Maria da Silva")
    assert "cpf" in resposta.lower()
    conv = conversation_module.Conversation(telefone)
    assert conv.state == "cadastro_cpf"

    resposta = dialog_module.responder(telefone, "11122233344")
    assert "nascimento" in resposta.lower()
    conv = conversation_module.Conversation(telefone)
    assert conv.state == "cadastro_nascimento"

    resposta = dialog_module.responder(telefone, "01/01/1990")

    assert "agendada com sucesso" in resposta.lower()
    assert "4242" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"


def test_cadastro_com_falha_na_criacao_encaminha_para_humano_sem_quebrar(
    monkeypatch, tmp_path
):
    _isolar_conversas(monkeypatch, tmp_path)

    monkeypatch.setattr(
        dialog_module,
        "consultar_horarios",
        lambda tipo, data, _data2: {"content": []},
    )
    monkeypatch.setattr(
        dialog_module,
        "identificar_paciente",
        lambda telefone: {"existe": False, "paciente": None},
    )

    def _falha(*args, **kwargs):
        raise RuntimeError("Feegow indisponível")

    monkeypatch.setattr(dialog_module, "criar_paciente", _falha)

    telefone = "21988880005"

    dialog_module.responder(telefone, "oi")
    dialog_module.responder(telefone, "primeira consulta")
    dialog_module.responder(telefone, "20/08/2026")
    dialog_module.responder(telefone, "14:00")
    dialog_module.responder(telefone, "Maria da Silva")
    dialog_module.responder(telefone, "11122233344")
    resposta = dialog_module.responder(telefone, "01/01/1990")

    assert "secretária" in resposta.lower() or "secretaria" in resposta.lower()

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "finalizado"
