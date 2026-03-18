from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ATTRIBUTE_RE = re.compile(r"\[(?P<name>\w+)(?:\((?P<args>.*?)\))?\]")
CLASS_RE = re.compile(r"\bclass\s+(?P<name>\w+Controller)\b")
METHOD_RE = re.compile(
    r"^\s*(?:public|protected|internal)(?:\s+\w+)*\s+.+?\s+(?P<name>\w+)\s*\(",
)
CONTROLLER_NAME_RE = re.compile(r"ControllerName\(\s*@?\"([^\"]+)\"", re.IGNORECASE)
ROUTE_RE = re.compile(r"Route\(\s*@?\"([^\"]+)\"", re.IGNORECASE)
STRING_LITERAL_RE = re.compile(r"@?\"([^\"]*)\"")
HTTP_METHODS = {
    "HttpGet": "GET",
    "HttpPost": "POST",
    "HttpPut": "PUT",
    "HttpDelete": "DELETE",
    "HttpPatch": "PATCH",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract best-effort .NET API endpoint evidence.")
    parser.add_argument("--repo", required=True, help="Local .NET repository root.")
    parser.add_argument("--glob", required=True, help="Glob for controller files relative to the repo root.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = extract_dotnet_api(Path(args.repo), args.glob)
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Dotnet endpoints written: {out_path}")
    return 0


def extract_dotnet_api(repo_root: Path, glob_pattern: str) -> dict[str, object]:
    repo = repo_root.expanduser().resolve()
    controller_files = [path for path in repo.glob(glob_pattern) if path.is_file()] if repo.exists() else []

    endpoints: list[dict[str, str]] = []
    controllers: set[str] = set()
    files_with_endpoints = 0
    for file_path in controller_files:
        file_endpoints = parse_controller_file(file_path)
        if file_endpoints:
            files_with_endpoints += 1
        endpoints.extend(file_endpoints)
        controllers.update(endpoint["controller"] for endpoint in file_endpoints)

    method_counts: dict[str, int] = {}
    anonymous_endpoints = 0
    for endpoint in endpoints:
        method = endpoint["http_method"]
        method_counts[method] = method_counts.get(method, 0) + 1
        if endpoint["auth"] == "anonymous":
            anonymous_endpoints += 1

    return {
        "summary": {
            "repo": str(repo),
            "glob": glob_pattern,
            "scanned_files": len(controller_files),
            "files_with_endpoints": files_with_endpoints,
            "controllers": len(controllers),
            "endpoints": len(endpoints),
            "anonymous_endpoints": anonymous_endpoints,
            "methods": method_counts,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "endpoints": endpoints,
    }


def parse_controller_file(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    pending_attrs: list[str] = []
    class_attrs: list[str] = []
    controller_name = ""
    base_route = ""
    endpoints: list[dict[str, str]] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            pending_attrs.append(stripped)
            continue

        class_match = CLASS_RE.search(line)
        if class_match:
            class_attrs = pending_attrs[:]
            pending_attrs.clear()
            controller_name = extract_controller_name(class_attrs, class_match.group("name"))
            base_route = extract_base_route(class_attrs, controller_name)
            continue

        if not controller_name:
            pending_attrs.clear()
            continue

        method_match = METHOD_RE.match(line)
        if method_match:
            method_attrs = pending_attrs[:]
            pending_attrs.clear()
            endpoint = build_endpoint(
                controller_name=controller_name,
                base_route=base_route,
                class_attrs=class_attrs,
                method_attrs=method_attrs,
                signature=line,
                action_name=method_match.group("name"),
            )
            if endpoint is not None:
                endpoints.append(endpoint)
            continue

        if stripped and not stripped.startswith("//"):
            pending_attrs.clear()

    return endpoints


def build_endpoint(
    *,
    controller_name: str,
    base_route: str,
    class_attrs: list[str],
    method_attrs: list[str],
    signature: str,
    action_name: str,
) -> dict[str, str] | None:
    http_attr = find_http_attribute(method_attrs)
    if http_attr is None:
        return None

    http_method = HTTP_METHODS[http_attr["name"]]
    method_template = extract_route_template(method_attrs) or extract_first_string(http_attr["raw"])
    route = compose_route(base_route, controller_name, action_name, method_template)
    auth = resolve_auth(class_attrs, method_attrs)
    binding = resolve_binding(method_attrs, signature, http_method)

    return {
        "controller": controller_name,
        "action": action_name,
        "http_method": http_method,
        "route": route,
        "auth": auth,
        "binding": binding,
        "raw": http_attr["raw"],
    }


def extract_controller_name(class_attrs: list[str], class_name: str) -> str:
    joined = " ".join(class_attrs)
    match = CONTROLLER_NAME_RE.search(joined)
    if match:
        return match.group(1).strip().lower()
    return class_name.removesuffix("Controller").lower()


def extract_base_route(class_attrs: list[str], controller_name: str) -> str:
    template = extract_route_template(class_attrs)
    if template:
        return normalize_route(template, controller_name, "[action]")
    return f"/{controller_name}"


def extract_route_template(attrs: list[str]) -> str | None:
    joined = " ".join(attrs)
    match = ROUTE_RE.search(joined)
    if match:
        return match.group(1).strip()
    return None


def find_http_attribute(attrs: list[str]) -> dict[str, str] | None:
    for raw in attrs:
        for match in ATTRIBUTE_RE.finditer(raw):
            name = match.group("name")
            if name in HTTP_METHODS:
                return {"name": name, "raw": raw}
    return None


def extract_first_string(text: str) -> str | None:
    match = STRING_LITERAL_RE.search(text)
    if match:
        return match.group(1)
    return None


def resolve_auth(class_attrs: list[str], method_attrs: list[str]) -> str:
    joined_method = " ".join(method_attrs)
    joined_class = " ".join(class_attrs)
    if "AllowAnonymous" in joined_method:
        return "anonymous"
    if "Authorize" in joined_method:
        return "authorized"
    if "AllowAnonymous" in joined_class:
        return "anonymous"
    if "Authorize" in joined_class:
        return "authorized"
    return "inherit"


def resolve_binding(method_attrs: list[str], signature: str, http_method: str) -> str:
    joined = " ".join(method_attrs) + " " + signature
    if "[FromQuery]" in joined:
        return "query"
    if "[FromBody]" in joined:
        return "body"
    if "[FromForm]" in joined:
        return "form"
    if http_method in {"GET", "DELETE"}:
        return "query"
    if http_method in {"POST", "PUT", "PATCH"}:
        return "body"
    return "unknown"


def compose_route(
    base_route: str,
    controller_name: str,
    action_name: str,
    method_template: str | None,
) -> str:
    normalized_base = normalize_route(base_route or f"/{controller_name}", controller_name, action_name)
    if method_template is None or method_template == "":
        return normalized_base
    if method_template.startswith("/"):
        return normalize_route(method_template, controller_name, action_name)
    route = f"{normalized_base.rstrip('/')}/{method_template.lstrip('/')}"
    return normalize_route(route, controller_name, action_name)


def normalize_route(route: str, controller_name: str, action_name: str) -> str:
    normalized = route.replace("[controller]", controller_name).replace("[action]", action_name)
    normalized = normalized.replace("//", "/").strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized


if __name__ == "__main__":
    raise SystemExit(main())
