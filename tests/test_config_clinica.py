from ana_feegow.client import FeegowClient

client = FeegowClient()

consultas = [
    ("Procedimentos", "/procedure/list"),
    ("Canais", "/appoints/list-channel"),
    ("Tabelas", "/price-table/list"),
]

for titulo, endpoint in consultas:
    print("\n==============================")
    print(titulo)
    print(endpoint)

    try:
        print(client.get(endpoint))
    except Exception as e:
        print(e)
