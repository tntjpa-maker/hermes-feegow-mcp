from ana_feegow.client import FeegowClient

client = FeegowClient()


def listar_status():
    """
    Lista todos os status disponíveis para agendamentos.
    """
    return client.get("/appoints/status")
