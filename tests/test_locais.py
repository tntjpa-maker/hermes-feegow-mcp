from ana_feegow.client import FeegowClient

client = FeegowClient()

for endpoint in [
    "/local/list",
    "/locals/list",
    "/location/list",
    "/locations/list",
]:
    print("\n====================")
    print(endpoint)
    try:
        print(client.get(endpoint))
    except Exception as e:
        print(e)
