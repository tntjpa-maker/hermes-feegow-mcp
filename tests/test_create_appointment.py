from pprint import pprint

from ana_feegow.appointments.create import criar_agendamento
from ana_feegow.errors import FeegowAPIError

dados = {
    "local_id": 1,
    "paciente_id": 68,
    "profissional_id": 1,
    "especialidade_id": 271,
    "procedimento_id": 1,
    "data": "10-07-2026",
    "horario": "15:30:00",
    "valor": 99.99,
    "plano": 0,
    "canal_id": 10,
    "tabela_id": 0,
    "notas": "Teste MCP ANA",
    "celular": "(21)99999-9999",
    "telefone": "",
    "email": "teste@magnolia.com",
    "retorno": False,
    "sys_user": 173285819,
}

try:
    resultado = criar_agendamento(dados)

    print("\n==========================")
    print("RESPOSTA")
    print("==========================")
    pprint(resultado)

except FeegowAPIError as e:
    print("\n==========================")
    print("STATUS:", e.status_code)
    print("==========================")
    print(e.body)

    if hasattr(e, "context"):
        print("\nPAYLOAD ENVIADO:")
        pprint(e.context.get("json"))
