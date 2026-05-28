"""sqli-sender - SQL 注入场景化载荷发送工具。

专注于根据不同注入场景构造并发送 HTTP 请求，不包含漏洞判定逻辑。
"""

__version__ = "0.1.0"

from .exceptions import (
    ConfigError,
    InjectionError,
    PayloadLoadError,
    PayloadNotFoundError,
    SqliSenderError,
)
from .payload import PayloadProcessor
from .sender import InjectionSender

__all__ = [
    "InjectionSender",
    "PayloadProcessor",
    "SqliSenderError",
    "PayloadLoadError",
    "PayloadNotFoundError",
    "InjectionError",
    "ConfigError",
]
