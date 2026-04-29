from collections import defaultdict

import polars as pl

from vnpy.trader.object import BarData, TradeData
from vnpy.trader.constant import Direction
from vnpy.trader.utility import round_to

from vnpy.alpha import AlphaStrategy


class EquityDemoStrategy(AlphaStrategy):
    """Equity Long-Only Demo Strategy"""

    top_k: int = 3                  # Maximum number of stocks to hold
    n_drop: int = 1                 # Number of stocks to sell each time
    min_days: int = 5               # Minimum holding period in days
    cash_ratio: float = 0.8         # Cash utilization ratio (reduce to prevent overtrading)
    min_volume: int = 100           # Minimum trading unit
    open_rate: float = 0.0005       # Opening commission rate
    close_rate: float = 0.0015      # Closing commission rate
    min_commission: int = 5         # Minimum commission value
    price_add: float = 0.01         # Order price adjustment ratio

    def on_init(self) -> None:
        """Strategy initialization callback"""
        # Dictionary to track stock holding days
        self.holding_days: defaultdict = defaultdict(int)

        self.write_log("Strategy initialized")
        self.write_log(f"初始资金: {self.get_cash_available():.2f}")
        self.write_log(f"策略参数: top_k={self.top_k}, n_drop={self.n_drop}, min_days={self.min_days}, cash_ratio={self.cash_ratio}")
        self.write_log(f"交易费率: open_rate={self.open_rate}, close_rate={self.close_rate}, min_commission={self.min_commission}")

    def on_trade(self, trade: TradeData) -> None:
        """Trade execution callback"""
        # Remove holding days record when selling
        if trade.direction == Direction.SHORT:
            self.holding_days.pop(trade.vt_symbol, None)

    def on_bars(self, bars: dict[str, BarData]) -> None:
        """K-line slice callback"""
        # 调试日志：当前时间和可用现金
        current_time = list(bars.values())[0].datetime if bars else "未知时间"
        available_cash = self.get_cash_available()
        self.write_log(f"on_bars调用，时间: {current_time}, 可用现金: {available_cash:.2f}")
        
        # Get the latest signals and sort them
        last_signal: pl.DataFrame = self.get_signal()
        self.write_log(f"获取到的信号数量: {len(last_signal)}")
        
        if last_signal.is_empty():
            self.write_log("没有获取到信号数据，跳过本次处理")
            return
            
        last_signal = last_signal.sort("signal", descending=True)
        self.write_log(f"信号排序完成，前3个信号: {last_signal.head(3)}")

        # Get position symbols and update holding days
        pos_symbols: list[str] = [vt_symbol for vt_symbol, pos in self.pos_data.items() if pos]
        self.write_log(f"当前持仓: {pos_symbols}")

        for vt_symbol in pos_symbols:
            self.holding_days[vt_symbol] += 1

        # Generate sell list
        active_symbols: set[str] = set(last_signal["vt_symbol"][:self.top_k])                         # Extract symbols with highest signals
        active_symbols.update(pos_symbols)                                                            # Merge with currently held symbols
        active_df: pl.DataFrame = last_signal.filter(pl.col("vt_symbol").is_in(active_symbols))       # Filter signals for these symbols
        self.write_log(f"活跃股票: {active_symbols}")

        component_symbols: set[str] = set(last_signal["vt_symbol"])                 # Extract current index component symbols
        sell_symbols: set[str] = set(pos_symbols).difference(component_symbols)     # Sell positions not in components
        self.write_log(f"成分股: {component_symbols}, 待卖出: {sell_symbols}")

        for vt_symbol in active_df["vt_symbol"][-self.n_drop:]:                     # Iterate through lowest signal portion
            if vt_symbol in pos_symbols:                                            # If the contract is in current positions
                sell_symbols.add(vt_symbol)                                         # Add it to sell list
        self.write_log(f"最终待卖出: {sell_symbols}")

        # Generate buy list
        buyable_df: pl.DataFrame = last_signal.filter(~pl.col("vt_symbol").is_in(pos_symbols))  # Filter contracts available for purchase
        buy_quantity: int = len(sell_symbols) + self.top_k - len(pos_symbols)                   # Calculate number of contracts to buy
        buy_symbols: list = list(buyable_df[:buy_quantity]["vt_symbol"])                        # Select buy contract code list
        self.write_log(f"可买入股票: {buyable_df.shape}, 需买入数量: {buy_quantity}, 待买入: {buy_symbols}")

        # Sell rebalancing
        available_cash: float = self.get_cash_available()                     # Get available cash after yesterday's settlement
        self.write_log(f"卖出再平衡前现金: {available_cash:.2f}")

        for vt_symbol in sell_symbols:
            if self.holding_days[vt_symbol] < self.min_days:
                self.write_log(f"{vt_symbol}持仓天数不足{self.min_days}天，跳过卖出")
                continue

            bar: BarData | None = bars.get(vt_symbol)
            if not bar:
                self.write_log(f"未获取到{vt_symbol}的行情数据，跳过卖出")
                continue
                
            sell_price: float = bar.close_price
            sell_volume: float = self.get_pos(vt_symbol)
            
            self.write_log(f"卖出{vt_symbol}, 价格: {sell_price:.2f}, 数量: {sell_volume:.2f}")
            self.set_target(vt_symbol, target=0)
        
        # 获取卖出后的可用现金
        available_cash = self.get_cash_available()
        self.write_log(f"卖出再平衡后现金: {available_cash:.2f}")

        # Buy rebalancing
        if buy_symbols and available_cash > 0:
            # 计算每只股票的最大买入金额，考虑手续费
            total_buy_value: float = available_cash * self.cash_ratio
            buy_value_per_stock: float = total_buy_value / len(buy_symbols)
            self.write_log(f"买入再平衡，总买入金额: {total_buy_value:.2f}, 每只股票买入金额: {buy_value_per_stock:.2f}")
            
            if buy_value_per_stock <= 0:
                self.write_log("买入金额不足，跳过买入")
                return

            for vt_symbol in buy_symbols:
                if vt_symbol not in bars:
                    self.write_log(f"未获取到{vt_symbol}的行情数据，跳过买入")
                    continue
                    
                buy_price: float = bars[vt_symbol].close_price
                if not buy_price or buy_price <= 0:
                    self.write_log(f"{vt_symbol}价格无效: {buy_price}, 跳过买入")
                    continue

                # 计算买入数量，考虑手续费和合约size
                # 获取合约的size（每手股数）
                size: float = self.strategy_engine.sizes.get(vt_symbol, 1)  # 默认值为1
                
                # 买入金额 = 买入价格 * 买入数量 * size + 手续费
                # 手续费 = 买入价格 * 买入数量 * size * 交易费率
                # 买入金额 = 买入价格 * 买入数量 * size * (1 + 交易费率)
                # 买入数量 = 买入金额 / (买入价格 * size * (1 + 交易费率))
                buy_amount: float = buy_value_per_stock / (1 + self.open_rate)
                buy_volume: float = round_to(buy_amount / (buy_price * size), self.min_volume)
                
                if buy_volume <= 0:
                    self.write_log(f"{vt_symbol}计算买入数量为0，跳过买入")
                    continue

                # 计算实际需要的资金（包括手续费）
                actual_cost: float = buy_price * buy_volume * size * (1 + self.open_rate)
                if actual_cost > available_cash:
                    # 如果实际需要的资金超过可用资金，调整买入数量
                    buy_amount = available_cash / (1 + self.open_rate)
                    buy_volume = round_to(buy_amount / (buy_price * size), self.min_volume)
                    if buy_volume <= 0:
                        self.write_log(f"{vt_symbol}调整后买入数量为0，跳过买入")
                        continue
                    # 重新计算实际成本
                    actual_cost = buy_price * buy_volume * size * (1 + self.open_rate)

                self.write_log(f"买入{vt_symbol}, 价格: {buy_price:.2f}, 数量: {buy_volume:.2f}, 预计成本: {actual_cost:.2f}")
                self.set_target(vt_symbol, buy_volume)
        else:
            self.write_log("无待买入股票或现金不足，跳过买入再平衡")

        # Execute trading
        self.write_log("执行交易")
        self.execute_trading(bars, price_add=self.price_add)
