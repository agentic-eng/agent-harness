from pathlib import Path
from agent_harness.detect import detect_stacks
from agent_harness.init.templates import HARNESS_YML, YAMLLINT_YML, PRECOMMIT_YML

def scaffold_project(project_dir: Path) -> list[str]:
    """Write harness config files. Returns list of actions taken."""
    actions = []
    stacks = detect_stacks(project_dir)
    stacks_str = ", ".join(sorted(stacks)) if stacks else "none detected"
    stacks_list = ", ".join(sorted(stacks))

    files = {
        ".harness.yml": HARNESS_YML.format(stacks=stacks_str, stacks_list=stacks_list),
        ".yamllint.yml": YAMLLINT_YML,
        ".pre-commit-config.yaml": PRECOMMIT_YML,
    }

    for filename, content in files.items():
        path = project_dir / filename
        if path.exists():
            actions.append(f"SKIP  {filename} (already exists)")
        else:
            path.write_text(content)
            actions.append(f"CREATE  {filename}")

    return actions
