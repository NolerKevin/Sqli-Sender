"""载荷构造器模块。

从 YAML 文件加载 SQL 注入载荷模板，支持多数据库类型和注入方式。
"""

import logging
import os
from typing import Any, Dict, List, Optional

import yaml

from .exceptions import PayloadLoadError, PayloadNotFoundError

logger = logging.getLogger(__name__)

# 模板中支持的占位符
PLACEHOLDER_QUERY = "{QUERY}"
PLACEHOLDER_BOOLEAN = "{BOOLEAN_CONDITION}"
PLACEHOLDER_SLEEP_TIME = "{SLEEP_TIME}"
PLACEHOLDER_COLUMNS = "{COLUMNS}"

_KNOWN_PLACEHOLDERS = frozenset([
    PLACEHOLDER_QUERY,
    PLACEHOLDER_BOOLEAN,
    PLACEHOLDER_SLEEP_TIME,
    PLACEHOLDER_COLUMNS,
])

DEFAULT_PAYLOAD_PATH = os.path.join(
    os.path.dirname(__file__), "payloads", "default.yaml"
)


class PayloadProcessor:
    """载荷构造器。

    从 YAML 文件加载载荷模板，并根据数据库类型和注入方式生成 payload 字符串。

    Attributes:
        templates: 从 YAML 加载的完整模板数据。
    """

    def __init__(self) -> None:
        self.templates: Dict[str, Any] = {}

    def load_from_file(self, path: str) -> None:
        """从 YAML 文件加载载荷模板。

        Args:
            path: YAML 文件路径。

        Raises:
            PayloadLoadError: 文件不存在或 YAML 解析失败时抛出。
        """
        if not os.path.exists(path):
            raise PayloadLoadError(f"载荷模板文件不存在: {path}")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.templates = yaml.safe_load(f)
            if not self.templates or "databases" not in self.templates:
                raise PayloadLoadError(
                    "YAML 文件中缺少 'databases' 根键"
                )
        except yaml.YAMLError as e:
            raise PayloadLoadError(f"YAML 解析失败: {e}") from e
        logger.info("已从 %s 加载载荷模板", path)

    def load_default(self) -> None:
        """加载内置的默认载荷模板。"""
        self.load_from_file(DEFAULT_PAYLOAD_PATH)

    def get_supported_databases(self) -> List[str]:
        """获取支持的数据库类型列表。

        Returns:
            数据库类型名称列表。
        """
        return list(self.templates.get("databases", {}).keys())

    def get_supported_injection_types(
        self, db_type: str
    ) -> List[str]:
        """获取指定数据库支持的注入方式列表。

        Args:
            db_type: 数据库类型（如 mysql, mssql）。

        Returns:
            注入方式名称列表。

        Raises:
            PayloadNotFoundError: 数据库类型不存在时抛出。
        """
        db = self.templates.get("databases", {}).get(db_type)
        if db is None:
            raise PayloadNotFoundError(f"不支持的数据库类型: {db_type}")
        return [
            k
            for k, v in db.items()
            if isinstance(v, list) and k.endswith("_based")
        ]

    def get_payloads(
        self,
        db_type: str,
        injection_type: str,
        **kwargs: Any,
    ) -> List[str]:
        """根据数据库类型和注入方式返回 payload 列表。

        支持在模板中使用以下占位符：
        - {QUERY}            : SQL 子查询语句
        - {BOOLEAN_CONDITION} : 布尔条件表达式
        - {SLEEP_TIME}       : 延时秒数
        - {COLUMNS}          : UNION 查询的列定义

        Args:
            db_type: 数据库类型（如 mysql, mssql, postgresql, oracle, sqlite）。
            injection_type: 注入方式（error_based, boolean_based, time_based,
                          union_based）。
            **kwargs: 用于替换模板占位符的键值对。
                      例如 query="SELECT user()", boolean_condition="1=1",
                      sleep_time=5, columns="1,2,3"。

        Returns:
            格式化后的 payload 字符串列表。

        Raises:
            PayloadNotFoundError: 数据库类型或注入方式不支持时抛出。
        """
        databases = self.templates.get("databases", {})
        if db_type not in databases:
            raise PayloadNotFoundError(
                f"不支持的数据库类型: {db_type}。"
                f" 可用类型: {list(databases.keys())}"
            )

        db = databases[db_type]
        templates: List[str] = db.get(injection_type, [])
        if not templates:
            raise PayloadNotFoundError(
                f"数据库 '{db_type}' 不支持注入方式 '{injection_type}'"
            )

        comment = db.get("comment", "")

        # 构建占位符映射
        placeholders: Dict[str, str] = {}
        for key, value in kwargs.items():
            placeholder = "{" + key.upper() + "}"
            if placeholder in _KNOWN_PLACEHOLDERS:
                placeholders[placeholder] = str(value)
            else:
                logger.debug("忽略未知占位符: %s", placeholder)

        results: List[str] = []
        for template in templates:
            payload = template
            for placeholder, value in placeholders.items():
                payload = payload.replace(placeholder, value)
            # 检查是否还有未替换的已知占位符（用户漏传的参数）
            missing = [
                p for p in _KNOWN_PLACEHOLDERS if p in payload
            ]
            if missing:
                logger.warning(
                    "payload 中存在未替换的占位符 %s: %s", missing, payload
                )
            # 如果模板中有尾随空格，注释符号前不加空格
            if comment and not template.endswith(" "):
                payload = payload.rstrip() + " " + comment
            else:
                payload = payload + comment
            results.append(payload)

        return results
