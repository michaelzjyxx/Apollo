
## Mac/Linux 用户解决方案

由于 `iFinDPy` 强依赖 Windows 客户端，非 Windows 用户有以下两种解决方案：

### 方案一：使用 HTTP 接口 (推荐)

同花顺提供了标准的 HTTP RESTful 接口，无需安装客户端，支持全平台。

1.  **获取 HTTP 接口权限**: 联系同花顺客户经理开通 HTTP 接口权限。
2.  **生成 HTTP 代码**:
    - 访问 [Web 版超级命令](https://quantapi.10jqka.com.cn/gwstatic/static/ds_web/super-command-web/index.html)。
    - 选择所需指标和参数。
    - 在生成代码区域选择 **"HTTP"** 标签。
    - 获取 `API 地址` (URL) 和 `请求体` (JSON Body)。
3.  **配置项目**:
    - 在 `config/config.yaml` 中设置 `ifind_api.mode: "http"`。
    - 填入你的 `access_token` (如果需要) 或配置请求头。

### 方案二：Windows 虚拟机/远程桌面

如果必须使用 SDK (例如需要高性能实时数据)：

1.  **虚拟机**: 使用 Parallels Desktop, VMWare Fusion 或 VirtualBox 安装 Windows。
2.  **远程开发**:
    - 在 Windows 机器上启动 SSH 服务。
    - 在 Mac 上使用 VS Code 的 "Remote - SSH" 插件连接到 Windows 机器进行开发。

---

### 3.4 HTTP 接口 (REST API)

对于 Mac/Linux 用户或无需安装终端的场景，可使用 HTTP 接口。

#### 3.4.1 鉴权 (Authentication)

*   **Endpoint**: `https://quantapi.51ifind.com/api/v1/get_access_token`
*   **Method**: POST
*   **Headers**: `Content-Type: application/json`, `refresh_token: <YOUR_REFRESH_TOKEN>`
*   **Body**: `{"refresh_token": "<YOUR_REFRESH_TOKEN>"}`

#### 3.4.2 基础数据 (Basic Data)

*   **Endpoint**: `https://quantapi.51ifind.com/api/v1/basic_data_service`
*   **Method**: POST
*   **Headers**: `access_token: <YOUR_ACCESS_TOKEN>`
*   **Body Example**:
    ```json
    {
      "codes": "600519.SH,000858.SZ",
      "indipara": [
        {
          "indicator": "ths_stock_short_name_stock",
          "indiparams": []
        }
      ]
    }
    ```

#### 3.4.3 日期序列 (Date Sequence)

*   **Endpoint**: `https://quantapi.51ifind.com/api/v1/date_sequence`
*   **Body Example**:
    ```json
    {
      "codes": "600519.SH",
      "startdate": "2023-01-01",
      "enddate": "2023-12-31",
      "functionpara": {
        "Interval": "D",
        "Fill": "Blank"
      },
      "indipara": [
        {
          "indicator": "ths_close_price_stock",
          "indiparams": []
        }
      ]
    }
    ```

#### 3.4.4 历史行情 (History Quotation)

*   **Endpoint**: `https://quantapi.51ifind.com/api/v1/cmd_history_quotation`
*   **Body Example**:
    ```json
    {
      "codes": "600519.SH",
      "indicators": "open,close,high,low,volume",
      "startdate": "2023-01-01",
      "enddate": "2023-12-31",
      "functionpara": {
        "Interval": "D",
        "CPS": "6"  // 6: 前复权
      }
    }
    ```

## 4. 缺失信息与待办事项
