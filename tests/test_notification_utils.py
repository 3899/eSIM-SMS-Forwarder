from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock
from urllib.parse import parse_qs, urlparse


MODULE_PATH = Path(__file__).resolve().parents[1] / "deploy" / "shared" / "notification_utils.py"
MODULE_NAME = "esim_sms_forwarder_notification_utils"


def load_notification_utils_module():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


notification_utils = load_notification_utils_module()


class ChannelTypeTests(unittest.TestCase):
    def test_infer_channel_type_maps_structured_channels(self) -> None:
        cases = {
            "schan://abc": "serverchan",
            "wecombot://abc": "wecom_bot",
            "feishu://abc": "feishu_bot",
            "lark://abc": "feishu_bot",
            "dingtalk://abc": "dingtalk_bot",
            "webhooklite://config?target=https%3A%2F%2Fexample.com": "webhook_lite",
            "wecomapp://config?corp_id=1": "wecom_app",
            "feishuapp://config?app_id=1": "feishu_app",
            "dingtalkcorp://config?url=https%3A%2F%2Fexample.com": "dingtalk_corp",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(notification_utils.infer_channel_type(url), expected)


class DispatchTests(unittest.TestCase):
    def test_send_notification_dispatches_apprise_and_native_targets(self) -> None:
        targets = [
            {"id": "mail", "label": "Email", "url": "mailto://user:pass@mail.example.com", "enabled": True, "type": "email"},
            {"id": "hook", "label": "Webhook", "url": "webhooklite://config?target=https%3A%2F%2Fexample.com", "enabled": True, "type": "webhook_lite"},
        ]
        with mock.patch.object(notification_utils, "send_apprise_notification", return_value=["Email"]) as apprise_mock:
            with mock.patch.object(notification_utils, "_send_native_notification", return_value="Webhook") as native_mock:
                labels = notification_utils.send_notification(targets, "Title", "Body")

        self.assertEqual(labels, ["Email", "Webhook"])
        apprise_mock.assert_called_once()
        native_mock.assert_called_once()

    def test_send_notification_raises_partial_failure(self) -> None:
        targets = [
            {"id": "mail", "label": "Email", "url": "mailto://user:pass@mail.example.com", "enabled": True, "type": "email"},
            {"id": "hook", "label": "Webhook", "url": "webhooklite://config?target=https%3A%2F%2Fexample.com", "enabled": True, "type": "webhook_lite"},
        ]
        with mock.patch.object(notification_utils, "send_apprise_notification", return_value=["Email"]):
            with mock.patch.object(notification_utils, "_send_native_notification", side_effect=RuntimeError("boom")):
                with self.assertRaisesRegex(RuntimeError, "部分通知发送失败"):
                    notification_utils.send_notification(targets, "Title", "Body")


class WebhookLiteTests(unittest.TestCase):
    def test_webhook_lite_get_appends_title_and_body(self) -> None:
        request_url: str | None = None

        def capture_request(method: str, url: str, **_: object) -> None:
            nonlocal request_url
            self.assertEqual(method, "GET")
            request_url = url

        target = "webhooklite://config?target=https%3A%2F%2Fexample.com%2Fhook%3Ffoo%3Dbar&method=GET&title_key=subject&body_key=content"
        with mock.patch.object(notification_utils, "_request_text", side_effect=capture_request):
            notification_utils._send_webhook_lite(target, "Hello", "World")

        self.assertIsNotNone(request_url)
        parsed = urlparse(request_url or "")
        query = parse_qs(parsed.query)
        self.assertEqual(query["foo"], ["bar"])
        self.assertEqual(query["subject"], ["Hello"])
        self.assertEqual(query["content"], ["World"])

    def test_webhook_lite_post_json_uses_request_text(self) -> None:
        sent = {}

        def capture_request(method: str, url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None) -> None:
            sent["method"] = method
            sent["url"] = url
            sent["data"] = data
            sent["headers"] = headers or {}

        target = "webhooklite://config?target=https%3A%2F%2Fexample.com%2Fhook&method=POST&format=json&title_key=title&body_key=body"
        with mock.patch.object(notification_utils, "_request_text", side_effect=capture_request):
            notification_utils._send_webhook_lite(target, "Hello", "World")

        self.assertEqual(sent["method"], "POST")
        self.assertEqual(sent["url"], "https://example.com/hook")
        self.assertEqual(sent["headers"]["Content-Type"], "application/json; charset=utf-8")
        self.assertIn(b'"title": "Hello"', sent["data"])
        self.assertIn(b'"body": "World"', sent["data"])


if __name__ == "__main__":
    unittest.main()
