import pandas as pd


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    基于三线反向突破图的趋势状态生成交易信号。

    入场信号：白色转向线出现当日（trend 由非 bull 变为 bull）→ 次日开盘买入
    出场信号：由回测引擎检测 trend 由 bull 变为 bear，此处无需处理

    输入 df 必须包含 trend 列（来自 ThreeLineBreak.run()）。
    输出在原 df 基础上增加 signal 列（bool）。
    """
    prev_trend = df["trend"].shift(1).fillna("neutral")
    df = df.copy()
    df["signal"] = (df["trend"] == "bull") & (prev_trend != "bull")
    return df
