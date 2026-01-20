# 申万二级行业数据获取指南

## 问题说明

当前系统配置中只有申万一级行业(31个),但根据质量筛选策略,我们需要使用申万二级行业(104个)进行筛选。

## 解决方案

### 方案1: 从iFinD API动态获取 (推荐)

**优势**:
- 数据实时更新
- 自动获取成分股
- 不需要人工维护

**实现步骤**:

```python
from iFinDPy import THS_DataQuery

# 1. 获取所有申万二级行业列表
def get_shenwan_l2_industries():
    """
    获取申万二级行业列表

    Returns:
        DataFrame: 包含code, name, parent_code列
    """
    # iFinD API调用示例(需要确认实际字段名)
    result = THS_DataQuery(
        thscode='',  # 空表示获取所有
        jsonIndicator='ths_shenwan_l2_industry_code;ths_shenwan_l2_industry_name;ths_shenwan_l1_industry_code',
        jsonparam='',
        begintime='',
        endtime=''
    )

    # 解析结果
    industries = []
    for row in result:
        industries.append({
            'code': row['ths_shenwan_l2_industry_code'],
            'name': row['ths_shenwan_l2_industry_name'],
            'parent_code': row['ths_shenwan_l1_industry_code']
        })

    return pd.DataFrame(industries)

# 2. 获取某个二级行业的成分股
def get_industry_constituents(industry_code: str, date: str):
    """
    获取行业成分股

    Args:
        industry_code: 行业代码(如801121.SI)
        date: 日期(如2024-01-01)

    Returns:
        List[str]: 股票代码列表
    """
    result = THS_DataQuery(
        thscode=industry_code,
        jsonIndicator='ths_member_stock',
        jsonparam='',
        begintime=date,
        endtime=date
    )

    return result['ths_member_stock'].tolist()

# 3. 获取股票所属的二级行业
def get_stock_industry(stock_code: str):
    """
    获取股票所属的申万二级行业

    Args:
        stock_code: 股票代码(如600519.SH)

    Returns:
        dict: {code: '801121.SI', name: '白酒', parent_code: '801120.SI'}
    """
    result = THS_DP(
        thscode=stock_code,
        jsonIndicator='ths_shenwan_l2_industry_code;ths_shenwan_l2_industry_name',
        jsonparam='',
        begintime='',
        endtime=''
    )

    return {
        'code': result['ths_shenwan_l2_industry_code'],
        'name': result['ths_shenwan_l2_industry_name'],
        'parent_code': result['ths_shenwan_l1_industry_code']
    }
```

**使用示例**:

```python
# 初始化时获取所有二级行业
industries_l2 = get_shenwan_l2_industries()
print(f"共有{len(industries_l2)}个二级行业")

# 获取白酒行业的成分股
baijiu_stocks = get_industry_constituents('801121.SI', '2024-01-01')
print(f"白酒行业有{len(baijiu_stocks)}只股票")

# 获取贵州茅台所属行业
maotai_industry = get_stock_industry('600519.SH')
print(f"贵州茅台属于: {maotai_industry['name']}")
```

---

### 方案2: 使用静态配置文件 (备用)

如果iFinD API无法获取二级行业数据,可以使用静态配置文件。

**配置文件**: `config/shenwan_industries.yaml`

**优势**:
- 不依赖API
- 可以离线使用

**劣势**:
- 需要人工维护
- 可能不是最新数据

**使用方法**:

```python
import yaml

# 加载配置文件
with open('config/shenwan_industries.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 获取所有二级行业
industries_l2 = config['shenwan_l2']
print(f"共有{len(industries_l2)}个二级行业")

# 按一级行业分组
from collections import defaultdict
l2_by_l1 = defaultdict(list)
for industry in industries_l2:
    l2_by_l1[industry['parent']].append(industry)

# 查看食品饮料下的二级行业
for industry in l2_by_l1['801120.SI']:
    print(f"{industry['code']}: {industry['name']}")
```

---

### 方案3: 混合方案 (最佳实践)

结合方案1和方案2的优势:

```python
class IndustryManager:
    """行业管理器"""

    def __init__(self, ifind_client, config_path='config/shenwan_industries.yaml'):
        self.ifind_client = ifind_client
        self.config_path = config_path
        self._cache = {}

    def get_l2_industries(self, use_cache=True):
        """
        获取二级行业列表

        优先从iFinD获取,失败则使用配置文件
        """
        if use_cache and 'l2_industries' in self._cache:
            return self._cache['l2_industries']

        try:
            # 尝试从iFinD获取
            industries = self._fetch_from_ifind()
            logger.info(f"从iFinD获取到{len(industries)}个二级行业")
        except Exception as e:
            logger.warning(f"从iFinD获取失败: {e}, 使用配置文件")
            # 失败则使用配置文件
            industries = self._load_from_config()

        self._cache['l2_industries'] = industries
        return industries

    def _fetch_from_ifind(self):
        """从iFinD获取"""
        # 实现方案1的逻辑
        pass

    def _load_from_config(self):
        """从配置文件加载"""
        # 实现方案2的逻辑
        pass
```

---

## 数据验证

无论使用哪种方案,都需要验证数据的完整性:

