import subprocess


def notificar_secretaria(
    telefone_paciente: str,
    motivo: str,
    ultima_mensagem: str = "",
):

    mensagem = f"""
🚨 ANA

Paciente precisa de atendimento humano.

Telefone:
{telefone_paciente}

Motivo:
{motivo}

Última mensagem:
{ultima_mensagem}
"""

    comando = (
        f'Envie a seguinte mensagem: "{mensagem.strip()}" '
        f'para o número 5521985929056'
    )

    subprocess.Popen(
        [
            "hermes",
            "chat",
            comando,
        ]
    )
