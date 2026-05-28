"""请求主入口模块。

InjectionSender 负责根据配置构造 HTTP 请求，将 payload 注入到指定位置并发送。
"""

import logging
from typing import Any, Dict, Optional

import requests

from .exceptions import ConfigError, InjectionError
from .utils import deep_replace

logger = logging.getLogger(__name__)


class InjectionSender:
    """SQL 注入载荷发送器。

    负责构造 HTTP 请求，将 payload 注入到目标位置并发送，返回原始响应。

    使用 ``{{PAYLOAD}}`` 作为占位符，在请求配置（URL、参数、Headers、Cookies 等）
    的字符串值中放置该占位符，调用 ``send()`` 时会被实际 payload 替换。

    Attributes:
        url: 目标 URL。
        method: HTTP 请求方法（GET、POST、PUT 等）。
        params: URL 查询参数字典。
        data: 请求体数据（表单或原始数据）。
        headers: 自定义请求头。
        cookies: Cookie 字典。
        injection_point: 注入位置描述（'param' / 'header' / 'cookie'），
                         主要作为元数据标记使用。
        injection_type: 注入方式描述（'error' / 'boolean' / 'time' / 'union'），
                        主要作为元数据标记使用。
        timeout: 请求超时秒数。
        proxies: 代理配置。
        verify_ssl: 是否验证 SSL 证书。
    """

    def __init__(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        injection_point: str = "param",
        injection_type: str = "boolean",
        timeout: int = 30,
        proxies: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
    ) -> None:
        self.url = url
        self.method = method.upper()
        self.params = params or {}
        self.data = data
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.injection_point = injection_point
        self.injection_type = injection_type
        self.timeout = timeout
        self.proxies = proxies
        self.verify_ssl = verify_ssl

        self._validate()

    def _validate(self) -> None:
        """验证配置合法性。

        Raises:
            ConfigError: 配置不合法时抛出。
        """
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        if self.method not in valid_methods:
            raise ConfigError(
                f"不支持的 HTTP 方法: {self.method}。"
                f" 可用方法: {valid_methods}"
            )
        valid_points = {"param", "header", "cookie", "data"}
        if self.injection_point not in valid_points:
            raise ConfigError(
                f"不支持的注入位置: {self.injection_point}。"
                f" 可用位置: {valid_points}"
            )
        valid_types = {"error", "boolean", "time", "union"}
        if self.injection_type not in valid_types:
            raise ConfigError(
                f"不支持的注入方式: {self.injection_type}。"
                f" 可用方式: {valid_types}"
            )

    def send(self, payload: str) -> requests.Response:
        """发送带有指定 payload 的 HTTP 请求。

        将请求配置中所有 ``{{PAYLOAD}}`` 占位符替换为实际 payload 后发送请求。

        Args:
            payload: 要注入的 payload 字符串。

        Returns:
            requests.Response 原始响应对象。

        Raises:
            InjectionError: 请求发送失败时抛出。
        """
        try:
            req_url = deep_replace(self.url, payload)
            req_params = deep_replace(self.params, payload)
            req_data = deep_replace(self.data, payload)
            req_headers = deep_replace(self.headers, payload)
            req_cookies = deep_replace(self.cookies, payload)

            logger.debug(
                "发送请求: %s %s | params=%s | data=%s",
                self.method, req_url, req_params, req_data,
            )
            if isinstance(req_headers, dict):
                logger.debug("请求头: %s", req_headers)

            response = requests.request(
                method=self.method,
                url=req_url,
                params=req_params,
                data=req_data,
                headers=req_headers,
                cookies=req_cookies,
                timeout=self.timeout,
                proxies=self.proxies,
                verify=self.verify_ssl,
            )
            logger.info(
                "请求完成: %s %s -> %d", self.method, req_url, response.status_code
            )
            return response

        except requests.RequestException as e:
            raise InjectionError(f"请求发送失败: {e}") from e

    def send_batch(
        self, payloads: list[str], delay: float = 0
    ) -> list[requests.Response]:
        """批量发送多个 payload。

        Args:
            payloads: payload 字符串列表。
            delay: 每次请求之间的延迟秒数（暂未实现，保留接口）。

        Returns:
            响应对象列表。
        """
        import time

        responses: list[requests.Response] = []
        for i, payload in enumerate(payloads):
            resp = self.send(payload)
            responses.append(resp)
            if delay > 0 and i < len(payloads) - 1:
                time.sleep(delay)
        return responses

    def __repr__(self) -> str:
        return (
            f"InjectionSender(url={self.url!r}, method={self.method!r}, "
            f"injection_point={self.injection_point!r}, "
            f"injection_type={self.injection_type!r})"
        )
