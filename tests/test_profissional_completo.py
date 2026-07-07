from pprint import pprint

from ana_feegow.client import FeegowClient

client = FeegowClient()

r = client.get("/professional/list")

pprint(r)
