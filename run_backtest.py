import sys
import yaml

sys.path.insert(0, "src")

from data import get_loader
from indicators import ThreeLineBreak
from strategy import generate_signals
from backtest import Backtester

# ── 加载配置 ────────────────────────────────────────────────────────────────
with open("config/config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

# ── 数据 ─────────────────────────────────────────────────────────────────────
df = get_loader(config).load()
print(f"数据加载完成：{df['date'].min().date()} ~ {df['date'].max().date()}，共 {len(df)} 行\n")

# ── 三线反向突破图 ────────────────────────────────────────────────────────────
n = config["three_line_break"]["n"]
df = ThreeLineBreak(n=n).run(df)

trend_counts = df["trend"].value_counts()
print(f"趋势分布（N={n}）：")
for label, count in trend_counts.items():
    print(f"  {label:>8}: {count} 天")
print()

# ── 信号生成 ──────────────────────────────────────────────────────────────────
df = generate_signals(df)
print(f"入场信号次数：{df['signal'].sum()}\n")

# ── 回测 ──────────────────────────────────────────────────────────────────────
bt_cfg = config["backtest"]
bt = Backtester(
    initial_capital=bt_cfg["initial_capital"],
    commission=bt_cfg["commission"],
    slippage=bt_cfg["slippage"],
)
result = bt.run(df)

# ── 输出结果 ──────────────────────────────────────────────────────────────────
print("=" * 40)
print("绩效指标")
print("=" * 40)
m = result.metrics
print(f"  交易次数    : {m['total_trades']}")
print(f"  胜率        : {m['win_rate']:.2%}")
print(f"  总收益率    : {m['total_return']:.2%}")
print(f"  年化收益率  : {m['annualized_return']:.2%}")
print(f"  最大回撤    : {m['max_drawdown']:.2%}")
print(f"  夏普比率    : {m['sharpe_ratio']:.2f}")

if not result.trades.empty:
    print()
    print("=" * 40)
    print("交易记录（前10笔）")
    print("=" * 40)
    cols = ["entry_date", "exit_date", "entry_price", "exit_price", "pnl", "return_pct"]
    print(result.trades[cols].head(10).to_string(index=False))
