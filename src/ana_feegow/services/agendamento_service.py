from ana_feegow.tools.appointments import criar_agendamento
from ana_feegow.settings.clinic import CLINIC
from ana_feegow.settings.services import SERVICES


def agendar_consulta(
    paciente_id: int,
    tipo_consulta: str,
    data: str,
    horario: str,
    celular: str = "",
    telefone: str = "",
    email: str = "",
    retorno: bool = False,
    notas: str = "",
):

    servico = SERVICES[tipo_consulta]

    dados = {
        "local_id": CLINIC["local_id"],
        "paciente_id": paciente_id,
        "profissional_id": CLINIC["profissional_id"],
        "especialidade_id": CLINIC["especialidade_id"],
        "procedimento_id": servico["procedimento_id"],
        "data": data,
        "horario": horario,
        "valor": servico["valor"],
        "plano": CLINIC["plano"],
        "canal_id": CLINIC["canal_id"],
        "tabela_id": CLINIC["tabela_id"],
        "notas": notas,
        "celular": celular,
        "telefone": telefone,
        "email": email,
        "retorno": retorno,
        "sys_user": CLINIC["sys_user"],
    }

    return criar_agendamento(dados)
