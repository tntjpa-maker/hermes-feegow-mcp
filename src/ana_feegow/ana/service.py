def identificar_servico(mensagem: str) -> str:
    msg = mensagem.lower()

    if any(x in msg for x in [
        "online",
        "vídeo",
        "video",
        "teleconsulta"
    ]):
        return "consulta_online"

    if any(x in msg for x in [
        "híbrida",
        "hibrida"
    ]):
        return "consulta_hibrida"

    return "consulta_presencial"
