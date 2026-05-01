import numpy as np
import pandas as pd
from typing import Dict


def calc_metrics(trades: pd.DataFrame, equity_curve: pd.DataFrame, initial_capital: float) -> Dict:
    """从交易记录和净值曲线计算绩效指标。"""
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "total_return": 0.0,
            "annualized_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
        }

    # 总收益率
    final_equity = equity_curve["equity"].iloc[-1]
    total_return = (final_equity - initial_capital) / initial_capital

    # 年化收益率
    n_days = (pd.Timestamp(equity_curve["date"].iloc[-1]) -
              pd.Timestamp(equity_curve["date"].iloc[0])).days
    n_years = n_days / 365.25
    annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0

    # 最大回撤
    max_drawdown = float(equity_curve["drawdown"].min())

    # 胜率
    total_trades = len(trades)
    win_rate = float((trades["pnl"] > 0).sum()) / total_trades

    # 年化夏普比（无风险利率 = 0）
    daily_returns = equity_curve["equity"].pct_change().dropna()
    std = daily_returns.std()
    sharpe = float((daily_returns.mean() / std) * np.sqrt(252)) if std > 0 else 0.0

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 4),
        "total_return": round(total_return, 4),
        "annualized_return": round(annualized_return, 4),
        "max_drawdown": round(max_drawdown, 4),
        "sharpe_ratio": round(sharpe, 4),
    }
