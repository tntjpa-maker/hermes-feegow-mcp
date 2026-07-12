def agendar(decisao, conv):

    # Início do fluxo
    if decisao["acao"] == "AGENDAR":
        conv.next("aguardando_motivo")
        return (
            "Perfeito! 😊\n\n"
            "É sua primeira consulta ou retorno?"
        )

    # Paciente respondeu o tipo
    if decisao["acao"] == "TIPO_CONSULTA":
        conv.update("motivo", decisao["intencao"])
        conv.next("aguardando_data")
        return "Qual dia você prefere para a consulta? (dd/mm/aaaa)"

    return "Não consegui entender."
