import re
import unicodedata


def _sem_acentos(s: str) -> str:
    """Remove acentos/diacriticos para tornar o casamento de palavras-chave
    resiliente a variacoes de digitacao (pacientes frequentemente omitem
    acentos, principalmente no celular). Usado apenas para comparacao, nunca
    para o texto exibido a paciente."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


# Sinais de alarme clinicos (AGENTS.md, Secao 6): a clinica define que estes
# sinais devem "interromper imediatamente qualquer atendimento comercial",
# independente do que a paciente estava perguntando ou fazendo na conversa.
# Antes desta lista, essa regra dependia inteiramente do LLM reconhecer o
# sinal em texto livre e decidir agir - sem nenhuma rede de seguranca no
# codigo caso o modelo (ou um fallback mais fraco, ver config.yaml) nao
# generalizasse bem. Isto e uma camada adicional best-effort por
# palavra-chave, cobrindo as formas mais diretas de relato - NAO substitui
# o julgamento do LLM sobre casos ambiguos/informais nao listados aqui.

_JANELA_PROXIMIDADE = 20  # caracteres de folga entre o termo-base e o
# qualificador de intensidade, para nao depender de frases EXATAS. Uma
# paciente escrevendo "sangramento MUITO intenso" (com uma palavra no meio)
# nao bateria com a frase fixa "sangramento intenso" - so com uma checagem
# de proximidade como esta.


def _termo_proximo(msg: str, base: str, qualificador: str, janela: int = _JANELA_PROXIMIDADE) -> bool:
    """True se um termo que bate com o regex `base` aparece a ate `janela`
    caracteres de um termo que bate com o regex `qualificador`, em qualquer
    ordem."""
    for m in re.finditer(base, msg):
        inicio = max(0, m.start() - janela)
        fim = min(len(msg), m.end() + janela)
        if re.search(qualificador, msg[inicio:fim]):
            return True
    return False


# Sangramento e dor sao verificados por proximidade (base + qualificador de
# intensidade dentro de uma janela de caracteres) em vez de frases fixas,
# porque sao as categorias mais propensas a variacao natural ("sangramento
# MUITO intenso", "dor BEM forte"). As demais categorias abaixo (febre,
# desmaio, falta de ar, mal-estar, piora) usam frases fixas porque sao, na
# pratica, formas de relato mais estereotipadas/curtas, com baixo risco de
# palavras intercaladas.
_SANGRAMENTO_BASE = r"sangr\w*|sangue"
_SANGRAMENTO_INTENSIDADE = r"muit\w*|intens\w*|fort\w*|demais|bastante"

_DOR_BASE = r"\bdor\b"
# Inclui "subit[ao]" (dor subita) alem dos qualificadores de intensidade: uma
# dor descrita como subita e, por si so, um sinal de alarme (ex.: "dor
# pelvica subita e muito forte"), mesmo quando a palavra de intensidade fica
# fora da janela de proximidade por causa de palavras intercaladas. Compara
# sempre contra texto sem acentos (ver _sem_acentos), por isso basta a forma
# ascii aqui.
_DOR_INTENSIDADE = r"muit\w*|intens\w*|fort\w*|insuportavel|demais|subit[ao]"

SINAIS_DE_ALARME = [
    # Sangramento e dor: ver _termo_proximo() acima, nao entram nesta lista.
    "hemorragia", "encharcando um absorvente",
    # Febre importante
    "febre alta", "febre importante", "febre muito alta",
    # Desmaio
    "desmaiei", "desmaiando", "vou desmaiar", "quase desmaiei", "desmaio",
    # Falta de ar
    "falta de ar", "não consigo respirar", "nao consigo respirar",
    "dificuldade para respirar",
    # Mal-estar importante
    "mal-estar importante", "muito mal estar", "passando muito mal",
    "passando mal",
    # Piora rápida de sintomas
    "piorando rápido", "piorando rapido", "piora rápida", "piora rapida",
    # Gestante com dor, sangramento ou perda de líquido
    "perdendo líquido", "perdendo liquido", "bolsa estourou",
    "rompeu a bolsa", "bolsa rompeu",
    # Dor no peito: sempre tratada como alarme, independente de
    # qualificador de intensidade, por risco cardiaco/pulmonar.
    "dor no peito", "dor no torax",
    # Reacao alergica a medicamento (risco de anafilaxia)
    "reacao alergica", "reacao alergica ao medicamento", "alergia forte",
    "alergia grave",
    # Sinais de infeccao pos-procedimento
    "secrecao com mau cheiro", "corrimento com mau cheiro",
    "caroco doloroso",
    # Vomito persistente / desidratacao
    "nao consigo beber agua", "nao consigo reter liquido",
    "vomitando sem parar",
    # Inchaco subito de membro (risco de trombose), comum apos inicio de
    # hormonio/anticoncepcional
    "perna inchou", "perna inchada", "inchaco na perna",
    # Pedido direto de ambulancia ou de saber se e uma emergencia em curso
    "chamar uma ambulancia", "pedir uma ambulancia", "enquanto peco ajuda",
]

# AGENTS.md, Secao 6 trata "gestante com dor, sangramento ou perda de
# liquido" como sinal de alarme SEM exigir qualificador de intensidade
# ("intenso"/"muito") - diferente das demais categorias acima, que exigem
# intensidade. Uma gestante relatando qualquer dor ou sangramento (mesmo
# leve em aparencia) e tratada como alarme por causa do risco obstetrico.
# Verificado separadamente porque depende da combinacao de duas palavras
# (contexto de gestacao + sintoma), nao de uma frase fixa.
PALAVRAS_GESTACAO = [
    "grávida", "gravida", "gestante", "gravidez", "gestação", "gestacao",
]
PALAVRAS_SINTOMA_GESTACIONAL = ["dor", "sangr", "líquido", "liquido", "bolsa"]


def _e_gestante_com_sintoma(msg: str) -> bool:
    return any(g in msg for g in PALAVRAS_GESTACAO) and any(
        s in msg for s in PALAVRAS_SINTOMA_GESTACIONAL
    )


# Overdose acidental (ex.: "tomei uma dose maior do remedio sem querer"):
# combinacao de uma palavra de medicacao/dose com uma expressao de acidente,
# em vez de frase fixa, para cobrir variacoes naturais do relato.
PALAVRAS_MEDICACAO_DOSE = ["dose", "remedio", "comprimido", "medicamento"]
PALAVRAS_ACIDENTE = ["sem querer", "por engano", "errado", "a mais", "demais"]


def _e_overdose_acidental(msg: str) -> bool:
    return any(m in msg for m in PALAVRAS_MEDICACAO_DOSE) and any(
        a in msg for a in PALAVRAS_ACIDENTE
    )


MENSAGEM_URGENCIA = (
    "Nosso atendimento é ambulatorial e não oferece suporte de urgência ou "
    "emergência. Diante do que você está relatando, procure imediatamente "
    "uma unidade de urgência para avaliação presencial. Não aguarde "
    "resposta por aqui se os sintomas forem intensos ou estiverem "
    "piorando."
)

# Sinais de risco de autoagressao/crise de saude mental. Nao ha, hoje, uma
# mensagem oficial da clinica para este cenario especifico em AGENTS.md
# (apenas a orientacao generica de encaminhar "situacao emocional delicada"
# para humano) - a mensagem abaixo evita qualquer conteudo clinico/
# institucional inventado, limitando-se a acolher, encaminhar para a
# equipe humana e citar o CVV (188), um recurso publico, gratuito e
# amplamente reconhecido no Brasil, nao uma politica da clinica.
SINAIS_AUTOAGRESSAO = [
    "pensamentos de morte", "pensamento de morte", "quero morrer",
    "penso em morrer", "vou me matar", "quero me matar",
    "não aguento mais viver", "nao aguento mais viver",
    "quero acabar com tudo", "não quero mais viver", "nao quero mais viver",
    "me machucar", "vou me machucar", "pensando em me machucar",
    # Relato de violencia sexual ou domestica: tratado pela mesma via de
    # encaminhamento humano imediato (nao ha, hoje, mensagem clinica
    # especifica em AGENTS.md para este cenario - ver MENSAGEM_AUTOAGRESSAO
    # abaixo, que cobre ambos os casos citando CVV e Central de Atendimento
    # a Mulher). Comparado apenas contra texto sem acentos.
    "violencia sexual", "abuso sexual", "abusada sexualmente",
    "abusado sexualmente", "fui estuprada", "fui estuprado",
    "assedio sexual", "fui forcada a", "forcada a ter relacao",
    "nao estou segura em casa", "risco dentro de casa",
    "nao me sinto segura em casa",
]

MENSAGEM_AUTOAGRESSAO = (
    "Sinto muito que você esteja passando por isso — o que você está "
    "sentindo é importante e merece cuidado. Vou encaminhar agora mesmo "
    "seu atendimento para nossa equipe humana. Se você estiver em risco "
    "imediato ou precisar conversar com alguém agora, também pode ligar "
    "para o CVV (188) ou, em casos de violência, para a Central de "
    "Atendimento à Mulher (180) — ambos gratuitos, sigilosos e "
    "disponíveis 24 horas por dia."
)


def decidir(mensagem: str) -> dict:
    # Ordem importa: intenções mais específicas (pedido de atendimento
    # humano, cancelamento, remarcação, perguntas informativas) são
    # checadas antes do gatilho genérico de agendamento, porque palavras
    # como "consulta" aparecem tanto em "quero marcar uma consulta" quanto
    # em "quanto custa a consulta?" - sem essa ordem, a segunda seria
    # classificada erroneamente como pedido de agendamento.
    msg = mensagem.lower().strip()
    # Versao sem acentos usada apenas para o casamento de palavras-chave dos
    # sinais de alarme/autoagressao (ver _sem_acentos acima): torna a deteccao
    # resiliente a mensagens digitadas sem acento, sem exigir manter duas
    # variantes (com/sem acento) de cada nova palavra-chave adicionada aqui.
    msg_ascii = _sem_acentos(msg)

    # Sinais de alarme clinicos e risco de autoagressao vem antes de
    # qualquer outra classificacao (inclusive "humano") porque precisam
    # disparar a mensagem de seguranca especifica, nao a resposta generica
    # de encaminhamento - e porque a regra da clinica e interromper
    # IMEDIATAMENTE qualquer outro fluxo quando presentes.
    if (
        any(x in msg_ascii for x in SINAIS_DE_ALARME)
        or _termo_proximo(msg_ascii, _SANGRAMENTO_BASE, _SANGRAMENTO_INTENSIDADE)
        or _termo_proximo(msg_ascii, _DOR_BASE, _DOR_INTENSIDADE)
        or _e_gestante_com_sintoma(msg_ascii)
        or _e_overdose_acidental(msg_ascii)
    ):
        return {
            "acao": "EMERGENCIA",
            "intencao": "sinal_de_alarme",
        }

    if any(x in msg_ascii for x in SINAIS_AUTOAGRESSAO):
        return {
            "acao": "AUTOAGRESSAO",
            "intencao": "risco_autoagressao",
        }

    if any(x in msg for x in [
        "atendente",
        "humano",
        "secretária",
        "secretaria",
        "#sech",
    ]):
        return {
            "acao": "HUMANO",
            "intencao": "atendimento_humano",
        }

    if any(x in msg for x in [
        "cancelar",
        "desmarcar",
    ]):
        return {
            "acao": "CANCELAR",
            "intencao": "cancelamento",
        }

    if any(x in msg for x in [
        "remarcar",
        "reagendar",
    ]):
        return {
            "acao": "REMARCAR",
            "intencao": "remarcacao",
        }

    if any(x in msg for x in [
        "preço",
        "preco",
        "valor",
        "quanto custa",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "preco",
        }

    if any(x in msg for x in [
        "endereço",
        "endereco",
        "onde fica",
        "localização",
        "localizacao",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "endereco",
        }

    if any(x in msg for x in [
        "convênio",
        "convenio",
        "plano de saúde",
        "plano de saude",
        "unimed",
        "amil",
        "bradesco",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "convenio",
        }

    if any(x in msg for x in [
        "avaliações",
        "avaliacoes",
        "avaliação da dra",
        "avaliacao da dra",
        "reviews",
        "doctoralia",
        "estrelas",
        "nota no google",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "avaliacoes",
        }

    if any(x in msg for x in [
        "pre-natal",
        "pré-natal",
        "prenatal",
        "pre natal",
        "pré natal",
        "obstetricia",
        "obstetrícia",
        "parto",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "obstetricia",
        }

    # Perguntas explicativas ("o que é", "como funciona") sobre um tipo de
    # consulta são informativas, não um pedido de agendamento - precisam ser
    # checadas antes do gatilho genérico de "consulta"/"agendar"/"marcar"
    # logo abaixo, senão "o que é a consulta híbrida?" cairia classificada
    # como AGENDAR só por conter a palavra "consulta".
    if any(x in msg for x in [
        "o que é",
        "o que e",
        "como funciona",
        "como é",
        "como e",
        "o que significa",
    ]):
        if any(x in msg for x in ["híbrida", "hibrida"]):
            return {
                "acao": "RESPONDER",
                "intencao": "consulta_hibrida_info",
            }

        if any(x in msg for x in ["online", "vídeo", "video", "teleconsulta"]):
            return {
                "acao": "RESPONDER",
                "intencao": "consulta_online_info",
            }

        if "presencial" in msg:
            return {
                "acao": "RESPONDER",
                "intencao": "consulta_presencial_info",
            }

    if any(x in msg for x in [
        "consulta",
        "agendar",
        "marcar",
        "horário",
        "horario",
    ]):
        return {
            "acao": "AGENDAR",
            "intencao": "agendamento",
        }

    saudacoes = {
        "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite",
        "oi bom dia", "oi boa tarde", "oi boa noite",
        "ola bom dia", "ola boa tarde", "ola boa noite",
        "olá bom dia", "olá boa tarde", "olá boa noite",
        "eae", "e ai", "e aí", "opa", "salve", "oii", "oie",
    }
    msg_sem_pontuacao = msg.strip("!?.,; ")
    if msg_sem_pontuacao in saudacoes:
        return {
            "acao": "RESPONDER",
            "intencao": "saudacao",
        }

    return {
        "acao": "RESPONDER",
        "intencao": "informacao",
    }



def inferir_temperatura(mensagem: str, decisao: dict) -> str:
    """Infere a 'temperatura' do lead (Quente/Morno/Frio) a partir da
    mensagem atual e da decisao (acao/intencao) ja calculada por decidir()
    para essa mesma mensagem - reaproveitando o resultado em vez de fazer uma
    segunda classificacao. Nao ha chamada de LLM neste projeto (decidir() e
    puramente baseado em palavras-chave), entao esta e uma heuristica no
    mesmo espirito: um sinal simples para priorizacao humana no funil de
    recuperacao, nao uma verdade absoluta."""
    msg = mensagem.lower()
    acao = decisao.get("acao")

    sinais_frios = (
        "nao tenho interesse",
        "so queria saber",
        "so estou pesquisando",
        "depois eu vejo",
        "vou pensar",
        "nao quero",
        "desisti",
        "nao e mais necessario",
    )
    if any(s in msg for s in sinais_frios):
        return "FRIO"

    if acao == "AGENDAR":
        return "QUENTE"

    sinais_quentes = (
        "hoje",
        "amanha",
        "urgente",
        "o quanto antes",
        "assim que possivel",
        "pode ser agora",
    )
    if any(s in msg for s in sinais_quentes):
        return "QUENTE"

    return "MORNO"
