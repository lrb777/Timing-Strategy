import logging
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

OHLCV = ["date", "open", "high", "low", "close", "volume"]


class BaseDataLoader(ABC):

    def __init__(self, config: dict):
        self.raw_dir = Path(config["data"]["raw_dir"])
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    @abstractmethod
    def _cache_key(self) -> str:
        """返回唯一的缓存文件名 key。"""

    @abstractmethod
    def _fetch(self) -> pd.DataFrame:
        """从数据源拉取原始数据，返回含 OHLCV 列的 DataFrame。"""

    def load(self, use_cache: bool = True) -> pd.DataFrame:
        cache_path = self.raw_dir / f"{self._cache_key}.csv"
        if use_cache and cache_path.exists():
            logger.info(f"从缓存加载: {cache_path}")
            return pd.read_csv(cache_path, parse_dates=["date"])
        df = self._fetch()
        df = self._validate(df)
        df.to_csv(cache_path, index=False)
        logger.info(f"已缓存 {len(df)} 行 → {cache_path}")
        return df

    def _validate(self, df: pd.DataFrame) -> pd.DataFrame:
        before = len(df)
        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df[df["close"] > 0]
        df = df.sort_values("date").reset_index(drop=True)
        dropped = before - len(df)
        if dropped:
            logger.warning(f"清除 {dropped} 行无效数据")
        return df
