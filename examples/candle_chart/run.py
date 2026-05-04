from datetime import datetime, timedelta

from vnpy.trader.ui import create_qapp, QtCore
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.chart import ChartWidget, VolumeItem, CandleItem


if __name__ == "__main__":
    app = create_qapp()

    # Generate sample bar data
    bars = []
    start_datetime = datetime(2019, 7, 1)
    base_price = 4000.0
    
    for i in range(1000):
        # Create datetime with 1-minute intervals
        dt = start_datetime + timedelta(minutes=i)
        
        # Generate sample OHLC data with some random variation
        open_price = base_price + (i * 0.5) + (i % 10)
        high_price = open_price + 2.0 + (i % 5)
        low_price = open_price - 1.0 - (i % 3)
        close_price = low_price + (high_price - low_price) * 0.7 + (i % 4)
        
        bar = BarData(
            symbol="IF888",
            exchange=Exchange.CFFEX,
            datetime=dt,
            interval=Interval.MINUTE,
            volume=i * 100,
            turnover=close_price * i * 100,
            open_interest=100000 + i * 100,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            gateway_name="DB"
        )
        bars.append(bar)

    widget = ChartWidget()
    widget.add_plot("candle", hide_x_axis=True)
    widget.add_plot("volume", maximum_height=200)
    widget.add_item(CandleItem, "candle", "candle")
    widget.add_item(VolumeItem, "volume", "volume")
    widget.add_cursor()

    n = 1000
    history = bars[:n]
    new_data = bars[n:]

    widget.update_history(history)

    def update_bar() -> None:
        bar = new_data.pop(0)
        widget.update_bar(bar)

    timer = QtCore.QTimer()
    timer.timeout.connect(update_bar)
    # timer.start(100)

    widget.show()
    app.exec()
