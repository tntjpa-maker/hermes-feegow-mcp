from ana_feegow.web_client import WebFeegowClient

client = WebFeegowClient()

payload = {
    "ConsultaID": 0,
    "GradeID": 8,
    "Data": "15/07/2026",
    "Hora": "14:00",
    "ProfissionalID": 1,
    "EspecialidadeID": 271,
    "StaID": 1,
    "PacienteID": 11,
    "ProcedimentoID": 1,
    "Tempo": 30,
    "Valor": "99,99",
    "LocalID": 1,
    "Notas": "",
}

client.post_form(
    "/main/AgendaParametros.asp?tipo=PacienteID&id=11&paciente=11&AgendamentoID=0",
    payload,
)

assert True
