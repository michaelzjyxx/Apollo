
import sys
import os
from datetime import datetime
import pandas as pd
from loguru import logger
import json

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.ifind_api import IFindAPIClient

# 配置 logger
logger.remove()
logger.add(sys.stderr, level="INFO")

def verify_indicators():
    """验证 iFinD 指标"""
    
    # 测试配置
    stock_code = "920000.BJ"
    start_date = datetime(2026, 1, 21)
    end_date = datetime(2026, 1, 21)
    
    indicators_to_test = {
        "基础信息": [
            "ths_stock_short_name_stock",
            "ths_ipo_date_stock",
            "ths_stock_status",
        ],
        "财务指标": [
            "ths_net_profit_stock",
            "ths_net_profit_ttm_stock",
            "ths_total_assets_stock",
            "ths_total_liabilities_stock",
            "ths_current_assets_stock",
            "ths_current_liabilities_stock",
            "ths_inventory_stock",
            "ths_net_assets_stock",
            "ths_goodwill_stock",
            "ths_operating_revenue_stock",
            "ths_operating_cost_stock",
            "ths_cash_flow_oper_act_stock",
            "ths_gross_profit_margin_stock",
            "ths_net_profit_growth_rate_stock",
            "ths_roe_stock",
        ],
        "行情估值": [
            "ths_close_price_stock",
            "ths_market_value_stock",
            "ths_pe_ttm_stock",
            "ths_pb_stock",
            "ths_pledge_ratio_stock",
            "ths_institutional_ownership_stock",
        ],
    }

    end_date_str = end_date.strftime("%Y-%m-%d")

    indicators_with_params = [
        {
            "category": "基础信息",
            "indicator": "ths_the_sw_industry_stock",
            "indiparams": ["1", end_date_str],
        },
        {
            "category": "基础信息",
            "indicator": "ths_the_sw_industry_stock",
            "indiparams": ["2", end_date_str],
        },
    ]

    results = []

    with IFindAPIClient() as client:
        logger.info(f"开始验证指标，测试标的: {stock_code}, 时间范围: {start_date.date()} - {end_date.date()}")
        
        for category, indicators in indicators_to_test.items():
            logger.info(f"\n=== 正在测试类别: {category} ===")
            
            for indicator in indicators:
                status = "❌ 失败"
                details = "未知错误"
                sample_val = "N/A"
                source = "date_sequence"
                
                # 1. 尝试 date_sequence (时间序列)
                try:
                    df = client.get_stock_data(
                        stock_codes=stock_code,
                        indicator=indicator,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if not df.empty and "value" in df.columns:
                        valid_data = df["value"].dropna()
                        if not valid_data.empty:
                            status = "✅ 成功"
                            sample_val = valid_data.iloc[-1]
                            details = f"序列数据: {len(valid_data)} 条"
                        else:
                            details = "返回了行但数值全为空"
                    else:
                        details = "返回为空 DataFrame"
                        
                except Exception as e:
                    details = f"date_sequence 异常: {str(e)}"

                # 2. 如果失败，尝试 basic_data_service (基础数据/截面)
                if status != "✅ 成功":
                    try:
                        # 构造 basic_data_service 请求
                        payload = {
                            "codes": stock_code,
                            "indipara": [
                                {
                                    "indicator": indicator,
                                    "indiparams": []
                                }
                            ]
                        }
                        
                        # 这里的 endpoint 可能需要确认，暂时尝试 "basic_data_service"
                        # 注意：如果 basic_data_service 需要特定的日期参数，这里可能缺省
                        data = client._http_request("basic_data_service", payload)
                        
                        val, errorcode, errmsg, has_table, has_field = client._extract_basic_data_value(
                            data,
                            indicator,
                        )
                        if val is not None:
                            status = "✅ 成功"
                            source = "basic_data"
                            sample_val = val
                            details = "通过 basic_data_service 获取成功"
                        elif errorcode not in (None, 0):
                            details += f" | API Error: {errmsg} ({errorcode})"
                        elif not has_table:
                            details += " | basic_data table 为空"
                        elif not has_field:
                            details += f" | basic_data 响应中无字段 {indicator}"
                        else:
                            details += " | basic_data 返回 None"
                            
                    except Exception as e:
                        details += f" | basic_data 异常: {str(e)}"

                logger.info(f"[{status}] {indicator} ({source}): {details}")
                if status == "✅ 成功":
                     logger.info(f"    -> 示例值: {sample_val}")
                
                results.append({
                    "category": category,
                    "indicator": indicator,
                    "status": status,
                    "source": source,
                    "details": details,
                    "sample": str(sample_val)
                })

        for item in indicators_with_params:
            indicator = item["indicator"]
            status = "❌ 失败"
            details = "未知错误"
            sample_val = "N/A"
            source = "basic_data"
            try:
                payload = {
                    "codes": stock_code,
                    "indipara": [
                        {
                            "indicator": indicator,
                            "indiparams": item["indiparams"],
                        }
                    ],
                }
                logger.info(f"IFIND_REQUEST payload={json.dumps(payload, ensure_ascii=False)}")
                data = client._http_request("basic_data_service", payload)
                if isinstance(data, dict):
                    logger.info(f"IFIND_RESPONSE data={json.dumps(data, ensure_ascii=False)}")
                else:
                    logger.info(f"IFIND_RESPONSE type={type(data).__name__} data={data}")
                val, errorcode, errmsg, has_table, has_field = client._extract_basic_data_value(
                    data,
                    indicator,
                )
                if val is not None:
                    status = "✅ 成功"
                    sample_val = val
                    details = f"参数: {item['indiparams']}"
                elif errorcode not in (None, 0):
                    details = f"API Error: {errmsg} ({errorcode}), 参数: {item['indiparams']}"
                elif not has_table:
                    details = f"basic_data table 为空, 参数: {item['indiparams']}"
                elif not has_field:
                    details = f"响应中无字段, 参数: {item['indiparams']}"
                else:
                    details = f"值为空, 参数: {item['indiparams']}"
            except Exception as e:
                details = f"异常: {str(e)}, 参数: {item['indiparams']}"

            logger.info(f"[{status}] {indicator} ({source}): {details}")
            if status == "✅ 成功":
                logger.info(f"    -> 示例值: {sample_val}")

            results.append({
                "category": item["category"],
                "indicator": indicator,
                "status": status,
                "source": source,
                "details": details,
                "sample": str(sample_val),
            })

    # 打印汇总报告
    print("\n" + "="*100)
    print(f"{'指标验证报告':^100}")
    print("="*100)
    print(f"{'类别':<10} | {'指标代码':<35} | {'状态':<8} | {'来源':<12} | {'示例值':<20}")
    print("-" * 100)
    
    for res in results:
        print(f"{res['category']:<10} | {res['indicator']:<35} | {res['status']:<8} | {res['source']:<12} | {res['sample'][:20]}")
    print("="*100)

if __name__ == "__main__":
    verify_indicators()
