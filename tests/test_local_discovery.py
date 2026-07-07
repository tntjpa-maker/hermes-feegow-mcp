from ana_feegow.client import FeegowClient

client = FeegowClient()

for endpoint in [
    "/appoints/local",
    "/appoints/locals",
    "/schedule/local",
    "/unit/list",
    "/units/list",
]:
    print("\n====================")
    print(endpoint)
    try:
        print(client.get(endpoint))
    except Exception as e:
        print(e)
