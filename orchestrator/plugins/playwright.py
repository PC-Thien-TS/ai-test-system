"""Playwright plugin for web UI testing with real execution."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    BasePlugin,
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)


class PlaywrightPlugin(BasePlugin):
    """Playwright-based web UI testing plugin with real execution."""
    
    def __init__(self):
        super().__init__()
        self._browser = None
        self._context = None
        self._page = None
        self._playwright = None
    
    @property
    def name(self) -> str:
        return "web_playwright"
    
    @property
    def version(self) -> str:
        return "3.0.0"
    
    @property
    def supported_product_types(self) -> List[str]:
        return [ProductType.WEB.value]
    
    @property
    def supported_execution_paths(self) -> List[ExecutionPath]:
        return [
            ExecutionPath.SMOKE,
            ExecutionPath.STANDARD,
            ExecutionPath.DEEP,
            ExecutionPath.INTELLIGENT,
        ]
    
    async def initialize(self, context: ExecutionContext) -> bool:
        """
        Initialize Playwright browser context.
        
        Args:
            context: Execution context.
            
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            from playwright.async_api import async_playwright
            
            self._playwright = await async_playwright().start()
            
            # Get browser type from config
            browser_type = context.config.get("browser_type", "chromium")
            headless = context.config.get("headless", True)
            
            browser = getattr(self._playwright, browser_type, self._playwright.chromium)
            self._browser = await browser.launch(headless=headless)
            
            # Create context with options
            context_options = {
                "viewport": context.config.get("viewport", {"width": 1280, "height": 720}),
                "ignore_https_errors": context.config.get("ignore_https_errors", True),
                "user_agent": context.config.get("user_agent"),
            }
            context_options = {k: v for k, v in context_options.items() if v is not None}
            
            self._context = await self._browser.new_context(**context_options)
            
            # Create page
            self._page = await self._context.new_page()
            
            # Set up console logging
            console_messages = []
            self._page.on("console", lambda msg: console_messages.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location,
            }))
            
            # Set up network logging
            network_requests = []
            self._page.on("request", lambda request: network_requests.append({
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
            }))
            
            # Store for evidence collection
            context.metadata["_console_messages"] = console_messages
            context.metadata["_network_requests"] = network_requests
            
            self._initialized = True
            return True
            
        except ImportError:
            return False
        except Exception as e:
            print(f"Playwright initialization error: {e}")
            return False
    
    async def execute(self, context: ExecutionContext) -> PluginExecutionResult:
        """
        Execute Playwright tests based on execution path.
        
        Args:
            context: Execution context.
            
        Returns:
            PluginExecutionResult with evidence and metrics.
        """
        result = PluginExecutionResult(
            plugin_name=self.name,
            status=ExecutionStatus.RUNNING,
            success=False,
        )
        
        try:
            # Get test URL from config
            base_url = context.config.get("base_url", "http://localhost:3000")
            test_paths = self._get_test_paths(context.execution_path, context.config)
            
            evidence_items = []
            assertions_passed = 0
            assertions_failed = 0
            
            for test_path in test_paths:
                url = f"{base_url}{test_path}"
                
                # Navigate to URL
                start_time = datetime.utcnow()
                await self._page.goto(url, wait_until="networkidle")
                load_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Collect evidence based on execution path depth
                path_evidence = await self._collect_page_evidence(
                    context,
                    url,
                    load_time,
                    test_path,
                )
                evidence_items.extend(path_evidence)
                
                # Run assertions
                passed, failed = await self._run_assertions(context, test_path)
                assertions_passed += passed
                assertions_failed += failed
            
            # Collect console and network evidence
            console_evidence = await self._collect_console_evidence(context)
            evidence_items.extend(console_evidence)
            
            network_evidence = await self._collect_network_evidence(context)
            evidence_items.extend(network_evidence)
            
            # Determine success
            success = assertions_failed == 0
            
            result.success = success
            result.status = ExecutionStatus.COMPLETED
            result.evidence = evidence_items
            result.metrics = {
                "assertions_passed": assertions_passed,
                "assertions_failed": assertions_failed,
                "total_assertions": assertions_passed + assertions_failed,
                "pages_tested": len(test_paths),
                "avg_load_time": sum(e.content.get("load_time", 0) for e in evidence_items if e.evidence_type == EvidenceType.METRIC) / len(test_paths) if test_paths else 0,
            }
            
            if not success:
                result.error_message = f"{assertions_failed} assertions failed"
                result.error_details = {"failed_assertions": assertions_failed}
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.success = False
            result.error_message = str(e)
            result.error_details = {"exception_type": type(e).__name__}
        
        return result
    
    async def cleanup(self, context: ExecutionContext) -> bool:
        """
        Clean up Playwright resources.
        
        Args:
            context: Execution context.
            
        Returns:
            True if cleanup successful, False otherwise.
        """
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            return True
        except Exception as e:
            print(f"Playwright cleanup error: {e}")
            return False
    
    async def validate_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate Playwright plugin configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []
        
        if "base_url" not in config:
            errors.append("Missing required field: base_url")
        
        browser_type = config.get("browser_type", "chromium")
        if browser_type not in ["chromium", "firefox", "webkit"]:
            errors.append(f"Invalid browser_type: {browser_type}. Must be chromium, firefox, or webkit")
        
        return (len(errors) == 0, errors)
    
    def _get_test_paths(self, execution_path: ExecutionPath, config: Dict[str, Any]) -> List[str]:
        """
        Get test paths based on execution path.
        
        Args:
            execution_path: The execution path.
            config: Plugin configuration.
            
        Returns:
            List of test paths to visit.
        """
        default_paths = ["/"]
        
        path_config = config.get("test_paths", {})
        
        if execution_path == ExecutionPath.SMOKE:
            return path_config.get("smoke", default_paths)
        elif execution_path == ExecutionPath.STANDARD:
            return path_config.get("standard", ["/", "/about", "/contact"])
        elif execution_path == ExecutionPath.DEEP:
            return path_config.get("deep", ["/", "/about", "/contact", "/products", "/pricing"])
        elif execution_path == ExecutionPath.INTELLIGENT:
            return path_config.get("intelligent", ["/", "/about", "/contact", "/products", "/pricing", "/dashboard", "/settings"])
        
        return default_paths
    
    async def _collect_page_evidence(
        self,
        context: ExecutionContext,
        url: str,
        load_time: float,
        test_path: str,
    ) -> List[EvidenceItem]:
        """
        Collect evidence from a page.
        
        Args:
            context: Execution context.
            url: The page URL.
            load_time: Page load time in seconds.
            test_path: The test path.
            
        Returns:
            List of evidence items.
        """
        evidence = []
        output_path = context.output_path
        
        # Take screenshot
        screenshot_path = output_path / "screenshots"
        screenshot_path.mkdir(parents=True, exist_ok=True)
        screenshot_file = screenshot_path / f"{test_path.replace('/', '_')}.png"
        
        await self._page.screenshot(path=str(screenshot_file))
        
        evidence.append(EvidenceItem(
            evidence_type=EvidenceType.SCREENSHOT,
            content={
                "path": str(screenshot_file),
                "url": url,
                "test_path": test_path,
                "viewport": {"width": 1280, "height": 720},
            },
            severity="info",
            source="playwright",
        ))
        
        # Collect page metrics
        metrics = await self._page.evaluate("""() => {
            return {
                title: document.title,
                url: window.location.href,
                dom_elements: document.querySelectorAll('*').length,
                scripts: document.querySelectorAll('script').length,
                stylesheets: document.querySelectorAll('link[rel="stylesheet"]').length,
                images: document.querySelectorAll('img').length,
                links: document.querySelectorAll('a').length,
            }
        }""")
        
        evidence.append(EvidenceItem(
            evidence_type=EvidenceType.METRIC,
            content={
                "url": url,
                "test_path": test_path,
                "load_time": load_time,
                "dom_elements": metrics["dom_elements"],
                "scripts": metrics["scripts"],
                "stylesheets": metrics["stylesheets"],
                "images": metrics["images"],
                "links": metrics["links"],
                "title": metrics["title"],
            },
            severity="info",
            source="playwright",
        ))
        
        return evidence
    
    async def _run_assertions(
        self,
        context: ExecutionContext,
        test_path: str,
    ) -> tuple[int, int]:
        """
        Run assertions for a test path.
        
        Args:
            context: Execution context.
            test_path: The test path.
            
        Returns:
            Tuple of (passed_count, failed_count).
        """
        passed = 0
        failed = 0
        
        # Default assertions
        try:
            # Check for HTTP errors
            response = await self._page.evaluate("""() => {
                return performance.getEntriesByType('navigation')[0].responseStatus;
            }""")
            
            if response and response >= 400:
                failed += 1
            else:
                passed += 1
                
        except Exception:
            failed += 1
        
        # Check page title
        try:
            title = await self._page.title()
            if title and len(title) > 0:
                passed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        
        # Check for JavaScript errors
        console_messages = context.metadata.get("_console_messages", [])
        js_errors = [msg for msg in console_messages if msg["type"] == "error"]
        
        if len(js_errors) == 0:
            passed += 1
        else:
            failed += 1
        
        return passed, failed
    
    async def _collect_console_evidence(self, context: ExecutionContext) -> List[EvidenceItem]:
        """
        Collect console log evidence.
        
        Args:
            context: Execution context.
            
        Returns:
            List of evidence items.
        """
        evidence = []
        console_messages = context.metadata.get("_console_messages", [])
        
        for msg in console_messages:
            severity = "critical" if msg["type"] == "error" else "info"
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.CONSOLE_LOG,
                content={
                    "type": msg["type"],
                    "text": msg["text"],
                    "location": msg["location"],
                },
                severity=severity,
                source="playwright",
            ))
        
        return evidence
    
    async def _collect_network_evidence(self, context: ExecutionContext) -> List[EvidenceItem]:
        """
        Collect network request evidence.
        
        Args:
            context: Execution context.
            
        Returns:
            List of evidence items.
        """
        evidence = []
        network_requests = context.metadata.get("_network_requests", [])
        
        for req in network_requests:
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.NETWORK_LOG,
                content={
                    "url": req["url"],
                    "method": req["method"],
                    "resource_type": req["resource_type"],
                },
                severity="info",
                source="playwright",
            ))
        
        return evidence
