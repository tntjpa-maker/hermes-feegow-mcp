import requests

from ana_feegow.config import settings


class WebFeegowClient:

    def __init__(self):
        self.session = requests.Session()

        self.session.headers.update({
            "x-access-token": settings.FEEGOW_ACCESS_TOKEN,
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
        })

    def post_form(self, endpoint, payload):

        r = self.session.post(
            f"https://app.feegow.com{endpoint}",
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            },
            timeout=settings.FEEGOW_TIMEOUT,
        )

        print("STATUS:", r.status_code)
        print(r.text)

        return r
