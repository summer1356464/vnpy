#!/usr/bin/env python3
"""
测试增强版缓存数据服务

功能测试：
1. 股票元信息管理
2. 上市/退市时间检查
3. 缓存一致性验证
4. AlphaLab 缓存扫描
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import os
import tempfile
import shutil

# 设置测试配置
os.environ["VNPY_CONFIG"] = "test"

from vnpy.trader.stock_metadata import (
    StockMetadataManager, 
    StockMetadata, 
    DataStatus
)
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest, BarData
import polars as pl


class TestStockMetadataManager:
    """测试股票元信息管理器"""
    
    @pytest.fixture
    def metadata_manager(self):
        """创建元信息管理器实例"""
        yield StockMetadataManager()
    
    def test_init_tables(self, metadata_manager):
        """测试初始化表"""
        assert metadata_manager.database is not None
    
    def test_save_and_get_metadata(self, metadata_manager):
        """测试保存和获取元信息"""
        metadata = StockMetadata(
            symbol="000001",
            exchange=Exchange.SZSE,
            listed_date=datetime(2010, 1, 1),
            delisted_date=None,
            first_trade_date=datetime(2010, 1, 1),
            last_trade_date=datetime(2024, 1, 1),
            parquet_daily_start=datetime(2020, 1, 1),
            parquet_daily_end=datetime(2024, 1, 1),
            parquet_daily_count=1000,
            data_status=DataStatus.COMPLETE,
            fetch_attempts=1
        )
        
        result = metadata_manager.save_metadata(metadata)
        assert result is True
        
        retrieved = metadata_manager.get_metadata("000001", Exchange.SZSE)
        assert retrieved is not None
        assert retrieved.symbol == "000001"
        assert retrieved.exchange == Exchange.SZSE
        assert retrieved.listed_date == datetime(2010, 1, 1)
        assert retrieved.data_status == DataStatus.COMPLETE
        assert retrieved.parquet_daily_count == 1000
    
    def test_check_date_range_before_listed(self, metadata_manager):
        """测试检查上市前日期"""
        metadata = StockMetadata(
            symbol="000001",
            exchange=Exchange.SZSE,
            listed_date=datetime(2020, 1, 1),
            data_status=DataStatus.PARTIAL
        )
        metadata_manager.save_metadata(metadata)
        
        result = metadata_manager.check_date_range(
            "000001",
            Exchange.SZSE,
            datetime(2019, 1, 1),
            datetime(2021, 1, 1)
        )
        
        assert result["valid"] is True
        assert result["before_listed"] is True
        assert result["actual_start"] == datetime(2020, 1, 1)
        assert "早于上市日期" in result["message"]
    
    def test_check_date_range_after_delisted(self, metadata_manager):
        """测试检查退市后日期"""
        metadata = StockMetadata(
            symbol="000002",
            exchange=Exchange.SZSE,
            listed_date=datetime(2010, 1, 1),
            delisted_date=datetime(2023, 1, 1),
            data_status=DataStatus.PARTIAL
        )
        metadata_manager.save_metadata(metadata)
        
        result = metadata_manager.check_date_range(
            "000002",
            Exchange.SZSE,
            datetime(2022, 1, 1),
            datetime(2024, 1, 1)
        )
        
        assert result["valid"] is True
        assert result["after_delisted"] is True
        assert result["actual_end"] == datetime(2023, 1, 1)
        assert "晚于退市日期" in result["message"]
    
    def test_check_date_range_completely_invalid(self, metadata_manager):
        """测试完全无效的日期范围"""
        metadata = StockMetadata(
            symbol="000003",
            exchange=Exchange.SZSE,
            listed_date=datetime(2020, 1, 1),
            delisted_date=datetime(2023, 1, 1),
            data_status=DataStatus.COMPLETE
        )
        metadata_manager.save_metadata(metadata)
        
        # 检查完全在上市前的范围
        result1 = metadata_manager.check_date_range(
            "000003",
            Exchange.SZSE,
            datetime(2018, 1, 1),
            datetime(2019, 1, 1)
        )
        assert result1["valid"] is False
        
        # 检查完全在退市后的范围
        result2 = metadata_manager.check_date_range(
            "000003",
            Exchange.SZSE,
            datetime(2024, 1, 1),
            datetime(2025, 1, 1)
        )
        assert result2["valid"] is False
    
    def test_update_metadata_from_fetch(self, metadata_manager):
        """测试从获取结果更新元信息"""
        # 创建模拟的BarData（添加gateway_name参数）
        bars = [
            BarData(
                symbol="000001",
                exchange=Exchange.SZSE,
                datetime=datetime(2020, 1, 1),
                interval=Interval.DAILY,
                open_price=10.0,
                high_price=11.0,
                low_price=9.0,
                close_price=10.5,
                volume=1000,
                turnover=10500,
                open_interest=0,
                gateway_name="TEST"
            ),
            BarData(
                symbol="000001",
                exchange=Exchange.SZSE,
                datetime=datetime(2020, 1, 2),
                interval=Interval.DAILY,
                open_price=10.5,
                high_price=12.0,
                low_price=10.0,
                close_price=11.5,
                volume=1500,
                turnover=17250,
                open_interest=0,
                gateway_name="TEST"
            )
        ]
        
        req = HistoryRequest(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime(2020, 1, 1),
            end=datetime(2020, 1, 2)
        )
        
        # 更新元信息
        metadata_manager.update_metadata_from_fetch(
            symbol="000001",
            exchange=Exchange.SZSE,
            req=req,
            fetched_bars=bars,
            fetch_success=True
        )
        
        # 验证更新
        metadata = metadata_manager.get_metadata("000001", Exchange.SZSE)
        assert metadata is not None
        assert metadata.first_trade_date == datetime(2020, 1, 1)
        assert metadata.last_trade_date == datetime(2020, 1, 2)
        assert metadata.data_status == DataStatus.PARTIAL
        assert metadata.fetch_attempts == 1
    
    def test_mark_fetch_failed(self, metadata_manager):
        """测试标记获取失败"""
        # 使用一个新的股票代码，避免与前面测试的数据冲突
        metadata_manager.mark_fetch_failed(
            symbol="999999",
            exchange=Exchange.SZSE,
            reason="网络超时"
        )
        
        metadata = metadata_manager.get_metadata("999999", Exchange.SZSE)
        assert metadata is not None
        assert metadata.data_status == DataStatus.FETCH_FAILED
        assert metadata.fetch_attempts == 1
    
    def test_validate_cache_consistency(self, metadata_manager):
        """测试验证缓存一致性"""
        # 先保存元信息
        metadata = StockMetadata(
            symbol="000001",
            exchange=Exchange.SZSE,
            parquet_daily_start=datetime(2020, 1, 1),
            parquet_daily_end=datetime(2024, 1, 1),
            parquet_daily_count=1000,
            db_start=datetime(2020, 1, 1),
            db_end=datetime(2024, 1, 1),
            data_status=DataStatus.COMPLETE
        )
        metadata_manager.save_metadata(metadata)
        
        # 验证一致性
        result = metadata_manager.validate_cache_consistency(
            "000001",
            Exchange.SZSE,
            Interval.DAILY
        )
        
        assert "consistent" in result
        assert "parquet_overview" in result
    
    def test_scan_alpha_lab_cache(self, metadata_manager):
        """测试扫描 AlphaLab 缓存目录"""
        # 创建临时目录模拟 AlphaLab 缓存结构
        with tempfile.TemporaryDirectory() as temp_dir:
            lab_path = Path(temp_dir)
            daily_path = lab_path / "daily"
            daily_path.mkdir()
            
            # 创建测试 parquet 文件
            data = {
                "datetime": [datetime(2020, 1, 1), datetime(2024, 1, 1)],
                "open": [10.0, 20.0],
                "high": [11.0, 21.0],
                "low": [9.0, 19.0],
                "close": [10.5, 20.5],
                "volume": [1000.0, 2000.0],
                "turnover": [10500.0, 41000.0],
                "open_interest": [0.0, 0.0]
            }
            df = pl.DataFrame(data)
            df = df.with_columns(pl.col("datetime").cast(pl.Datetime(time_unit="ns")))
            parquet_file = daily_path / "000001.SZSE.parquet"
            df.write_parquet(parquet_file)
            
            # 验证文件创建成功
            assert parquet_file.exists(), f"Parquet file not created: {parquet_file}"
            
            # 扫描缓存
            result = metadata_manager.scan_alpha_lab_cache(str(lab_path))
            
            # 打印扫描结果用于调试
            print(f"Scan result: {result}")
            print(f"Daily path: {daily_path}")
            print(f"Files in daily: {list(daily_path.glob('*.parquet'))}")
            
            # 验证扫描结果
            assert result["scanned_daily"] == 1, f"Expected 1 scanned daily, got {result['scanned_daily']}"
            assert result["updated"] >= 1, f"Expected at least 1 update, got {result['updated']}"
            assert result["new_stocks"] >= 1, f"Expected at least 1 new stock, got {result['new_stocks']}"
            
            # 验证元信息已更新
            metadata = metadata_manager.get_metadata("000001", Exchange.SZSE)
            assert metadata is not None, "Metadata should not be None"
            assert metadata.parquet_daily_start == datetime(2020, 1, 1), f"Start mismatch: {metadata.parquet_daily_start}"
            assert metadata.parquet_daily_end == datetime(2024, 1, 1), f"End mismatch: {metadata.parquet_daily_end}"
            assert metadata.parquet_daily_count == 2, f"Count mismatch: {metadata.parquet_daily_count}"
            assert metadata.lab_path == str(lab_path), f"Lab path mismatch: {metadata.lab_path}"
    
    def test_get_stocks_with_status(self, metadata_manager):
        """测试获取指定状态的股票"""
        # 添加测试数据
        for i in range(5):
            status = DataStatus.PARTIAL if i % 2 == 0 else DataStatus.COMPLETE
            metadata = StockMetadata(
                symbol=f"0000{i+1}",
                exchange=Exchange.SZSE,
                data_status=status,
                fetch_attempts=1
            )
            metadata_manager.save_metadata(metadata)
        
        # 获取PARTIAL状态的股票
        partial_stocks = metadata_manager.get_stocks_with_status(DataStatus.PARTIAL)
        assert len(partial_stocks) >= 2
        
        # 获取COMPLETE状态的股票
        complete_stocks = metadata_manager.get_stocks_with_status(DataStatus.COMPLETE)
        assert len(complete_stocks) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])