from __future__ import annotations

import sys

import orchestrator.manual_qa as manual_qa
import pytest

from orchestrator.manual_qa.project_service import ProjectProfileService


def test_creates_project_profile():
    service = ProjectProfileService()

    project = service.create_project_profile(
        name="Checkout Portal",
        product_type="web",
        owner="qa-team",
        tags=["checkout", "manual"],
    )

    assert project.project_id == "checkout-portal"
    assert project.name == "Checkout Portal"
    assert project.product_type == "web"
    assert project.owner == "qa-team"


def test_normalizes_project_id_from_name():
    service = ProjectProfileService()

    project = service.create_project_profile(
        name="  Payments API v2  ",
        product_type="api",
    )

    assert project.project_id == "payments-api-v2"


def test_rejects_unsupported_product_type():
    service = ProjectProfileService()

    with pytest.raises(ValueError, match="Unsupported product_type"):
        service.create_project_profile(name="Unsupported", product_type="desktop")


def test_importing_manual_qa_does_not_import_mobile_dependencies():
    assert manual_qa is not None
    assert "mobile_appium" not in sys.modules
    assert "appium" not in sys.modules
