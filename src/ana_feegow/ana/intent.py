def identificar_intencao(mensagem: str) -> str:
    msg = mensagem.lower()

    if any(x in msg for x in [
        "agendar",
        "marcar",
        "consulta",
        "horário",
        "horario"
    ]):
        return "agendamento"

    if any(x in msg for x in [
        "remarcar",
        "trocar horário",
        "trocar horario"
    ]):
        return "remarcacao"

    if any(x in msg for x in [
        "cancelar",
        "desmarcar"
    ]):
        return "cancelamento"

    if any(x in msg for x in [
        "pix",
        "pagamento",
        "comprovante"
    ]):
        return "pagamento"

    return "desconhecido"
