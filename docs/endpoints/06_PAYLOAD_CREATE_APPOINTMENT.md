# Payload - Criar Agendamento

Endpoint

POST /appoints/new-appoint

Payload homologado

{
    "local_id": 1,
    "paciente_id": 68,
    "profissional_id": 1,
    "especialidade_id": 271,
    "procedimento_id": 1,
    "data": "10-07-2026",
    "horario": "15:30:00",
    "valor": 99.99,
    "plano": 0,
    "canal_id": 0,
    "tabela_id": 0,
    "notas": "Agendado pela ANA",
    "celular": "",
    "telefone": "",
    "email": "",
    "retorno": false,
    "sys_user": 173285819
}

Resposta

{
    "success": true,
    "content": {
        "agendamento_id": 31,
        "eventos": 0
    }
}

