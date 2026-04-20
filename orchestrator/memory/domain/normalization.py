from __future__ import annotations

import hashlib
import json
import re
from typing import Optional

from orchestrator.memory.domain.models import IncomingFailureRecord
from orchestrator.storage.domain.models import FailureSignature

HEX_ADDR_RE = re.compile(r"0x[0-9a-fA-F]+")
FILE_LINE_RE = re.compile(r'File "([^"]+)", line \d+, in ([A-Za-z0-9_<>]+)')
WS_RE = re.compile(r"\s+")


def normalize_stack_trace(stack_trace: Optional[str]) -> str:
    if not stack_trace:
        return ""
    cleaned = HEX_ADDR_RE.sub("0xADDR", stack_trace)
    signatures: list[str] = []
    for path, func in FILE_LINE_RE.findall(cleaned):
        base = path.replace("\\", "/").split("/")[-1]
        signatures.append(f"{base}:{func}")
    if signatures:
        return "|".join(signatures[:8])
    compact = WS_RE.sub(" ", cleaned.strip()).lower()
    return compact[:400]


def normalize_message_fingerprint(message: Optional[str]) -> str:
    if not message:
        return ""
    compact = WS_RE.sub(" ", message.strip()).lower()
    compact = re.sub(r"\d+", "#", compact)
    return hashlib.sha256(compact.encode("utf-8")).hexdigest()


def build_signature_hash(
    *,
    error_type: str,
    endpoint: Optional[str],
    plugin: Optional[str],
    normalized_stack_signature: str,
    raw_message_fingerprint: str,
    component: Optional[str],
    fingerprint: Optional[str],
) -> str:
    payload = {
        "error_type": (error_type or "").strip().lower(),
        "endpoint": (endpoint or "").strip().lower(),
        "plugin": (plugin or "").strip().lower(),
        "normalized_stack_signature": (normalized_stack_signature or "").strip().lower(),
        "raw_message_fingerprint": (raw_message_fingerprint or "").strip().lower(),
        "component": (component or "").strip().lower(),
        "fingerprint": (fingerprint or "").strip().lower(),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_failure_signature(incoming: IncomingFailureRecord) -> FailureSignature:
    normalized_stack = normalize_stack_trace(incoming.stack_trace)
    raw_message_fingerprint = normalize_message_fingerprint(incoming.message)
    component = incoming.component or incoming.plugin or "unknown_component"
    fingerprint = incoming.fingerprint or f"{incoming.error_type}:{incoming.endpoint or component}"
    signature_hash = build_signature_hash(
        error_type=incoming.error_type,
        endpoint=incoming.endpoint,
        plugin=incoming.plugin,
        normalized_stack_signature=normalized_stack,
        raw_message_fingerprint=raw_message_fingerprint,
        component=component,
        fingerprint=fingerprint,
    )
    return FailureSignature(
        fingerprint=fingerprint,
        error_type=incoming.error_type,
        component=component,
        endpoint=incoming.endpoint,
        message_hash=raw_message_fingerprint,
        plugin=incoming.plugin,
        normalized_stack_signature=normalized_stack,
        raw_message_fingerprint=raw_message_fingerprint,
        signature_hash=signature_hash,
        metadata=dict(incoming.metadata or {}),
    )
