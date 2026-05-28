"""工具函数与辅助模块。"""

import logging
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


def replace_placeholder_in_value(
    value: str, payload: str, placeholder: str = "{{PAYLOAD}}"
) -> str:
    """替换字符串中的占位符为实际载荷。

    Args:
        value: 原始字符串。
        payload: 要替换的载荷内容。
        placeholder: 占位符字符串，默认为 {{PAYLOAD}}。

    Returns:
        替换后的字符串。
    """
    return value.replace(placeholder, payload)


def deep_replace(
    data: Union[str, Dict[str, Any], None],
    payload: str,
    placeholder: str = "{{PAYLOAD}}",
) -> Union[str, Dict[str, Any], None]:
    """递归替换字典或字符串中的占位符。

    Args:
        data: 原始字典或字符串。
        payload: 要替换的载荷内容。
        placeholder: 占位符字符串。

    Returns:
        替换后的字典或字符串。
    """
    if data is None:
        return None
    if isinstance(data, str):
        return replace_placeholder_in_value(data, payload, placeholder)
    if isinstance(data, dict):
        return {
            key: deep_replace(value, payload, placeholder)
            for key, value in data.items()
        }
    return data


def merge_dict(
    base: Dict[str, Any], override: Dict[str, Any]
) -> Dict[str, Any]:
    """合并两个字典，override 会覆盖 base 中同名的键。

    Args:
        base: 基础字典。
        override: 覆盖字典。

    Returns:
        合并后的新字典。
    """
    result = base.copy()
    result.update(override)
    return result
