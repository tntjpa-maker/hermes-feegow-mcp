from ana_feegow.client import FeegowClient

client = FeegowClient()

endpoints = [
    "/procedure/list",
    "/procedures/list",
    "/procedure/search",
    "/procedures/search",
    "/product/list",
    "/products/list",

    "/price-table/list",
    "/pricetable/list",
    "/price/list",
    "/table/list",
    "/tables/list",
]

for ep in endpoints:
    print("\n========================")
    print(ep)
    try:
        print(client.get(ep))
    except Exception as e:
        print(e)
