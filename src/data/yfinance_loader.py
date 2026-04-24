import logging

import pandas as pd
import yfinance as yf

from .base import BaseDataLoader, OHLCV

logger = logging.getLogger(__name__)


class YFinanceLoader(BaseDataLoader):

    def __init__(self, config: dict):
        super().__init__(config)
        self.ticker = config["data"]["yfinance_ticker"]
        self.start_date = config["data"]["start_date"]
        self.end_date = config["data"].get("end_date")

    @property
    def _cache_key(self) -> str:
        end = self.end_date or "today"
        ticker = self.ticker.replace("^", "")
        return f"yfinance_{ticker}_{self.start_date}_{end}"

    @staticmethod
    def _fmt(date_str: str) -> str:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    def _fetch(self) -> pd.DataFrame:
        start = self._fmt(self.start_date)
        end = self._fmt(self.end_date) if self.end_date else None
        logger.info(f"yfinance 拉取 {self.ticker}  {start} → {end or '今天'}")

        raw = yf.download(
            self.ticker, start=start, end=end,
            auto_adjust=True, progress=False, multi_level_index=False
        )

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw.columns = [c.lower() for c in raw.columns]
        df = raw.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()

        return df[OHLCV]
