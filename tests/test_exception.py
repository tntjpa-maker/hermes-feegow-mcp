from pprint import pprint

from ana_feegow.client import FeegowClient
from ana_feegow.errors import FeegowAPIError

client = FeegowClient()

try:
    client.get("/appoints/list")
except FeegowAPIError as e:
    print("\n===== ATRIBUTOS =====")
    pprint(vars(e))

    print("\n===== DIR =====")
    pprint(dir(e))

    print("\n===== STR =====")
    print(str(e))
