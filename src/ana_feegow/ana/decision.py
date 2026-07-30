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
