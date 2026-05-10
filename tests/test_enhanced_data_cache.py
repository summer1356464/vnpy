#!/usr/bin/env python3
"""
EnhancedDataCache 测试用例
"""
import pytest
import tempfile
from datetime import datetime
from pathlib import Path
import polars as pl

from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.enhanced_data_cache import EnhancedDataCache, QueryResult
from vnpy.trader.utility import extract_vt_symbol
from vnpy.trader.stock_metadata import DataStatus


class TestEnhancedDataCache:
    """EnhancedDataCache 测试类"""
    
    @pytest.fixture
    def data_cache(self):
        """创建临时的 EnhancedDataCache 实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            lab_path = Path(temp_dir)
            yield EnhancedDataCache(str(lab_path))
    
    @pytest.fixture
    def sample_parquet_data(self, data_cache):
        """创建测试用的 Parquet 缓存数据"""
        daily_path = Path(data_cache.lab_path) / "daily"
        daily_path.mkdir(parents=True, exist_ok=True)
        
        # 创建测试数据
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
        
        return str(parquet_file)
    
    def test_init(self, data_cache):
        """测试初始化"""
        assert data_cache is not None
        assert data_cache.lab is not None
        assert data_cache.metadata_manager is not None
        assert data_cache.datafeed is not None
        assert data_cache.lab_path is not None
    
    def test_get_cache_summary(self, data_cache):
        """测试获取缓存摘要"""
        summary = data_cache.get_cache_summary()
        assert "lab_path" in summary
        assert "scanned_daily" in summary
        assert "scanned_minute" in summary
        assert "stocks_by_status" in summary
        assert "total_stocks" in summary
    
    def test_scan_lab_cache(self, data_cache, sample_parquet_data):
        """测试扫描 AlphaLab 缓存"""
        result = data_cache.scan_lab_cache()
        assert result["scanned_daily"] >= 1
        assert result["updated"] >= 1
    
    def test_query_bar_history_cache_hit(self, data_cache, sample_parquet_data):
        """测试查询命中缓存"""
        data_cache.scan_lab_cache()  # 先扫描缓存
        
        result = data_cache.query_bar_history(
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime(2020, 1, 1),
            end=datetime(2024, 1, 1)
        )
        
        assert result is not None
        assert result.skipped is False
        assert result.hit_cache is True
        assert len(result.bars) >= 1
    
    def test_query_bar_history_before_listed(self, data_cache):
        """测试查询上市前的数据（应被跳过）"""
        # 先设置上市日期
        data_cache.update_listed_date("000002", Exchange.SZSE, datetime(2023, 1, 1))
        
        # 验证元信息已保存
        metadata = data_cache.get_metadata("000002", Exchange.SZSE)
        assert metadata is not None
        assert metadata.listed_date == datetime(2023, 1, 1)
        
        result = data_cache.query_bar_history(
            symbol="000002",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            start=datetime(2020, 1, 1),
            end=datetime(2022, 1, 1)  # 在上市日期之前
        )
        
        assert result is not None
        assert result.skipped is True
        assert "上市日期之前" in result.skipped_reason
    
    def test_batch_query(self, data_cache, sample_parquet_data):
        """测试批量查询"""
        data_cache.scan_lab_cache()
        
        vt_symbols = ["000001.SZSE", "000002.SZSE"]
        results = data_cache.batch_query(
            vt_symbols=vt_symbols,
            interval=Interval.DAILY,
            start=datetime(2020, 1, 1),
            end=datetime(2024, 1, 1)
        )
        
        assert len(results) == 2
        assert "000001.SZSE" in results
        assert "000002.SZSE" in results
        assert results["000001.SZSE"].hit_cache is True
    
    def test_validate_cache_consistency(self, data_cache, sample_parquet_data):
        """测试验证缓存一致性"""
        data_cache.scan_lab_cache()
        
        result = data_cache.validate_cache_consistency("000001.SZSE")
        assert "consistent" in result
        assert "parquet_overview" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
