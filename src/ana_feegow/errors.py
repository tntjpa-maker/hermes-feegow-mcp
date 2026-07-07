class FeegowError(Exception):
    pass


class FeegowAuthError(FeegowError):
    pass


class FeegowTimeoutError(FeegowError):
    pass


class FeegowAPIError(FeegowError):
    def __init__(self, status_code: int, message: str, payload=None):
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}
        super().__init__(f"Feegow API Error {status_code}: {message}")