```python
def validate_industries(industries_l2):
    """
    验证二级行业数据

    检查项:
    1. 数量是否正确(约104个)
    2. 是否有重复
    3. 是否都有parent_code
    4. parent_code是否都是有效的一级行业
    """
    # 1. 检查数量
    assert 90 <= len(industries_l2) <= 120, f"二级行业数量异常: {len(industries_l2)}"

    # 2. 检查重复
    codes = [ind['code'] for ind in industries_l2]
    assert len(codes) == len(set(codes)), "存在重复的行业代码"

    # 3. 检查parent_code
    for ind in industries_l2:
        assert 'parent' in ind or 'parent_code' in ind, f"行业{ind['code']}缺少parent_code"

    # 4. 检查parent_code有效性
    valid_l1_codes = set(SHENWAN_L1_INDUSTRIES.keys())
    for ind in industries_l2:
        parent = ind.get('parent') or ind.get('parent_code')
        assert parent in valid_l1_codes, f"行业{ind['code']}的parent_code无效: {parent}"

    logger.info("二级行业数据验证通过")
```

---

## 关键字段确认清单

在实施前,需要确认以下iFinD字段名:

| 数据项 | 可能的字段名 | 需要确认 |
|-------|------------|---------|
| 二级行业代码 | `ths_shenwan_l2_industry_code` | ✅ |
| 二级行业名称 | `ths_shenwan_l2_industry_name` | ✅ |
| 一级行业代码 | `ths_shenwan_l1_industry_code` | ✅ |
| 行业成分股 | `ths_member_stock` | ✅ |
| 股票所属行业 | `ths_shenwan_l2_industry_code` | ✅ |

**确认方法**:
1. 查阅iFinD官方文档
2. 咨询iFinD技术支持
3. 在iFinD客户端中测试查询

---

## 实施步骤

### 第一步: 确认iFinD字段名 (1天)

```python
# 测试脚本
from iFinDPy import THS_iFinDLogin, THS_DataQuery

# 登录
THS_iFinDLogin(username, password)

# 测试获取二级行业列表
result = THS_DataQuery(
    thscode='',
    jsonIndicator='ths_shenwan_l2_industry_code',  # 尝试不同的字段名
    jsonparam='',
    begintime='',
    endtime=''
)
print(result)
```

### 第二步: 实现IndustryManager (2-3天)

```python
# src/data/industry_manager.py
class IndustryManager:
    """行业管理器"""

    def get_l2_industries(self):
        """获取二级行业列表"""
        pass

    def get_industry_constituents(self, industry_code, date):
        """获取行业成分股"""
        pass

    def get_stock_industry(self, stock_code):
        """获取股票所属行业"""
        pass

    def calculate_industry_metrics(self, industry_code, date):
        """计算行业指标(总营收、中位数毛利率等)"""
        pass
```

### 第三步: 集成到筛选流程 (1-2天)

```python
# 在质量筛选中使用
industry_manager = IndustryManager(ifind_client)

# 获取所有二级行业
industries_l2 = industry_manager.get_l2_industries()

# 对每个行业进行筛选
for industry in industries_l2:
    # 获取成分股
    stocks = industry_manager.get_industry_constituents(
        industry['code'],
        date='2024-01-01'
    )

    # 计算行业指标
    industry_metrics = industry_manager.calculate_industry_metrics(
        industry['code'],
        date='2024-01-01'
    )

    # 对每只股票进行质量筛选
    for stock in stocks:
        # 计算市占率
        market_share = stock_revenue / industry_metrics['total_revenue']

        # 计算毛利率优势
        margin_advantage = stock_margin - industry_metrics['median_margin']

        # ... 其他筛选逻辑
```

---

## 常见问题

### Q1: iFinD是否支持二级行业查询?

**A**: 需要确认。大部分金融数据终端都支持申万二级行业,但字段名可能不同。

**确认方法**:
1. 查阅iFinD官方文档
2. 在iFinD客户端中搜索"申万二级行业"
3. 咨询iFinD技术支持

---

### Q2: 如果iFinD不支持二级行业怎么办?

**A**: 有以下替代方案:

**方案A: 使用Wind/Choice**
- Wind和Choice都支持申万二级行业
- 可以作为补充数据源

**方案B: 自己维护映射关系**
- 从Wind/Choice获取一次完整的二级行业数据
- 保存到配置文件中
- 定期(如每季度)更新一次

**方案C: 使用一级行业 + 细分**
- 如果二级行业数据实在无法获取
- 可以在一级行业基础上,根据业务特征手动细分
- 例如: 食品饮料 → 白酒、乳制品、调味品等

---

### Q3: 二级行业分类会变化吗?

**A**: 会的。申万行业分类会定期调整。

**应对措施**:
1. 定期(如每季度)更新行业分类数据
2. 在数据库中记录行业分类的版本和生效日期
3. 历史回测时使用当时的行业分类

---

### Q4: 如何处理行业成分股变更?

**A**: 行业成分股会因为公司业务变化而调整。

**处理方法**:
1. 每次筛选时实时获取最新成分股
2. 或: 每月更新一次成分股列表
3. 在计算市占率时,使用同一时点的成分股

---

## 总结

**推荐方案**: 混合方案(方案3)
- 优先从iFinD API动态获取
- 失败则使用静态配置文件
- 定期验证数据完整性

**关键步骤**:
1. ✅ 确认iFinD字段名(1天)
2. ✅ 实现IndustryManager(2-3天)
3. ✅ 集成到筛选流程(1-2天)
4. ✅ 测试和验证(1天)

**总工时**: 约5-7天

---

## 相关文档

- [申万行业分类配置](../config/shenwan_industries.yaml)
- [iFinD字段映射表](./ifind_field_mapping.md)
- [数据源评估报告](./data_source_evaluation.md)
