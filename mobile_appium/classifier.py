from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "schemas" / "mobile_app_manifest.yaml"

SCREEN_TYPE_AUTH_LOGIN = "AUTH_LOGIN"
SCREEN_TYPE_CONTENT_LIST = "CONTENT_LIST"
SCREEN_TYPE_CONTENT_DETAIL = "CONTENT_DETAIL"
SCREEN_TYPE_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class MobileScreenClassification:
    screen_name: str
    screen_type: str
    source: str


def _load_yaml_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_mobile_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_yaml_document(path or DEFAULT_MANIFEST_PATH)


def resolve_manifest_screen(manifest: dict[str, Any], screen_name: str) -> dict[str, Any] | None:
    screens = manifest.get("screens")
    if not isinstance(screens, list):
        return None
    for screen in screens:
        if not isinstance(screen, dict):
            continue
        if str(screen.get("name", "")).strip() == screen_name:
            return screen
        if str(screen.get("screen_id", "")).strip() == screen_name:
            return screen
    return None


def classify_screen(
    screen_name: str,
    *,
    manifest: dict[str, Any] | None = None,
    manifest_path: Path | None = None,
) -> MobileScreenClassification:
    normalized_screen_name = str(screen_name).strip()
    loaded_manifest = manifest if manifest is not None else load_mobile_manifest(manifest_path)
    screen = resolve_manifest_screen(loaded_manifest, normalized_screen_name)

    if not isinstance(screen, dict):
        return MobileScreenClassification(
            screen_name=normalized_screen_name,
            screen_type=SCREEN_TYPE_UNKNOWN,
            source="screen_not_found",
        )

    declared_type = str(screen.get("type", "")).strip().upper()
    if declared_type in {
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
    }:
        return MobileScreenClassification(
            screen_name=str(screen.get("name", normalized_screen_name)).strip() or normalized_screen_name,
            screen_type=declared_type,
            source="manifest_type",
        )

    elements = screen.get("elements", [])
    roles = set()
    if isinstance(elements, list):
        roles = {str(element.get("role", "")).strip().upper() for element in elements if isinstance(element, dict)}

    auth_required_roles = {"INPUT_USERNAME", "INPUT_PASSWORD", "ACTION_SUBMIT"}
    signal_roles = {"SIGNAL_ERROR", "SIGNAL_LOADING"}
    if auth_required_roles.issubset(roles) and roles.intersection(signal_roles):
        return MobileScreenClassification(
            screen_name=str(screen.get("name", normalized_screen_name)).strip() or normalized_screen_name,
            screen_type=SCREEN_TYPE_AUTH_LOGIN,
            source="manifest_roles",
        )

    list_roles = {
        "LIST_CONTAINER",
        "CONTENT_LIST",
        "LIST_CONTENT",
        "ITEM_CARD",
        "ITEM_TITLE",
        "ACTION_OPEN_DETAIL",
        "INPUT_SEARCH",
        "ACTION_FILTER",
    }
    if roles.intersection(list_roles) and roles.intersection({"SIGNAL_LOADING", "SIGNAL_EMPTY", "SIGNAL_ERROR", "SIGNAL_REFRESH"}):
        return MobileScreenClassification(
            screen_name=str(screen.get("name", normalized_screen_name)).strip() or normalized_screen_name,
            screen_type=SCREEN_TYPE_CONTENT_LIST,
            source="manifest_roles",
        )

    detail_roles = {
        "DETAIL_CONTAINER",
        "CONTENT_TITLE",
        "CONTENT_IMAGE",
        "CONTENT_PRICE",
        "CONTENT_DESCRIPTION",
        "NAVIGATION_BACK",
        "ACTION_ADD_TO_CART",
    }
    if roles.intersection(detail_roles) and roles.intersection({"SIGNAL_LOADING", "SIGNAL_ERROR"}):
        return MobileScreenClassification(
            screen_name=str(screen.get("name", normalized_screen_name)).strip() or normalized_screen_name,
            screen_type=SCREEN_TYPE_CONTENT_DETAIL,
            source="manifest_roles",
        )

    return MobileScreenClassification(
        screen_name=str(screen.get("name", normalized_screen_name)).strip() or normalized_screen_name,
        screen_type=SCREEN_TYPE_UNKNOWN,
        source="manifest_unknown",
    )
