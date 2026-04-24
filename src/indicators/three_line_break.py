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

    画线规则：
    - 第一天记为基价，不画线
    - 白线阶段：
        收盘 > 最后一根线高点 → 新白线
        收盘 < 最近 N 根连续白线最低低点 → 黑色转向线（阶段切换）
    - 黑线阶段：
        收盘 < 最后一根线低点 → 新黑线
        收盘 > 最近 N 根连续黑线最高高点 → 白色转向线（阶段切换）

    转向线计入 N 根计数。
    趋势状态仅在转向线出现时切换，首次转向线前为中性。
    """

    def __init__(self, n: int = 3):
        self.n = n
        self.lines: List[Line] = []
        self._base: Optional[float] = None
        self._trend: Optional[str] = None  # 'white' | 'black'，仅在转向线时更新

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
        self._trend = None

    def _process(self, close: float, date: pd.Timestamp) -> str:
        # 第一天：记录基价
        if self._base is None:
            self._base = close
            return "neutral"

        # 尚无任何线：与基价比较确定第一根线
        if not self.lines:
            if close > self._base:
                self._add(close, self._base, "white", False, date)
            elif close < self._base:
                self._add(self._base, close, "black", False, date)
            return self._signal()

        last = self.lines[-1]
        phase = last.color

        if phase == "white":
            if close > last.high:
                # 新高 → 新白线（延续）
                self._add(close, last.high, "white", False, date)
            else:
                threshold = self._reversal_threshold("white")
                if threshold is not None and close < threshold:
                    # 跌破 N 根白线最低低点 → 黑色转向线
                    self._add(last.high, close, "black", True, date)

        elif phase == "black":
            if close < last.low:
                # 新低 → 新黑线（延续）
                self._add(last.low, close, "black", False, date)
            else:
                threshold = self._reversal_threshold("black")
                if threshold is not None and close > threshold:
                    # 突破 N 根黑线最高高点 → 白色转向线
                    self._add(close, last.low, "white", True, date)

        return self._signal()

    def _add(self, high: float, low: float, color: str, is_reversal: bool, date: pd.Timestamp):
        self.lines.append(Line(high=high, low=low, color=color, is_reversal=is_reversal, date=date))
        if is_reversal:
            self._trend = color

    def _signal(self) -> str:
        if self._trend is None:
            return "neutral"
        return "bull" if self._trend == "white" else "bear"

    def _reversal_threshold(self, phase: str) -> Optional[float]:
        """
        从末尾收集当前阶段连续同色线（含转向线），最多 N 根。
        不足 N 根时返回 None。
        """
        collected = []
        for line in reversed(self.lines):
            if line.color == phase:
                collected.append(line)
                if len(collected) == self.n:
                    break
            else:
                break

        if len(collected) < self.n:
            return None

        return min(l.low for l in collected) if phase == "white" else max(l.high for l in collected)
