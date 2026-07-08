from pprint import pprint

from ana_feegow.appointments.create import criar_agendamento
from ana_feegow.errors import FeegowAPIError

dados = {
    "local_id": 1,
    "paciente_id": 12,
    "profissional_id": 1,
    "especialidade_id": 271,
    "procedimento_id": 1,
    "data": "09-07-2026",
    "horario": "14:00:00",
    "valor": 99.99,
    "plano": 0,
    "canal_id": 0,
    "tabela_id": 0,
    "notas": "Agendado pela ANA",
    "celular": "(21)98592-9056",
    "telefone": "",
    "email": "",
    "retorno": False,
    "sys_user": 173285819,
}

try:
    pprint(criar_agendamento(dados))

except FeegowAPIError as e:
    print("\nSTATUS:", e.status_code)
    print("MENSAGEM:", e.message)
    pprint(e.payload)
