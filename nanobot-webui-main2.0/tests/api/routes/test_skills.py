from __future__ import annotations

from pathlib import Path

from nanobot.agent.skills import SkillsLoader
from webui.api.routes import skills


def test_skill_available_uses_standard_frontmatter_requirements(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    skill_dir = workspace / "skills" / "linux-hardware-check"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(
        "\n".join(
            [
                "---",
                "name: linux-hardware-check",
                "description: Natural-language hardware troubleshooting guidance.",
                "---",
                "",
                "# Linux Hardware Check",
                "",
                "This skill is pure natural language and does not require any CLI binary.",
            ]
        ),
        encoding="utf-8",
    )

    loader = SkillsLoader(workspace)

    available, reason = skills._skill_available(loader, "linux-hardware-check", str(skill_path))

    assert available is True
    assert reason is None
