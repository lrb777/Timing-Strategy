from dataclasses import dataclass
from typing import List, Optional

import pandas as pd


@dataclass
class Line:
    high: float
    low: float
    color: str         # 'white' | 'black'
    is_reversal: bool
    date: pd.Timestamp


class ThreeLineBreak:
    """
    三线反向突破图指标。

    画线规则（每日执行）：
    - 第一天记为基价，不画线
    - 今日收盘 > 图上最后一根线高点 → 画白线
    - 今日收盘 < 图上最后一根线低点 → 画黑线
    - 否则不画线

    转向线判断（画完后分类）：
    - 新白线之前连续有 N 根黑线 → 标记为白色转向线
    - 新黑线之前连续有 N 根白线 → 标记为黑色转向线
    """

    def __init__(self, n: int = 3):
        self.n = n
        self.lines: List[Line] = []
        self._base: Optional[float] = None

    # ------------------------------------------------------------------ #
    # 公开接口
    # ------------------------------------------------------------------ #

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        输入: 含 [date, close] 列的 DataFrame
        输出: 原 DataFrame 增加 'trend' 列（'bull' | 'bear' | 'neutral'）
        """
        self._reset()
        trends = [self._process(row.close, row.date) for row in df.itertuples()]
        out = df.copy()
        out["trend"] = trends
        return out

    @property
    def lines_df(self) -> pd.DataFrame:
        """返回所有已画线的 DataFrame，用于调试或可视化。"""
        if not self.lines:
            return pd.DataFrame(columns=["date", "high", "low", "color", "is_reversal"])
        return pd.DataFrame([
            {"date": l.date, "high": l.high, "low": l.low,
             "color": l.color, "is_reversal": l.is_reversal}
            for l in self.lines
        ])

    # ------------------------------------------------------------------ #
    # 内部逻辑
    # ------------------------------------------------------------------ #

    def _reset(self):
        self.lines = []
        self._base = None

    def _process(self, close: float, date: pd.Timestamp) -> str:
        # 第一天：记录基价
        if self._base is None:
            self._base = close
            return "neutral"

        # 基价之后，尚无任何线：与基价比较
        if not self.lines:
            if close > self._base:
                self._add(close, self._base, "white", False, date)
            elif close < self._base:
                self._add(self._base, close, "black", False, date)
            return self._signal()

        last = self.lines[-1]

        if close > last.high:
            # 创新高 → 画白线；画完后判断是否为转向线
            is_rev = last.color == "black" and self._consecutive_count("black") >= self.n
            self._add(close, last.high, "white", is_rev, date)

        elif close < last.low:
            # 创新低 → 画黑线；画完后判断是否为转向线
            is_rev = last.color == "white" and self._consecutive_count("white") >= self.n
            self._add(last.low, close, "black", is_rev, date)

        return self._signal()

    def _add(self, high: float, low: float, color: str, is_reversal: bool, date: pd.Timestamp):
        self.lines.append(Line(high=high, low=low, color=color, is_reversal=is_reversal, date=date))

    def _signal(self) -> str:
        if not self.lines:
            return "neutral"
        return "bull" if self.lines[-1].color == "white" else "bear"

    def _consecutive_count(self, color: str) -> int:
        """从末尾向前统计连续同色线的数量。"""
        count = 0
        for line in reversed(self.lines):
            if line.color == color:
                count += 1
            else:
                break
        return count
