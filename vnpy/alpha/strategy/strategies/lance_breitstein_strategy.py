from collections import deque
from typing import Dict, List, Optional, Tuple
import numpy as np

from vnpy.trader.object import BarData
from vnpy.trader.constant import Direction
from vnpy.alpha.strategy.template import AlphaStrategy


class LanceBreitsteinStrategy(AlphaStrategy):
    """
    Lance Breitstein 原版交易规则策略实现
    严格遵循其公开核心规则，适配A股日线回测。

    核心哲学：
      趋势跟随 + 精确回踩入场
      - 永远不在价格稳定站上VWAP时做空
      - 永远不在价格稳定跌破VWAP时做多
      - 不追涨，等待价格回踩支撑位（趋势线/MA20/VWAP）后确认反弹再入场
    """

    # 策略参数
    lookback_days: int = 120      # 回溯天数（需足够计算所有均线）
    vwap_days: int = 20           # VWAP 计算窗口
    short_ma: int = 10            # 短期均线 (MA10)
    medium_ma: int = 20           # 中期均线 (MA20，Lance 常用支撑位)
    long_ma: int = 50             # 长期均线 (MA50，Lance 常用趋势基准)
    trendline_points: int = 3     # 趋势线所需摆动低点数量
    swing_window: int = 5         # 识别摆动高低点的窗口（左右各N根K线）
    pullback_tolerance: float = 0.03  # 回踩支撑位的容差（3%以内算"接近支撑"）
    position_size: float = 0.1   # 每个标的的最大仓位占总资金比例
    
    # 止盈止损参数
    exit_mode: str = "condition"  # 卖出模式："condition"(条件模式) 或 "fixed_ratio"(固定比例模式)
    take_profit_ratio: float = 3.5  # 止盈比例 (3.5R)
    stop_loss_ratio: float = 1.0    # 止损比例 (1R)

    def __init__(self, engine, strategy_name, vt_symbols, setting):
        super().__init__(engine, strategy_name, vt_symbols, setting)

        # 主数据缓存（日线，maxlen=lookback_days）
        self.bar_cache: Dict[str, deque] = {}
        for symbol in vt_symbols:
            self.bar_cache[symbol] = deque(maxlen=self.lookback_days)

        # 兼容性保留（不再主动使用，防止父类或脚本报错）
        self.weekly_bars: Dict[str, deque] = {s: deque(maxlen=30) for s in vt_symbols}
        self.daily_bars: Dict[str, deque] = {s: deque(maxlen=120) for s in vt_symbols}
        self.minute_bars: Dict[str, deque] = {s: deque(maxlen=1440) for s in vt_symbols}
        
        # 持仓记录（用于止盈止损计算）
        self.entry_prices: Dict[str, float] = {}  # 标的 -> 入场价格

    # ------------------------------------------------------------------
    # 生命周期回调
    # ------------------------------------------------------------------

    def on_init(self):
        """策略初始化"""
        self.write_log("Lance Breitstein 策略初始化完成")
        self.write_log(
            f"参数: lookback={self.lookback_days}, vwap_days={self.vwap_days}, "
            f"MA({self.short_ma}/{self.medium_ma}/{self.long_ma}), "
            f"swing_window={self.swing_window}, pullback_tol={self.pullback_tolerance}"
        )

    def on_bars(self, bars: Dict[str, BarData]):
        """每个交易日 K 线回调"""
        for vt_symbol, bar in bars.items():
            # 懒初始化
            if vt_symbol not in self.bar_cache:
                self.bar_cache[vt_symbol] = deque(maxlen=self.lookback_days)
            self.bar_cache[vt_symbol].append(bar)

        self.dynamic_select_and_trade(bars)

    def on_trade(self, trade):
        """成交回调"""
        self.write_log(
            f"成交: {trade.vt_symbol} {trade.direction.value} "
            f"{trade.offset.value} {trade.volume}手 @ {trade.price}"
        )

    # ------------------------------------------------------------------
    # 主交易逻辑
    # ------------------------------------------------------------------

    def dynamic_select_and_trade(self, bars: Dict[str, BarData]):
        """动态选股并管理仓位"""
        min_bars = max(self.long_ma, self.lookback_days // 2)

        # ① 筛选满足五大条件 + 三周期共振的候选标的
        candidates: List[str] = []
        for vt_symbol, bar in bars.items():
            cache = self.bar_cache.get(vt_symbol)
            if not cache or len(cache) < min_bars:
                continue
            if not self.check_five_conditions(vt_symbol):
                continue
            if not self.check_multi_timeframe_resonance(vt_symbol):
                continue
            candidates.append(vt_symbol)
        
        # 添加调试日志，显示候选标的数量
        self.write_log(f"符合条件的候选标的数量: {len(candidates)}")

        # ② 卖出逻辑 - 根据选择的模式执行
        current_positions = {sym: pos for sym, pos in self.pos_data.items() if pos > 0}
        for vt_symbol in current_positions:
            bar = bars.get(vt_symbol)
            if not bar:
                continue
                
            if self.exit_mode == "condition":
                # 条件模式：清仓不再满足条件的持仓
                if vt_symbol not in candidates:
                    self.write_log(f"{vt_symbol} 不再满足条件，清仓")
                    self.set_target(vt_symbol, 0)
                    # 清除入场价格记录
                    if vt_symbol in self.entry_prices:
                        del self.entry_prices[vt_symbol]
            
            elif self.exit_mode == "fixed_ratio":
                # 固定比例模式：止盈止损
                if vt_symbol in self.entry_prices:
                    entry_price = self.entry_prices[vt_symbol]
                    current_price = bar.close_price
                    
                    # 计算涨跌幅
                    price_change = (current_price - entry_price) / entry_price
                    
                    # 止盈：达到或超过3.5%（3.5R）
                    if price_change >= self.take_profit_ratio / 100:
                        self.write_log(f"{vt_symbol} 止盈卖出：入场价 {entry_price}, 当前价 {current_price}, 涨幅 {price_change:.2%}")
                        self.set_target(vt_symbol, 0)
                        del self.entry_prices[vt_symbol]
                    # 止损：达到或低于-1%（-1R）
                    elif price_change <= -self.stop_loss_ratio / 100:
                        self.write_log(f"{vt_symbol} 止损卖出：入场价 {entry_price}, 当前价 {current_price}, 跌幅 {abs(price_change):.2%}")
                        self.set_target(vt_symbol, 0)
                        del self.entry_prices[vt_symbol]
                else:
                    # 无入场价格记录时，使用条件模式退出
                    self.write_log(f"{vt_symbol} 无入场价格记录，使用条件模式退出")
                    if vt_symbol not in candidates:
                        self.write_log(f"{vt_symbol} 不再满足条件，清仓")
                        self.set_target(vt_symbol, 0)

        if not candidates:
            self.write_log("无符合条件的候选标的")
            self.execute_trading(bars)
            return

        # ③ 计算每个标的目标仓位
        # 正确逻辑：position_size = 0.1 表示 每个标的最多占总资金的10%，而非所有标的平分
        
        # 可用现金
        available_cash = self.get_cash_available()
        
        # 计算当前已持仓金额
        current_holding_value = sum(
            pos * bars[symbol].close_price 
            for symbol, pos in current_positions.items() 
            if symbol in bars and pos > 0
        )
        
        # 总资金 = 可用现金 + 当前持仓金额
        total_capital = available_cash + current_holding_value
        
        # 每个标的的最大仓位金额 = 总资金 × position_size（每个标的独立计算）
        max_position_value_per_symbol = total_capital * self.position_size
        
        self.write_log(f"资金状态: 总资金={total_capital:.2f}, 可用现金={available_cash:.2f}, 当前持仓={current_holding_value:.2f}")
        self.write_log(f"每个标的最大仓位金额: {max_position_value_per_symbol:.2f} (总资金 × {self.position_size*100:.0f}%)")
        
        # 计算可开新仓的候选标的（未持仓的）
        new_candidates = [sym for sym in candidates if sym not in current_positions]

        for vt_symbol in candidates:
            bar = bars[vt_symbol]
            price = bar.close_price
            if price <= 0:
                continue

            current_pos = current_positions.get(vt_symbol, 0)

            # 已持仓：检查是否需要调整
            if current_pos > 0:
                current_value = current_pos * price
                
                # 如果当前持仓金额超过单标的上限，减少仓位
                if current_value > max_position_value_per_symbol * 1.1:  # 10%容差
                    target_pos = max_position_value_per_symbol / price
                    self.write_log(f"{vt_symbol} 当前持仓 {current_value:.2f} 超过上限，调整至 {max_position_value_per_symbol:.2f}")
                    self.set_target(vt_symbol, target_pos)
                continue

            # 未持仓：只有回踩支撑才开新仓
            if vt_symbol in new_candidates and self.check_entry_condition(vt_symbol, bar):
                # 检查可用现金是否足够
                if available_cash < max_position_value_per_symbol:
                    self.write_log(f"{vt_symbol} 可用现金不足 ({available_cash:.2f} < {max_position_value_per_symbol:.2f})，跳过开仓")
                    continue
                    
                # 计算目标仓位（不超过单标的上限）
                target_pos = max_position_value_per_symbol / price
                self.write_log(f"{vt_symbol} 触发回踩入场，目标仓位 {target_pos:.2f} (约 {max_position_value_per_symbol:.2f} 元)")
                self.set_target(vt_symbol, target_pos)
                # 记录入场价格
                self.entry_prices[vt_symbol] = price
                self.write_log(f"{vt_symbol} 记录入场价格: {price}")
                # 更新可用现金（预扣）
                available_cash -= max_position_value_per_symbol
            else:
                self.write_log(f"{vt_symbol} 满足趋势条件，等待回踩支撑")

        self.execute_trading(bars)

    # ------------------------------------------------------------------
    # 五大硬条件
    # ------------------------------------------------------------------

    def check_five_conditions(self, vt_symbol: str) -> bool:
        """检查五大硬条件，全部满足才返回 True"""
        bars = list(self.bar_cache[vt_symbol])

        if not self.check_trend_structure(bars):
            return False
        if not self.check_vwap_condition(bars):
            return False
        if not self.check_ma_condition(bars):
            return False
        if not self.check_kline_strength(bars):
            return False
        if not self.check_trendline(bars):
            return False

        return True

    # ------------------------------------------------------------------
    # 条件1：价格结构趋势（HH + HL）
    # ------------------------------------------------------------------

    def check_trend_structure(self, bars: List[BarData]) -> bool:
        """
        验证价格形成"更高高点（HH）+ 更高低点（HL）"的上升趋势结构。
        需要至少识别出 2 个递增的摆动高点和 2 个递增的摆动低点。
        """
        if len(bars) < self.swing_window * 4 + 1:
            return False

        highs = [b.high_price for b in bars]
        lows = [b.low_price for b in bars]

        swing_highs = self._find_swing_highs(highs, self.swing_window)
        swing_lows = self._find_swing_lows(lows, self.swing_window)

        # 至少需要 2 个摆动高点和 2 个摆动低点
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return False

        # 取最近的摆动点（已按索引排序）
        last_two_highs = swing_highs[-2:]
        last_two_lows = swing_lows[-2:]

        # HH：最近高点 > 前一高点
        hh = last_two_highs[-1][1] > last_two_highs[-2][1]
        # HL：最近低点 > 前一低点
        hl = last_two_lows[-1][1] > last_two_lows[-2][1]

        return hh and hl

    # ------------------------------------------------------------------
    # 条件2：VWAP 铁律
    # ------------------------------------------------------------------

    def check_vwap_condition(self, bars: List[BarData]) -> bool:
        """
        计算最近 vwap_days 的成交量加权均价（VWAP），
        要求当前收盘价站在 VWAP 上方。
        """
        if len(bars) < self.vwap_days:
            return False

        recent = bars[-self.vwap_days:]
        total_volume = sum(b.volume for b in recent)
        if total_volume == 0:
            return False

        total_turnover = sum(b.turnover for b in recent)
        vwap = total_turnover / total_volume

        return bars[-1].close_price > vwap

    # ------------------------------------------------------------------
    # 条件3：多周期均线多头排列
    # ------------------------------------------------------------------

    def check_ma_condition(self, bars: List[BarData]) -> bool:
        """
        检查 MA10 > MA20 > MA50 的多头排列，
        并要求 MA10 和 MA20 均处于上升斜率。
        """
        closes = [b.close_price for b in bars]

        ma10 = self._calc_ma(closes, self.short_ma)
        ma20 = self._calc_ma(closes, self.medium_ma)
        ma50 = self._calc_ma(closes, self.long_ma)

        if not ma10 or not ma20 or not ma50:
            return False
        if len(ma10) < 3 or len(ma20) < 3:
            return False

        # 多头排列
        bull_aligned = ma10[-1] > ma20[-1] > ma50[-1]
        # MA10 连续上升（最近 3 期）
        ma10_rising = ma10[-1] > ma10[-2] > ma10[-3]
        # MA20 连续上升
        ma20_rising = ma20[-1] > ma20[-2] > ma20[-3]

        return bull_aligned and ma10_rising and ma20_rising

    # ------------------------------------------------------------------
    # 条件4：K线趋势强度（量价配合）
    # ------------------------------------------------------------------

    def check_kline_strength(self, bars: List[BarData]) -> bool:
        """
        最近 20 根 K 线中：
          1. 阳线比例 > 50%
          2. 阳线平均成交量 >= 阴线平均成交量（量价配合，上涨有量）
        """
        recent = bars[-20:]
        if len(recent) < 10:
            return False

        up_bars = [b for b in recent if b.close_price > b.open_price]
        down_bars = [b for b in recent if b.close_price <= b.open_price]

        # 阳线比例
        up_ratio = len(up_bars) / len(recent)
        if up_ratio <= 0.5:
            return False

        # 量价配合
        if up_bars and down_bars:
            avg_up_vol = sum(b.volume for b in up_bars) / len(up_bars)
            avg_dn_vol = sum(b.volume for b in down_bars) / len(down_bars)
            if avg_up_vol < avg_dn_vol:
                return False

        return True

    # ------------------------------------------------------------------
    # 条件5：趋势线有效确认（线性回归）
    # ------------------------------------------------------------------

    def check_trendline(self, bars: List[BarData]) -> bool:
        """
        通过线性回归拟合最近若干摆动低点，构建上升趋势线，要求：
          1. 趋势线斜率 > 0（上升）
          2. 当前收盘价 >= 趋势线在当前位置的预期值（未跌破趋势线）
        """
        if len(bars) < self.swing_window * 4 + 1:
            return False

        lows = [b.low_price for b in bars]
        swing_lows = self._find_swing_lows(lows, self.swing_window)

        if len(swing_lows) < self.trendline_points:
            return False

        # 取最近 trendline_points 个摆动低点
        used_points = swing_lows[-self.trendline_points:]

        slope, tl_value = self._calc_trendline(used_points, len(bars) - 1)

        if slope is None:
            return False

        # 斜率必须为正
        if slope <= 0:
            return False

        current_close = bars[-1].close_price
        return current_close >= tl_value

    # ------------------------------------------------------------------
    # 三周期共振（周线合成 + 日线均线 + 短期强度）
    # ------------------------------------------------------------------

    def check_multi_timeframe_resonance(self, vt_symbol: str) -> bool:
        """
        三周期共振（基于日线数据模拟）：
          - 周线级别：用最近 10 根日线合成约 2 根周线，确认周线上升趋势
          - 日线级别：MA10 > MA20 且均线上升，价格在 MA20 上方
          - 短周期（模拟60min）：最近 5 根日线中 ≥ 3 根阳线 且收盘价呈上升趋势
        三周期全部满足才返回 True。
        """
        bars = list(self.bar_cache[vt_symbol])
        if len(bars) < max(self.long_ma, 20):
            return False

        # --- 周线共振 ---
        if not self._check_weekly_trend(bars):
            return False

        # --- 日线共振 ---
        if not self._check_daily_trend(bars):
            return False

        # --- 短周期共振 ---
        if not self._check_short_term_strength(bars):
            return False

        return True

    def _check_weekly_trend(self, bars: List[BarData]) -> bool:
        """
        用最近 10 根日线合成 2 根"伪周线"，判断周线趋势向上。
        伪周线收盘价 = 该周最后一根日线收盘价。
        伪周线低点 = 该周最低 low。
        """
        if len(bars) < 10:
            return False

        # 第一周：倒数第6-10根；第二周：倒数第1-5根
        week1 = bars[-10:-5]
        week2 = bars[-5:]

        close1 = week1[-1].close_price
        close2 = week2[-1].close_price
        low1 = min(b.low_price for b in week1)
        low2 = min(b.low_price for b in week2)

        # 周线上升：收盘价递增 + 低点递增（HL 结构）
        return close2 > close1 and low2 > low1

    def _check_daily_trend(self, bars: List[BarData]) -> bool:
        """
        日线共振：
          - 价格在 MA20 上方
          - MA10 > MA20（多头排列）
          - MA10 和 MA20 均呈上升斜率（连续 3 期）
        """
        closes = [b.close_price for b in bars]
        ma10 = self._calc_ma(closes, self.short_ma)
        ma20 = self._calc_ma(closes, self.medium_ma)

        if not ma10 or not ma20 or len(ma10) < 3 or len(ma20) < 3:
            return False

        price_above_ma20 = bars[-1].close_price > ma20[-1]
        bull_aligned = ma10[-1] > ma20[-1]
        ma10_rising = ma10[-1] > ma10[-2] > ma10[-3]
        ma20_rising = ma20[-1] > ma20[-2]

        return price_above_ma20 and bull_aligned and ma10_rising and ma20_rising

    def _check_short_term_strength(self, bars: List[BarData]) -> bool:
        """
        短周期强度（模拟60分钟级别）：
          - 最近 5 根日线中 ≥ 3 根阳线
          - 近 5 日整体收盘均价高于前 5 日（整体动能向上，避免单日回调误判）
        """
        if len(bars) < 10:
            return False

        recent5 = bars[-5:]
        prev5 = bars[-10:-5]

        up_count = sum(1 for b in recent5 if b.close_price > b.open_price)
        if up_count < 3:
            return False

        # 近5日均价 vs 前5日均价（整体趋势向上）
        avg_recent = sum(b.close_price for b in recent5) / 5
        avg_prev = sum(b.close_price for b in prev5) / 5

        return avg_recent > avg_prev

    # ------------------------------------------------------------------
    # 入场条件：回踩支撑位确认
    # ------------------------------------------------------------------

    def check_entry_condition(self, vt_symbol: str, bar: BarData) -> bool:
        """
        Lance 入场铁律：不追涨，等待价格回踩支撑位后确认反弹再入场。
        三种有效支撑（满足任意一种即可）：
          1. 趋势线回踩：当日低点触及趋势线（3%容差）且收盘收在趋势线上方
          2. MA20 回踩：当日低点触及 MA20（3%容差）且收盘收在 MA20 上方
          3. VWAP 回踩：当日低点触及 VWAP（1%容差）且收盘收在 VWAP 上方

        同时要求：
          - 阳线收盘（close > open）
          - 成交量 >= 近 5 日均量的 0.8 倍（量能配合）
        """
        bars = list(self.bar_cache[vt_symbol])
        if len(bars) < max(self.medium_ma, self.vwap_days, 5):
            return False

        current_low = bar.low_price
        current_close = bar.close_price
        current_open = bar.open_price

        # 必须阳线收盘
        if current_close <= current_open:
            return False

        # 成交量确认（>= 近5日均量 * 0.8）
        if len(bars) >= 5:
            avg_vol_5 = sum(b.volume for b in bars[-5:]) / 5
            if avg_vol_5 > 0 and bar.volume < avg_vol_5 * 0.8:
                return False

        closes = [b.close_price for b in bars]
        tol = self.pullback_tolerance

        # --- 支撑1：MA20 回踩 ---
        ma20 = self._calc_ma(closes, self.medium_ma)
        if ma20:
            ma20_val = ma20[-1]
            if current_low <= ma20_val * (1 + tol) and current_close > ma20_val:
                self.write_log(f"{vt_symbol} MA20回踩确认 low={current_low:.2f} MA20={ma20_val:.2f}")
                return True

        # --- 支撑2：VWAP 回踩 ---
        recent_bars = bars[-self.vwap_days:]
        total_vol = sum(b.volume for b in recent_bars)
        if total_vol > 0:
            vwap = sum(b.turnover for b in recent_bars) / total_vol
            vwap_tol = min(tol, 0.01)  # VWAP 用更严格的 1% 容差
            if current_low <= vwap * (1 + vwap_tol) and current_close > vwap:
                self.write_log(f"{vt_symbol} VWAP回踩确认 low={current_low:.2f} VWAP={vwap:.2f}")
                return True

        # --- 支撑3：趋势线回踩 ---
        lows_list = [b.low_price for b in bars]
        swing_lows = self._find_swing_lows(lows_list, self.swing_window)
        if len(swing_lows) >= self.trendline_points:
            used = swing_lows[-self.trendline_points:]
            slope, tl_val = self._calc_trendline(used, len(bars) - 1)
            if slope is not None and slope > 0:
                if current_low <= tl_val * (1 + tol) and current_close > tl_val:
                    self.write_log(
                        f"{vt_symbol} 趋势线回踩确认 low={current_low:.2f} TL={tl_val:.2f}"
                    )
                    return True

        return False

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _find_swing_highs(
        self, highs: List[float], window: int
    ) -> List[Tuple[int, float]]:
        """
        识别摆动高点：索引 i 处的价格高于左右各 window 根 K 线的最高价。
        返回 [(index, price), ...] 按 index 升序。
        """
        result = []
        n = len(highs)
        for i in range(window, n - window):
            left = highs[i - window: i]
            right = highs[i + 1: i + window + 1]
            if highs[i] >= max(left) and highs[i] >= max(right):
                result.append((i, highs[i]))
        return result

    def _find_swing_lows(
        self, lows: List[float], window: int
    ) -> List[Tuple[int, float]]:
        """
        识别摆动低点：索引 i 处的价格低于左右各 window 根 K 线的最低价。
        返回 [(index, price), ...] 按 index 升序。
        """
        result = []
        n = len(lows)
        for i in range(window, n - window):
            left = lows[i - window: i]
            right = lows[i + 1: i + window + 1]
            if lows[i] <= min(left) and lows[i] <= min(right):
                result.append((i, lows[i]))
        return result

    def _calc_trendline(
        self,
        swing_points: List[Tuple[int, float]],
        target_idx: int
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        对一组摆动点做线性回归，返回 (斜率, 趋势线在 target_idx 处的值)。
        如果点数不足或计算失败，返回 (None, None)。
        """
        if len(swing_points) < 2:
            return None, None

        xs = np.array([p[0] for p in swing_points], dtype=float)
        ys = np.array([p[1] for p in swing_points], dtype=float)

        # 用最小二乘法
        x_mean = xs.mean()
        y_mean = ys.mean()
        denom = ((xs - x_mean) ** 2).sum()
        if denom == 0:
            return None, None

        slope = ((xs - x_mean) * (ys - y_mean)).sum() / denom
        intercept = y_mean - slope * x_mean
        tl_value = slope * target_idx + intercept

        return slope, tl_value

    def _calc_ma(self, data: List[float], period: int) -> List[float]:
        """计算简单移动平均线，返回值列表（长度 = len(data) - period + 1）"""
        if len(data) < period:
            return []
        result = []
        for i in range(period, len(data) + 1):
            result.append(sum(data[i - period: i]) / period)
        return result

    # 兼容旧接口（原脚本中有调用）
    def calculate_ma(self, data: List[float], period: int) -> List[float]:
        return self._calc_ma(data, period)
