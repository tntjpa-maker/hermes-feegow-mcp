import re
from datetime import date, datetime, timedelta


def interpretar_preferencia(texto: str):

    texto = texto.lower().strip()

    hoje = date.today()

    data_encontrada = re.search(
        r"\b(?:dia\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b",
        texto,
    )

    if data_encontrada:
        dia, mes, ano = data_encontrada.groups()
        ano = int(ano) if ano else hoje.year

        try:
            data_desejada = date(
                ano,
                int(mes),
                int(dia),
            )

            if not data_encontrada.group(3) and data_desejada < hoje:
                data_desejada = date(
                    hoje.year + 1,
                    int(mes),
                    int(dia),
                )

            return {
                "tipo": "data_especifica",
                "data_inicio": data_desejada.isoformat(),
                "periodo": None,
                "flexivel": True,
            }
        except ValueError:
            return None

    if "amanhã" in texto or "amanha" in texto:
        return {
            "tipo": "amanha",
            "data_inicio": (hoje + timedelta(days=1)).isoformat(),
            "periodo": None,
            "flexivel": True,
        }

    if (
        "próxima semana" in texto
        or "proxima semana" in texto
        or "semana que vem" in texto
    ):
        return {
            "tipo": "proxima_semana",
            "data_inicio": (hoje + timedelta(days=7)).isoformat(),
            "periodo": None,
            "flexivel": True,
        }

    primeira_vaga = [
        "qualquer dia",
        "qualquer horário",
        "qualquer horario",
        "qualquer",
        "primeira vaga",
        "primeiro horário",
        "primeiro horario",
        "encaixe",
        "quando tiver",
        "quando tem vaga",
        "qual dia tem vaga",
        "qual dia possui vaga",
        "tem vaga",
        "tem horário",
        "tem horario",
        "disponibilidade",
        "vaga disponível",
        "vaga disponivel",
    ]

    if any(x in texto for x in primeira_vaga):
        return {
            "tipo": "primeira_vaga",
            "data_inicio": hoje.isoformat(),
            "periodo": None,
            "flexivel": True,
        }


    periodo = None

    if any(x in texto for x in ["manhã", "manha"]):
        periodo = "manha"

    elif "tarde" in texto:
        periodo = "tarde"

    elif any(x in texto for x in ["noite", "fim da tarde"]):
        periodo = "noite"

    if periodo:
        return {
            "tipo": "periodo",
            "data_inicio": hoje.isoformat(),
            "periodo": periodo,
            "flexivel": True,
        }

    return None
