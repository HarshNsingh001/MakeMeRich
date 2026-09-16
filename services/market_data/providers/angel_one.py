"""
Angel One SmartAPI adapter.
Docs: https://smartapi.angelone.in/docs

Authentication uses:
  - API key
  - Client ID
  - PIN
  - TOTP (time-based OTP from secret)

Set in .env:
  ANGEL_ONE_API_KEY=
  ANGEL_ONE_CLIENT_ID=
  ANGEL_ONE_PIN=
  ANGEL_ONE_TOTP_SECRET=
"""

import logging
import pyotp
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx

from providers.base import (
    MarketDataProvider,
    CandleData,
    QuoteData,
    InstrumentData,
    CorporateActionData,
)
from core.monitoring import CircuitBreaker, log_audit_event, get_structured_logger

logger = get_structured_logger(__name__)

# Angel One API base URL
BASE_URL = "https://apiconnect.angelone.in"

# Timeframe mapping: our internal → Angel One API interval names
TIMEFRAME_MAP = {
    "1min":  "ONE_MINUTE",
    "5min":  "FIVE_MINUTE",
    "15min": "FIFTEEN_MINUTE",
    "30min": "THIRTY_MINUTE",
    "1hour": "ONE_HOUR",
    "1day":  "ONE_DAY",
    "1week": "ONE_WEEK",
}


class AngelOneProvider(MarketDataProvider):
    """
    Angel One SmartAPI market data adapter.

    Usage:
        provider = AngelOneProvider(api_key=..., client_id=..., pin=..., totp_secret=...)
        await provider.authenticate()
        quote = await provider.get_quote("RELIANCE")
    """

    def __init__(self, api_key: str, client_id: str, pin: str, totp_secret: str):
        self._api_key = api_key
        self._client_id = client_id
        self._pin = pin
        self._totp_secret = totp_secret
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-UserType": "USER",
                "X-SourceID": "WEB",
                "X-ClientLocalIP": "127.0.0.1",
                "X-ClientPublicIP": "127.0.0.1",
                "X-MACAddress": "00:00:00:00:00:00",
                "X-PrivateKey": api_key,
            },
            timeout=30.0,
        )

    @property
    def provider_name(self) -> str:
        return "angel_one"

    def _get_totp(self) -> str:
        return pyotp.TOTP(self._totp_secret).now()

    async def authenticate(self) -> bool:
        """Login and store JWT token. Must be called before any data fetch."""
        try:
            resp = await self._client.post(
                "/rest/auth/angelbroking/user/v1/loginByPassword",
                json={
                    "clientcode": self._client_id,
                    "password": self._pin,
                    "totp": self._get_totp(),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") and data.get("data"):
                self._jwt_token = data["data"]["jwtToken"]
                self._refresh_token = data["data"]["refreshToken"]
                self._client.headers.update({"Authorization": f"Bearer {self._jwt_token}"})
                logger.info("Angel One: authenticated successfully")
                return True
            logger.error("Angel One: auth failed — %s", data.get("message"))
            return False
        except Exception as e:
            logger.error("Angel One: auth error — %s", e)
            return False

    async def get_quote(
        self, symbol: str, exchange: str = "NSE", token: Optional[str] = None
    ) -> QuoteData:
        """Fetch LTP + OHLC quote for a symbol."""
        if not self._circuit_breaker.can_execute():
            raise Exception("Circuit breaker is OPEN for Angel One")
            
        try:
            tok = token or symbol
            resp = await self._client.post(
                "/rest/secure/angelbroking/market/v1/quote/",
                json={"mode": "FULL", "exchangeTokens": {exchange: [tok]}},
            )
            resp.raise_for_status()
            data = resp.json()
            fetched = data["data"]["fetched"][0]
            now = datetime.utcnow()
            quote = QuoteData(
                symbol=symbol,
                exchange=exchange,
                ltp=Decimal(str(fetched.get("ltp", 0))),
                open=Decimal(str(fetched.get("open", 0))) or None,
                high=Decimal(str(fetched.get("high", 0))) or None,
                low=Decimal(str(fetched.get("low", 0))) or None,
                close=Decimal(str(fetched.get("close", 0))) or None,
                volume=int(fetched.get("tradeVolume", 0)) or None,
                change=Decimal(str(fetched.get("netChange", 0))) or None,
                change_pct=Decimal(str(fetched.get("percentChange", 0))) or None,
                quote_timestamp=now,
            )
            self._circuit_breaker.record_success()
            return quote
        except httpx.HTTPError as e:
            self._circuit_breaker.record_failure()
            log_audit_event(logger, "PROVIDER_FAIL", "provider", "angel_one", {"endpoint": "get_quote", "error": str(e)})
            raise

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        from_date: datetime,
        to_date: datetime,
        exchange: str = "NSE",
        token: Optional[str] = None,
    ) -> list[CandleData]:
        """Fetch historical OHLCV candles."""
        interval = TIMEFRAME_MAP.get(timeframe, "ONE_DAY")
        tok = token or symbol
        resp = await self._client.post(
            "/rest/secure/angelbroking/historical/v1/getCandleData",
            json={
                "exchange": exchange,
                "symboltoken": tok,
                "interval": interval,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M"),
            },
        )
        resp.raise_for_status()
        candles = []
        for row in resp.json().get("data", []):
            # row format: [timestamp, open, high, low, close, volume]
            candles.append(CandleData(
                symbol=symbol,
                exchange=exchange,
                timeframe=timeframe,
                timestamp=datetime.fromisoformat(row[0]),
                open=Decimal(str(row[1])),
                high=Decimal(str(row[2])),
                low=Decimal(str(row[3])),
                close=Decimal(str(row[4])),
                volume=int(row[5]),
            ))
        return candles

    async def get_instrument_master(self, exchange: str = "NSE") -> list[InstrumentData]:
        """Fetch full NSE equity instrument list (uses open endpoint, no auth needed)."""
        resp = await httpx.AsyncClient().get(
            "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
        )
        resp.raise_for_status()
        instruments = []
        seen = set()
        for item in resp.json():
            if item.get("exch_seg") != exchange:
                continue
            raw_sym = item.get("symbol", "")
            if exchange == "NSE" and not raw_sym.endswith("-EQ"):
                continue
            clean_sym = raw_sym[:-3] if raw_sym.endswith("-EQ") else raw_sym
            if clean_sym in seen:
                continue
            seen.add(clean_sym)
            instruments.append(InstrumentData(
                symbol=clean_sym,
                exchange=exchange,
                name=item.get("name", clean_sym),
                instrument_type="EQ",
                isin=item.get("isin"),
                sector=None,   # enriched separately or via NSE master
                token=item.get("token"),
                lot_size=int(item.get("lotsize", 1)),
            ))
        return instruments

    async def get_corporate_actions(
        self, symbol: str, exchange: str = "NSE"
    ) -> list[CorporateActionData]:
        """
        Angel One SmartAPI does not currently expose a corporate actions endpoint.
        Returns empty list — corporate actions are fetched from NSE website or
        a secondary source and stored separately.
        """
        logger.warning(
            "Angel One: no corporate actions endpoint available. "
            "Fetch from NSE website manually."
        )
        return []

    async def close(self):
        await self._client.aclose()
