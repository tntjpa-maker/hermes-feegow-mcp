def executar_estado(conv, mensagem):
    """
    Máquina de estados legada.
    Será eliminada gradualmente.
    """

    if conv.state == "inicio":
        conv.next("aguardando_motivo")

        return (
            "Olá! 😊 Sou a ANA, secretária virtual da Dra. Thalita.\n\n"
            "É sua primeira consulta ou retorno?"
        )

    return None
