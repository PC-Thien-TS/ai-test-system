from __future__ import annotations


_FILE_FLOW_RULES: tuple[tuple[str, str], ...] = (
{{FILE_FLOW_RULES}}
)


def map_changed_files_to_flows(files: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for file_path in files:
        normalized = file_path.replace("\\", "/").lower()
        for token, flow_id in _FILE_FLOW_RULES:
            if token not in normalized:
                continue
            result.setdefault(flow_id, []).append(file_path)
    return result

