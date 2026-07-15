from ana_feegow.services.preference_parser import interpretar_preferencia


def resolver_intencao(mensagem: str):

    texto = mensagem.lower().strip()

    preferencia = interpretar_preferencia(texto)

    if preferencia:
        return {
            "tipo": "nova_busca",
            "dados": preferencia,
        }

    if any(x in texto for x in [
        "outro dia",
        "outra data",
        "23/",
        "24/",
        "25/",
        "26/",
        "27/",
        "esse mês",
        "este mês",
        "mês que vem",
        "proxima semana",
        "próxima semana",
        "amanhã",
        "quinta",
        "sexta",
        "sábado",
        "sabado",
        "domingo",
    ]):
        return {
            "tipo": "nova_busca",
            "dados": None,
        }

    if any(x in texto for x in [
        "qualquer horário",
        "qualquer horario",
        "primeira vaga",
        "primeiro horário",
        "primeiro horario",
        "encaixe",
    ]):
        return {
            "tipo": "primeira_vaga",
        }

    return {
        "tipo": "continuar",
    }
