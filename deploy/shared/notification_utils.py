#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


NOTIFICATION_TARGETS_KEY = "NOTIFICATION_TARGETS_JSON"
BEIJING_TZ = timezone(timedelta(hours=8))
SCRIPT_DIR = Path(__file__).resolve().parent
NOTIFICATION_ICON_ENV_KEY = "ESIM_SMS_FORWARDER_NOTIFICATION_ICON"
DEFAULT_HTTP_TIMEOUT = int(os.environ.get("ESIM_SMS_FORWARDER_NOTIFICATION_TIMEOUT", "15"))

CHANNEL_TYPE_LABELS = {
    "bark": "Bark",
    "telegram": "Telegram",
    "gotify": "Gotify",
    "ntfy": "ntfy",
    "email": "Email",
    "discord": "Discord",
    "pushplus": "PushPlus",
    "serverchan": "Server酱",
    "wecom_bot": "企业微信群机器人",
    "feishu_bot": "飞书机器人",
    "dingtalk_bot": "钉钉群机器人",
    "webhook_lite": "Webhook",
    "wecom_app": "企业微信应用",
    "feishu_app": "飞书企业应用",
    "dingtalk_corp": "钉钉企业内机器人",
    "slack": "Slack",
    "json": "JSON",
    "matrix": "Matrix",
    "xmpp": "XMPP",
    "pushbullet": "Pushbullet",
    "pushover": "Pushover",
    "signal": "Signal",
    "line": "LINE",
    "teams": "Teams",
    "mattermost": "Mattermost",
    "office365": "Office 365",
}
NATIVE_CHANNEL_TYPES = {"webhook_lite", "wecom_app", "feishu_app", "dingtalk_corp"}


def _stable_target_id(label: str, url: str) -> str:
    digest = hashlib.sha1(f"{label}\n{url}".encode("utf-8", errors="ignore")).hexdigest()
    return digest[:12]


def infer_channel_type(url: str) -> str:
    scheme = urlparse(url).scheme.strip().lower()
    if scheme in {"bark", "barks"}:
        return "bark"
    if scheme in {"mailto", "mailtos"}:
        return "email"
    if scheme in {"tgram", "telegram"}:
        return "telegram"
    if scheme == "schan":
        return "serverchan"
    if scheme == "wecombot":
        return "wecom_bot"
    if scheme in {"feishu", "lark"}:
        return "feishu_bot"
    if scheme == "dingtalk":
        return "dingtalk_bot"
    if scheme == "webhooklite":
        return "webhook_lite"
    if scheme == "wecomapp":
        return "wecom_app"
    if scheme == "feishuapp":
        return "feishu_app"
    if scheme == "dingtalkcorp":
        return "dingtalk_corp"
    if scheme:
        return scheme
    return "custom"


def channel_type_label(channel_type: str) -> str:
    normalized = channel_type.strip().lower()
    if normalized in CHANNEL_TYPE_LABELS:
        return CHANNEL_TYPE_LABELS[normalized]
    if not normalized:
        return "渠道"
    if normalized.endswith("s") and normalized[:-1] in CHANNEL_TYPE_LABELS:
        return CHANNEL_TYPE_LABELS[normalized[:-1]]
    return normalized.upper()


def format_channel_label(target: dict[str, Any]) -> str:
    label = str(target.get("label", "")).strip()
    if label:
        return label
    return channel_type_label(str(target.get("type", "")))


def normalize_notification_target(target: dict[str, Any]) -> dict[str, Any]:
    url = str(target.get("url", "")).strip()
    label = str(target.get("label", "")).strip()
    enabled_raw = target.get("enabled", True)
    if isinstance(enabled_raw, bool):
        enabled = enabled_raw
    else:
        enabled = str(enabled_raw).strip().lower() not in {"0", "false", "no", "off", ""}
    channel_type = infer_channel_type(url)
    normalized_label = label or channel_type_label(channel_type)
    target_id = str(target.get("id", "")).strip() or _stable_target_id(normalized_label, url)
    return {
        "id": target_id,
        "label": normalized_label,
        "url": url,
        "enabled": enabled,
        "type": channel_type,
    }


