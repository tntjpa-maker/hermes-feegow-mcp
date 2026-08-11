"""Testa a rede de seguranca deterministica para sinais de alarme clinicos
e risco de autoagressao (ver decision.py: SINAIS_DE_ALARME,
SINAIS_AUTOAGRESSAO, e dialog.responder()).

Contexto: antes desta rede de seguranca, o reconhecimento de urgencia
medica (AGENTS.md, Secao 6) e de risco de autoagressao dependia
inteiramente do LLM (hermes) interpretar a mensagem e agir - sem nenhum
backstop no codigo caso o modelo (ou um provedor de fallback mais fraco)
nao generalizasse bem. Estes testes garantem que, para as formas mais
diretas de relato, a resposta de seguranca e enviada de forma
deterministica, independente do estado da conversa.
"""

import ana_feegow.ana.conversation as conversation_module
import ana_feegow.ana.dialog as dialog_module
from ana_feegow.ana.decision import MENSAGEM_AUTOAGRESSAO, MENSAGEM_URGENCIA


def _isolar_conversas(monkeypatch, tmp_path):
    monkeypatch.setattr(conversation_module, "BASE", tmp_path)


def test_sangramento_intenso_interrompe_e_nao_altera_estado(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880101"

    resposta = dialog_module.responder(
        telefone,
        "Estou sangrando muito e encharcando um absorvente por hora; posso esperar a consulta?",
    )

    assert resposta == MENSAGEM_URGENCIA

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "inicio"


def test_dor_forte_no_meio_do_fluxo_de_agendamento_interrompe_imediatamente(
    monkeypatch, tmp_path
):
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880102"

    # Comeca um agendamento normal (estado avanca para aguardando_motivo).
    dialog_module.responder(telefone, "oi")
    conv = conversation_module.Conversation(telefone)
    assert conv.state == "aguardando_motivo"

    # No meio do fluxo, relata um sinal de alarme - deve interromper na
    # hora, com a mensagem oficial de urgencia (AGENTS.md, Secao 6),
    # mesmo a mensagem tambem contendo a palavra "emergencia"/"consulta".
    resposta = dialog_module.responder(
        telefone, "Estou grávida e com dor forte; devo ir à emergência?"
    )
    assert resposta == MENSAGEM_URGENCIA

    # O estado do fluxo em andamento nao e destruido - a paciente pode
    # continuar de onde parou depois de buscar ajuda de urgencia.
    conv_depois = conversation_module.Conversation(telefone)
    assert conv_depois.state == "aguardando_motivo"


def test_desmaio_e_dor_abdominal_dispara_mensagem_de_urgencia(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880103"

    resposta = dialog_module.responder(
        telefone, "Estou desmaiando e com dor abdominal; posso ir à clínica?"
    )
    assert resposta == MENSAGEM_URGENCIA


def test_gestante_com_perda_de_liquido_dispara_mensagem_de_urgencia(
    monkeypatch, tmp_path
):
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880104"

    resposta = dialog_module.responder(
        telefone, "Acho que rompeu a bolsa e estou perdendo líquido, o que faço?"
    )
    assert resposta == MENSAGEM_URGENCIA


def test_gestante_com_sangramento_leve_tambem_dispara_alarme_mesmo_sem_intensidade(
    monkeypatch, tmp_path
):
    """AGENTS.md, Secao 6: para gestantes, dor/sangramento/perda de liquido
    e sinal de alarme mesmo sem qualificador de intensidade - diferente
    das demais categorias, que exigem 'intenso'/'muito'."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880108"

    resposta = dialog_module.responder(
        telefone, "Tive sangramento no início da gravidez, o que faço?"
    )
    assert resposta == MENSAGEM_URGENCIA


def test_sangramento_com_palavra_intercalada_dispara_alarme(monkeypatch, tmp_path):
    """Regressao do Achado critico #2 do relatorio de testes de 30/07: a
    frase original relatada pela paciente ('sangramento MUITO intenso', com
    'muito' entre o substantivo e o qualificador) nao batia com a lista de
    frases fixas original ('sangramento intenso') e escapava da rede de
    seguranca. Ver _termo_proximo() em decision.py."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880110"

    resposta = dialog_module.responder(
        telefone, "estou com um sangramento muito intenso agora, o que eu faço?"
    )
    assert resposta == MENSAGEM_URGENCIA


def test_dor_com_palavra_intercalada_dispara_alarme(monkeypatch, tmp_path):
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880111"

    resposta = dialog_module.responder(telefone, "estou com uma dor bem forte na barriga")
    assert resposta == MENSAGEM_URGENCIA


def test_dor_leve_isolada_nao_dispara_alarme(monkeypatch, tmp_path):
    """A checagem por proximidade nao deve virar um gatilho generico para
    qualquer mencao a 'dor' - so quando ha um qualificador de intensidade
    por perto."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880112"

    resposta = dialog_module.responder(telefone, "sinto uma dor leve, é normal?")
    assert resposta != MENSAGEM_URGENCIA


def test_dor_e_intensidade_distantes_no_texto_nao_disparam_falso_positivo(
    monkeypatch, tmp_path
):
    """'dor' e uma palavra de intensidade presentes na mensagem, mas longe
    uma da outra (fora da janela de proximidade) e sem relacao entre si, nao
    devem disparar o alarme."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880113"

    resposta = dialog_module.responder(
        telefone,
        "tomo muito café todos os dias e por isso ontem tive uma dor de cabeça leve",
    )
    assert resposta != MENSAGEM_URGENCIA


def test_gestacao_sem_sintoma_nao_dispara_alarme(monkeypatch, tmp_path):
    """Pergunta sobre gestacao sem relatar dor/sangramento/perda de liquido
    nao deve ser tratada como emergencia."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880109"

    resposta = dialog_module.responder(telefone, "Ela atende gestação de alto risco?")
    assert resposta != MENSAGEM_URGENCIA


def test_risco_de_autoagressao_encaminha_para_humano_com_mensagem_especifica(
    monkeypatch, tmp_path
):
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880105"

    resposta = dialog_module.responder(
        telefone,
        "Estou com pensamentos de morte; a ginecologista pode ajudar ou devo procurar outro serviço?",
    )

    assert resposta == MENSAGEM_AUTOAGRESSAO
    assert "188" in resposta

    conv = conversation_module.Conversation(telefone)
    assert conv.state == "aguardando_humano"


def test_pedido_de_humano_normal_continua_com_mensagem_generica(monkeypatch, tmp_path):
    """Garante que a nova checagem nao capturou pedidos normais de humano
    (sem sinal de alarme) - devem continuar com o fluxo/mensagem existente."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880106"

    resposta = dialog_module.responder(telefone, "quero falar com um humano")

    assert "secretária" in resposta.lower()
    assert resposta != MENSAGEM_URGENCIA
    assert resposta != MENSAGEM_AUTOAGRESSAO


def test_pergunta_sobre_sinais_de_urgencia_sem_relatar_sintoma_nao_dispara_alarme(
    monkeypatch, tmp_path
):
    """'Que sinais indicam que devo ir a uma emergencia?' e uma pergunta
    generica (nao relata um sintoma ativo) - nao deve ser tratada como
    sinal de alarme, e sim seguir o fluxo normal de informacao."""
    _isolar_conversas(monkeypatch, tmp_path)
    telefone = "21988880107"

    resposta = dialog_module.responder(
        telefone, "Que sinais indicam que devo ir a uma emergência?"
    )

    assert resposta != MENSAGEM_URGENCIA
