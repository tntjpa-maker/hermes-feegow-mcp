from ana_feegow.client import FeegowClient

client = FeegowClient()

def remarcar_agendamento(dados):
    return client.post(
        "/appoints/reschedule",
        dados,
    )
