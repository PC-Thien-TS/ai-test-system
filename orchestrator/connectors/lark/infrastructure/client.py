from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib import error, request


@dataclass(init=False)
class LarkClientResponse:
    success: bool
    status_code: int
    data: Dict[str, Any] = field(default_factory=dict)
    raw_body: str = ""
    error: Optional[str] = None

    def __init__(
        self,
        success: bool,
        status_code: int,
        data: Optional[Dict[str, Any]] = None,
        raw_body: str = "",
        error: Optional[str] = None,
        response_json: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.success = success
        self.status_code = status_code
        self.data = data if data is not None else dict(response_json or {})
        self.raw_body = raw_body
        self.error = error


class LarkWebhookClient:
    """Lightweight webhook client with no third-party dependency."""

    def send(self, webhook_url: str, payload: Dict[str, Any], timeout_seconds: float = 5.0) -> LarkClientResponse:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as resp:
                status_code = int(resp.getcode())
                raw = resp.read().decode("utf-8", errors="replace")
                parsed: Dict[str, Any] = {}
                if raw:
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        parsed = {}
                return LarkClientResponse(
                    success=200 <= status_code < 300,
                    status_code=status_code,
                    data=parsed,
                    raw_body=raw,
                )
        except error.HTTPError as exc:
            raw = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace")
            except Exception:
                raw = ""
            return LarkClientResponse(
                success=False,
                status_code=int(exc.code),
                raw_body=raw,
                error=f"HTTPError: {exc}",
            )
        except Exception as exc:
            return LarkClientResponse(
                success=False,
                status_code=0,
                error=f"{type(exc).__name__}: {exc}",
            )
