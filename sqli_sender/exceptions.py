"""自定义异常模块。"""


class SqliSenderError(Exception):
    """sqli-sender 基础异常。"""


class PayloadLoadError(SqliSenderError):
    """载荷模板加载失败时抛出。"""


class InjectionError(SqliSenderError):
    """请求发送或注入失败时抛出。"""


class PayloadNotFoundError(SqliSenderError):
    """未找到匹配的载荷时抛出。"""


class ConfigError(SqliSenderError):
    """配置错误时抛出。"""
