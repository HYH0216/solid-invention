"""Read-only client for the Trading 212 public API (Invest / Stocks ISA accounts).

Uses only the standard library so it runs without installing anything.
"""

import base64
import json
import urllib.error
import urllib.request

LIVE_URL = "https://live.trading212.com/api/v0"
DEMO_URL = "https://demo.trading212.com/api/v0"

ERRORS = {
    401: "Trading 212 rejected the credentials (401): check T212_API_KEY / T212_API_SECRET, "
         "that the key hasn't been deleted, and that it has no IP-address restriction",
    403: "Trading 212 API key lacks permission for this endpoint (403): enable read access for account data and portfolio",
    429: "Trading 212 rate limit hit (429): try again in a minute",
}


class Trading212Client:
    def __init__(self, api_key: str, api_secret: str, demo: bool = False, timeout: float = 30):
        token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
        self.base_url = DEMO_URL if demo else LIVE_URL
        self.timeout = timeout
        self.headers = {"Authorization": f"Basic {token}", "Accept": "application/json"}

    def _get(self, path: str):
        request = urllib.request.Request(f"{self.base_url}{path}", headers=self.headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:300]
            message = ERRORS.get(exc.code, f"Trading 212 returned HTTP {exc.code} for {path}")
            raise RuntimeError(f"{message}. Response: {detail or '(empty)'}") from None

    def account_summary(self) -> dict:
        return self._get("/equity/account/summary")

    def positions(self) -> list[dict]:
        return self._get("/equity/positions")
