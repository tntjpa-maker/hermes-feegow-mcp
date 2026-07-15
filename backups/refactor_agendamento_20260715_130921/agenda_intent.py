import re
from datetime import date, timedelta


def interpretar_agenda(texto: str):

    texto = texto.lower().strip()

    hoje = date.today()

    # ------------------------------
    # Data específica
    # ------------------------------

    m = re.search(
        r"\b(?:dia\s+)?(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?\b",
        texto,
    )

    if m:

        dia, mes, ano = m.groups()

        ano = int(ano) if ano else hoje.year

        return {
            "tipo": "DATA_ESPECIFICA",
            "inicio": f"{ano:04d}-{int(mes):02d}-{int(dia):02d}",
        }

    # ------------------------------

    if "próxima semana" in texto or "proxima semana" in texto:
        return {
            "tipo": "PROXIMA_SEMANA",
            "inicio": (hoje + timedelta(days=7)).isoformat(),
        }

    # ------------------------------

    if "essa semana" in texto:
        return {
            "tipo": "SEMANA_ATUAL",
            "inicio": hoje.isoformat(),
        }

    # ------------------------------

    if "próximo mês" in texto or "proximo mes" in texto:
        return {
            "tipo": "PROXIMO_MES",
        }

    # ------------------------------

    if "esse mês" in texto or "este mês" in texto:
        return {
            "tipo": "MES_ATUAL",
        }

    # ------------------------------

    if any(x in texto for x in [
        "qualquer dia",
        "primeira vaga",
        "encaixe",
    ]):
        return {
            "tipo": "PRIMEIRA_VAGA",
            "inicio": hoje.isoformat(),
        }

    return None
