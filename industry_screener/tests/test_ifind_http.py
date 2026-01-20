
import sys
import os
from datetime import datetime
from loguru import logger
import pandas as pd

# 添加项目根目录到 python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.ifind_api import IFindAPIClient

def test_ifind_connection():
    """测试 iFinD HTTP 接口连接"""
    logger.info("开始测试 iFinD HTTP 接口连接...")
    
    # 1. 初始化客户端 (会自动读取 config.yaml)
    client = IFindAPIClient()
    
    # 2. 检查配置
    if client.api_mode != "http":
        logger.error(f"错误: 当前模式为 {client.api_mode}, 请在 config.yaml 中设置为 http")
        return
    
    logger.info(f"API 模式: {client.api_mode}")
    logger.info(f"Refresh Token: {client.refresh_token[:20]}..." if client.refresh_token else "未配置")
    
    # 3. 连接 (会自动获取/刷新 Access Token)
    logger.info("尝试连接并获取 Access Token...")
    if not client.connect():
        logger.error("连接失败")
        return
    
    # 4. 测试获取个股数据 (茅台: 600519.SH)
    logger.info("测试获取个股数据: 600519.SH (贵州茅台)...")
    try:
        df = client.get_stock_data(
            stock_codes="600519.SH",
            indicator="ths_close_price_stock", # 收盘价
            start_date=datetime(2023, 12, 1),
            end_date=datetime(2023, 12, 5)
        )
        
        if not df.empty:
            logger.success("获取个股数据成功!")
            print("\n数据预览:")
            print(df)
        else:
            logger.warning("获取数据为空，请检查指标名称或权限")
            
    except Exception as e:
        logger.error(f"获取个股数据失败: {e}")

    # 5. 断开连接
    client.disconnect()
    logger.info("测试完成")

if __name__ == "__main__":
    test_ifind_connection()
