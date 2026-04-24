import argparse
import sys
import yaml

sys.path.insert(0, "src")
from data import get_loader

parser = argparse.ArgumentParser()
parser.add_argument("--start", help="起始日期，格式 YYYYMMDD")
parser.add_argument("--end", help="结束日期，格式 YYYYMMDD，不填表示今天")
parser.add_argument("--source", help="数据源：yfinance | mt5")
parser.add_argument("--refresh", action="store_true", help="忽略缓存，强制重新拉取")
args = parser.parse_args()

with open("config/config.yaml", encoding="utf-8") as f:
    config = yaml.safe_load(f)

if args.start:
    config["data"]["start_date"] = args.start
if args.end:
    config["data"]["end_date"] = args.end
if args.source:
    config["data"]["source"] = args.source

df = get_loader(config).load(use_cache=not args.refresh)
print("数据形状:", df.shape)
print("时间范围:", df["date"].min().date(), "~", df["date"].max().date())
print(df.head())
