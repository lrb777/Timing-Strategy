from .base import BaseDataLoader
from .mt5_loader import MT5Loader
from .yfinance_loader import YFinanceLoader

_REGISTRY: dict[str, type[BaseDataLoader]] = {
    "yfinance": YFinanceLoader,
    "mt5": MT5Loader,
}


def get_loader(config: dict) -> BaseDataLoader:
    source = config["data"]["source"]
    if source not in _REGISTRY:
        raise ValueError(
            f"未知数据源 '{source}'，可选: {list(_REGISTRY)}"
        )
    return _REGISTRY[source](config)
