def find_id(value):
    """Procura um ID (agendamento/paciente) em uma resposta da Feegow,
    aceitando os formatos observados na prática: inteiro, string numérica,
    ou dicionário/lista aninhados sob chaves como "content", "paciente",
    "agendamento" ou "data". Compartilhado entre o motor de webhooks e o
    diálogo conversacional para evitar duas implementações divergentes.
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if isinstance(value, dict):
        for key in (
            "agendamento_id",
            "appointment_id",
            "patient_id",
            "paciente_id",
            "id",
        ):
            candidate = find_id(value.get(key))
            if candidate:
                return candidate
        for key in ("content", "paciente", "agendamento", "data"):
            candidate = find_id(value.get(key))
            if candidate:
                return candidate
        for item in value.values():
            candidate = find_id(item)
            if candidate:
                return candidate
    if isinstance(value, list):
        for item in value:
            candidate = find_id(item)
            if candidate:
                return candidate
    return None


def ok(message, **kwargs):
    retorno = {
        "success": True,
        "message": message,
    }

    retorno.update(kwargs)
    return retorno


def fail(message, **kwargs):
    retorno = {
        "success": False,
        "message": message,
    }

    retorno.update(kwargs)
    return retorno