def load_notification_targets(config: dict[str, str]) -> list[dict[str, Any]]:
    raw_targets = str(config.get(NOTIFICATION_TARGETS_KEY, "")).strip()
    if raw_targets:
        try:
            parsed = json.loads(raw_targets)
        except json.JSONDecodeError:
            parsed = []
        if isinstance(parsed, dict):
            parsed = parsed.get("targets", [])
        if isinstance(parsed, list):
            return [normalize_notification_target(item) for item in parsed if isinstance(item, dict)]
    return []


def configured_notification_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [target for target in targets if str(target.get("url", "")).strip() and bool(target.get("enabled", True))]


def configured_channel_labels(targets: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for target in configured_notification_targets(targets):
        label = format_channel_label(target)
        if label not in labels:
            labels.append(label)
    return labels


def save_notification_targets_in_config(config: dict[str, str], targets: list[dict[str, Any]]) -> dict[str, str]:
    sanitized = [normalize_notification_target(target) for target in targets if isinstance(target, dict)]
    config[NOTIFICATION_TARGETS_KEY] = json.dumps(sanitized, ensure_ascii=False, separators=(",", ":"))
    return config


def ensure_notification_config(config: dict[str, str]) -> dict[str, str]:
    if "MODEM_ID" not in config:
        config["MODEM_ID"] = "any"
    if "FORWARD_SMS_STATES" not in config:
        config["FORWARD_SMS_STATES"] = "received"
    if NOTIFICATION_TARGETS_KEY not in config:
        config[NOTIFICATION_TARGETS_KEY] = "[]"
    return config


def resolve_notification_icon_path() -> str | None:
    raw_override = os.environ.get(NOTIFICATION_ICON_ENV_KEY, "").strip()
    candidates = [
        Path(raw_override) if raw_override else None,
        SCRIPT_DIR / "frontend_dist" / "app-icon.png",
        SCRIPT_DIR.parent / "web_admin" / "frontend_dist" / "app-icon.png",
        SCRIPT_DIR.parent.parent / "frontend" / "public" / "app-icon.png",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return str(candidate)
    return None


def format_beijing_timestamp(raw_timestamp: str) -> str:
    if not raw_timestamp:
        return "未知时间"
    try:
        normalized = raw_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(BEIJING_TZ).strftime("%Y年%m月%d日 %H时%M分")
    except Exception:
        return raw_timestamp


def format_sms_state_label(state: str) -> str:
    return {
        "received": "已接收",
        "receiving": "接收中",
        "sent": "已发送",
        "sending": "发送中",
        "stored": "已存储",
    }.get(state, state or "未知")


def format_sms_notification(detail: dict[str, str]) -> tuple[str, str]:
    number = detail.get("number") or "unknown"
    title = f"收到短信：{number}"
    body = "\n\n".join(
        [
            detail.get("text") or "(empty)",
            f"时间：{detail.get('timestamp') or '未知时间'}\n状态：{format_sms_state_label(detail.get('state', ''))}",
        ]
    )
    return title, body


def _channel_type_for_target(target: dict[str, Any]) -> str:
    channel_type = str(target.get("type", "")).strip().lower()
    if channel_type:
        return channel_type
    return infer_channel_type(str(target.get("url", "")))


def _native_notification_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [target for target in configured_notification_targets(targets) if _channel_type_for_target(target) in NATIVE_CHANNEL_TYPES]


def _apprise_notification_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [target for target in configured_notification_targets(targets) if _channel_type_for_target(target) not in NATIVE_CHANNEL_TYPES]


def _request_json(method: str, url: str, *, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {"Accept": "application/json"}
    if headers:
        request_headers.update(headers)
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json; charset=utf-8")
    request = Request(url, data=data, headers=request_headers, method=method.upper())
    try:
        with urlopen(request, timeout=DEFAULT_HTTP_TIMEOUT) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"网络请求失败：{exc.reason}") from exc
    try:
        parsed = json.loads(text or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"响应不是合法 JSON：{text[:200]}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("响应 JSON 格式不正确")
    return parsed


def _request_text(method: str, url: str, *, data: bytes | None = None, headers: dict[str, str] | None = None) -> None:
    request = Request(url, data=data, headers=headers or {}, method=method.upper())
    try:
        with urlopen(request, timeout=DEFAULT_HTTP_TIMEOUT):
            return
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"网络请求失败：{exc.reason}") from exc


def _query_values(url: str) -> dict[str, str]:
    parsed = urlparse(url)
    return {
        key: values[-1]
        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
    }


def _csv_items(raw_value: str) -> list[str]:
    values: list[str] = []
    for item in raw_value.replace(";", ",").split(","):
        normalized = item.strip()
        if normalized:
            values.append(normalized)
    return values


def _bool_value(raw_value: str, default: bool = False) -> bool:
    if not raw_value:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _compose_text_message(title: str, body: str) -> str:
    normalized_title = title.strip()
    normalized_body = body.strip()
    if normalized_title and normalized_body:
        return f"{normalized_title}\n\n{normalized_body}"
    return normalized_title or normalized_body


def _send_webhook_lite(url: str, title: str, body: str) -> None:
    values = _query_values(url)
    endpoint = values.get("target", "").strip()
    if not endpoint:
        raise RuntimeError("Webhook 缺少目标地址")
    method = values.get("method", "POST").strip().upper() or "POST"
    payload_format = values.get("format", "json").strip().lower() or "json"
    title_key = values.get("title_key", "title").strip() or "title"
    body_key = values.get("body_key", "body").strip() or "body"
    if method not in {"GET", "POST"}:
        raise RuntimeError(f"Webhook 不支持的请求方式：{method}")
    if method == "GET":
        parsed = urlparse(endpoint)
        existing = parse_qs(parsed.query, keep_blank_values=True)
        existing[title_key] = [title]
        existing[body_key] = [body]
        query = urlencode(existing, doseq=True)
        request_url = urlunparse(parsed._replace(query=query))
        _request_text("GET", request_url)
        return
    if payload_format == "form":
        payload = urlencode({title_key: title, body_key: body}).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}
        _request_text("POST", endpoint, data=payload, headers=headers)
        return
    if payload_format == "json":
        payload = json.dumps({title_key: title, body_key: body}, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8"}
        _request_text("POST", endpoint, data=payload, headers=headers)
        return
    if payload_format == "text":
        payload = _compose_text_message(title, body).encode("utf-8")
        headers = {"Content-Type": "text/plain; charset=utf-8"}
        _request_text("POST", endpoint, data=payload, headers=headers)
        return
    raise RuntimeError(f"Webhook 不支持的负载类型：{payload_format}")


def _send_wecom_app(url: str, title: str, body: str) -> None:
    values = _query_values(url)
    corp_id = values.get("corp_id", "").strip()
    secret = values.get("secret", "").strip()
    agent_id = values.get("agent_id", "").strip()
    if not corp_id or not secret or not agent_id:
        raise RuntimeError("企业微信应用配置不完整")
    token_response = _request_json(
        "GET",
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken?"
        + urlencode({"corpid": corp_id, "corpsecret": secret}),
    )
    if int(token_response.get("errcode", -1)) != 0:
        raise RuntimeError(str(token_response.get("errmsg") or "获取企业微信 access_token 失败"))
    access_token = str(token_response.get("access_token", "")).strip()
    if not access_token:
        raise RuntimeError("企业微信 access_token 为空")
    payload = {
        "touser": values.get("to_user", "@all").strip() or "@all",
        "toparty": values.get("to_party", "").strip(),
        "totag": values.get("to_tag", "").strip(),
        "msgtype": "text",
        "agentid": int(agent_id),
        "text": {"content": _compose_text_message(title, body)},
        "safe": 0,
        "enable_duplicate_check": 0,
    }
    response = _request_json(
        "POST",
        "https://qyapi.weixin.qq.com/cgi-bin/message/send?" + urlencode({"access_token": access_token}),
        payload=payload,
    )
    if int(response.get("errcode", -1)) != 0:
        raise RuntimeError(str(response.get("errmsg") or "企业微信应用消息发送失败"))


def _send_feishu_app(url: str, title: str, body: str) -> None:
    values = _query_values(url)
    app_id = values.get("app_id", "").strip()
    app_secret = values.get("app_secret", "").strip()
    receive_id = values.get("receive_id", "").strip()
    receive_id_type = values.get("receive_id_type", "user_id").strip() or "user_id"
    if not app_id or not app_secret or not receive_id:
        raise RuntimeError("飞书企业应用配置不完整")
    token_response = _request_json(
        "POST",
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        payload={"app_id": app_id, "app_secret": app_secret},
    )
    if int(token_response.get("code", -1)) != 0:
        raise RuntimeError(str(token_response.get("msg") or "获取飞书 tenant_access_token 失败"))
    access_token = str(token_response.get("tenant_access_token", "")).strip()
    if not access_token:
        raise RuntimeError("飞书 tenant_access_token 为空")
    content = json.dumps({"text": _compose_text_message(title, body)}, ensure_ascii=False)
    response = _request_json(
        "POST",
        "https://open.feishu.cn/open-apis/im/v1/messages?" + urlencode({"receive_id_type": receive_id_type}),
        payload={"receive_id": receive_id, "msg_type": "text", "content": content},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if int(response.get("code", -1)) != 0:
        raise RuntimeError(str(response.get("msg") or "飞书企业应用消息发送失败"))


def _send_dingtalk_corp(url: str, title: str, body: str) -> None:
    values = _query_values(url)
    webhook_url = values.get("url", "").strip()
    secret = values.get("secret", "").strip()
    at_mobiles = _csv_items(values.get("at_mobiles", ""))
    if not webhook_url:
        raise RuntimeError("钉钉企业内机器人缺少 Webhook 地址")
    request_url = webhook_url
    if secret:
        timestamp = str(round(datetime.now(tz=timezone.utc).timestamp() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        sign = base64.b64encode(
            hmac.new(secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256).digest()
        ).decode("utf-8")
        separator = "&" if "?" in webhook_url else "?"
        request_url = f"{webhook_url}{separator}{urlencode({'timestamp': timestamp, 'sign': sign})}"
    payload = {
        "msgtype": "text",
        "text": {"content": _compose_text_message(title, body)},
        "at": {"atMobiles": at_mobiles, "isAtAll": _bool_value(values.get("at_all", ""))},
    }
    response = _request_json("POST", request_url, payload=payload)
    errcode = response.get("errcode")
    if errcode not in {None, 0, "0"}:
        raise RuntimeError(str(response.get("errmsg") or "钉钉企业内机器人发送失败"))


def _send_native_notification(target: dict[str, Any], title: str, body: str) -> str:
    channel_type = _channel_type_for_target(target)
    url = str(target.get("url", "")).strip()
    if channel_type == "webhook_lite":
        _send_webhook_lite(url, title, body)
    elif channel_type == "wecom_app":
        _send_wecom_app(url, title, body)
    elif channel_type == "feishu_app":
        _send_feishu_app(url, title, body)
    elif channel_type == "dingtalk_corp":
        _send_dingtalk_corp(url, title, body)
    else:
        raise RuntimeError(f"不支持的原生通知渠道：{channel_type}")
    return format_channel_label(target)


def send_apprise_notification(targets: list[dict[str, Any]], title: str, body: str) -> list[str]:
    try:
        import apprise
    except ImportError as exc:
        raise RuntimeError("Apprise 未安装，无法发送通知") from exc
    configured = _apprise_notification_targets(targets)
    if not configured:
        raise RuntimeError("未配置任何启用的 Apprise 通知渠道")
    app = apprise.Apprise()
    for target in configured:
        app.add(str(target["url"]))
    notify_kwargs: dict[str, Any] = {"title": title, "body": body}
    icon_path = resolve_notification_icon_path()
    if icon_path:
        notify_kwargs["attach"] = icon_path
    result = app.notify(**notify_kwargs)
    if not result:
        raise RuntimeError("Apprise 推送失败")
    return configured_channel_labels(configured)


def send_notification(targets: list[dict[str, Any]], title: str, body: str) -> list[str]:
    configured = configured_notification_targets(targets)
    if not configured:
        raise RuntimeError("未配置任何启用的通知渠道")
    delivered: list[str] = []
    failures: list[str] = []
    apprise_targets = _apprise_notification_targets(configured)
    if apprise_targets:
        try:
            delivered.extend(send_apprise_notification(apprise_targets, title, body))
        except Exception as exc:
            failures.append(f"Apprise: {exc}")
    for target in _native_notification_targets(configured):
        try:
            delivered.append(_send_native_notification(target, title, body))
        except Exception as exc:
            failures.append(f"{format_channel_label(target)}: {exc}")
    if failures:
        failure_text = "；".join(failures)
        if delivered:
            raise RuntimeError(f"部分通知发送失败；成功：{'、'.join(delivered)}；失败：{failure_text}")
        raise RuntimeError(failure_text)
    if not delivered:
        raise RuntimeError("没有可发送的通知渠道")
    return delivered
