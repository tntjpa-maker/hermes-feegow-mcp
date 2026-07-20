import time
from typing import Any, Dict, Optional

import requests

from ana_feegow.config import settings
from ana_feegow.errors import FeegowAPIError, FeegowAuthError, FeegowTimeoutError


class FeegowClient:
    def __init__(self, base_url=None, token=None, timeout=None, retries=None):
        self.base_url = (base_url or settings.FEEGOW_BASE_URL).rstrip("/")
        self.token = token or settings.FEEGOW_ACCESS_TOKEN
        self.timeout = timeout or settings.FEEGOW_TIMEOUT
        self.retries = retries or settings.FEEGOW_RETRIES

        if not self.token:
            raise FeegowAuthError("FEEGOW_ACCESS_TOKEN não configurado.")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "x-access-token": self.token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def request(self, method: str, endpoint: str, params=None, json=None):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        last_error = None

        for attempt in range(1, self.retries + 1):
            try:
                print("=" * 60)
                print("FEEGOW REQUEST")
                print("METHOD:", method)
                print("URL:", url)
                print("PARAMS:", params)
                print("JSON:", json)

                response = requests.request(
                    method=method.upper(),
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json,
                    timeout=self.timeout,
                )

                print("STATUS:", response.status_code)
                print("BODY:", response.text[:1000])

                if response.status_code in (401, 403):
                    raise FeegowAuthError(f"Erro de autenticação Feegow: {response.status_code}")

                if response.status_code >= 400:
                    raise FeegowAPIError(
                        response.status_code,
                        response.text,
                        {"url": url, "params": params, "json": json},
                    )

                try:
                    return response.json()
                except ValueError:
                    return {"raw": response.text}

            except requests.Timeout as exc:
                last_error = exc
                time.sleep(0.5 * attempt)

            except requests.RequestException as exc:
                last_error = exc
                time.sleep(0.5 * attempt)

        if isinstance(last_error, requests.Timeout):
            raise FeegowTimeoutError(f"Timeout ao acessar Feegow: {url}")

        raise FeegowAPIError(0, f"Falha ao acessar Feegow após {self.retries} tentativas.", {"url": url})

    def get(self, endpoint: str, params=None):
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint: str, payload):
        return self.request("POST", endpoint, json=payload)

    def put(self, endpoint: str, payload):
        return self.request("PUT", endpoint, json=payload)

    def delete(self, endpoint: str, params=None, payload=None):
        return self.request("DELETE", endpoint, params=params, json=payload)
