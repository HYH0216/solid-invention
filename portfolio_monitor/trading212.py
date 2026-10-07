"""Read-only client for the Trading 212 public API (Invest / Stocks ISA accounts)."""

import base64

import requests

LIVE_URL = "https://live.trading212.com/api/v0"
DEMO_URL = "https://demo.trading212.com/api/v0"


class Trading212Client:
    def __init__(self, api_key: str, api_secret: str, demo: bool = False, timeout: float = 30):
        token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        self.base_url = DEMO_URL if demo else LIVE_URL
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Basic {token}"

    def _get(self, path: str):
        resp = self.session.get(f"{self.base_url}{path}", timeout=self.timeout)
        if resp.status_code == 401:
            raise RuntimeError("Trading 212 rejected the credentials (401): check API key and secret")
        if resp.status_code == 403:
            raise RuntimeError("Trading 212 API key lacks permission for " + path + " (403)")
        if resp.status_code == 429:
            raise RuntimeError("Trading 212 rate limit hit (429): try again later")
        resp.raise_for_status()
        return resp.json()

    def account_summary(self) -> dict:
        return self._get("/equity/account/summary")

    def positions(self) -> list[dict]:
        return self._get("/equity/positions")
