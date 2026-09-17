"""Release-specific checks for v0.12.0."""

import json
from pathlib import Path

_ROOT = Path(__file__).parents[1]


def test_release_version_is_consistent() -> None:
    manifest = json.loads(
        (_ROOT / "custom_components" / "nibe_local" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    readme = (_ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert manifest["version"] == "0.12.0"
    assert "Aktuelle Integrationsversion: **0.12.0**" in readme
    assert "## 0.12.0" in changelog
