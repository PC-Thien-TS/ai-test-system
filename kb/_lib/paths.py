from __future__ import annotations

from pathlib import Path
from typing import Any

from kb._lib.types import DomainKBConfig, KBConfig


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def kb_root() -> Path:
    return repo_root() / "kb"


def config_path() -> Path:
    return kb_root() / "config.yaml"


def requirements_dir(domain: str) -> Path:
    return repo_root() / "requirements" / domain


def index_dir(domain: str) -> Path:
    return kb_root() / "index" / domain


def domain_dir(domain: str) -> Path:
    return repo_root() / "domains" / domain


def domain_design_dir(domain: str) -> Path:
    return domain_dir(domain) / "design"


def domain_prompts_dir(domain: str) -> Path:
    return domain_dir(domain) / "prompts"


def output_dir(domain: str, run_id: str) -> Path:
    return repo_root() / "outputs" / domain / run_id


def load_kb_config(domain: str) -> KBConfig:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required for KB commands. Install it locally with 'pip install PyYAML'."
        ) from exc

    path = config_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing KB config file: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    defaults = raw.get("defaults") or {}
    domains = raw.get("domains") or {}
    overrides = domains.get(domain) or {}

    def pick(name: str, fallback: Any = None) -> Any:
        return overrides.get(name, defaults.get(name, fallback))

    domain_cfg = DomainKBConfig(
        top_k_per_step={str(key): int(value) for key, value in (overrides.get("top_k_per_step") or {}).items()},
        step_queries={
            str(key): [str(item) for item in value]
            for key, value in (overrides.get("step_queries") or {}).items()
        },
    )
    return KBConfig(
        embedding_model_name=str(pick("embedding_model_name")),
        embedding_local_path=pick("embedding_local_path"),
        local_files_only=bool(pick("local_files_only", True)),
        chunk_size_chars=int(pick("chunk_size_chars", 1200)),
        chunk_overlap_chars=int(pick("chunk_overlap_chars", 200)),
        index_backend=str(pick("index_backend", "auto")),
        default_top_k=int(pick("default_top_k", 6)),
        max_pack_chars=int(pick("max_pack_chars", 8000)),
        domain=domain_cfg,
    )
