from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


# =========================
# Interfaces (extensible)
# =========================

class LLMClient(Protocol):
    """LLM adapter interface. You can plug OpenAI, Azure OpenAI, Gemini, local LLM, etc."""
    def complete(self, *, system: str, user: str, temperature: float = 0.2) -> str:
        ...


class Storage(Protocol):
    """Storage interface: local filesystem, S3, GDrive, etc."""
    def read_text(self, path: Path) -> str:
        ...

    def write_text(self, path: Path, content: str) -> None:
        ...

    def write_json(self, path: Path, data: Any) -> None:
        ...


@dataclass
class FileStorage:
    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# =========================
# Context & Step model
# =========================

@dataclass
class RunContext:
    run_id: str
    root: Path
    domain: str
    domain_dir: Path
    output_dir: Path
    artifacts: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.artifacts[key] = value


class Step(Protocol):
    name: str

    def run(self, ctx: RunContext, *, llm: Optional[LLMClient], storage: Storage) -> None:
        ...


@dataclass
class PromptStep:
    """
    Generic step:
    - read prompt template
    - build system/user messages
    - call llm
    - parse output as json/markdown/text
    """
    name: str
    prompt_path: Path
    system: str
    temperature: float = 0.2
    # where to save output artifact
    out_key: str = ""
    out_format: str = "json"  # json | md | text
    # context variables to inject into prompt
    inject: Dict[str, str] = field(default_factory=dict)

    def _render(self, template: str, variables: Dict[str, str]) -> str:
        # tiny templating: {{var}}
        out = template
        for k, v in variables.items():
            out = out.replace("{{" + k + "}}", v)
        return out

    def run(self, ctx: RunContext, *, llm: Optional[LLMClient], storage: Storage) -> None:
        if llm is None:
            raise RuntimeError(f"Step '{self.name}' requires llm client, but llm=None")

        tpl = storage.read_text(self.prompt_path)

        # prepare variables from ctx artifacts + inject
        vars_: Dict[str, str] = {}
        for k, v in self.inject.items():
            # v can refer to ctx artifact via special syntax: @artifact:key
            if v.startswith("@artifact:"):
                art_key = v.split(":", 1)[1]
                vars_[k] = json.dumps(ctx.get(art_key), ensure_ascii=False, indent=2)
            elif v.startswith("@file:"):
                rel = v.split(":", 1)[1]
                vars_[k] = storage.read_text(ctx.domain_dir / rel)
            else:
                vars_[k] = v

        user_msg = self._render(tpl, vars_)

        started = time.time()
        raw = llm.complete(system=self.system, user=user_msg, temperature=self.temperature)
        elapsed = round(time.time() - started, 3)

        ctx.meta.setdefault("timings", {})[self.name] = elapsed

        # parse output
        if self.out_format == "json":
            try:
                data = json.loads(strip_fenced_block(raw))
            except Exception as e:
                # Save raw for debugging
                storage.write_text(ctx.output_dir / f"debug_{self.name}.txt", raw)
                raise RuntimeError(f"JSON parse failed in step '{self.name}': {e}") from e
            ctx.set(self.out_key, data)
        elif self.out_format in ("md", "text"):
            ctx.set(self.out_key, raw)
        else:
            raise ValueError(f"Unknown out_format: {self.out_format}")


@dataclass
class SaveArtifactStep:
    """Save selected artifacts to output files."""
    name: str
    mappings: List[Dict[str, str]]  # [{"key":"testcases","path":"02_testcases.json","format":"json"}]

    def run(self, ctx: RunContext, *, llm: Optional[LLMClient], storage: Storage) -> None:
        for m in self.mappings:
            key = m["key"]
            rel_path = m["path"]
            fmt = m.get("format", "json")
            val = ctx.get(key)

            if fmt == "json":
                storage.write_json(ctx.output_dir / rel_path, val)
            else:
                storage.write_text(ctx.output_dir / rel_path, "" if val is None else str(val))


# =========================
# Orchestrator
# =========================

