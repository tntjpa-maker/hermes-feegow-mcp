from pprint import pprint

from ana_feegow.workflows.remarcacao import remarcar_consulta

resultado = remarcar_consulta(
    agendamento_antigo=31,
    paciente_id=68,
    tipo_consulta="consulta_presencial",
    nova_data="15-07-2026",
    novo_horario="10:00:00",
    celular="21999999999",
    email="teste@magnolia.com",
)

print()
print("=" * 60)
print("REMARCAÇÃO")
print("=" * 60)
pprint(resultado)
