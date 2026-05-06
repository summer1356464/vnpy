from types import ModuleType
from collections.abc import Callable
from importlib import import_module

from .object import HistoryRequest, TickData, BarData
from .setting import SETTINGS
from .locale import _


class BaseDatafeed:
    """
    Abstract datafeed class for connecting to different datafeed.
    """

    def init(self, output: Callable = print) -> bool:
        """
        Initialize datafeed service connection.
        """
        return False

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> list[BarData]:
        """
        Query history bar data.
        """
        output(_("查询K线数据失败：没有正确配置数据服务"))
        return []

    def query_tick_history(self, req: HistoryRequest, output: Callable = print) -> list[TickData]:
        """
        Query history tick data.
        """
        output(_("查询Tick数据失败：没有正确配置数据服务"))
        return []


datafeed: BaseDatafeed | None = None


def get_datafeed() -> BaseDatafeed:
    """
    Get the global datafeed instance.
    """
    global datafeed
    if datafeed:
        return datafeed

    # Read datafeed related global setting
    datafeed_name: str = SETTINGS["datafeed.name"]
    use_cache: bool = SETTINGS.get("datafeed.use_cache", True)

    # Create base datafeed
    base_datafeed = BaseDatafeed()
    
    if not datafeed_name:
        datafeed = base_datafeed
        print(_("没有配置要使用的数据服务，请修改全局配置中的datafeed相关内容"))
    else:
        module_name: str = f"vnpy_{datafeed_name}"

        # Try to import datafeed module
        try:
            module: ModuleType = import_module(module_name)

            # Create datafeed object from module
            base_datafeed = module.Datafeed()
        # Use base class if failed
        except ModuleNotFoundError:
            print(_("无法加载数据服务模块，请运行 pip install {} 尝试安装").format(module_name))
    
    # Wrap with cache if enabled, regardless of whether datafeed is base or custom
    if use_cache:
        try:
            # Import inside function to avoid circular import
            from .cached_datafeed import create_cached_datafeed
            from .parquet_cache_backend import ParquetCacheBackend
            
            # Use cache path from settings if available
            cache_path = SETTINGS.get("datafeed.cache_path", "./data_cache")
            cache_backend = ParquetCacheBackend(cache_root=cache_path)
            
            datafeed = create_cached_datafeed(base_datafeed, cache_backend)
            print(_("已启用数据缓存功能"))
            print(f"缓存路径: {cache_path}")
        except ImportError:
            datafeed = base_datafeed
            print(_("数据缓存模块导入失败，将使用原始数据源"))
    else:
        datafeed = base_datafeed

    return datafeed
