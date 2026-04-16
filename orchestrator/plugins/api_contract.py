"""API Contract Testing plugin for API validation with real execution."""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from jsonschema import validate, ValidationError as JsonSchemaValidationError

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    BasePlugin,
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)


class ApiContractPlugin(BasePlugin):
    """API Contract Testing plugin with real execution using requests + jsonschema."""
    
    def __init__(self):
        super().__init__()
        self._session: Optional[requests.Session] = None
        self._auth_token: Optional[str] = None
    
    @property
    def name(self) -> str:
        return "api_contract"
    
    @property
    def version(self) -> str:
        return "3.0.0"
    
    @property
    def supported_product_types(self) -> List[str]:
        return [ProductType.API.value]
    
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
        Initialize requests session with auth token.
        
        Args:
            context: Execution context.
            
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            self._session = requests.Session()
            
            # Set auth token if provided
            auth_token = context.config.get("auth_token")
            if auth_token:
                self._auth_token = auth_token
                self._session.headers.update({
                    "Authorization": f"Bearer {auth_token}"
                })
            
            # Set default headers
            self._session.headers.update({
                "Content-Type": "application/json",
                "Accept": "application/json",
            })
            
            # Set timeout from config
            timeout = context.config.get("timeout", 30)
            self._session.timeout = timeout
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"API Contract plugin initialization error: {e}")
            return False
    
    async def execute(self, context: ExecutionContext) -> PluginExecutionResult:
        """
        Execute API contract tests based on execution path.
        
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
            # Get base URL from config
            base_url = context.config.get("base_url", "http://localhost:8000")
            
            # Get test endpoints based on execution path
            endpoints = self._get_test_endpoints(context.execution_path, context.config)
            
            evidence_items = []
            assertions_passed = 0
            assertions_failed = 0
            total_latency = 0.0
            schema_validations_passed = 0
            schema_validations_failed = 0
            
            for endpoint_config in endpoints:
                endpoint_evidence = await self._test_endpoint(
                    context,
                    base_url,
                    endpoint_config,
                )
                evidence_items.extend(endpoint_evidence["evidence"])
                assertions_passed += endpoint_evidence["assertions_passed"]
                assertions_failed += endpoint_evidence["assertions_failed"]
                total_latency += endpoint_evidence["latency"]
                schema_validations_passed += endpoint_evidence["schema_validations_passed"]
                schema_validations_failed += endpoint_evidence["schema_validations_failed"]
            
            # Determine success
            success = assertions_failed == 0
            
            result.success = success
            result.status = ExecutionStatus.COMPLETED
            result.evidence = evidence_items
            result.metrics = {
                "assertions_passed": assertions_passed,
                "assertions_failed": assertions_failed,
                "total_assertions": assertions_passed + assertions_failed,
                "endpoints_tested": len(endpoints),
                "avg_latency_ms": (total_latency / len(endpoints)) if endpoints else 0,
                "schema_validations_passed": schema_validations_passed,
                "schema_validations_failed": schema_validations_failed,
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
        Clean up requests session.
        
        Args:
            context: Execution context.
            
        Returns:
            True if cleanup successful, False otherwise.
        """
        try:
            if self._session:
                self._session.close()
                self._session = None
            self._auth_token = None
            return True
        except Exception as e:
            print(f"API Contract plugin cleanup error: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate API Contract plugin configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []
        
        if "base_url" not in config:
            errors.append("Missing required field: base_url")
        
        timeout = config.get("timeout")
        if timeout is not None and (not isinstance(timeout, (int, float)) or timeout <= 0):
            errors.append("Invalid timeout: must be a positive number")
        
        retry_count = config.get("retry_count", 0)
        if not isinstance(retry_count, int) or retry_count < 0:
            errors.append("Invalid retry_count: must be a non-negative integer")
        
        return (len(errors) == 0, errors)
    
    def _get_test_endpoints(self, execution_path: ExecutionPath, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get test endpoints based on execution path.
        
        Args:
            execution_path: The execution path.
            config: Plugin configuration.
            
        Returns:
            List of endpoint configurations.
        """
        endpoints_config = config.get("endpoints", {})
        
        if execution_path == ExecutionPath.SMOKE:
            return endpoints_config.get("smoke", [
                {"path": "/health", "method": "GET", "expected_status": 200},
            ])
        elif execution_path == ExecutionPath.STANDARD:
            return endpoints_config.get("standard", [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "POST", "expected_status": 201, "body": {"name": "test"}},
            ])
        elif execution_path == ExecutionPath.DEEP:
            return endpoints_config.get("deep", [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "POST", "expected_status": 201, "body": {"name": "test"}},
                {"path": "/api/users/1", "method": "GET", "expected_status": 200},
                {"path": "/api/users/1", "method": "PUT", "expected_status": 200, "body": {"name": "updated"}},
                {"path": "/api/users/1", "method": "DELETE", "expected_status": 204},
                {"path": "/api/users/999", "method": "GET", "expected_status": 404},  # Negative case
            ])
        elif execution_path == ExecutionPath.INTELLIGENT:
            return endpoints_config.get("intelligent", [
                {"path": "/health", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "GET", "expected_status": 200},
                {"path": "/api/users", "method": "POST", "expected_status": 201, "body": {"name": "test"}},
                {"path": "/api/users/1", "method": "GET", "expected_status": 200},
                {"path": "/api/users/1", "method": "PUT", "expected_status": 200, "body": {"name": "updated"}},
                {"path": "/api/users/1", "method": "DELETE", "expected_status": 204},
                {"path": "/api/users/999", "method": "GET", "expected_status": 404},
                {"path": "/api/users", "method": "POST", "expected_status": 400, "body": {}},  # Edge payload
                {"path": "/api/users", "method": "POST", "expected_status": 401},  # Auth failure
            ])
        
        return []
    
    async def _test_endpoint(
        self,
        context: ExecutionContext,
        base_url: str,
        endpoint_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Test a single endpoint and collect evidence.
        
        Args:
            context: Execution context.
            base_url: Base URL for the API.
            endpoint_config: Endpoint configuration.
            
        Returns:
            Dictionary with evidence, assertions, latency, and schema validation results.
        """
        path = endpoint_config.get("path", "/")
        method = endpoint_config.get("method", "GET")
        expected_status = endpoint_config.get("expected_status", 200)
        body = endpoint_config.get("body")
        schema = endpoint_config.get("schema")
        headers = endpoint_config.get("headers", {})
        
        url = urljoin(base_url, path)
        evidence_items = []
        assertions_passed = 0
        assertions_failed = 0
        schema_validations_passed = 0
        schema_validations_failed = 0
        
        start_time = time.time()
        
        try:
            # Make request with retry logic
            response = await self._make_request_with_retry(
                method=method,
                url=url,
                body=body,
                headers=headers,
                context=context,
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Collect request/response trace evidence
            evidence_items.append(EvidenceItem(
                evidence_type=EvidenceType.TRACE,
                content={
                    "url": url,
                    "method": method,
                    "request_body": body,
                    "request_headers": headers,
                    "status_code": response.status_code,
                    "response_headers": dict(response.headers),
                    "response_body": self._safe_json_parse(response.text),
                    "latency_ms": latency_ms,
                },
                severity="info",
                source="api_contract",
            ))
            
            # Collect latency metric
            evidence_items.append(EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "endpoint": path,
                    "method": method,
                    "latency_ms": latency_ms,
                    "status_code": response.status_code,
                },
                severity="info",
                source="api_contract",
            ))
            
            # Status code assertion
            if response.status_code == expected_status:
                assertions_passed += 1
            else:
                assertions_failed += 1
                evidence_items.append(EvidenceItem(
                    evidence_type=EvidenceType.ASSERTION,
                    content={
                        "assertion": "status_code",
                        "expected": expected_status,
                        "actual": response.status_code,
                        "passed": False,
                    },
                    severity="high",
                    source="api_contract",
                ))
            
            # Schema validation if schema provided
            if schema and response.status_code in [200, 201]:
                try:
                    response_json = response.json()
                    validate(instance=response_json, schema=schema)
                    schema_validations_passed += 1
                    assertions_passed += 1
                except JsonSchemaValidationError as e:
                    schema_validations_failed += 1
                    assertions_failed += 1
                    evidence_items.append(EvidenceItem(
                        evidence_type=EvidenceType.ASSERTION,
                        content={
                            "assertion": "schema_validation",
                            "error": str(e),
                            "path": e.path,
                            "validator": e.validator,
                            "passed": False,
                        },
                        severity="high",
                        source="api_contract",
                    ))
        
        except requests.exceptions.Timeout:
            latency_ms = (time.time() - start_time) * 1000
            assertions_failed += 1
            evidence_items.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "request_timeout",
                    "url": url,
                    "method": method,
                    "latency_ms": latency_ms,
                    "passed": False,
                },
                severity="critical",
                source="api_contract",
            ))
        
        except requests.exceptions.ConnectionError as e:
            latency_ms = (time.time() - start_time) * 1000
            assertions_failed += 1
            evidence_items.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "connection_error",
                    "url": url,
                    "method": method,
                    "error": str(e),
                    "latency_ms": latency_ms,
                    "passed": False,
                },
                severity="critical",
                source="api_contract",
            ))
        
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            assertions_failed += 1
            evidence_items.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "unexpected_error",
                    "url": url,
                    "method": method,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "latency_ms": latency_ms,
                    "passed": False,
                },
                severity="critical",
                source="api_contract",
            ))
        
        return {
            "evidence": evidence_items,
            "assertions_passed": assertions_passed,
            "assertions_failed": assertions_failed,
            "latency": latency_ms,
            "schema_validations_passed": schema_validations_passed,
            "schema_validations_failed": schema_validations_failed,
        }
    
    async def _make_request_with_retry(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]],
        headers: Dict[str, str],
        context: ExecutionContext,
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method.
            url: Request URL.
            body: Request body.
            headers: Request headers.
            context: Execution context.
            
        Returns:
            Response object.
        """
        retry_count = context.config.get("retry_count", 0)
        retry_delay = context.config.get("retry_delay", 1.0)
        
        for attempt in range(retry_count + 1):
            try:
                if method == "GET":
                    response = self._session.get(url, headers=headers)
                elif method == "POST":
                    response = self._session.post(url, json=body, headers=headers)
                elif method == "PUT":
                    response = self._session.put(url, json=body, headers=headers)
                elif method == "DELETE":
                    response = self._session.delete(url, headers=headers)
                elif method == "PATCH":
                    response = self._session.patch(url, json=body, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                return response
            
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < retry_count:
                    await asyncio.sleep(retry_delay)
                    continue
                raise
        
        raise Exception("Max retries exceeded")
    
    def _safe_json_parse(self, text: str) -> Any:
        """
        Safely parse JSON text.
        
        Args:
            text: JSON text to parse.
            
        Returns:
            Parsed JSON or original text if parsing fails.
        """
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text
