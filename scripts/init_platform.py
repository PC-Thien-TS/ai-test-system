"""Initialize the Universal Testing Platform from existing domains.

This script provides backward compatibility by importing existing domain-based
testing configurations into the new project-based platform registry.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.project_service import ProjectService


def main() -> int:
    """Initialize the platform from existing domains."""
    print("Initializing Universal Testing Platform v2.0+...")
    
    service = ProjectService(REPO_ROOT)
    
    # Import existing domains as projects
    print("\nImporting existing domains...")
    imported = service.import_existing_domains()
    
    if imported:
        print(f"Imported {len(imported)} projects:")
        for project in imported:
            print(f"  - {project.name} ({project.project_id})")
    else:
        print("No existing domains found to import.")
    
    # Import existing output directories as runs
    print("\nImporting existing runs...")
    outputs_dir = REPO_ROOT / "outputs"
    if outputs_dir.exists():
        run_count = 0
        for domain_dir in outputs_dir.iterdir():
            if domain_dir.is_dir():
                project = service.project_registry.get_project_by_name(domain_dir.name)
                if project:
                    for run_dir in domain_dir.iterdir():
                        if run_dir.is_dir():
                            run = service.run_registry.import_from_output_dir(run_dir, project.project_id)
                            if run:
                                run_count += 1
        print(f"Imported {run_count} runs.")
    
    # Show platform summary
    print("\nPlatform summary:")
    summary = service.get_platform_summary()
    print(f"  Total projects: {summary.total_projects}")
    print(f"  Active projects: {summary.active_projects}")
    print(f"  Total runs: {summary.total_runs}")
    
    print("\nPlatform initialization complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
