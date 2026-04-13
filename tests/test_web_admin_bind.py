from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "deploy" / "web_admin" / "4g_wifi_admin.py"
MODULE_NAME = "esim_sms_forwarder_web_admin"


def load_web_admin_module():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


web_admin = load_web_admin_module()


class ListenStrategyTests(unittest.TestCase):
    def test_default_prefers_dual_stack(self) -> None:
        attempts = web_admin.resolve_listen_attempts(None)
        self.assertGreaterEqual(len(attempts), 1)
        self.assertEqual(attempts[0].bind_host, web_admin.DEFAULT_IPV6_LISTEN_HOST)
        self.assertEqual(attempts[0].mode, "dual-stack")
        self.assertTrue(attempts[0].dual_stack)
        self.assertFalse(attempts[0].explicit)

    def test_default_auto_keyword_prefers_dual_stack(self) -> None:
        attempts = web_admin.resolve_listen_attempts("auto")
        self.assertGreaterEqual(len(attempts), 1)
        self.assertEqual(attempts[0].bind_host, web_admin.DEFAULT_IPV6_LISTEN_HOST)
        self.assertTrue(attempts[0].dual_stack)

    def test_explicit_ipv4_host_is_ipv4_only(self) -> None:
        attempts = web_admin.resolve_listen_attempts("0.0.0.0")
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].bind_host, "0.0.0.0")
        self.assertEqual(attempts[0].address_family, web_admin.socket.AF_INET)
        self.assertFalse(attempts[0].dual_stack)
        self.assertTrue(attempts[0].explicit)

    def test_explicit_ipv6_host_is_ipv6(self) -> None:
        attempts = web_admin.resolve_listen_attempts("::1")
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].bind_host, "::1")
        self.assertEqual(attempts[0].address_family, web_admin.socket.AF_INET6)
        self.assertEqual(attempts[0].mode, "ipv6")
        self.assertFalse(attempts[0].dual_stack)

    def test_ipv6_url_is_bracketed(self) -> None:
        self.assertEqual(web_admin.format_http_url("::1", 8080), "http://[::1]:8080/")

    def test_ipv4_url_is_not_bracketed(self) -> None:
        self.assertEqual(web_admin.format_http_url("192.168.1.10", 8080), "http://192.168.1.10:8080/")

    def test_auto_dual_stack_falls_back_to_ipv4(self) -> None:
        fallback_server = object()

        with mock.patch.object(web_admin, "_instantiate_http_server") as instantiate:
            instantiate.side_effect = [OSError("ipv6 unavailable"), fallback_server]
            server, config = web_admin.create_http_server(None, 8080, web_admin.AppHandler)

        self.assertIs(server, fallback_server)
        self.assertEqual(config.bind_host, web_admin.DEFAULT_IPV4_LISTEN_HOST)
        self.assertEqual(config.address_family, web_admin.socket.AF_INET)
        self.assertEqual(instantiate.call_count, 2)

    def test_explicit_ipv4_does_not_fallback(self) -> None:
        with mock.patch.object(web_admin, "_instantiate_http_server", side_effect=OSError("bind failed")) as instantiate:
            with self.assertRaises(RuntimeError):
                web_admin.create_http_server("0.0.0.0", 8080, web_admin.AppHandler)

        self.assertEqual(instantiate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
