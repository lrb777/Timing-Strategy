from dataclasses import dataclass

import pandas as pd

from .metrics import calc_metrics


@dataclass
class BacktestResult:
    trades: pd.DataFrame       # 每笔交易记录
    equity_curve: pd.DataFrame # 逐日净值与回撤
    metrics: dict              # 汇总绩效指标


class Backtester:
    """
    轻量级逐 bar 回测引擎。

    输入 DataFrame 必须包含以下列：
      - date   : 日期
      - open   : 开盘价
      - close  : 收盘价
      - trend  : 'bull' | 'bear' | 'neutral'（来自 ThreeLineBreak）
      - signal : bool（True = 当日收盘确认多头入场信号）

    交易规则：
      入场：trend == 'bull' AND signal == True → 次日开盘买入（仅空仓时触发）
      出场：trend 由 'bull' 变为 'bear'       → 次日开盘卖出
      持仓期间忽略新入场信号
      回测结束时若仍持仓，按最后收盘价强制平仓

    成本模型（每笔单边）：
      - 滑点：买入时 open * (1 + slippage)，卖出时 open * (1 - slippage)
      - 手续费：成交金额 * commission（买卖各扣一次）

    仓位管理：
      - 每次入场全仓买入（使用全部现金）
      - 不加仓、不做空
    """

    def __init__(
        self,
        initial_capital: float = 100_000,
        commission: float = 0.0003,
        slippage: float = 0.0001,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run(self, df: pd.DataFrame) -> BacktestResult:
        df = df.reset_index(drop=True)

        cash = self.initial_capital
        shares = 0.0
        entry_cost_per_share = 0.0  # 买入时含手续费的每股全成本
        entry_date = None
        pending_entry = False
        pending_exit = False
        prev_trend = df["trend"].iloc[0] if len(df) > 0 else "neutral"

        trades = []
        equity_records = []

        for _, row in df.iterrows():
            # ── 执行上一 bar 挂单（次日开盘撮合）──────────────────────────────
            if pending_exit and shares > 0:
                exec_price = row["open"] * (1 - self.slippage)
                net_per_share = exec_price * (1 - self.commission)
                proceeds = shares * net_per_share
                pnl = proceeds - shares * entry_cost_per_share
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row["date"],
                    "entry_price": entry_cost_per_share,
                    "exit_price": net_per_share,
                    "shares": shares,
                    "pnl": pnl,
                    "return_pct": round(net_per_share / entry_cost_per_share - 1, 6),
                })
                cash += proceeds
                shares = 0.0
                entry_cost_per_share = 0.0
                entry_date = None
                pending_exit = False

            elif pending_entry and shares == 0:
                exec_price = row["open"] * (1 + self.slippage)
                cost_per_share = exec_price * (1 + self.commission)
                shares = cash / cost_per_share
                cash = 0.0
                entry_cost_per_share = cost_per_share
                entry_date = row["date"]
                pending_entry = False

            # ── 当日权益估值（持仓按收盘价标记）─────────────────────────────
            current_equity = cash + shares * row["close"]
            equity_records.append({"date": row["date"], "equity": current_equity})

            # ── 生成下一 bar 的挂单（出场优先）──────────────────────────────
            trend = row["trend"]
            if shares > 0 and trend == "bear" and prev_trend == "bull":
                pending_exit = True
            elif shares == 0 and trend == "bull" and row["signal"]:
                pending_entry = True

            prev_trend = trend

        # ── 回测结束仍持仓 → 按最后收盘价强制平仓 ─────────────────────────
        if shares > 0:
            last = df.iloc[-1]
            net_per_share = last["close"] * (1 - self.commission)
            proceeds = shares * net_per_share
            pnl = proceeds - shares * entry_cost_per_share
            trades.append({
                "entry_date": entry_date,
                "exit_date": last["date"],
                "entry_price": entry_cost_per_share,
                "exit_price": net_per_share,
                "shares": shares,
                "pnl": pnl,
                "return_pct": round(net_per_share / entry_cost_per_share - 1, 6),
            })
            equity_records[-1]["equity"] = cash + proceeds

        # ── 构建净值曲线与回撤 ───────────────────────────────────────────
        equity_df = pd.DataFrame(equity_records)
        equity_df["peak"] = equity_df["equity"].cummax()
        equity_df["drawdown"] = (equity_df["equity"] - equity_df["peak"]) / equity_df["peak"]
        equity_df = equity_df.drop(columns=["peak"])

        trades_df = (
            pd.DataFrame(trades)
            if trades
            else pd.DataFrame(columns=[
                "entry_date", "exit_date", "entry_price", "exit_price",
                "shares", "pnl", "return_pct",
            ])
        )

        metrics = calc_metrics(trades_df, equity_df, self.initial_capital)
        return BacktestResult(trades=trades_df, equity_curve=equity_df, metrics=metrics)
