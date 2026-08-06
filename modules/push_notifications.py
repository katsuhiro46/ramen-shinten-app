import hashlib
import json
import os
from typing import Any, Dict, List, Tuple

import requests

try:
    from pywebpush import WebPushException, webpush
except Exception:
    WebPushException = Exception
    webpush = None


SUBSCRIPTIONS_SET_KEY = "ramen:push:subscription_endpoints"
SUBSCRIPTION_PREFIX = "ramen:push:subscription:"


def vapid_public_key() -> str:
    return os.getenv("VAPID_PUBLIC_KEY", "").strip()


def vapid_private_key() -> str:
    return os.getenv("VAPID_PRIVATE_KEY", "").strip()


def vapid_subject() -> str:
    return os.getenv("VAPID_SUBJECT", "mailto:admin@example.com").strip()


def app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "/").strip() or "/"


def upstash_url() -> str:
    return os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")


def upstash_token() -> str:
    return os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()


def storage_configured() -> bool:
    return bool(upstash_url() and upstash_token())


def push_configured() -> bool:
    return bool(storage_configured() and vapid_public_key() and vapid_private_key())


def public_config() -> Dict[str, Any]:
    return {
        "enabled": push_configured(),
        "storageConfigured": storage_configured(),
        "publicKey": vapid_public_key(),
    }


def subscription_key(endpoint: str) -> str:
    digest = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    return f"{SUBSCRIPTION_PREFIX}{digest}"


def redis_command(*command: Any) -> Any:
    if not storage_configured():
        raise RuntimeError("Upstash Redis is not configured")

    response = requests.post(
        upstash_url(),
        headers={"Authorization": f"Bearer {upstash_token()}"},
        json=list(command),
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if "error" in payload and payload["error"]:
        raise RuntimeError(payload["error"])
    return payload.get("result")


def normalize_subscription(subscription: Dict[str, Any]) -> Dict[str, Any]:
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys") or {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        raise ValueError("Invalid push subscription")

    return {
        "endpoint": endpoint,
        "expirationTime": subscription.get("expirationTime"),
        "keys": {
            "p256dh": keys["p256dh"],
            "auth": keys["auth"],
        },
    }


def save_subscription(subscription: Dict[str, Any]) -> None:
    normalized = normalize_subscription(subscription)
    endpoint = normalized["endpoint"]
    redis_command("SADD", SUBSCRIPTIONS_SET_KEY, endpoint)
    redis_command("SET", subscription_key(endpoint), json.dumps(normalized))


def delete_subscription(subscription: Dict[str, Any]) -> None:
    endpoint = subscription.get("endpoint")
    if not endpoint:
        return

    redis_command("SREM", SUBSCRIPTIONS_SET_KEY, endpoint)
    redis_command("DEL", subscription_key(endpoint))


def subscription_registered(endpoint: str) -> bool:
    if not endpoint or not storage_configured():
        return False
    return bool(redis_command("GET", subscription_key(endpoint)))


def list_subscriptions() -> List[Dict[str, Any]]:
    endpoints = redis_command("SMEMBERS", SUBSCRIPTIONS_SET_KEY) or []
    subscriptions = []

    for endpoint in endpoints:
        raw_subscription = redis_command("GET", subscription_key(endpoint))
        if not raw_subscription:
            redis_command("SREM", SUBSCRIPTIONS_SET_KEY, endpoint)
            continue
        try:
            subscriptions.append(json.loads(raw_subscription))
        except json.JSONDecodeError:
            redis_command("DEL", subscription_key(endpoint))
            redis_command("SREM", SUBSCRIPTIONS_SET_KEY, endpoint)

    return subscriptions


def send_notification(subscription: Dict[str, Any], payload: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        if webpush is None:
            raise RuntimeError("pywebpush is not installed")

        webpush(
            subscription_info=subscription,
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid_private_key(),
            vapid_claims={"sub": vapid_subject()},
            headers={
                "TTL": "86400",
                "Urgency": "high",
                "Topic": payload.get("tag", "ramen-shinten")[:32],
            },
            timeout=15,
        )
        return True, "sent"
    except WebPushException as e:
        status_code = getattr(getattr(e, "response", None), "status_code", None)
        if status_code in (404, 410):
            delete_subscription(subscription)
        return False, f"webpush error {status_code or ''}".strip()
    except Exception as e:
        return False, str(e)


def send_to_all(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not push_configured():
        return {"sent": 0, "failed": 0, "skipped": "push is not configured"}

    sent = 0
    failed = 0
    errors = []

    for subscription in list_subscriptions():
        ok, message = send_notification(subscription, payload)
        if ok:
            sent += 1
        else:
            failed += 1
            errors.append(message)

    return {
        "sent": sent,
        "failed": failed,
        "errors": errors[:5],
    }
