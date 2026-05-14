"""Deterministic Web Playwright script draft generation for Manual QA."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Sequence

from orchestrator.manual_qa.models import (
    ManualTestCase,
    WebPlaywrightReadiness,
    WebPlaywrightScriptDraft,
)


class WebPlaywrightScriptGenerator:
    """Generate Playwright Python draft artifacts without executing them."""

    _BASE_TIME = datetime(2024, 1, 12, 0, 0, 0)
    _ACTION_PRIORITY = ("fill", "type", "select", "upload", "check", "uncheck", "hover", "submit", "click")
    _WEB_TERMS = (
        "page",
        "screen",
        "form",
        "field",
        "button",
        "link",
        "dropdown",
        "modal",
        "table",
        "browser",
        "click",
        "submit",
        "login page",
        "homepage",
        "dashboard",
        "navbar",
        "sidebar",
        "search box",
    )

    def __init__(self) -> None:
        self._next_draft_number = 1
        self._next_timestamp_offset = 0

    def generate_web_playwright_script_draft(
        self,
        test_case: ManualTestCase,
        readiness: WebPlaywrightReadiness | None = None,
        base_url_env_var: str = "WEB_BASE_URL",
        base_url_default: str = "http://localhost:3000",
        metadata: dict | None = None,
    ) -> WebPlaywrightScriptDraft:
        if readiness is not None:
            if readiness.readiness_status == "Not Suitable":
                raise ValueError(
                    f"Test case '{test_case.test_case_id}' is not suitable for Web Playwright draft generation."
                )
        elif not self._looks_web_like(test_case):
            raise ValueError(
                f"Test case '{test_case.test_case_id}' does not look web UI-like and cannot be drafted as a Playwright script."
            )

        warnings: list[str] = []
        assumptions: list[str] = [
            "Draft only. Not executed or verified.",
            f"Assumes {base_url_env_var} points to a reachable web application base URL.",
        ]

        page_url = ""
        if readiness is not None:
            page_url = readiness.page_url or ""
        if not page_url:
            page_url = self._detect_page_url(test_case)
        if not page_url:
            page_url = "/TODO_PAGE_URL"
            warnings.append("Page URL not detected. Added TODO page URL placeholder.")

        selector_hints = list(readiness.selector_hints) if readiness is not None else []
        if not selector_hints:
            selector_hints = self._detect_selector_hints(test_case)
        if not selector_hints:
            selector_hints = ["TODO_SELECTOR"]
            warnings.append("Selector hints not detected. Added TODO selector placeholder.")

        action_hints = list(readiness.action_hints) if readiness is not None else []
        if not action_hints:
            action_hints = self._detect_action_hints(test_case)
        if not action_hints:
            action_hints = ["click"]
            warnings.append("Action hints not detected. Added default click placeholder.")

        assertion_hints = list(readiness.assertion_hints) if readiness is not None else []
        if not assertion_hints:
            assertion_hints = self._detect_assertion_hints(test_case)
        if not assertion_hints:
            warnings.append("Assertion hints not detected. Added TODO assertion placeholder.")

        if self._contains_login_terms(test_case):
            assumptions.append("Assumes test credentials or a reusable authenticated state will be supplied manually.")

        safe_name = self._safe_test_name(test_case)
        file_name = f"test_{safe_name}.py"
        script_content = self._render_script(
            test_case=test_case,
            readiness=readiness,
            page_url=page_url,
            selector_hints=selector_hints,
            action_hints=action_hints,
            assertion_hints=assertion_hints,
            base_url_env_var=base_url_env_var,
            base_url_default=base_url_default,
            warnings=warnings,
            safe_name=safe_name,
        )

        draft = WebPlaywrightScriptDraft(
            draft_id=f"WEB-DRAFT-{self._next_draft_number:03d}",
            test_case_id=test_case.test_case_id,
            requirement_ids=list(test_case.requirement_ids),
            module=test_case.module,
            title=test_case.title,
            readiness_id=readiness.readiness_id if readiness is not None else "",
            framework="playwright-python",
            language="python",
            file_name=file_name,
            script_content=script_content,
            status="Draft",
            warnings=warnings,
            assumptions=assumptions,
            metadata={
                "page_url": page_url,
                "selector_hints": list(selector_hints),
                "action_hints": list(action_hints),
                "assertion_hints": list(assertion_hints),
                "base_url_env_var": base_url_env_var,
                **dict(metadata or {}),
            },
            created_at=self._next_timestamp(),
        )
        self._next_draft_number += 1
        return draft

    def generate_web_playwright_script_drafts(
        self,
        test_cases: Sequence[ManualTestCase],
        readiness_items: Sequence[WebPlaywrightReadiness] | None = None,
        base_url_env_var: str = "WEB_BASE_URL",
        base_url_default: str = "http://localhost:3000",
        metadata: dict | None = None,
    ) -> list[WebPlaywrightScriptDraft]:
        readiness_by_case_id = {item.test_case_id: item for item in (readiness_items or [])}
        drafts: list[WebPlaywrightScriptDraft] = []
        for test_case in test_cases:
            readiness = readiness_by_case_id.get(test_case.test_case_id)
            try:
                drafts.append(
                    self.generate_web_playwright_script_draft(
                        test_case,
                        readiness=readiness,
                        base_url_env_var=base_url_env_var,
                        base_url_default=base_url_default,
                        metadata=metadata,
                    )
                )
            except ValueError:
                continue
        return drafts

    def _render_script(
        self,
        *,
        test_case: ManualTestCase,
        readiness: WebPlaywrightReadiness | None,
        page_url: str,
        selector_hints: Sequence[str],
        action_hints: Sequence[str],
        assertion_hints: Sequence[str],
        base_url_env_var: str,
        base_url_default: str,
        warnings: Sequence[str],
        safe_name: str,
    ) -> str:
        docstring_lines = [
            "Manual QA Playwright script draft only.",
            f"Source test case: {test_case.test_case_id}",
            f"Requirement IDs: {', '.join(test_case.requirement_ids) if test_case.requirement_ids else 'None'}",
            f"Readiness ID: {readiness.readiness_id if readiness is not None else 'N/A'}",
            "Status: Draft only. Not executed / not verified.",
        ]
        if warnings:
            docstring_lines.append(f"Warnings: {'; '.join(warnings)}")

        lines = [
            "import os",
            "from playwright.sync_api import Page, expect",
            "",
            f'BASE_URL = os.getenv("{base_url_env_var}", "{base_url_default}")',
            "",
            "",
            f"def test_{safe_name}(page: Page):",
            '    """',
        ]
        lines.extend(f"    {line}" for line in docstring_lines)
        lines.extend(
            [
                '    """',
                "    # Manual QA Playwright draft only. Not executed by the generator.",
                f"    page.goto({self._page_expression(page_url)})",
            ]
        )
        interaction_lines = self._render_interactions(selector_hints, action_hints)
        lines.extend(f"    {line}" for line in interaction_lines)
        assertion_lines = self._render_assertions(assertion_hints, selector_hints, page_url, test_case)
        lines.extend(f"    {line}" for line in assertion_lines)
        lines.append("")
        return "\n".join(lines)

    def _render_interactions(self, selector_hints: Sequence[str], action_hints: Sequence[str]) -> list[str]:
        if not selector_hints:
            return ['# TODO: add stable selectors before refining Playwright interactions.']

        locator = self._selector_to_locator(selector_hints[0])
        action_sequence: list[str] = []
        for action in self._dedupe(action_hints):
            action_sequence.append(self._action_to_line(locator, action, selector_hints))
        return action_sequence or ['# TODO: refine user action details from the manual test case.']

    def _render_assertions(
        self,
        assertion_hints: Sequence[str],
        selector_hints: Sequence[str],
        page_url: str,
        test_case: ManualTestCase,
    ) -> list[str]:
        text = f"{test_case.expected_result} {' '.join(test_case.steps)}".lower()
        if not assertion_hints:
            return ['# TODO: refine assertion from expected result.']
        if "url contains" in assertion_hints or "redirects" in assertion_hints or "user lands on" in assertion_hints:
            target_url = self._infer_assertion_url(page_url, text)
            return [f"expect(page).to_have_url({target_url})"]
        if any(term in assertion_hints for term in ("should see", "element visible", "visible", "displays")):
            locator = self._selector_to_locator(selector_hints[-1] if selector_hints else "TODO_SELECTOR")
            return [f"expect({locator}).to_be_visible()"]
        if any(term in assertion_hints for term in ("success message", "validation error", "message appears")):
            return ['expect(page.get_by_text("TODO_TEXT")).to_be_visible()']
        return ['# TODO: refine assertion from expected result.']

    def _action_to_line(self, locator: str, action: str, selector_hints: Sequence[str]) -> str:
        action_value = action.lower()
        if action_value in {"fill", "type"}:
            return f'{locator}.fill("TODO_VALUE")'
        if action_value == "select":
            return f'{locator}.select_option("TODO_OPTION")'
        if action_value == "upload":
            return f'{locator}.set_input_files("TODO_FILE")'
        if action_value == "check":
            return f"{locator}.check()"
        if action_value == "uncheck":
            return f"{locator}.uncheck()"
        if action_value == "hover":
            return f"{locator}.hover()"
        if action_value == "submit":
            submit_locator = self._find_submit_locator(selector_hints)
            if submit_locator:
                return f"{submit_locator}.click()"
            return '# TODO: identify the submit control and replace this placeholder action.'
        return f"{locator}.click()"

    def _find_submit_locator(self, selector_hints: Sequence[str]) -> str | None:
        for hint in selector_hints:
            lowered = hint.lower()
            if any(term in lowered for term in ("login", "sign in", "submit", "save")):
                return self._selector_to_locator(hint)
        return None

    def _selector_to_locator(self, hint: str) -> str:
        value = str(hint or "").strip().rstrip(".,;:)")
        lowered = value.lower()
        data_testid_match = re.search(r"data-testid[=\s:\"'-]+([a-z0-9_-]+)", lowered)
        if data_testid_match:
            return f'page.get_by_test_id("{data_testid_match.group(1)}")'
        role_match = re.search(r"role[=\s:\"'-]+([a-z0-9_-]+)(?:.*name[=\s:\"'-]+([a-z0-9 _-]+))?", lowered)
        if role_match:
            role_name = role_match.group(1)
            accessible_name = role_match.group(2)
            if accessible_name:
                return f'page.get_by_role("{role_name}", name="{self._cleanup_text(accessible_name)}")'
            return f'page.get_by_role("{role_name}")'
        button_text_match = re.search(r"button text[=\s:\"'-]+([a-z0-9 _-]+)", lowered)
        if button_text_match:
            return f'page.get_by_role("button", name="{self._cleanup_text(button_text_match.group(1))}")'
        field_label_match = re.search(r"field label[=\s:\"'-]+([a-z0-9 _-]+)", lowered)
        if field_label_match:
            return f'page.get_by_label("{self._cleanup_text(field_label_match.group(1))}")'
        if value.startswith("#"):
            return f'page.locator("{value}")'
        if value.startswith("."):
            return f'page.locator("{value}")'
        if value == "TODO_SELECTOR":
            return 'page.locator("TODO_SELECTOR")'
        return 'page.locator("TODO_SELECTOR")'

    def _detect_page_url(self, test_case: ManualTestCase) -> str | None:
        text = " ".join(
            [
                test_case.title,
                " ".join(test_case.steps),
                " ".join(test_case.preconditions),
                str(test_case.metadata.get("page_url", "")),
            ]
        ).lower()
        full_url = re.search(r"https?://[^\s'\"`]+", text)
        if full_url:
            return full_url.group(0).rstrip(".,;:)")
        route = re.search(r"(?<!api)(/[a-z0-9][a-z0-9/_-]*)", text)
        if route:
            return route.group(1).rstrip(".,;:)")
        return None

    def _detect_selector_hints(self, test_case: ManualTestCase) -> list[str]:
        text = " ".join(
            [
                " ".join(test_case.steps),
                str(test_case.metadata.get("selector_hints", "")),
            ]
        ).lower()
        hints: list[str] = []
        patterns = (
            r"data-testid[=\s:\"'-]+[a-z0-9_-]+",
            r"role[=\s:\"'-]+[a-z0-9_-]+(?:.*name[=\s:\"'-]+[a-z0-9 _-]+)?",
            r"button text[=\s:\"'-]+[a-z0-9 _-]+",
            r"field label[=\s:\"'-]+[a-z0-9 _-]+",
            r"#[a-z0-9_-]+",
            r"\.[a-z0-9_-]+",
        )
        for pattern in patterns:
            for match in re.findall(pattern, text):
                clean = str(match).strip().rstrip(".,;:)")
                if clean and clean not in hints:
                    hints.append(clean)
        return hints

    def _detect_action_hints(self, test_case: ManualTestCase) -> list[str]:
        text = " ".join([test_case.title, " ".join(test_case.steps)]).lower()
        hints: list[str] = []
        for action in self._ACTION_PRIORITY:
            if re.search(rf"\b{re.escape(action)}\b", text):
                hints.append(action)
        return hints

    def _detect_assertion_hints(self, test_case: ManualTestCase) -> list[str]:
        text = f"{test_case.expected_result} {' '.join(test_case.steps)}".lower()
        mapping = (
            "should see",
            "element visible",
            "visible",
            "url contains",
            "redirects",
            "success message",
            "validation error",
            "message appears",
            "user lands on",
            "displays",
        )
        hints: list[str] = []
        for term in mapping:
            if re.search(rf"\b{re.escape(term)}\b", text):
                hints.append(term)
        return hints

    def _infer_assertion_url(self, page_url: str, text: str) -> str:
        route = re.search(r"(/[a-z0-9][a-z0-9/_-]*)", text)
        if route:
            return f'f"{{BASE_URL}}{route.group(1)}"'
        if "dashboard" in text:
            return 'f"{BASE_URL}/dashboard"'
        if page_url and page_url != "/TODO_PAGE_URL":
            return self._page_expression(page_url)
        return 'f"{BASE_URL}/TODO_ASSERTION_URL"'

    def _page_expression(self, page_url: str) -> str:
        if page_url.startswith("http://") or page_url.startswith("https://"):
            return repr(page_url)
        if page_url.startswith("/"):
            return f'f"{{BASE_URL}}{page_url}"'
        return f'f"{{BASE_URL}}/{page_url}"'

    def _contains_login_terms(self, test_case: ManualTestCase) -> bool:
        text = f"{test_case.title} {' '.join(test_case.steps)}".lower()
        return "login" in text or "sign in" in text

    def _looks_web_like(self, test_case: ManualTestCase) -> bool:
        text = " ".join(
            [
                test_case.module,
                test_case.title,
                " ".join(test_case.preconditions),
                " ".join(test_case.steps),
                test_case.expected_result,
            ]
        ).lower()
        return any(term in text for term in self._WEB_TERMS)

    def _safe_test_name(self, test_case: ManualTestCase) -> str:
        base = f"{test_case.test_case_id}_{test_case.title}".lower()
        slug = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
        return slug or "web_playwright_draft"

    def _cleanup_text(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", str(value or "").strip())
        return cleaned.strip(" .,:;").title()

    def _dedupe(self, items: Sequence[str]) -> list[str]:
        values: list[str] = []
        for item in items:
            clean = str(item or "").strip()
            if clean and clean not in values:
                values.append(clean)
        return values

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_WEB_PLAYWRIGHT_SCRIPT_GENERATOR = WebPlaywrightScriptGenerator()


def generate_web_playwright_script_draft(
    test_case: ManualTestCase,
    readiness: WebPlaywrightReadiness | None = None,
    base_url_env_var: str = "WEB_BASE_URL",
    base_url_default: str = "http://localhost:3000",
    metadata: dict | None = None,
) -> WebPlaywrightScriptDraft:
    """Convenience wrapper for generating a single Web Playwright draft."""

    return _DEFAULT_WEB_PLAYWRIGHT_SCRIPT_GENERATOR.generate_web_playwright_script_draft(
        test_case,
        readiness=readiness,
        base_url_env_var=base_url_env_var,
        base_url_default=base_url_default,
        metadata=metadata,
    )


def generate_web_playwright_script_drafts(
    test_cases: Sequence[ManualTestCase],
    readiness_items: Sequence[WebPlaywrightReadiness] | None = None,
    base_url_env_var: str = "WEB_BASE_URL",
    base_url_default: str = "http://localhost:3000",
    metadata: dict | None = None,
) -> list[WebPlaywrightScriptDraft]:
    """Convenience wrapper for generating Web Playwright drafts in input order."""

    return _DEFAULT_WEB_PLAYWRIGHT_SCRIPT_GENERATOR.generate_web_playwright_script_drafts(
        test_cases,
        readiness_items=readiness_items,
        base_url_env_var=base_url_env_var,
        base_url_default=base_url_default,
        metadata=metadata,
    )
