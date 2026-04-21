from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
    SCREEN_TYPE_UNKNOWN,
    classify_screen,
)
from mobile_appium.planner import plan_screen


def test_classifier_identifies_login_screen_from_manifest():
    classification = classify_screen("LoginScreen")

    assert classification.screen_type == SCREEN_TYPE_AUTH_LOGIN


def test_classifier_identifies_real_content_list_screen_from_manifest():
    classification = classify_screen("ListScreen")

    assert classification.screen_type == SCREEN_TYPE_CONTENT_LIST


def test_classifier_identifies_real_content_detail_screen_from_manifest():
    classification = classify_screen("DetailScreen")

    assert classification.screen_type == SCREEN_TYPE_CONTENT_DETAIL


def test_classifier_returns_unknown_for_missing_screen():
    classification = classify_screen("MissingScreen")

    assert classification.screen_type == SCREEN_TYPE_UNKNOWN


def _write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _workspace_manifest_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_manifests" / f"{test_name}_{run_id}.yaml"


def test_classifier_identifies_content_list_from_roles():
    manifest_path = _workspace_manifest_path("content_list_classifier")
    try:
        _write_manifest(
            manifest_path,
            {
                "screens": [
                    {
                        "screen_id": "feed_screen",
                        "name": "FeedScreen",
                        "elements": [
                            {"role": "LIST_CONTAINER"},
                            {"role": "ITEM_CARD"},
                            {"role": "SIGNAL_LOADING"},
                        ],
                    }
                ]
            },
        )

        classification = classify_screen("FeedScreen", manifest_path=manifest_path)

        assert classification.screen_type == SCREEN_TYPE_CONTENT_LIST
    finally:
        manifest_path.unlink(missing_ok=True)


def test_classifier_identifies_content_detail_from_roles():
    manifest_path = _workspace_manifest_path("content_detail_classifier")
    try:
        _write_manifest(
            manifest_path,
            {
                "screens": [
                    {
                        "screen_id": "article_detail",
                        "name": "ArticleDetailScreen",
                        "elements": [
                            {"role": "DETAIL_CONTAINER"},
                            {"role": "CONTENT_TITLE"},
                            {"role": "SIGNAL_LOADING"},
                        ],
                    }
                ]
            },
        )

        classification = classify_screen("ArticleDetailScreen", manifest_path=manifest_path)

        assert classification.screen_type == SCREEN_TYPE_CONTENT_DETAIL
    finally:
        manifest_path.unlink(missing_ok=True)


def test_planner_generates_content_list_validation_steps():
    manifest_path = _workspace_manifest_path("content_list_planner")
    try:
        _write_manifest(
            manifest_path,
            {
                "screens": [
                    {
                        "screen_id": "feed_screen",
                        "name": "FeedScreen",
                        "type": "CONTENT_LIST",
                        "elements": [
                            {"role": "LIST_CONTAINER"},
                            {"role": "ITEM_CARD"},
                            {"role": "SIGNAL_LOADING"},
                        ],
                    }
                ]
            },
        )

        plan = plan_screen("FeedScreen", username="", password="", manifest_path=manifest_path)

        assert plan.screen_type == SCREEN_TYPE_CONTENT_LIST
        assert [step.action for step in plan.steps] == [
            "validate_list_loaded",
            "validate_list_items_visible",
        ]
        assert plan.oracle.success_condition == "list_items_visible"
    finally:
        manifest_path.unlink(missing_ok=True)


def test_planner_generates_content_detail_validation_steps():
    manifest_path = _workspace_manifest_path("content_detail_planner")
    try:
        _write_manifest(
            manifest_path,
            {
                "screens": [
                    {
                        "screen_id": "article_detail",
                        "name": "ArticleDetailScreen",
                        "type": "CONTENT_DETAIL",
                        "elements": [
                            {"role": "DETAIL_CONTAINER"},
                            {"role": "CONTENT_TITLE"},
                            {"role": "SIGNAL_LOADING"},
                        ],
                    }
                ]
            },
        )

        plan = plan_screen("ArticleDetailScreen", username="", password="", manifest_path=manifest_path)

        assert plan.screen_type == SCREEN_TYPE_CONTENT_DETAIL
        assert [step.action for step in plan.steps] == [
            "validate_detail_loaded",
            "validate_detail_content_visible",
        ]
        assert plan.oracle.success_condition == "detail_content_visible"
    finally:
        manifest_path.unlink(missing_ok=True)


def test_planner_uses_structured_content_list_artifacts():
    plan = plan_screen("ListScreen", username="", password="")

    assert plan.screen_type == SCREEN_TYPE_CONTENT_LIST
    assert [step.action for step in plan.steps] == [
        "validate_list_loaded",
        "validate_list_items_visible",
    ]
    assert plan.oracle.success_condition == "list_items_visible"
    assert plan.oracle.failure_condition == "error_message_visible"


def test_planner_uses_structured_content_detail_artifacts():
    plan = plan_screen("DetailScreen", username="", password="")

    assert plan.screen_type == SCREEN_TYPE_CONTENT_DETAIL
    assert [step.action for step in plan.steps] == [
        "validate_detail_loaded",
        "validate_detail_content_visible",
    ]
    assert plan.oracle.success_condition == "detail_content_visible"
    assert plan.oracle.failure_condition == "error_message_visible"
