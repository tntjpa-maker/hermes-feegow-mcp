def decidir(mensagem: str) -> dict:
    # Ordem importa: intenções mais específicas (pedido de atendimento
    # humano, cancelamento, remarcação, perguntas informativas) são
    # checadas antes do gatilho genérico de agendamento, porque palavras
    # como "consulta" aparecem tanto em "quero marcar uma consulta" quanto
    # em "quanto custa a consulta?" - sem essa ordem, a segunda seria
    # classificada erroneamente como pedido de agendamento.
    msg = mensagem.lower().strip()

    if any(x in msg for x in [
        "atendente",
        "humano",
        "secretária",
        "secretaria",
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
