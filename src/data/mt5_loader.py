import logging
from datetime import datetime

import pandas as pd

from .base import BaseDataLoader, OHLCV

logger = logging.getLogger(__name__)


class MT5Loader(BaseDataLoader):

    def __init__(self, config: dict):
        super().__init__(config)
        self.symbol = config["data"]["mt5_symbol"]
        self.start_date = config["data"]["start_date"]
        self.end_date = config["data"].get("end_date")

    @property
    def _cache_key(self) -> str:
        end = self.end_date or "today"
        return f"mt5_{self.symbol}_{self.start_date}_{end}"

    @staticmethod
    def _parse(date_str: str) -> datetime:
        return datetime.strptime(date_str, "%Y%m%d")

    def _fetch(self) -> pd.DataFrame:
        try:
            import MetaTrader5 as mt5
        except ImportError:
            raise ImportError(
                "MetaTrader5 未安装，请执行: pip install MetaTrader5\n"
                "注意：该包仅支持 Windows，且需要 MT5 客户端保持运行。"
            )

        if not mt5.initialize():
            raise RuntimeError(f"MT5 初始化失败: {mt5.last_error()}")

        try:
            start = self._parse(self.start_date)
            end = self._parse(self.end_date) if self.end_date else datetime.now()
            logger.info(f"MT5 拉取 {self.symbol}  {start.date()} → {end.date()}")

            rates = mt5.copy_rates_range(self.symbol, mt5.TIMEFRAME_D1, start, end)

            if rates is None or len(rates) == 0:
                raise RuntimeError(
                    f"{self.symbol} 无数据: {mt5.last_error()}\n"
                    "请确认 MT5 已登录，且该品种在报价列表中可见。"
                )

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s").dt.normalize()
            df = df.rename(columns={"time": "date", "tick_volume": "volume"})
            return df[OHLCV]
        finally:
            mt5.shutdown()