@dataclass
class Orchestrator:
    root: Path
    storage: Storage = field(default_factory=FileStorage)

    def _make_run_id(self) -> str:
        return time.strftime("%Y%m%d_%H%M%S")

    def load_domain(self, domain: str) -> Path:
        domain_dir = self.root / "domains" / domain
        if not domain_dir.exists():
            raise FileNotFoundError(f"Domain '{domain}' not found at: {domain_dir}")
        return domain_dir

    def build_order_state_machine_pipeline(self, domain_dir: Path) -> List[Step]:
        """
        STATE-MACHINE-FIRST pipeline (recommended for order):
        1) Extract state machine + transitions (from design docs)
        2) Build rule matrix (allowed transitions)
        3) Generate testcases based on matrix + API contract + rules
        4) Review & refine testcases
        5) Build regression suite
        6) Release checklist
        7) Save outputs
        """

        p = domain_dir / "prompts"
        design = domain_dir / "design"

        steps: List[Step] = [
            PromptStep(
                name="01_extract_state_machine",
                prompt_path=p / "01_extract_state_machine.md",
                system="You are a careful QA/BA. Output ONLY valid JSON.",
                out_key="state_machine",
                out_format="json",
                inject={
                    "STATE_MACHINE_DOC": "@file:design/state_machine.md",
                    "API_CONTRACT_DOC": "@file:design/api_contract.md",
                    "RULES_DOC": "@file:design/rules.md",
                },
            ),
            PromptStep(
                name="02_build_rule_matrix",
                prompt_path=p / "02_build_rule_matrix.md",
                system="You are a strict QA. Output ONLY valid JSON.",
                out_key="rule_matrix",
                out_format="json",
                inject={"STATE_MACHINE_JSON": "@artifact:state_machine"},
            ),
            PromptStep(
                name="03_generate_testcases",
                prompt_path=p / "03_generate_testcases.md",
                system="You are a senior QA. Output ONLY valid JSON.",
                out_key="testcases",
                out_format="json",
                inject={
                    "STATE_MACHINE_JSON": "@artifact:state_machine",
                    "RULE_MATRIX_JSON": "@artifact:rule_matrix",
                    "API_CONTRACT_DOC": "@file:design/api_contract.md",
                    "RULES_DOC": "@file:design/rules.md",
                    "KB_GLOSSARY": "@file:knowledge_base/glossary.md",
                    "KB_COMMON_RULES": "@file:knowledge_base/common_rules.md",
                    "KB_BUG_PATTERNS": "@file:knowledge_base/bug_patterns.md",
                },
            ),
            PromptStep(
                name="04_review_refine",
                prompt_path=p / "04_review_refine.md",
                system="You are a QA reviewer. Output ONLY valid JSON.",
                out_key="testcases_refined",
                out_format="json",
                inject={"TESTCASES_JSON": "@artifact:testcases"},
            ),
            PromptStep(
                name="05_build_regression",
                prompt_path=p / "05_build_regression.md",
                system="You are a QA lead. Output ONLY valid JSON.",
                out_key="regression_suite",
                out_format="json",
                inject={"TESTCASES_REFINED_JSON": "@artifact:testcases_refined"},
            ),
            PromptStep(
                name="06_release_checklist",
                prompt_path=p / "06_release_checklist.md",
                system="You are a QA lead. Output ONLY Markdown.",
                out_key="release_checklist",
                out_format="md",
                inject={
                    "STATE_MACHINE_JSON": "@artifact:state_machine",
                    "REGRESSION_JSON": "@artifact:regression_suite",
                    "TESTCASES_REFINED_JSON": "@artifact:testcases_refined",
                },
            ),
            SaveArtifactStep(
                name="99_save_outputs",
                mappings=[
                    {"key": "state_machine", "path": "01_state_machine.json", "format": "json"},
                    {"key": "rule_matrix", "path": "02_rule_matrix.json", "format": "json"},
                    {"key": "testcases", "path": "03_testcases_raw.json", "format": "json"},
                    {"key": "testcases_refined", "path": "04_testcases_refined.json", "format": "json"},
                    {"key": "regression_suite", "path": "05_regression_suite.json", "format": "json"},
                    {"key": "release_checklist", "path": "06_release_checklist.md", "format": "text"},
                    {"key": "meta", "path": "run_meta.json", "format": "json"},
                ],
            ),
        ]
        return steps

    def run(self, *, domain: str, llm: Optional[LLMClient] = None, output_base: Optional[Path] = None) -> RunContext:
        domain_dir = self.load_domain(domain)
        run_id = self._make_run_id()

        out_root = output_base or (self.root / "outputs")
        output_dir = out_root / domain / run_id
        output_dir.mkdir(parents=True, exist_ok=True)

        ctx = RunContext(
            run_id=run_id,
            root=self.root,
            domain=domain,
            domain_dir=domain_dir,
            output_dir=output_dir,
        )

        # attach meta so it gets saved
        ctx.meta = {
            "run_id": run_id,
            "domain": domain,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cwd": str(os.getcwd()),
            "timings": {},
        }
        ctx.set("meta", ctx.meta)

        # Choose pipeline by domain (later you can load from pipeline.yaml)
        if domain == "order":
            steps = self.build_order_state_machine_pipeline(domain_dir)
        else:
            raise NotImplementedError(f"No pipeline registered for domain='{domain}' yet")

        for step in steps:
            step.run(ctx, llm=llm, storage=self.storage)

        ctx.meta["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        ctx.set("meta", ctx.meta)
        self.storage.write_json(output_dir / "run_meta.json", ctx.meta)

        return ctx


def strip_fenced_block(text: str) -> str:
    normalized = text.lstrip("\ufeff").strip()
    if not normalized.startswith("```"):
        return normalized

    lines = normalized.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return normalized
