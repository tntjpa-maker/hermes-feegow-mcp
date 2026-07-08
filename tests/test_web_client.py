from ana_feegow.web_client import WebFeegowClient

client = WebFeegowClient()

print(
    client.get(
        "/main/GradeAgenda-1.asp",
        {
            "Data": "15/07/2026",
            "ProfissionalID": 1,
        },
    )
)
