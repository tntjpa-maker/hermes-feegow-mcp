def decidir(mensagem: str) -> dict:
    msg = mensagem.lower().strip()

    # ===== PERGUNTAS =====

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
        "local",
        "onde fica",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "endereco",
        }

    if any(x in msg for x in [
        "convênio",
        "convenio",
        "plano",
        "unimed",
        "amil",
        "bradesco",
    ]):
        return {
            "acao": "RESPONDER",
            "intencao": "convenio",
        }

    # ===== OPERAÇÕES =====

    if any(x in msg for x in [
        "remarcar",
        "reagendar",
    ]):
        return {
            "acao": "REMARCAR",
            "intencao": "remarcacao",
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
        "agendar",
        "marcar consulta",
        "marcar horário",
        "quero consulta",
        "consulta presencial",
    ]):
        return {
            "acao": "AGENDAR",
            "intencao": "agendamento",
        }


    if any(x in msg for x in [
        "primeira",
        "primeira consulta",
    ]):
        return {
            "acao": "TIPO_CONSULTA",
            "intencao": "primeira_consulta",
        }

    if any(x in msg for x in [
        "retorno",
    ]):
        return {
            "acao": "TIPO_CONSULTA",
            "intencao": "retorno",
        }

    return {
        "acao": "RESPONDER",
        "intencao": "informacao",
    }
