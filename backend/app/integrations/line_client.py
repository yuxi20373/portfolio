import base64
import hashlib
import hmac
import logging

import requests

from ..config import settings

logger = logging.getLogger("line_client")

LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def verify_signature(body: bytes, signature: str) -> bool:
    if not settings.line_channel_secret:
        logger.warning("LINE_CHANNEL_SECRET is not set - skipping signature verification (dev only)")
        return True
    mac = hmac.new(settings.line_channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode("utf-8")
    return hmac.compare_digest(expected, signature or "")


def reply(reply_token: str, text: str):
    if not settings.line_channel_access_token:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN is not set - cannot reply")
        return
    headers = {
        "Authorization": f"Bearer {settings.line_channel_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text[:4900]}],  # LINE per-message length guard
    }
    resp = requests.post(LINE_REPLY_URL, headers=headers, json=payload, timeout=15)
    if resp.status_code != 200:
        logger.error("LINE reply failed: %s %s", resp.status_code, resp.text)
