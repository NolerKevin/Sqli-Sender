"""sqli-sender 单元测试。"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import yaml

from sqli_sender import (
    InjectionSender,
    PayloadProcessor,
    ConfigError,
    InjectionError,
    PayloadLoadError,
    PayloadNotFoundError,
)


class TestPayloadProcessor(unittest.TestCase):
    """PayloadProcessor 单元测试。"""

    def setUp(self):
        self.processor = PayloadProcessor()
        # 加载默认模板
        default_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "sqli_sender",
            "payloads",
            "default.yaml",
        )
        self.processor.load_from_file(default_path)

    def test_load_default_success(self):
        """测试加载默认模板成功。"""
        self.assertIn("mysql", self.processor.templates["databases"])
        self.assertIn("mssql", self.processor.templates["databases"])

    def test_load_from_file_not_exists(self):
        """测试加载不存在的文件抛出异常。"""
        with self.assertRaises(PayloadLoadError):
            self.processor.load_from_file("/nonexistent/path.yaml")

    def test_load_invalid_yaml(self):
        """测试加载无效 YAML 抛出异常。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: : broken")
            path = f.name
        try:
            with self.assertRaises(PayloadLoadError):
                self.processor.load_from_file(path)
        finally:
            os.unlink(path)

    def test_load_missing_databases_key(self):
        """测试缺少 databases 键的 YAML 抛出异常。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump({"foo": "bar"}, f)
            path = f.name
        try:
            with self.assertRaises(PayloadLoadError):
                self.processor.load_from_file(path)
        finally:
            os.unlink(path)

    def test_get_supported_databases(self):
        """测试获取支持的数据库列表。"""
        dbs = self.processor.get_supported_databases()
        self.assertIn("mysql", dbs)
        self.assertIn("mssql", dbs)
        self.assertIn("postgresql", dbs)
        self.assertIn("oracle", dbs)
        self.assertIn("sqlite", dbs)

    def test_get_supported_injection_types(self):
        """测试获取支持的注入方式列表。"""
        types = self.processor.get_supported_injection_types("mysql")
        self.assertIn("error_based", types)
        self.assertIn("boolean_based", types)
        self.assertIn("time_based", types)
        self.assertIn("union_based", types)

    def test_get_supported_injection_types_unknown_db(self):
        """测试查询不存在的数据库类型抛出异常。"""
        with self.assertRaises(PayloadNotFoundError):
            self.processor.get_supported_injection_types("unknown_db")

    def test_get_payloads_boolean(self):
        """测试生成布尔盲注 payload。"""
        payloads = self.processor.get_payloads(
            "mysql", "boolean_based", boolean_condition="1=1"
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertIn("1=1", p)
            self.assertTrue(
                p.endswith("-- ") or p.endswith("--"),
                f"payload 应以注释结尾: {p}",
            )

    def test_get_payloads_error_based(self):
        """测试生成报错注入 payload。"""
        payloads = self.processor.get_payloads(
            "mysql", "error_based", query="SELECT user()"
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertIn("SELECT user()", p)

    def test_get_payloads_time_based(self):
        """测试生成时间盲注 payload。"""
        payloads = self.processor.get_payloads(
            "mysql",
            "time_based",
            boolean_condition="1=1",
            sleep_time="5",
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertTrue(
                "SLEEP(5)" in p or "BENCHMARK" in p,
                f"payload 应包含 SLEEP 或 BENCHMARK: {p}",
            )

    def test_get_payloads_union(self):
        """测试生成联合查询 payload。"""
        payloads = self.processor.get_payloads(
            "mysql", "union_based", columns="1,2,3"
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertIn("1,2,3", p)
            self.assertIn("UNION", p)

    def test_get_payloads_unknown_db(self):
        """测试不支持的数据库类型抛出异常。"""
        with self.assertRaises(PayloadNotFoundError):
            self.processor.get_payloads(
                "unknown_db", "boolean_based", boolean_condition="1=1"
            )

    def test_get_payloads_unsupported_injection_type(self):
        """测试不支持的注入方式抛出异常。"""
        with self.assertRaises(PayloadNotFoundError):
            self.processor.get_payloads(
                "sqlite", "error_based", query="SELECT 1"
            )

    def test_get_payloads_mssql(self):
        """测试 MSSQL 载荷生成。"""
        payloads = self.processor.get_payloads(
            "mssql", "time_based",
            boolean_condition="1=1", sleep_time="5",
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertIn("WAITFOR", p)

    def test_get_payloads_postgresql(self):
        """测试 PostgreSQL 载荷生成。"""
        payloads = self.processor.get_payloads(
            "postgresql", "time_based",
            boolean_condition="1=1", sleep_time="5",
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertIn("pg_sleep", p)

    def test_get_payloads_oracle(self):
        """测试 Oracle 载荷生成。"""
        payloads = self.processor.get_payloads(
            "oracle", "union_based", columns="1,2 FROM dual"
        )
        self.assertTrue(len(payloads) > 0)
        for p in payloads:
            self.assertIn("FROM DUAL", p)


class TestInjectionSender(unittest.TestCase):
    """InjectionSender 单元测试。"""

    def test_init_defaults(self):
        """测试默认初始化。"""
        sender = InjectionSender(url="http://example.com")
        self.assertEqual(sender.url, "http://example.com")
        self.assertEqual(sender.method, "GET")
        self.assertEqual(sender.params, {})
        self.assertEqual(sender.headers, {})
        self.assertEqual(sender.cookies, {})
        self.assertEqual(sender.injection_point, "param")
        self.assertEqual(sender.injection_type, "boolean")

    def test_init_with_custom_values(self):
        """测试自定义配置初始化。"""
        sender = InjectionSender(
            url="http://example.com/login",
            method="POST",
            params={"page": "1"},
            data={"username": "admin{{PAYLOAD}}", "password": "pass"},
            headers={"X-Custom": "test"},
            cookies={"session": "abc"},
            injection_point="data",
            injection_type="error",
            timeout=15,
        )
        self.assertEqual(sender.method, "POST")
        self.assertEqual(sender.data["username"], "admin{{PAYLOAD}}")
        self.assertEqual(sender.injection_type, "error")

    def test_validate_invalid_method(self):
        """测试不支持的 HTTP 方法抛出异常。"""
        with self.assertRaises(ConfigError):
            InjectionSender(url="http://example.com", method="INVALID")

    def test_validate_invalid_injection_point(self):
        """测试不支持的注入位置抛出异常。"""
        with self.assertRaises(ConfigError):
            InjectionSender(
                url="http://example.com",
                injection_point="invalid",
            )

    def test_validate_invalid_injection_type(self):
        """测试不支持的注入方式抛出异常。"""
        with self.assertRaises(ConfigError):
            InjectionSender(
                url="http://example.com",
                injection_type="invalid",
            )

    @patch("sqli_sender.sender.requests.request")
    def test_send_replace_payload_in_params(self, mock_request):
        """测试 send 替换 params 中的占位符。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(
            url="http://example.com/page.php",
            params={"id": "1{{PAYLOAD}}"},
        )
        response = sender.send(" AND 1=1-- ")

        # 验证 requests.request 被正确调用
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"id": "1 AND 1=1-- "})

    @patch("sqli_sender.sender.requests.request")
    def test_send_replace_payload_in_data(self, mock_request):
        """测试 send 替换 POST data 中的占位符。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(
            url="http://example.com/login",
            method="POST",
            data={"username": "admin{{PAYLOAD}}", "password": "pass"},
        )
        response = sender.send("' OR 1=1-- ")

        _, kwargs = mock_request.call_args
        self.assertEqual(
            kwargs["data"]["username"], "admin' OR 1=1-- "
        )
        self.assertEqual(kwargs["data"]["password"], "pass")

    @patch("sqli_sender.sender.requests.request")
    def test_send_replace_payload_in_headers(self, mock_request):
        """测试 send 替换 headers 中的占位符。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(
            url="http://example.com",
            headers={"X-Forwarded-For": "{{PAYLOAD}}"},
            injection_point="header",
        )
        response = sender.send("127.0.0.1")

        _, kwargs = mock_request.call_args
        self.assertEqual(
            kwargs["headers"]["X-Forwarded-For"], "127.0.0.1"
        )

    @patch("sqli_sender.sender.requests.request")
    def test_send_replace_payload_in_cookies(self, mock_request):
        """测试 send 替换 cookies 中的占位符。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(
            url="http://example.com",
            cookies={"session": "{{PAYLOAD}}"},
            injection_point="cookie",
        )
        response = sender.send("' OR 1=1-- ")

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["cookies"]["session"], "' OR 1=1-- ")

    @patch("sqli_sender.sender.requests.request")
    def test_send_replace_in_url(self, mock_request):
        """测试 send 替换 URL 中的占位符。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(
            url="http://example.com/page.php?id=1{{PAYLOAD}}",
            method="GET",
        )
        response = sender.send(" AND 1=1")

        _, kwargs = mock_request.call_args
        self.assertEqual(
            kwargs["url"], "http://example.com/page.php?id=1 AND 1=1"
        )

    @patch("sqli_sender.sender.requests.request")
    def test_send_request_exception(self, mock_request):
        """测试请求异常时抛出 InjectionError。"""
        from requests.exceptions import ConnectionError

        mock_request.side_effect = ConnectionError("connection failed")

        sender = InjectionSender(url="http://example.com")
        with self.assertRaises(InjectionError):
            sender.send("test")

    @patch("sqli_sender.sender.requests.request")
    def test_send_batch(self, mock_request):
        """测试批量发送。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(url="http://example.com")
        responses = sender.send_batch(["p1", "p2", "p3"])

        self.assertEqual(len(responses), 3)
        self.assertEqual(mock_request.call_count, 3)

    def test_repr(self):
        """测试 __repr__。"""
        sender = InjectionSender(
            url="http://example.com",
            method="POST",
            injection_point="param",
            injection_type="boolean",
        )
        r = repr(sender)
        self.assertIn("InjectionSender", r)
        self.assertIn("http://example.com", r)

    @patch("sqli_sender.sender.requests.request")
    def test_no_placeholder_no_replacement(self, mock_request):
        """测试无需替换占位符时正常运行。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        sender = InjectionSender(
            url="http://example.com",
            params={"id": "1"},
        )
        response = sender.send(" AND 1=1")

        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"], {"id": "1"})
        self.assertNotIn("{{PAYLOAD}}", str(kwargs))


class TestUtils(unittest.TestCase):
    """工具函数单元测试。"""

    def test_deep_replace_string(self):
        """测试字符串替换。"""
        from sqli_sender.utils import deep_replace
        result = deep_replace("hello {{PAYLOAD}}", "world")
        self.assertEqual(result, "hello world")

    def test_deep_replace_dict(self):
        """测试字典递归替换。"""
        from sqli_sender.utils import deep_replace
        data = {
            "a": "1{{PAYLOAD}}",
            "b": "normal",
            "c": {"d": "{{PAYLOAD}}"},
        }
        result = deep_replace(data, " injected")
        self.assertEqual(result["a"], "1 injected")
        self.assertEqual(result["b"], "normal")
        self.assertEqual(result["c"]["d"], " injected")

    def test_deep_replace_none(self):
        """测试 None 值。"""
        from sqli_sender.utils import deep_replace
        self.assertIsNone(deep_replace(None, "payload"))

    def test_merge_dict(self):
        """测试字典合并。"""
        from sqli_sender.utils import merge_dict
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_dict(base, override)
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 3)
        self.assertEqual(result["c"], 4)


if __name__ == "__main__":
    unittest.main()
